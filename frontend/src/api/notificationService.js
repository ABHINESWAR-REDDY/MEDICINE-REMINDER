import apiClient from './client';

export const notificationService = {
  /**
   * Fetch real database notifications for the authenticated patient.
   * @param {Object} params { filter_type, unread_only }
   */
  async getNotifications(params = {}) {
    const response = await apiClient.get('/api/v1/patient/notifications', { params });
    return response.data;
  },

  /**
   * Get count of active unread notifications for badge display.
   */
  async getUnreadCount() {
    const response = await apiClient.get('/api/v1/patient/notifications/unread-count');
    return response.data;
  },

  /**
   * Mark a specific notification as read.
   * @param {number} notificationId
   */
  async markAsRead(notificationId) {
    const response = await apiClient.post(`/api/v1/patient/notifications/${notificationId}/read`);
    return response.data;
  },

  /**
   * Mark all unread notifications for the patient as read.
   */
  async markAllAsRead() {
    const response = await apiClient.post('/api/v1/patient/notifications/read-all');
    return response.data;
  },
};

export default notificationService;
