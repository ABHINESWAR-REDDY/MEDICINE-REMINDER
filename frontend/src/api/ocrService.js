import apiClient from './client';

export const ocrService = {
  /**
   * Upload and scan prescription file (returns { job_id, status: 'queued' }).
   * @param {FormData} formData - Multipart form containing 'file'
   */
  async scanPrescription(formData) {
    const response = await apiClient.post('/api/v1/ocr/prescription', formData);
    return response.data;
  },

  /**
   * Poll asynchronous prescription OCR job status.
   * @param {string} jobId - Unique OCR job UUID
   */
  async getPrescriptionJob(jobId) {
    const response = await apiClient.get(`/api/v1/ocr/prescription/${jobId}`);
    return response.data;
  },

  /**
   * Confirm and save reviewed prescription, medicine, and schedule.
   * @param {Object} payload - User-reviewed prescription, medicine, and schedule data
   */
  async confirmPrescription(payload) {
    const response = await apiClient.post('/api/v1/ocr/confirm', payload);
    return response.data;
  },

  /**
   * Autocomplete search against the global medicine reference dataset.
   * @param {string} query - Search term
   */
  async searchReferenceMedicines(query) {
    const response = await apiClient.get('/api/v1/ocr/reference-medicines', {
      params: { query },
    });
    return response.data;
  },
};

export default ocrService;
