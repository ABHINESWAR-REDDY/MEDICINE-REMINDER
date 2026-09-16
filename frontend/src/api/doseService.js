import api from './client';

export const doseService = {
  getTodayDoses: async (targetDate) => {
    const params = targetDate ? { target_date: targetDate } : {};
    const res = await api.get('/api/v1/patient/doses', { params });
    return res.data;
  },

  markDoseTaken: async (doseId) => {
    const res = await api.post(`/api/v1/patient/doses/${doseId}/take`);
    return res.data;
  },

  markDoseSkipped: async (doseId) => {
    const res = await api.post(`/api/v1/patient/doses/${doseId}/skip`);
    return res.data;
  },

  getAdherence: async (days = 30) => {
    const res = await api.get('/api/v1/patient/adherence', { params: { days } });
    return res.data;
  },
};

export default doseService;
