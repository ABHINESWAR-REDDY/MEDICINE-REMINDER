"""Email service supporting Google SMTP App Passwords and branded email templates."""

import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, formataddr
from typing import Optional
from app.core.config import settings
from app.core.logging import logger


class EmailService:
    """Service handling email delivery via Google SMTP (STARTTLS) and HTML templating."""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD.replace(" ", "").strip() if settings.SMTP_PASSWORD else None
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER or "noreply@pillsync.app"
        self.from_name = settings.SMTP_FROM_NAME or "PillSync"
        self.use_tls = settings.SMTP_TLS

    def is_configured(self) -> bool:
        """Check if SMTP credentials (Google App Password) are configured in the environment."""
        return bool(self.user and self.password)

    def send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """
        Send a multipart MIME email via SMTP directly to the recipient's primary inbox.
        Falls back to logger in development if SMTP credentials are not configured.
        """
        if not self.is_configured():
            logger.warning(
                "SMTP credentials not configured. Email to [%s] logged for development. Subject: %s",
                to_email,
                subject
            )
            logger.info("EMAIL CONTENT [%s]:\n%s", to_email, text_body)
            return True

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((self.from_name, self.from_email))
        msg["To"] = to_email
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = f"<{uuid.uuid4()}@{self.from_email.split('@')[-1]}>"
        
        # Primary Inbox Headers to prevent landing in Spam / Promotional tabs
        msg["X-Priority"] = "1"
        msg["X-MSMail-Priority"] = "High"
        msg["Importance"] = "High"
        msg["Auto-Submitted"] = "auto-generated"

        # Attach text and HTML parts (UTF-8 encoding)
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())
                logger.info("Successfully sent email to %s (Subject: %s)", to_email, subject)
                return True
        except Exception as exc:
            logger.error("Failed to send email to %s via SMTP: %s", to_email, str(exc))
            # In development/fallback, also log the text body so verification is never blocked
            logger.info("DEVELOPMENT FALLBACK EMAIL [%s]:\n%s", to_email, text_body)
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

        return self.send_email(to_email, subject, html_body, text_body)

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

        return self.send_email(to_email, subject, html_body, text_body)

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

        return self.send_email(to_email, subject, html_body, text_body)

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

        return self.send_email(to_email, subject, html_body, text_body)


email_service = EmailService()

