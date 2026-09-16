import apiClient from './client';

/**
 * Medication, Condition, Prescription, and Schedule API service.
 * Connects directly to FastAPI backend without any mock data.
 */
export const medicationService = {
  // ==================== CONDITIONS ====================
  async listConditions() {
    const response = await apiClient.get('/api/v1/conditions');
    return response.data;
  },

  async getCondition(id) {
    const response = await apiClient.get(`/api/v1/conditions/${id}`);
    return response.data;
  },

  async createCondition(data) {
    const response = await apiClient.post('/api/v1/conditions', data);
    return response.data;
  },

  async updateCondition(id, data) {
    const response = await apiClient.put(`/api/v1/conditions/${id}`, data);
    return response.data;
  },

  async deleteCondition(id) {
    const response = await apiClient.delete(`/api/v1/conditions/${id}`);
    return response.data;
  },

  // ==================== PRESCRIPTIONS ====================
  async listPrescriptions(status = null) {
    const params = status ? { status } : {};
    const response = await apiClient.get('/api/v1/prescriptions', { params });
    return response.data;
  },

  async getPrescription(id) {
    const response = await apiClient.get(`/api/v1/prescriptions/${id}`);
    return response.data;
  },

  async createPrescription(data) {
    const response = await apiClient.post('/api/v1/prescriptions', data);
    return response.data;
  },

  async updatePrescription(id, data) {
    const response = await apiClient.put(`/api/v1/prescriptions/${id}`, data);
    return response.data;
  },

  async deletePrescription(id) {
    const response = await apiClient.delete(`/api/v1/prescriptions/${id}`);
    return response.data;
  },

  // ==================== MEDICINES ====================
  async listMedicines(isActive = null) {
    const params = isActive !== null ? { is_active: isActive } : {};
    const response = await apiClient.get('/api/v1/medicines', { params });
    return response.data;
  },

  async getMedicine(id) {
    const response = await apiClient.get(`/api/v1/medicines/${id}`);
    return response.data;
  },

  async createMedicine(data) {
    const response = await apiClient.post('/api/v1/medicines', data);
    return response.data;
  },

  async updateMedicine(id, data) {
    const response = await apiClient.put(`/api/v1/medicines/${id}`, data);
    return response.data;
  },

  async deactivateMedicine(id) {
    const response = await apiClient.post(`/api/v1/medicines/${id}/deactivate`);
    return response.data;
  },

  async deleteMedicine(id) {
    const response = await apiClient.delete(`/api/v1/medicines/${id}`);
    return response.data;
  },

  async createMedicineSchedule(medicineId, data) {
    const response = await apiClient.post(`/api/v1/medicines/${medicineId}/schedules`, data);
    return response.data;
  },

  async listMedicineSchedules(medicineId) {
    const response = await apiClient.get(`/api/v1/medicines/${medicineId}/schedules`);
    return response.data;
  },

  // ==================== SCHEDULES ====================
  async listSchedules(isActive = null) {
    const params = isActive !== null ? { is_active: isActive } : {};
    const response = await apiClient.get('/api/v1/schedules', { params });
    return response.data;
  },

  async getSchedule(id) {
    const response = await apiClient.get(`/api/v1/schedules/${id}`);
    return response.data;
  },

  async updateSchedule(id, data) {
    const response = await apiClient.put(`/api/v1/schedules/${id}`, data);
    return response.data;
  },

  async deleteSchedule(id) {
    const response = await apiClient.delete(`/api/v1/schedules/${id}`);
    return response.data;
  },

  // ==================== PATIENT PORTAL ====================
  async getMedicationHistory() {
    const response = await apiClient.get('/api/v1/patient/medication-history');
    return response.data;
  },

  async getRefillPredictions() {
    const response = await apiClient.get('/api/v1/patient/refill-predictions');
    return response.data;
  },
};

export default medicationService;

