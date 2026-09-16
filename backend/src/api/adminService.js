import api from './client';

export const adminService = {
  getDashboard: async () => {
    const res = await api.get('/api/v1/admin/dashboard');
    return res.data;
  },

  getCaregivers: async (status) => {
    const params = status ? { status } : {};
    const res = await api.get('/api/v1/admin/caregivers', { params });
    return res.data;
  },

  getPendingCaregivers: async () => {
    const res = await api.get('/api/v1/admin/caregivers/pending');
    return res.data;
  },

  approveCaregiver: async (id) => {
    const res = await api.post(`/api/v1/admin/caregivers/${id}/approve`);
    return res.data;
  },

  rejectCaregiver: async (id) => {
    const res = await api.post(`/api/v1/admin/caregivers/${id}/reject`);
    return res.data;
  },

  activateCaregiver: async (id) => {
    const res = await api.post(`/api/v1/admin/caregivers/${id}/activate`);
    return res.data;
  },

  deactivateCaregiver: async (id) => {
    const res = await api.post(`/api/v1/admin/caregivers/${id}/deactivate`);
    return res.data;
  },

  getAssignments: async () => {
    const res = await api.get('/api/v1/admin/assignments');
    return res.data;
  },

  assignPatient: async (caregiverId, patientId) => {
    const res = await api.post('/api/v1/admin/assignments', {
      caregiver_id: caregiverId,
      patient_id: patientId,
    });
    return res.data;
  },

  revokeAssignment: async (assignmentId) => {
    const res = await api.delete(`/api/v1/admin/assignments/${assignmentId}`);
    return res.data;
  },

  getAuditLogs: async (limit = 50, offset = 0) => {
    const res = await api.get('/api/v1/admin/audit-logs', { params: { limit, offset } });
    return res.data;
  },

  getPatients: async (status, search) => {
    const params = {};
    if (status) params.status = status;
    if (search) params.search = search;
    const res = await api.get('/api/v1/admin/patients', { params });
    return res.data;
  },

  togglePatientActive: async (patientId) => {
    const res = await api.post(`/api/v1/admin/patients/${patientId}/toggle-active`);
    return res.data;
  },

  // 1. Platform Activities
  getPlatformActivities: async (params = {}) => {
    const res = await api.get('/api/v1/admin/activities', { params });
    return res.data;
  },

  // 2. Notification Settings
  getNotificationSettings: async () => {
    const res = await api.get('/api/v1/admin/notification-settings');
    return res.data;
  },

  updateNotificationSettings: async (data) => {
    const res = await api.put('/api/v1/admin/notification-settings', data);
    return res.data;
  },

  // 3. Platform Analytics
  getPlatformAnalytics: async (params = {}) => {
    const res = await api.get('/api/v1/admin/analytics', { params });
    return res.data;
  },

  // 4. System Operations & Health
  getSystemHealth: async () => {
    const res = await api.get('/api/v1/admin/system/health');
    return res.data;
  },

  reconcileDoses: async () => {
    const res = await api.post('/api/v1/admin/system/reconcile-doses');
    return res.data;
  },

  reconcileNotifications: async () => {
    const res = await api.post('/api/v1/admin/system/reconcile-notifications');
    return res.data;
  },

  runConsistencyCheck: async () => {
    const res = await api.post('/api/v1/admin/system/consistency-check');
    return res.data;
  },
};

export default adminService;
