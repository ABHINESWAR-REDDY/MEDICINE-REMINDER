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
   * Update allowed profile attributes (name)
   */
  updateProfile: async ({ name }) => {
    const response = await apiClient.put('/api/v1/profile', { name });
    return response.data;
  },
};

export default profileService;
