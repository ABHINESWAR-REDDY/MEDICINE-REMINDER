import apiClient from './client';

/**
 * Patient Portal API service for Medication History & Refill Predictions.
 */
export const patientService = {
  async getMedicationHistory() {
    const response = await apiClient.get('/api/v1/patient/medication-history');
    return response.data;
  },

  async getRefillPredictions() {
    const response = await apiClient.get('/api/v1/patient/refill-predictions');
    return response.data;
  },
};

export default patientService;
