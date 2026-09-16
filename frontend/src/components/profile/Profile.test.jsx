import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider } from '../../context/AuthContext';
import Profile from './Profile';
import authService from '../../api/authService';
import profileService from '../../api/profileService';

vi.mock('../../api/authService', () => ({
  default: {
    getMe: vi.fn(),
    changePassword: vi.fn(),
  },
  authService: {
    getMe: vi.fn(),
    changePassword: vi.fn(),
  },
}));

vi.mock('../../api/profileService', () => ({
  default: {
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
  },
  profileService: {
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
  },
}));

describe('Profile Component - Password Change & Eye Toggle Indicators', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('pillsync_auth_token', 'valid_test_token');
    authService.getMe.mockResolvedValue({
      id: 5,
      name: 'Sarah Connor',
      email: 'sarah@example.com',
      role: 'PATIENT',
      is_active: true,
    });
  });

  it('renders profile details with loaded user information and 3 password eye toggles', async () => {
    render(
      <AuthProvider>
        <Profile />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Settings/i })).toBeInTheDocument();
      expect(screen.getByText('sarah@example.com')).toBeInTheDocument();
      expect(screen.getByText('PATIENT')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Show current password' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Show new password' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Show confirm password' })).toBeInTheDocument();
    });
  });

  it('shows live password match/mismatch indicator and controls update password button', async () => {
    render(
      <AuthProvider>
        <Profile />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Current Password')).toBeInTheDocument();
    });

    const updateBtn = screen.getByRole('button', { name: /Update Password/i });
    expect(updateBtn).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Current Password'), {
      target: { value: 'OldPassword123!' },
    });
    fireEvent.change(screen.getByLabelText('New Password'), {
      target: { value: 'NewPassword456!' },
    });

    // Mismatched confirm password
    fireEvent.change(screen.getByLabelText('Confirm New Password'), {
      target: { value: 'wrongpassword' },
    });
    expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
    expect(updateBtn).toBeDisabled();

    // Matched confirm password
    fireEvent.change(screen.getByLabelText('Confirm New Password'), {
      target: { value: 'NewPassword456!' },
    });
    expect(screen.getByText('Passwords match')).toBeInTheDocument();
    expect(updateBtn).toBeEnabled();
  });

  it('changes password when valid current and new passwords are supplied', async () => {
    authService.changePassword.mockResolvedValueOnce({
      message: 'Password changed successfully.',
    });

    render(
      <AuthProvider>
        <Profile />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Current Password')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Current Password'), {
      target: { value: 'OldPassword123!' },
    });
    fireEvent.change(screen.getByLabelText('New Password'), {
      target: { value: 'NewPassword456!' },
    });
    fireEvent.change(screen.getByLabelText('Confirm New Password'), {
      target: { value: 'NewPassword456!' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Update Password/i }));

    await waitFor(() => {
      expect(authService.changePassword).toHaveBeenCalledWith({
        current_password: 'OldPassword123!',
        new_password: 'NewPassword456!',
        new_password_confirmation: 'NewPassword456!',
      });
      expect(screen.getByText(/Password changed successfully!/i)).toBeInTheDocument();
    });
  });
});
