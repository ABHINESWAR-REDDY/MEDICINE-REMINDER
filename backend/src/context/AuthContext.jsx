import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import authService from '../api/authService';
import profileService from '../api/profileService';
import { TOKEN_STORAGE_KEY } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => {
    try {
      return localStorage.getItem(TOKEN_STORAGE_KEY) || null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Clear authentication and remove client token
  const logout = useCallback(() => {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      // Ignore
    }
    setToken(null);
    setUser(null);
    setError(null);
  }, []);

  // Validate session against backend on boot
  useEffect(() => {
    let isMounted = true;

    const initializeAuth = async () => {
      const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (!storedToken) {
        if (isMounted) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const userData = await authService.getMe();
        if (isMounted) {
          setUser(userData);
          setToken(storedToken);
        }
      } catch (err) {
        if (isMounted) {
          logout();
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    initializeAuth();

    return () => {
      isMounted = false;
    };
  }, [logout]);

  // Helper to extract clean error message from backend response
  const formatErrorMessage = (err, fallback) => {
    if (err.response) {
      const status = err.response.status;
      const detail = err.response.data?.detail;

      if (detail && typeof detail === 'object' && detail.message) {
        return detail.message;
      }
      if (status === 409) {
        return typeof detail === 'string' ? detail : 'This email or account is already registered.';
      }
      if (status === 403) {
        return typeof detail === 'string'
          ? detail
          : 'You do not have permission to perform this action.';
      }
      if (status === 422) {
        if (typeof detail === 'string') {
          return detail;
        }
        if (Array.isArray(detail) && detail.length > 0) {
          return detail.map((d) => d.msg.replace('Value error, ', '')).join('. ');
        }
        return 'Please review the highlighted fields and try again.';
      }
      if (status >= 500) {
        return 'Something went wrong on the server. Please try again later.';
      }
      if (typeof detail === 'string') {
        return detail;
      }
    }
    return err.message || fallback;
  };

  // Login handler
  const login = async (email, password) => {
    setError(null);
    try {
      const response = await authService.login({ email, password });
      const { access_token, user: userData } = response;
      localStorage.setItem(TOKEN_STORAGE_KEY, access_token);
      setToken(access_token);
      setUser(userData);
      return userData;
    } catch (err) {
      const message = formatErrorMessage(
        err,
        'Invalid email or password. Please check your credentials.'
      );
      setError(message);
      throw new Error(message);
    }
  };

  // Direct Register handler
  const register = async (registerData) => {
    setError(null);
    try {
      const registeredUser = await authService.register(registerData);
      return registeredUser;
    } catch (err) {
      const message = formatErrorMessage(
        err,
        'Registration failed. Please review your information.'
      );
      setError(message);
      throw new Error(message);
    }
  };

  // Send registration OTP code to email
  const sendRegisterOtp = async (registerData) => {
    setError(null);
    try {
      const res = await authService.sendRegisterOtp(registerData);
      return res;
    } catch (err) {
      const message = formatErrorMessage(
        err,
        'Failed to send verification code. Please check your information.'
      );
      setError(message);
      throw new Error(message);
    }
  };

  // Verify registration OTP and create account
  const verifyRegisterOtp = async (verifyData) => {
    setError(null);
    try {
      const registeredUser = await authService.verifyRegisterOtp(verifyData);
      return registeredUser;
    } catch (err) {
      const message = formatErrorMessage(
        err,
        'Verification failed. Please check the code and try again.'
      );
      setError(message);
      throw new Error(message);
    }
  };

  // Update profile handler
  const updateProfile = async (profileData) => {
    try {
      const updatedUser = await profileService.updateProfile(profileData);
      setUser(updatedUser);
      return updatedUser;
    } catch (err) {
      const message = formatErrorMessage(err, 'Failed to update profile.');
      throw new Error(message);
    }
  };

  // Change password handler
  const changePassword = async (passwordData) => {
    try {
      const result = await authService.changePassword(passwordData);
      return result;
    } catch (err) {
      const message = formatErrorMessage(err, 'Failed to change password.');
      throw new Error(message);
    }
  };

  const value = {
    user,
    token,
    isAuthenticated: Boolean(user),
    isLoading,
    error,
    login,
    register,
    sendRegisterOtp,
    verifyRegisterOtp,
    logout,
    updateProfile,
    changePassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
