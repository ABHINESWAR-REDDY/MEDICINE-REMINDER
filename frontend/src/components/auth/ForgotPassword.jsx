import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import authService from '../../api/authService';
import {
  Pill,
  Lock,
  Mail,
  AlertCircle,
  CheckCircle,
  Loader2,
  Eye,
  EyeOff,
  Check,
  X,
  ShieldCheck,
  KeyRound,
  ArrowLeft,
  RotateCcw,
} from 'lucide-react';
import ThemeToggle from '../common/ThemeToggle';

export const ForgotPassword = () => {
  const navigate = useNavigate();

  const [step, setStep] = useState('EMAIL'); // 'EMAIL' | 'RESET'
  const [email, setEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirmation, setNewPasswordConfirmation] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  useEffect(() => {
    let timer;
    if (resendCooldown > 0) {
      timer = setInterval(() => {
        setResendCooldown((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Dynamic Password Requirements Checklist
  const passwordRequirements = [
    {
      id: 'length',
      label: 'Minimum 8 characters',
      met: newPassword.length >= 8,
    },
    {
      id: 'uppercase',
      label: 'At least one uppercase letter (A-Z)',
      met: /[A-Z]/.test(newPassword),
    },
    {
      id: 'lowercase',
      label: 'At least one lowercase letter (a-z)',
      met: /[a-z]/.test(newPassword),
    },
    {
      id: 'number',
      label: 'At least one number (0-9)',
      met: /[0-9]/.test(newPassword),
    },
    {
      id: 'special',
      label: 'At least one special character',
      met: /[!@#$%^&*()_+\-=\[\]{};':",.<>/?\\|`~]/.test(newPassword),
    },
  ];

  const isAllPasswordCriteriaMet = passwordRequirements.every((req) => req.met);
  const hasTypedConfirmPassword = newPasswordConfirmation.length > 0;
  const isPasswordMatching = newPassword.length > 0 && newPasswordConfirmation.length > 0 && newPassword === newPasswordConfirmation;
  const isResetFormValid = otpCode.trim().length === 6 && isAllPasswordCriteriaMet && isPasswordMatching;

  // Step 1: Send Reset OTP Code
  const handleSendResetCode = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!email.trim()) {
      setErrorMsg('Please enter your registered email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      await authService.sendForgotPasswordOtp({ email: email.trim() });
      setStep('RESET');
      setResendCooldown(60);
      setSuccessMsg(`If an account exists for ${email.trim()}, a 6-digit reset code has been sent.`);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to send reset code.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Step 2: Verify OTP and Reset Password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const cleanedOtp = otpCode.trim();
    if (!cleanedOtp || cleanedOtp.length !== 6 || !/^\d+$/.test(cleanedOtp)) {
      setErrorMsg('Please enter the 6-digit reset code sent to your email.');
      return;
    }

    if (!isAllPasswordCriteriaMet) {
      setErrorMsg('Please satisfy all password security requirements.');
      return;
    }

    if (newPassword !== newPasswordConfirmation) {
      setErrorMsg('New passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await authService.resetPasswordWithOtp({
        email: email.trim(),
        otp_code: cleanedOtp,
        new_password: newPassword,
        new_password_confirmation: newPasswordConfirmation,
      });

      setSuccessMsg('Password reset successfully! Redirecting to login...');
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 2000);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Password reset failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-slate-100 relative">
      <div className="absolute top-4 right-4 sm:top-6 sm:right-8">
        <ThemeToggle />
      </div>
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Brand Logo Header */}
        <div className="flex justify-center items-center gap-3">
          <div className="flex items-center justify-center h-12 w-12 rounded-2xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
            <Pill className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">PillSync</h1>
          </div>
        </div>
        <h2 className="mt-4 text-center text-xl font-semibold tracking-tight text-slate-200">
          {step === 'EMAIL' ? 'Reset Your Password' : 'Set New Password'}
        </h2>
        <p className="mt-1 text-center text-xs text-slate-400">
          {step === 'EMAIL'
            ? 'Enter your account email to receive a secure 6-digit reset code'
            : `Enter the 6-digit code sent to ${email} and choose a new password`}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-slate-900/80 backdrop-blur border border-slate-800 py-8 px-6 shadow-2xl rounded-2xl sm:px-10">
          {errorMsg && (
            <div
              role="alert"
              className="mb-6 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5"
            >
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div
              role="status"
              className="mb-6 p-3.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-300 text-xs flex items-start gap-2.5 leading-relaxed"
            >
              <CheckCircle className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {step === 'EMAIL' ? (
            /* STEP 1: Enter Email */
            <form className="space-y-4" onSubmit={handleSendResetCode}>
              <div>
                <label htmlFor="email" className="block text-xs font-medium text-slate-300">
                  Registered Email Address
                </label>
                <div className="mt-1.5 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    autoFocus
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full pl-9 pr-3 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 text-xs transition-colors"
                    placeholder="name@example.com"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !email.trim()}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-xs font-semibold text-slate-950 bg-teal-400 hover:bg-teal-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Sending reset code...</span>
                  </>
                ) : (
                  <span>Send Reset Code</span>
                )}
              </button>
            </form>
          ) : (
            /* STEP 2: Enter Code & New Password */
            <form className="space-y-4" onSubmit={handleResetPassword}>
              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl text-center space-y-0.5">
                <p className="text-[11px] text-slate-400">Reset code sent to:</p>
                <p className="text-xs font-semibold text-teal-400">{email}</p>
              </div>

              <div>
                <label htmlFor="otpCode" className="block text-xs font-medium text-slate-300 text-center">
                  Enter 6-Digit Reset Code
                </label>
                <div className="mt-1.5 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <KeyRound className="h-4 w-4" />
                  </div>
                  <input
                    id="otpCode"
                    name="otpCode"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    required
                    autoFocus
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    className="block w-full text-center tracking-[0.5em] text-base font-mono py-2.5 bg-slate-950/80 border border-slate-700 rounded-xl text-teal-300 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:border-teal-500 transition-colors"
                    placeholder="••••••"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="newPassword" className="block text-xs font-medium text-slate-300">
                  New Password
                </label>
                <div className="mt-1.5 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    id="newPassword"
                    name="newPassword"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="block w-full pl-9 pr-10 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 text-xs transition-colors"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    tabIndex={0}
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 focus:outline-none transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>

                {/* Password Requirements */}
                <div className="mt-2.5 p-2.5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-slate-400">Password requirements:</span>
                    {isAllPasswordCriteriaMet && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        Strong
                      </span>
                    )}
                  </div>
                  <ul className="space-y-1 text-xs" aria-label="Password requirements checklist">
                    {passwordRequirements.map((req) => (
                      <li
                        key={req.id}
                        className={`flex items-center gap-1.5 ${
                          req.met ? 'text-emerald-400' : 'text-rose-400/80'
                        }`}
                      >
                        {req.met ? (
                          <Check className="w-3 h-3 text-emerald-400 shrink-0" />
                        ) : (
                          <X className="w-3 h-3 text-rose-400 shrink-0" />
                        )}
                        <span className={req.met ? 'text-emerald-300 text-[11px]' : 'text-slate-400 text-[11px]'}>
                          {req.label}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div>
                <label htmlFor="newPasswordConfirmation" className="block text-xs font-medium text-slate-300">
                  Confirm New Password
                </label>
                <div className="mt-1.5 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    id="newPasswordConfirmation"
                    name="newPasswordConfirmation"
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    value={newPasswordConfirmation}
                    onChange={(e) => setNewPasswordConfirmation(e.target.value)}
                    className={`block w-full pl-9 pr-10 py-2.5 bg-slate-950/60 border rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 text-xs transition-colors ${
                      hasTypedConfirmPassword
                        ? isPasswordMatching
                          ? 'border-emerald-500/60 focus:border-emerald-500 focus:ring-emerald-500/30'
                          : 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30'
                        : 'border-slate-800 focus:border-teal-500 focus:ring-teal-500/30'
                    }`}
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    tabIndex={0}
                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 focus:outline-none transition-colors"
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>

                {/* Real-Time Password Match Feedback */}
                {hasTypedConfirmPassword && (
                  <div className="mt-2 text-xs flex items-center gap-1.5 font-medium transition-colors">
                    {isPasswordMatching ? (
                      <span className="text-emerald-400 flex items-center gap-1.5">
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span>Passwords match</span>
                      </span>
                    ) : (
                      <span className="text-rose-400 flex items-center gap-1.5">
                        <X className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                        <span>Passwords do not match</span>
                      </span>
                    )}
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !isResetFormValid}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-xs font-semibold text-slate-950 bg-teal-400 hover:bg-teal-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Resetting password...</span>
                  </>
                ) : (
                  <span>Reset Password</span>
                )}
              </button>

              <div className="flex items-center justify-between pt-1 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setStep('EMAIL');
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  className="inline-flex items-center gap-1.5 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Change email</span>
                </button>

                <button
                  type="button"
                  onClick={handleSendResetCode}
                  disabled={resendCooldown > 0 || isSubmitting}
                  className="inline-flex items-center gap-1.5 text-teal-400 hover:text-teal-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>
                    {resendCooldown > 0 ? `Resend code (${resendCooldown}s)` : 'Resend code'}
                  </span>
                </button>
              </div>
            </form>
          )}

          <div className="mt-6 pt-6 border-t border-slate-800 text-center">
            <p className="text-xs text-slate-400">
              Remember your password?{' '}
              <Link
                to="/login"
                className="font-medium text-teal-400 hover:text-teal-300 transition-colors"
              >
                Back to Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
