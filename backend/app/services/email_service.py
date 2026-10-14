"""Email service supporting Brevo HTTP API (production transactional emails) and local SMTP fallback."""

import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, formataddr
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.core.logging import logger


class EmailService:
    """
    Service handling transactional email delivery.
    - Production: Dispatches via Brevo HTTPS REST API (POST https://api.brevo.com/v3/smtp/email).
    - Local Development: Dispatches via Brevo HTTP API or falls back to local SMTP (STARTTLS).
    """

    def __init__(self):
        # Brevo HTTP API Configuration
        self.brevo_api_key = settings.BREVO_API_KEY
        self.brevo_api_url = settings.BREVO_API_URL
        self.brevo_timeout = settings.BREVO_TIMEOUT_SECONDS

        # Sender configuration
        self.from_email = (
            settings.BREVO_FROM_EMAIL
            or settings.SMTP_FROM_EMAIL
            or settings.SMTP_USER
            or "noreply@pillsync.app"
        )
        self.from_name = (
            settings.BREVO_FROM_NAME
            or settings.SMTP_FROM_NAME
            or "PillSync"
        )

        # Local SMTP Configuration (fallback for local development only)
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = (
            settings.SMTP_PASSWORD.replace(" ", "").strip()
            if settings.SMTP_PASSWORD
            else None
        )
        self.use_tls = settings.SMTP_TLS
        self.environment = (settings.ENVIRONMENT or "development").strip().lower()

    def is_brevo_configured(self) -> bool:
        """Check if Brevo API credentials and sender details are configured."""
        return bool(
            self.brevo_api_key
            and self.brevo_api_key.strip()
            and self.from_email
            and self.from_email.strip()
        )

    def is_smtp_configured(self) -> bool:
        """Check if local SMTP credentials are configured."""
        return bool(self.user and self.password)

    def is_configured(self) -> bool:
        """
        Check if email delivery is configured and ready:
        - In production: Strictly requires BREVO_API_KEY and sender email (no SMTP credentials required).
        - In non-production: Brevo API or local development SMTP credentials.
        """
        if self.environment in ("production", "prod"):
            return self.is_brevo_configured()
        return self.is_brevo_configured() or self.is_smtp_configured()

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        to_name: Optional[str] = None
    ) -> bool:
        """
        Send a transactional email using Brevo HTTP API (production) or local SMTP fallback.
        Never logs API keys, passwords, or OTP secrets.
        Never reports success if Brevo rejects the request.
        """
        # 1. Primary path: Brevo HTTP API
        if self.is_brevo_configured():
            return self._send_via_brevo_api(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                to_name=to_name
            )

        # 2. Production safety guard: In production, Brevo API key is strictly required
        if self.environment in ("production", "prod"):
            logger.error(
                "Email delivery failed: BREVO_API_KEY is not configured in production environment. "
                "Transactional email to [%s] was aborted.",
                to_email
            )
            return False

        # 3. Local development fallback: SMTP if configured
        if self.is_smtp_configured():
            logger.info("BREVO_API_KEY not configured. Falling back to local SMTP for [%s].", to_email)
            return self._send_via_smtp(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )

        # 4. Local development unconfigured fallback: Simulate delivery without leaking secrets/OTPs
        logger.warning(
            "Neither Brevo API nor SMTP credentials configured in %s mode. "
            "Simulating delivery for [%s] (no secrets/OTPs logged).",
            self.environment,
            to_email
        )
        return True

    def _send_via_brevo_api(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        to_name: Optional[str] = None
    ) -> bool:
        """Dispatch email via Brevo HTTPS API: POST https://api.brevo.com/v3/smtp/email."""
        headers = {
            "accept": "application/json",
            "api-key": self.brevo_api_key.strip(),
            "content-type": "application/json",
        }

        recipient: Dict[str, Any] = {"email": to_email}
        if to_name and str(to_name).strip():
            recipient["name"] = str(to_name).strip()

        payload = {
            "sender": {
                "name": self.from_name,
                "email": self.from_email,
            },
            "to": [recipient],
            "subject": subject,
            "htmlContent": html_body,
            "textContent": text_body,
        }

        try:
            with httpx.Client(timeout=self.brevo_timeout) as client:
                response = client.post(self.brevo_api_url, json=payload, headers=headers)

            if 200 <= response.status_code < 300:
                logger.info("Successfully sent transactional email to [%s] via Brevo API.", to_email)
                return True

            # Handle Brevo HTTP error responses without exposing secrets
            err_detail = "Unknown error"
            try:
                err_data = response.json()
                err_detail = err_data.get("message") or err_data.get("code") or str(err_data)[:120]
            except Exception:
                err_detail = response.text[:120] if response.text else "No response body"

            logger.error(
                "Brevo API rejected email to [%s] with HTTP %s: %s",
                to_email,
                response.status_code,
                err_detail
            )
            return False

        except httpx.TimeoutException:
            logger.error(
                "Brevo API request timed out sending email to [%s] after %s seconds.",
                to_email,
                self.brevo_timeout
            )
            return False
        except httpx.RequestError as exc:
            logger.error(
                "Network error connecting to Brevo API for [%s]: %s",
                to_email,
                type(exc).__name__
            )
            return False
        except Exception as exc:
            logger.error(
                "Unexpected error during Brevo API email delivery for [%s]: %s",
                to_email,
                type(exc).__name__
            )
            return False

    def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """Send multipart MIME email via local SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((self.from_name, self.from_email))
        msg["To"] = to_email
        msg["Date"] = formatdate(localtime=True)
        domain = self.from_email.split("@")[-1] if "@" in self.from_email else "pillsync.app"
        msg["Message-ID"] = f"<{uuid.uuid4()}@{domain}>"

        msg["X-Priority"] = "1"
        msg["X-MSMail-Priority"] = "High"
        msg["Importance"] = "High"
        msg["Auto-Submitted"] = "auto-generated"

        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())
                logger.info("Successfully sent email to [%s] via local SMTP.", to_email)
                return True
        except Exception as exc:
            logger.error(
                "Failed to send email to [%s] via local SMTP: %s",
                to_email,
                type(exc).__name__
            )
            return False

    def send_registration_otp(
        self,
        to_email: str,
        name: str,
        otp_code: str,
        expire_minutes: int = 10
    ) -> bool:
        """Send 6-digit email verification code for new user registration."""
        subject = f"{otp_code} is your PillSync verification code"

        text_body = (
            f"Hello {name},\n\n"
            f"Your PillSync account verification code is: {otp_code}\n\n"
            f"This code will expire in {expire_minutes} minutes.\n"
            f"Please enter this code on the registration page to verify your email.\n\n"
            f"If you did not request this verification, please ignore this email.\n\n"
            f"— The PillSync Security Team"
        )

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #020617; color: #f8fafc; margin: 0; padding: 24px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; }}
            .brand {{ color: #14b8a6; font-size: 20px; font-weight: bold; margin-bottom: 24px; }}
            .title {{ font-size: 18px; font-weight: 600; color: #ffffff; margin-bottom: 12px; }}
            .desc {{ font-size: 13px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
            .otp-box {{ background: #020617; border: 1px solid #334155; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 24px; }}
            .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #2dd4bf; font-family: monospace; }}
            .footer {{ font-size: 11px; color: #64748b; border-top: 1px solid #1e293b; padding-top: 16px; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">💊 PillSync</div>
            <div class="title">Verify your email address</div>
            <div class="desc">Hello <strong>{name}</strong>,<br>Use the 6-digit verification code below to complete your PillSync registration:</div>
            <div class="otp-box">
              <div class="otp-code">{otp_code}</div>
            </div>
            <div class="desc" style="font-size: 12px; color: #94a3b8;">This code is valid for <strong>{expire_minutes} minutes</strong>. For your security, never share this code with anyone.</div>
            <div class="footer">If you did not attempt to register an account with PillSync, you can safely disregard this email.</div>
          </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html_body, text_body, to_name=name)

    def send_password_reset_otp(
        self,
        to_email: str,
        name: str,
        otp_code: str,
        expire_minutes: int = 10
    ) -> bool:
        """Send 6-digit password reset verification code."""
        subject = f"{otp_code} is your PillSync password reset code"

        text_body = (
            f"Hello {name},\n\n"
            f"Your PillSync password reset code is: {otp_code}\n\n"
            f"This code will expire in {expire_minutes} minutes.\n"
            f"If you did not request a password reset, please review your account security immediately.\n\n"
            f"— The PillSync Security Team"
        )

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #020617; color: #f8fafc; margin: 0; padding: 24px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; }}
            .brand {{ color: #14b8a6; font-size: 20px; font-weight: bold; margin-bottom: 24px; }}
            .title {{ font-size: 18px; font-weight: 600; color: #ffffff; margin-bottom: 12px; }}
            .desc {{ font-size: 13px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
            .otp-box {{ background: #020617; border: 1px solid #334155; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 24px; }}
            .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #38bdf8; font-family: monospace; }}
            .footer {{ font-size: 11px; color: #64748b; border-top: 1px solid #1e293b; padding-top: 16px; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">💊 PillSync</div>
            <div class="title">Reset your account password</div>
            <div class="desc">Hello <strong>{name}</strong>,<br>We received a password reset request for your account. Enter this code to set a new password:</div>
            <div class="otp-box">
              <div class="otp-code">{otp_code}</div>
            </div>
            <div class="desc" style="font-size: 12px; color: #94a3b8;">This code is valid for <strong>{expire_minutes} minutes</strong>. If you did not request this, please review your account security.</div>
            <div class="footer">PillSync Security • Automated Notification</div>
          </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html_body, text_body, to_name=name)

    def send_caregiver_approval_email(
        self,
        to_email: str,
        name: str
    ) -> bool:
        """Send notification email when admin approves a caregiver account."""
        subject = "PillSync Caregiver Account Approved"

        text_body = (
            f"Hello {name},\n\n"
            f"Your PillSync caregiver account has been approved by the administrator.\n\n"
            f"You can now log in to your PillSync account and access the caregiver portal.\n\n"
            f"Account:\n{to_email}\n\n"
            f"Status:\nAPPROVED\n\n"
            f"Thank you,\n"
            f"PillSync Administration"
        )

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #020617; color: #f8fafc; margin: 0; padding: 24px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; }}
            .brand {{ color: #14b8a6; font-size: 20px; font-weight: bold; margin-bottom: 24px; }}
            .title {{ font-size: 18px; font-weight: 600; color: #ffffff; margin-bottom: 12px; }}
            .desc {{ font-size: 13px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
            .status-box {{ background: #020617; border: 1px solid #10b981; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 24px; }}
            .status-text {{ font-size: 20px; font-weight: 800; letter-spacing: 2px; color: #34d399; font-family: monospace; }}
            .account-info {{ font-size: 13px; color: #e2e8f0; background: #1e293b; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; }}
            .footer {{ font-size: 11px; color: #64748b; border-top: 1px solid #1e293b; padding-top: 16px; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">💊 PillSync</div>
            <div class="title">Caregiver Account Approved</div>
            <div class="desc">Hello <strong>{name}</strong>,<br><br>Your PillSync caregiver account has been approved by the administrator.<br>You can now log in and access your caregiver supervision portal.</div>
            <div class="status-box">
              <div class="status-text">STATUS: APPROVED</div>
            </div>
            <div class="account-info">
              <div><strong>Registered Account:</strong> {to_email}</div>
            </div>
            <div class="desc">Thank you,<br><strong>PillSync Administration</strong></div>
            <div class="footer">PillSync Healthcare Governance • Automated Notification</div>
          </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html_body, text_body, to_name=name)

    def send_caregiver_rejection_email(
        self,
        to_email: str,
        name: str,
        reason: Optional[str] = None
    ) -> bool:
        """Send notification email when admin rejects a caregiver registration."""
        subject = "PillSync Caregiver Account Rejected"

        reason_text = f"\nReason:\n{reason}\n" if reason else ""
        text_body = (
            f"Hello {name},\n\n"
            f"Your PillSync caregiver account registration has been rejected by the administrator.\n\n"
            f"Account:\n{to_email}\n\n"
            f"Status:\nREJECTED\n"
            f"{reason_text}\n"
            f"Thank you,\n"
            f"PillSync Administration"
        )

        reason_html = f'<div style="font-size: 12px; color: #f87171; margin-top: 8px;"><strong>Reason:</strong> {reason}</div>' if reason else ''
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #020617; color: #f8fafc; margin: 0; padding: 24px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; }}
            .brand {{ color: #14b8a6; font-size: 20px; font-weight: bold; margin-bottom: 24px; }}
            .title {{ font-size: 18px; font-weight: 600; color: #ffffff; margin-bottom: 12px; }}
            .desc {{ font-size: 13px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
            .status-box {{ background: #020617; border: 1px solid #ef4444; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 24px; }}
            .status-text {{ font-size: 20px; font-weight: 800; letter-spacing: 2px; color: #f87171; font-family: monospace; }}
            .account-info {{ font-size: 13px; color: #e2e8f0; background: #1e293b; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; }}
            .footer {{ font-size: 11px; color: #64748b; border-top: 1px solid #1e293b; padding-top: 16px; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">💊 PillSync</div>
            <div class="title">Caregiver Account Registration Update</div>
            <div class="desc">Hello <strong>{name}</strong>,<br><br>Your PillSync caregiver account registration has been reviewed and was rejected by the administrator.</div>
            <div class="status-box">
              <div class="status-text">STATUS: REJECTED</div>
            </div>
            <div class="account-info">
              <div><strong>Registered Account:</strong> {to_email}</div>
              {reason_html}
            </div>
            <div class="desc">Thank you,<br><strong>PillSync Administration</strong></div>
            <div class="footer">PillSync Healthcare Governance • Automated Notification</div>
          </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html_body, text_body, to_name=name)


email_service = EmailService()

