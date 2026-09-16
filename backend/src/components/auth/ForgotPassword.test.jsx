import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ForgotPassword from './ForgotPassword';
import authService from '../../api/authService';

vi.mock('../../api/authService', () => ({
  default: {
    sendForgotPasswordOtp: vi.fn(),
    resetPasswordWithOtp: vi.fn(),
  },
  authService: {
    sendForgotPasswordOtp: vi.fn(),
    resetPasswordWithOtp: vi.fn(),
  },
}));

const renderForgotPassword = () => {
  return render(
    <BrowserRouter>
      <ForgotPassword />
    </BrowserRouter>
  );
};

describe('ForgotPassword Component - Email OTP Password Reset', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders email input and submit button in initial EMAIL step', () => {
    renderForgotPassword();

    expect(screen.getByRole('heading', { name: /Reset Your Password/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Registered Email Address/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Send Reset Code/i })).toBeInTheDocument();
  });

  it('submits email and progresses to OTP and new password step', async () => {
    authService.sendForgotPasswordOtp.mockResolvedValue({
      message: 'If an account exists, a reset code has been sent.',
    });

    renderForgotPassword();

    fireEvent.change(screen.getByLabelText(/Registered Email Address/i), {
      target: { value: 'user@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Send Reset Code/i }));

    await waitFor(() => {
      expect(authService.sendForgotPasswordOtp).toHaveBeenCalledWith({
        email: 'user@example.com',
      });
      expect(screen.getByRole('heading', { name: /Set New Password/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/Enter 6-Digit Reset Code/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^New Password$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^Confirm New Password$/i)).toBeInTheDocument();
    });
  });

  it('submits valid OTP and new password, completing reset flow', async () => {
    authService.sendForgotPasswordOtp.mockResolvedValue({});
    authService.resetPasswordWithOtp.mockResolvedValue({
      message: 'Password has been reset successfully.',
    });

    renderForgotPassword();

    // Step 1: Send OTP
    fireEvent.change(screen.getByLabelText(/Registered Email Address/i), {
      target: { value: 'user@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Send Reset Code/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Enter 6-Digit Reset Code/i)).toBeInTheDocument();
    });

    // Step 2: Reset password
    fireEvent.change(screen.getByLabelText(/Enter 6-Digit Reset Code/i), {
      target: { value: '123456' },
    });
    fireEvent.change(screen.getByLabelText(/^New Password$/i), {
      target: { value: 'BrandNewPass123!' },
    });
    fireEvent.change(screen.getByLabelText(/^Confirm New Password$/i), {
      target: { value: 'BrandNewPass123!' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Reset Password/i }));

    await waitFor(() => {
      expect(authService.resetPasswordWithOtp).toHaveBeenCalledWith({
        email: 'user@example.com',
        otp_code: '123456',
        new_password: 'BrandNewPass123!',
        new_password_confirmation: 'BrandNewPass123!',
      });
      expect(screen.getByRole('status')).toHaveTextContent(/Password reset successfully/i);
    });
  });
});
