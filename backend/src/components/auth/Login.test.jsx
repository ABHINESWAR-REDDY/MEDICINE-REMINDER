import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from './Login';
import { AuthProvider } from '../../context/AuthContext';
import authService from '../../api/authService';

vi.mock('../../api/authService', () => ({
  default: {
    login: vi.fn(),
    getMe: vi.fn(),
  },
  authService: {
    login: vi.fn(),
    getMe: vi.fn(),
  },
}));

const renderLogin = () => {
  return render(
    <AuthProvider>
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    </AuthProvider>
  );
};

describe('Login Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders login form inputs, brand heading, and password show/hide button', () => {
    renderLogin();

    expect(screen.getByRole('heading', { name: /Sign in to your account/i })).toBeInTheDocument();
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign in/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument();
  });

  it('toggles password visibility when eye icon is clicked', () => {
    renderLogin();

    const passwordInput = screen.getByLabelText('Password');
    const toggleBtn = screen.getByRole('button', { name: 'Show password' });

    expect(passwordInput).toHaveAttribute('type', 'password');

    fireEvent.click(toggleBtn);
    expect(passwordInput).toHaveAttribute('type', 'text');

    const hideBtn = screen.getByRole('button', { name: 'Hide password' });
    fireEvent.click(hideBtn);
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('submits credentials and handles success', async () => {
    authService.login.mockResolvedValue({
      access_token: 'fake_jwt_token',
      user: {
        id: 1,
        name: 'Jane Doe',
        email: 'jane@example.com',
        role: 'PATIENT',
        is_active: true,
      },
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText('Email Address'), {
      target: { value: 'jane@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Sign in/i }));

    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith({
        email: 'jane@example.com',
        password: 'password123',
      });
    });
  });

  it('displays error message on authentication failure', async () => {
    authService.login.mockRejectedValue({
      response: {
        status: 401,
        data: { detail: 'Invalid email or password.' },
      },
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText('Email Address'), {
      target: { value: 'wrong@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrongpass' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Invalid email or password.');
    });
  });
});
