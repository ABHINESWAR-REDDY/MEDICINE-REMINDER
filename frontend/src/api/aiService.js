import apiClient from './client';

export const aiService = {
  /**
   * Send a question or message to PillSync AI Healthcare Assistant with multi-source verification.
   * @param {string} message - User query text
   * @param {Array} conversationHistory - Prior conversation turns
   * @param {boolean} includePatientContext - Whether to connect active medications
   * @param {number|null} patientId - Optional patient ID if caregiver
   */
  async sendMessage(message, conversationHistory = [], includePatientContext = true, patientId = null, language = null) {
    const currentLang = language || localStorage.getItem('pillsync_language') || 'en';
    const payload = {
      message,
      conversation_history: conversationHistory,
      include_patient_context: includePatientContext,
      patient_id: patientId,
      language: currentLang,
    };
    const response = await apiClient.post('/api/v1/ai/chat', payload);
    return response.data;
  },

  /**
   * Fetch categorized predefined questions for interactive exploration.
   */
  async getSuggestions() {
    const response = await apiClient.get('/api/v1/ai/suggestions');
    return response.data;
  },

  /**
   * Quick multi-source clinical monograph lookup for a medication name.
   */
  async lookupPill(medicineName) {
    const response = await apiClient.get(`/api/v1/ai/pill-lookup/${encodeURIComponent(medicineName)}`);
    return response.data;
  },

  /**
   * Verify confidence and clinical normalization of OCR-extracted medication text.
   */
  async verifyOcr(extractedText, confidence = 1.0) {
    const response = await apiClient.post('/api/v1/ai/verify-ocr', {
      extracted_text: extractedText,
      confidence,
    });
    return response.data;
  },
};

export default aiService;
