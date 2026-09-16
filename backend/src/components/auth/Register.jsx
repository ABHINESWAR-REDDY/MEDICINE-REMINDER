import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import authService from '../../api/authService';
import {
  Pill,
  Lock,
  Mail,
  User,
  AlertCircle,
  CheckCircle,
  Loader2,
  Eye,
  EyeOff,
  Check,
  X,
  ShieldCheck,
  Shield,
  Clock,
  AlertTriangle,
  KeyRound,
  ArrowLeft,
  RotateCcw,
} from 'lucide-react';
import ThemeToggle from '../common/ThemeToggle';

export const Register = () => {
  const navigate = useNavigate();
  const { sendRegisterOtp, verifyRegisterOtp } = useAuth();

  // Form State
  const [step, setStep] = useState('FORM'); // 'FORM' | 'OTP' | 'EMPLOYEE_ID'
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('Patient');
  const [password, setPassword] = useState('');
  const [passwordConfirmation, setPasswordConfirmation] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [employeeDigits, setEmployeeDigits] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Dynamic Single-Admin Availability State (Fails closed)
  const [adminAvailable, setAdminAvailable] = useState(false);

  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Calculate role prefix: PT for Patient, CG for Caregiver, AD for Admin
  const getRolePrefix = (r) => {
    const roleUpper = (r || 'Patient').toUpperCase();
    if (roleUpper === 'CAREGIVER') return 'CG';
    if (roleUpper === 'ADMIN') return 'AD';
    return 'PT';
  };

  const currentPrefix = getRolePrefix(role);
  const fullEmployeeId = `${currentPrefix}${employeeDigits}`;

  // Check admin registration status on mount
  useEffect(() => {
    let isMounted = true;
    const fetchAdminStatus = async () => {
      try {
        const res = await authService.getAdminRegistrationStatus();
        if (isMounted) {
          setAdminAvailable(Boolean(res?.adminRegistrationAvailable));
        }
      } catch {
        // Safe fail-closed fallback
        if (isMounted) {
          setAdminAvailable(false);
        }
      }
    };
    fetchAdminStatus();
    return () => {
      isMounted = false;
    };
  }, []);

  // Resend OTP Cooldown Timer
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
      met: password.length >= 8,
    },
    {
      id: 'uppercase',
      label: 'At least one uppercase letter (A-Z)',
      met: /[A-Z]/.test(password),
    },
    {
      id: 'lowercase',
      label: 'At least one lowercase letter (a-z)',
      met: /[a-z]/.test(password),
    },
    {
      id: 'number',
      label: 'At least one number (0-9)',
      met: /[0-9]/.test(password),
    },
    {
      id: 'special',
      label: 'At least one special character',
      met: /[!@#$%^&*()_+\-=\[\]{};':",.<>/?\\|`~]/.test(password),
    },
  ];

  const isAllPasswordCriteriaMet = passwordRequirements.every((req) => req.met);
  const hasTypedConfirmPassword = passwordConfirmation.length > 0;
  const isPasswordMatching = password.length > 0 && passwordConfirmation.length > 0 && password === passwordConfirmation;
  const isFormValid = name.trim().length > 0 && email.trim().length > 0 && isAllPasswordCriteriaMet && isPasswordMatching;

  // Step 1: Validate Form and Send Email OTP
  const handleInitiateOtp = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!name.trim()) {
      setErrorMsg('Please enter your full name.');
      return;
    }

    if (!email.trim()) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    if (!isAllPasswordCriteriaMet) {
      setErrorMsg('Please satisfy all password security requirements.');
      return;
    }

    if (password !== passwordConfirmation) {
      setErrorMsg('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await sendRegisterOtp({
        name: name.trim(),
        email: email.trim(),
        password,
        password_confirmation: passwordConfirmation,
        role: role.toUpperCase(),
      });

      setStep('OTP');
      setResendCooldown(60);
      setSuccessMsg(`A 6-digit verification code has been sent to ${email.trim()}.`);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to send verification code. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Resend OTP
  const handleResendOtp = async () => {
    if (resendCooldown > 0 || isSubmitting) return;
    setErrorMsg('');
    setSuccessMsg('');
    setIsSubmitting(true);

    try {
      await sendRegisterOtp({
        name: name.trim(),
        email: email.trim(),
        password,
        password_confirmation: passwordConfirmation,
        role: role.toUpperCase(),
      });
      setResendCooldown(60);
      setSuccessMsg(`A new verification code has been sent to ${email.trim()}.`);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to resend code. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Step 2: Validate OTP Code and proceed to ID creation
  const handleOtpContinue = (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const cleanedOtp = otpCode.trim();
    if (!cleanedOtp || cleanedOtp.length !== 6 || !/^\d+$/.test(cleanedOtp)) {
      setErrorMsg('Please enter the complete 6-digit verification code.');
      return;
    }

    // Proceed to Step 3: Create Member/Employee ID
    setStep('EMPLOYEE_ID');
    setSuccessMsg('Email code entered. Please choose your 6-digit ID to complete registration.');
  };

  // Step 3: Verify OTP, Validate Custom ID, and Complete Registration
  const handleFinalizeRegistration = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const cleanedOtp = otpCode.trim();
    if (!cleanedOtp || cleanedOtp.length !== 6 || !/^\d+$/.test(cleanedOtp)) {
      setErrorMsg('Verification code is missing or invalid. Please re-enter the code.');
      setStep('OTP');
      return;
    }

    const cleanedDigits = employeeDigits.trim();
    if (!cleanedDigits || cleanedDigits.length !== 6 || !/^\d{6}$/.test(cleanedDigits)) {
      setErrorMsg(`Please enter exactly 6 numeric digits for your ${role} ID.`);
      return;
    }

    const targetEmployeeId = `${currentPrefix}${cleanedDigits}`;

    setIsSubmitting(true);
    try {
      await verifyRegisterOtp({
        name: name.trim(),
        email: email.trim(),
        password,
        password_confirmation: passwordConfirmation,
        role: role.toUpperCase(),
        otp_code: cleanedOtp,
        employee_id: targetEmployeeId,
      });

      if (role === 'Caregiver') {
        setSuccessMsg(
          `Caregiver registration submitted successfully with ID ${targetEmployeeId}. Your account is pending administrator approval before you can log in.`
        );
      } else if (role === 'Admin') {
        setSuccessMsg(
          `Administrator account registered and activated with ID ${targetEmployeeId}! Redirecting to login...`
        );
      } else {
        setSuccessMsg(
          `Patient account registered successfully with ID ${targetEmployeeId}! Redirecting to login...`
        );
      }

      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 2500);
    } catch (err) {
      const msg = err.message || 'Verification failed. Please check your details and try again.';
      setErrorMsg(msg);
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
          {step === 'EMPLOYEE_ID'
            ? `Create ${role === 'Patient' ? 'Patient ID' : role === 'Caregiver' ? 'Caregiver Employee ID' : 'Administrator ID'}`
            : step === 'OTP'
            ? 'Verify Email Address'
            : 'Create an Account'}
        </h2>
        <p className="mt-1 text-center text-xs text-slate-400">
          {step === 'EMPLOYEE_ID'
            ? `Choose a unique 6-digit ID starting with "${currentPrefix}" for your account`
            : step === 'OTP'
            ? `Enter the 6-digit code sent to ${email}`
            : 'Register to manage medication schedules, care supervision, and adherence'}
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
              <span className="font-medium">{errorMsg}</span>
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

          {step === 'FORM' ? (
            /* STEP 1: Registration Information Form */
            <form className="space-y-4" onSubmit={handleInitiateOtp}>
              <div>
                <label htmlFor="name" className="block text-xs font-medium text-slate-300">
                  Full Name
                </label>
                <div className="mt-1.5 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <User className="h-4 w-4" />
                  </div>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="block w-full pl-9 pr-3 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 text-xs transition-colors"
                    placeholder="Jane Doe"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="email" className="block text-xs font-medium text-slate-300">
                  Email Address
                </label>
                <div className="mt-1.5 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full pl-9 pr-3 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 text-xs transition-colors"
                    placeholder="name@example.com"
                  />
                </div>
              </div>

              {/* Account Type Role Selection Dropdown */}
              <div>
                <label htmlFor="role" className="block text-xs font-medium text-slate-300">
                  Account Type
                </label>
                <div className="mt-1.5 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Shield className="h-4 w-4" />
                  </div>
                  <select
                    id="role"
                    name="role"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="block w-full pl-9 pr-8 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 text-xs transition-colors"
                  >
                    <option value="Patient">Patient</option>
                    <option value="Caregiver">Caregiver</option>
                    {adminAvailable && <option value="Admin">Admin</option>}
                  </select>
                </div>

                {/* Contextual Role Helper Text */}
                <div className="mt-2 text-[11px] leading-relaxed">
                  {role === 'Patient' && (
                    <p className="text-teal-400 flex items-center gap-1.5">
                      <CheckCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>Patient accounts start with ID prefix <strong>PT</strong>. Activated immediately after verification.</span>
                    </p>
                  )}
                  {role === 'Caregiver' && (
                    <p className="text-amber-400 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 shrink-0" />
                      <span>Caregiver accounts start with ID prefix <strong>CG</strong>. Requires administrator approval before login.</span>
                    </p>
                  )}
                  {role === 'Admin' && adminAvailable && (
                    <p className="text-purple-400 flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                      <span>Administrator account starts with ID prefix <strong>AD</strong>. Full governance access.</span>
                    </p>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-xs font-medium text-slate-300">
                  Password
                </label>
                <div className="mt-1.5 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
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

                {/* Dynamic Password Requirements Checklist */}
                <div className="mt-3 p-3 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-slate-400">Password requirements:</span>
                    {isAllPasswordCriteriaMet && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        Strong password
                      </span>
                    )}
                  </div>
                  <ul className="space-y-1.5" aria-label="Password requirements checklist">
                    {passwordRequirements.map((req) => (
                      <li
                        key={req.id}
                        className={`flex items-center gap-2 text-xs transition-colors ${
                          req.met ? 'text-emerald-400' : 'text-rose-400/80'
                        }`}
                      >
                        {req.met ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        ) : (
                          <X className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                        )}
                        <span className={req.met ? 'text-emerald-300' : 'text-slate-400'}>
                          {req.label}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div>
                <label htmlFor="passwordConfirmation" className="block text-xs font-medium text-slate-300">
                  Confirm Password
                </label>
                <div className="mt-1.5 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    id="passwordConfirmation"
                    name="passwordConfirmation"
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    value={passwordConfirmation}
                    onChange={(e) => setPasswordConfirmation(e.target.value)}
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
                disabled={isSubmitting || !isFormValid}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-xs font-semibold text-slate-950 bg-teal-400 hover:bg-teal-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Sending verification code...</span>
                  </>
                ) : (
                  <span>Continue with Email Verification</span>
                )}
              </button>
            </form>
          ) : step === 'OTP' ? (
            /* STEP 2: Enter Email Verification Code */
            <form className="space-y-5" onSubmit={handleOtpContinue}>
              <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl text-center space-y-1">
                <p className="text-xs text-slate-400">Verification code sent to:</p>
                <p className="text-sm font-semibold text-teal-400">{email}</p>
              </div>

              <div>
                <label htmlFor="otpCode" className="block text-xs font-medium text-slate-300 text-center">
                  Enter 6-Digit Code
                </label>
                <div className="mt-2 relative rounded-xl shadow-sm">
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
                    className="block w-full text-center tracking-[0.5em] text-lg font-mono py-3 bg-slate-950/80 border border-slate-700 rounded-xl text-teal-300 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:border-teal-500 transition-colors"
                    placeholder="••••••"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || otpCode.length !== 6}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-xs font-semibold text-slate-950 bg-teal-400 hover:bg-teal-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <span>Verify & Continue to Create ID</span>
              </button>

              <div className="flex items-center justify-between pt-2 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setStep('FORM');
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  className="inline-flex items-center gap-1.5 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Edit details</span>
                </button>

                <button
                  type="button"
                  onClick={handleResendOtp}
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
          ) : (
            /* STEP 3: Create Role-Based Employee/Member ID (PT/CG/AD + 6 digits) */
            <form className="space-y-5" onSubmit={handleFinalizeRegistration}>
              <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400">Account Type</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-teal-500/10 text-teal-300 border border-teal-500/30">
                    {role.toUpperCase()}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Your ID must begin with prefix <strong className="text-teal-300 font-mono">{currentPrefix}</strong> followed by <strong>6 digits</strong> chosen by you.
                </p>
              </div>

              <div>
                <label htmlFor="employeeDigits" className="block text-xs font-medium text-slate-300 mb-1">
                  Choose Your 6-Digit ID Number
                </label>
                <div className="relative flex rounded-xl shadow-sm overflow-hidden border border-slate-700 bg-slate-950 focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-500/30">
                  <span className="inline-flex items-center px-4 bg-slate-800 text-teal-300 font-mono font-bold text-sm border-r border-slate-700 select-none">
                    {currentPrefix}
                  </span>
                  <input
                    id="employeeDigits"
                    name="employeeDigits"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    required
                    autoFocus
                    value={employeeDigits}
                    onChange={(e) => setEmployeeDigits(e.target.value.replace(/\D/g, ''))}
                    className="block w-full py-3 px-3.5 font-mono text-base tracking-widest text-slate-100 bg-transparent placeholder-slate-600 focus:outline-none"
                    placeholder="123456"
                  />
                </div>

                {/* Live ID Preview */}
                <div className="mt-2.5 flex items-center justify-between text-xs px-1">
                  <span className="text-slate-400">Full Account ID:</span>
                  <span className="font-mono font-bold text-sm text-teal-300 tracking-wider">
                    {employeeDigits ? fullEmployeeId : `${currentPrefix}______`}
                  </span>
                </div>

                {/* Explicit Red Warning When Taken / Duplicate */}
                {errorMsg && (errorMsg.toLowerCase().includes('already taken') || errorMsg.toLowerCase().includes('already exists')) && (
                  <p className="text-rose-500 font-semibold text-xs mt-2 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
                    <span>This ID is already taken. Please choose another ID.</span>
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting || employeeDigits.length !== 6}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-xs font-semibold text-slate-950 bg-teal-400 hover:bg-teal-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating account with ID {fullEmployeeId}...</span>
                  </>
                ) : (
                  <span>Complete Registration</span>
                )}
              </button>

              <div className="flex items-center justify-between pt-1 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setStep('OTP');
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  className="inline-flex items-center gap-1.5 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to OTP</span>
                </button>
              </div>
            </form>
          )}

          <div className="mt-6 pt-6 border-t border-slate-800 text-center">
            <p className="text-xs text-slate-400">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-medium text-teal-400 hover:text-teal-300 transition-colors"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
