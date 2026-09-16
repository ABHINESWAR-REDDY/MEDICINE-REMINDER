import apiClient from './client';

export const authService = {
  /**
   * Check whether first admin account registration is available.
   */
  async getAdminRegistrationStatus() {
    const response = await apiClient.get('/api/v1/auth/admin-registration-status');
    return response.data;
  },

  /**
   * Validate registration payload and dispatch a 6-digit verification code to the email.
   * @param {Object} data { name, email, password, password_confirmation, role }
   */
  async sendRegisterOtp(data) {
    const response = await apiClient.post('/api/v1/auth/register/send-otp', data);
    return response.data;
  },

  /**
   * Verify the 6-digit email OTP and persist the new account.
   * @param {Object} data { name, email, password, password_confirmation, role, otp_code, employee_id }
   */
  async verifyRegisterOtp(data) {
    const response = await apiClient.post('/api/v1/auth/register/verify-otp', data);
    return response.data;
  },

  /**
   * Check employee/member ID format and availability.
   * @param {string} employeeId
   * @param {string} role
   */
  async checkEmployeeId(employeeId, role = 'PATIENT') {
    const response = await apiClient.get('/api/v1/auth/check-employee-id', {
      params: { employee_id: employeeId, role }
    });
    return response.data;
  },

  /**
   * Send a password reset OTP code to the provided email address.
   * @param {Object} data { email }
   */
  async sendForgotPasswordOtp(data) {
    const response = await apiClient.post('/api/v1/auth/forgot-password/send-otp', data);
    return response.data;
  },

  /**
   * Verify OTP and reset account password.
   * @param {Object} data { email, otp_code, new_password, new_password_confirmation }
   */
  async resetPasswordWithOtp(data) {
    const response = await apiClient.post('/api/v1/auth/forgot-password/reset', data);
    return response.data;
  },

  /**
   * Direct registration.
   * @param {Object} data { name, email, password, password_confirmation, role }
   */
  async register(data) {
    const response = await apiClient.post('/api/v1/auth/register', data);
    return response.data;
  },

  /**
   * Authenticate user with credentials and obtain JWT access token.
   * @param {Object} credentials { email, password }
   */
  async login(credentials) {
    const response = await apiClient.post('/api/v1/auth/login', credentials);
    return response.data;
  },

  /**
   * Fetch current authenticated user profile.
   */
  async getMe() {
    const response = await apiClient.get('/api/v1/auth/me');
    return response.data;
  },

  /**
   * Change password for the current authenticated user.
   * @param {Object} data { current_password, new_password, new_password_confirmation }
   */
  async changePassword(data) {
    const response = await apiClient.post('/api/v1/auth/change-password', data);
    return response.data;
  },
};

export default authService;
