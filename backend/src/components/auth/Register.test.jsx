import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Register from './Register';
import { AuthProvider } from '../../context/AuthContext';
import authService from '../../api/authService';

vi.mock('../../api/authService', () => ({
  default: {
    sendRegisterOtp: vi.fn(),
    verifyRegisterOtp: vi.fn(),
    register: vi.fn(),
    login: vi.fn(),
    getMe: vi.fn(),
    getAdminRegistrationStatus: vi.fn(),
  },
  authService: {
    sendRegisterOtp: vi.fn(),
    verifyRegisterOtp: vi.fn(),
    register: vi.fn(),
    login: vi.fn(),
    getMe: vi.fn(),
    getAdminRegistrationStatus: vi.fn(),
  },
}));

const renderRegister = () => {
  return render(
    <AuthProvider>
      <BrowserRouter>
        <Register />
      </BrowserRouter>
    </AuthProvider>
  );
};

describe('Register Component - Dynamic Role Selection & Single-Admin Rule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders registration form fields, role dropdown, and eye toggle buttons', async () => {
    authService.getAdminRegistrationStatus.mockResolvedValue({ adminRegistrationAvailable: false });

    renderRegister();

    expect(screen.getByRole('heading', { name: /Create an Account/i })).toBeInTheDocument();
    expect(screen.getByLabelText('Full Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument();
    expect(screen.getByLabelText('Account Type')).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument();

    const roleSelect = screen.getByLabelText('Account Type');
    expect(roleSelect).toHaveValue('Patient');
    expect(
      screen.getByText(/Patient accounts start with ID prefix/i)
    ).toBeInTheDocument();

    expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Show confirm password' })).toBeInTheDocument();
  });

  it('displays Admin option in dropdown when adminRegistrationAvailable is true', async () => {
    authService.getAdminRegistrationStatus.mockResolvedValue({ adminRegistrationAvailable: true });

    renderRegister();

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Admin' })).toBeInTheDocument();
    });

    expect(screen.getByRole('option', { name: 'Patient' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Caregiver' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Admin' })).toBeInTheDocument();

    // Select Admin option and check helper text
    fireEvent.change(screen.getByLabelText('Account Type'), { target: { value: 'Admin' } });
    expect(
      screen.getByText(/Administrator account starts with ID prefix/i)
    ).toBeInTheDocument();
  });

  it('completely hides Admin option from dropdown when adminRegistrationAvailable is false', async () => {
    authService.getAdminRegistrationStatus.mockResolvedValue({ adminRegistrationAvailable: false });

    renderRegister();

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Patient' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Caregiver' })).toBeInTheDocument();
    });

    expect(screen.queryByRole('option', { name: 'Admin' })).not.toBeInTheDocument();
  });

  it('fails closed and hides Admin option if getAdminRegistrationStatus API fails', async () => {
    authService.getAdminRegistrationStatus.mockRejectedValue(new Error('Network error'));

    renderRegister();

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Patient' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Caregiver' })).toBeInTheDocument();
    });

    expect(screen.queryByRole('option', { name: 'Admin' })).not.toBeInTheDocument();
  });

  it('shows live password match and mismatch feedback and controls submit button state', async () => {
    authService.getAdminRegistrationStatus.mockResolvedValue({ adminRegistrationAvailable: false });

    renderRegister();

    const submitBtn = screen.getByRole('button', { name: /Continue with Email Verification/i });
    expect(submitBtn).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Full Name'), { target: { value: 'Jane Patient' } });
    fireEvent.change(screen.getByLabelText('Email Address'), { target: { value: 'jane@example.com' } });
    fireEvent.change(screen.getByLabelText(/^Password$/i), { target: { value: 'Bigshot@143' } });

    // Mismatched confirm password
    fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'bigshot@143' } });
    expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
    expect(submitBtn).toBeDisabled();

    // Matched confirm password
    fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'Bigshot@143' } });
    expect(screen.getByText('Passwords match')).toBeInTheDocument();
    expect(submitBtn).toBeEnabled();
  });

  it('submits Admin registration and displays administrator success message after OTP verification', async () => {
    authService.getAdminRegistrationStatus.mockResolvedValue({ adminRegistrationAvailable: true });
    authService.sendRegisterOtp.mockResolvedValue({
      message: 'Verification code sent to admin@example.com',
      email: 'admin@example.com',
    });
    authService.verifyRegisterOtp.mockResolvedValue({
      id: 1,
      name: 'System Admin',
      email: 'admin@example.com',
      role: 'ADMIN',
      approval_status: 'APPROVED',
      is_active: true,
    });

    renderRegister();

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Admin' })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Full Name'), { target: { value: 'System Admin' } });
    fireEvent.change(screen.getByLabelText('Email Address'), { target: { value: 'admin@example.com' } });
    fireEvent.change(screen.getByLabelText('Account Type'), { target: { value: 'Admin' } });
    fireEvent.change(screen.getByLabelText(/^Password$/i), { target: { value: 'AdminPass@123' } });
    fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'AdminPass@123' } });

    const submitBtn = screen.getByRole('button', { name: /Continue with Email Verification/i });
    expect(submitBtn).toBeEnabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Verify Email Address/i })).toBeInTheDocument();
    });

    const otpInput = screen.getByLabelText(/Enter 6-Digit Code/i);
    fireEvent.change(otpInput, { target: { value: '654321' } });

    const continueBtn = screen.getByRole('button', { name: /Verify & Continue to Create ID/i });
    fireEvent.click(continueBtn);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Create Administrator ID/i })).toBeInTheDocument();
    });

    const idInput = screen.getByPlaceholderText('123456');
    fireEvent.change(idInput, { target: { value: '999888' } });

    const completeBtn = screen.getByRole('button', { name: /Complete Registration/i });
    fireEvent.click(completeBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/Administrator account registered and activated with ID AD999888/i)
      ).toBeInTheDocument();
    });
  });
});
