import apiClient from './client';

export const profileService = {
  /**
   * Retrieve profile for the authenticated user
   */
  getProfile: async () => {
    const response = await apiClient.get('/api/v1/profile');
    return response.data;
  },

  /**
   * Update allowed profile attributes (name, language)
   */
  updateProfile: async (data) => {
    const response = await apiClient.put('/api/v1/profile', data);
    return response.data;
  },
};

export default profileService;
