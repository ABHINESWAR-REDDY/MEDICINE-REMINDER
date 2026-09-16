import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  User,
  Mail,
  Shield,
  Key,
  AlertCircle,
  CheckCircle,
  Loader2,
  Eye,
  EyeOff,
  Check,
  X,
  ShieldCheck,
} from 'lucide-react';

export const Profile = () => {
  const { user, updateProfile, changePassword } = useAuth();

  const [name, setName] = useState(user?.name || '');
  const [profileMsg, setProfileMsg] = useState({ type: '', text: '' });
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [passwordMsg, setPasswordMsg] = useState({ type: '', text: '' });
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  // Sync state when user profile is loaded or updated
  useEffect(() => {
    if (user?.name) {
      setName(user.name);
    }
  }, [user]);

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
  const hasTypedConfirmPassword = confirmPassword.length > 0;
  const isPasswordMatching = newPassword.length > 0 && confirmPassword.length > 0 && newPassword === confirmPassword;
  const isPasswordFormValid = currentPassword.trim().length > 0 && isAllPasswordCriteriaMet && isPasswordMatching;

  const handleUpdateName = async (e) => {
    e.preventDefault();
    setProfileMsg({ type: '', text: '' });

    if (!name.trim()) {
      setProfileMsg({ type: 'error', text: 'Name cannot be empty.' });
      return;
    }

    setIsUpdatingProfile(true);
    try {
      await updateProfile({ name: name.trim() });
      setProfileMsg({ type: 'success', text: 'Profile name updated successfully!' });
    } catch (err) {
      setProfileMsg({ type: 'error', text: err.message || 'Failed to update profile name.' });
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordMsg({ type: '', text: '' });

    if (!currentPassword) {
      setPasswordMsg({ type: 'error', text: 'Please enter your current password.' });
      return;
    }

    if (!isAllPasswordCriteriaMet) {
      setPasswordMsg({ type: 'error', text: 'Please satisfy all password security requirements.' });
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordMsg({ type: 'error', text: 'New passwords do not match.' });
      return;
    }

    setIsChangingPassword(true);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirmation: confirmPassword,
      });
      setPasswordMsg({ type: 'success', text: 'Password changed successfully!' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPasswordMsg({ type: 'error', text: err.message || 'Failed to change password.' });
    } finally {
      setIsChangingPassword(false);
    }
  };

  const getRoleBadgeStyle = (role) => {
    switch (role) {
      case 'ADMIN':
        return 'bg-purple-500/10 text-purple-300 border-purple-500/30';
      case 'CAREGIVER':
        return 'bg-blue-500/10 text-blue-300 border-blue-500/30';
      default:
        return 'bg-teal-500/10 text-teal-300 border-teal-500/30';
    }
  };

  return (
    <div className="space-y-8 w-full">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">User Profile</h2>
        <p className="text-sm text-slate-400 mt-1">
          Manage your account information and authentication credentials
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Profile Details Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Account Information</h3>
              <p className="text-xs text-slate-400">Authenticated user details</p>
            </div>
          </div>

          {profileMsg.text && (
            <div
              role="alert"
              className={`p-3 rounded-xl text-xs flex items-center gap-2 border ${
                profileMsg.type === 'success'
                  ? 'bg-teal-500/10 border-teal-500/20 text-teal-300'
                  : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
              }`}
            >
              {profileMsg.type === 'success' ? (
                <CheckCircle className="w-4 h-4 text-teal-400 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span>{profileMsg.text}</span>
            </div>
          )}

          <form onSubmit={handleUpdateName} className="space-y-4">
            <div>
              <label htmlFor="profileName" className="block text-xs font-medium text-slate-300 mb-1.5">
                Full Name
              </label>
              <input
                id="profileName"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="flex items-center gap-2 px-3 py-2 bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-400 text-xs cursor-not-allowed">
                <Mail className="w-3.5 h-3.5 text-slate-500" />
                <span>{user?.email || '—'}</span>
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Email is permanently bound to account</span>
            </div>

            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/80">
              <div>
                <span className="block text-[11px] font-medium text-slate-400">Role</span>
                <span
                  className={`inline-flex items-center gap-1 mt-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getRoleBadgeStyle(
                    user?.role
                  )}`}
                >
                  <Shield className="w-3 h-3" />
                  {user?.role || 'PATIENT'}
                </span>
              </div>

              <div>
                <span className="block text-[11px] font-medium text-slate-400">Account ID</span>
                <span className="inline-flex items-center gap-1 mt-1 font-mono text-xs font-bold text-teal-300 px-2 py-0.5 bg-slate-950 border border-slate-800 rounded-md">
                  {user?.employee_id || `PT${String(user?.id).padStart(6, '0')}`}
                </span>
              </div>

              <div>
                <span className="block text-[11px] font-medium text-slate-400">Status</span>
                <span className="inline-flex items-center gap-1.5 mt-1 text-xs text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  Active
                </span>
              </div>
            </div>

            {user?.role === 'PATIENT' && (
              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
                <span className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Assigned Caregiver Supervisor
                </span>
                {user?.assigned_caregiver_name ? (
                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-blue-500/10 text-blue-400 font-bold text-xs flex items-center justify-center border border-blue-500/20">
                        {user.assigned_caregiver_name.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-xs font-semibold text-white">{user.assigned_caregiver_name}</span>
                    </div>
                    <span className="font-mono text-[10px] text-blue-400 font-semibold bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                      {user.assigned_caregiver_employee_id || 'CG Assigned'}
                    </span>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic pt-0.5">No caregiver assigned yet</p>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={isUpdatingProfile || name === user?.name}
              className="w-full flex justify-center items-center gap-2 py-2 px-4 border border-transparent rounded-xl text-xs font-semibold text-slate-950 bg-teal-400 hover:bg-teal-300 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {isUpdatingProfile ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <span>Save Name</span>
              )}
            </button>
          </form>
        </div>

        {/* Change Password Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Security & Password</h3>
              <p className="text-xs text-slate-400">Update your account password</p>
            </div>
          </div>

          {passwordMsg.text && (
            <div
              role="alert"
              className={`p-3 rounded-xl text-xs flex items-center gap-2 border ${
                passwordMsg.type === 'success'
                  ? 'bg-teal-500/10 border-teal-500/20 text-teal-300'
                  : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
              }`}
            >
              {passwordMsg.type === 'success' ? (
                <CheckCircle className="w-4 h-4 text-teal-400 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span>{passwordMsg.text}</span>
            </div>
          )}

          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <label htmlFor="currentPass" className="block text-xs font-medium text-slate-300 mb-1.5">
                Current Password
              </label>
              <div className="relative rounded-xl shadow-sm">
                <input
                  id="currentPass"
                  type={showCurrentPassword ? 'text' : 'password'}
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full pl-3 pr-10 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  tabIndex={0}
                  onClick={() => setShowCurrentPassword((prev) => !prev)}
                  aria-label={showCurrentPassword ? 'Hide current password' : 'Show current password'}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 focus:outline-none transition-colors"
                >
                  {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <label htmlFor="newPass" className="block text-xs font-medium text-slate-300 mb-1.5">
                New Password
              </label>
              <div className="relative rounded-xl shadow-sm">
                <input
                  id="newPass"
                  type={showNewPassword ? 'text' : 'password'}
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full pl-3 pr-10 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  tabIndex={0}
                  onClick={() => setShowNewPassword((prev) => !prev)}
                  aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 focus:outline-none transition-colors"
                >
                  {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {/* Dynamic Password Requirements Checklist */}
              <div className="mt-2.5 p-2.5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-400">Password requirements:</span>
                  {isAllPasswordCriteriaMet && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      Strong password
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
              <label htmlFor="confirmPass" className="block text-xs font-medium text-slate-300 mb-1.5">
                Confirm New Password
              </label>
              <div className="relative rounded-xl shadow-sm">
                <input
                  id="confirmPass"
                  type={showConfirmPassword ? 'text' : 'password'}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={`w-full pl-3 pr-10 py-2 bg-slate-950/60 border rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 transition-colors ${
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
              disabled={isChangingPassword || !isPasswordFormValid}
              className="w-full flex justify-center items-center gap-2 py-2 px-4 border border-transparent rounded-xl text-xs font-semibold text-slate-950 bg-teal-400 hover:bg-teal-300 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {isChangingPassword ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Updating password...</span>
                </>
              ) : (
                <span>Update Password</span>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Profile;
