import api from './client';

export const caregiverService = {
  getDashboard: async () => {
    const res = await api.get('/api/v1/caregiver/dashboard');
    return res.data;
  },

  getPatients: async () => {
    const res = await api.get('/api/v1/caregiver/patients');
    return res.data;
  },

  getPatientDetail: async (patientId) => {
    const res = await api.get(`/api/v1/caregiver/patients/${patientId}`);
    return res.data;
  },

  getAlerts: async () => {
    const res = await api.get('/api/v1/caregiver/alerts');
    return res.data;
  },

  markAlertRead: async (alertId) => {
    const res = await api.post(`/api/v1/caregiver/alerts/${alertId}/read`);
    return res.data;
  },

  markAllAlertsRead: async () => {
    const res = await api.post('/api/v1/caregiver/alerts/read-all');
    return res.data;
  },

  getAdherenceReports: async (days = 30) => {
    const res = await api.get('/api/v1/caregiver/adherence-reports', { params: { days } });
    return res.data;
  },

  getPatientAdherenceReport: async (patientId, days = 30) => {
    const res = await api.get(`/api/v1/caregiver/patients/${patientId}/adherence`, { params: { days } });
    return res.data;
  },

  getRefillNotifications: async () => {
    const res = await api.get('/api/v1/caregiver/refill-notifications');
    return res.data;
  },
};

export default caregiverService;

