import apiClient from './client';

/**
 * Fetch health status from the backend API.
 * @returns {Promise<Object>} The health status payload.
 */
export const fetchHealthStatus = async () => {
  const response = await apiClient.get('/api/v1/health');
  return response.data;
};
