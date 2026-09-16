import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { caregiverService } from '../../api/caregiverService';
import {
  Bell,
  AlertTriangle,
  XCircle,
  Clock,
  Loader2,
  RefreshCw,
  ChevronRight,
  MessageSquare,
  Package,
  Check,
  CheckCheck,
} from 'lucide-react';


import ChatDrawer from '../chat/ChatDrawer';
import { formatLocalDateTime, formatLocalTime } from '../../utils/dateTime';

export const CaregiverAlerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [patientCount, setPatientCount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [selectedChatPatient, setSelectedChatPatient] = useState(null);

  const fetchAlerts = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const [alertsRes, patientsRes] = await Promise.allSettled([
        caregiverService.getAlerts(),
        caregiverService.getPatients(),
      ]);

      if (alertsRes.status === 'fulfilled' && Array.isArray(alertsRes.value)) {
        setAlerts(alertsRes.value);
        setError(null);
      } else if (alertsRes.status === 'rejected') {
        const err = alertsRes.reason;
        const msg = err.response?.data?.detail?.message || err.response?.data?.detail || err.message || 'Failed to load clinical alerts';
        setError(typeof msg === 'string' ? msg : 'Failed to load clinical alerts');
      }

      if (patientsRes.status === 'fulfilled' && Array.isArray(patientsRes.value)) {
        setPatientCount(patientsRes.value.length);
      }
    } catch (err) {
      console.error('Failed to load alerts:', err);
      setError('Unexpected error loading alerts');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts(true);
    const interval = setInterval(() => {
      fetchAlerts(false);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleMarkAlertRead = async (alertId) => {
    try {
      await caregiverService.markAlertRead(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (err) {
      console.error('Failed to mark alert as read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await caregiverService.markAllAlertsRead();
      setAlerts([]);
    } catch (err) {
      console.error('Failed to mark all alerts as read:', err);
    }
  };

  const handleOpenChat = (al) => {
    setSelectedChatPatient({
      id: al.patient_id,
      user_id: al.patient_id,
      name: al.patient_name,
      employee_id: al.patient_employee_id,
      role: 'PATIENT',
    });
    setIsChatOpen(true);
  };

  const formatTimestamp = (ts) => {
    return formatLocalDateTime(ts, { hour12: true });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Clinical & Adherence Alerts</h1>
          <p className="text-sm text-slate-400 mt-1">Real-time notifications for patient messages, missed doses, and adherence risks across assigned patients.</p>
        </div>
        <div className="flex items-center gap-2">
          {alerts.length > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-xs font-semibold border border-amber-500/20 transition-colors"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark All as Read
            </button>
          )}
          <button
            onClick={() => fetchAlerts(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold self-start"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Bell className="w-4 h-4 text-amber-400" />
            Active Alerts ({alerts.length})
          </h2>
          {alerts.length > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="text-xs text-amber-400 hover:text-amber-300 font-semibold inline-flex items-center gap-1 transition-colors"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              <span>Mark all read</span>
            </button>
          )}
        </div>

        {error && alerts.length === 0 ? (
          <div className="p-8 text-center text-rose-400 bg-rose-500/10 border border-rose-500/20 m-4 rounded-xl">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-rose-400" />
            <p className="text-sm font-semibold">{error}</p>
            <button
              onClick={() => fetchAlerts(true)}
              className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-semibold transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        ) : loading && alerts.length === 0 ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin mx-auto mb-2" />
            <p className="text-xs text-slate-400">Checking patient alerts...</p>
          </div>
        ) : patientCount === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Bell className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm font-medium">No patients are currently assigned to you.</p>
            <p className="text-xs text-slate-500 mt-1">When an administrator assigns patients to your supervision, their clinical alerts and messages will appear here.</p>
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Bell className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm font-medium">No missed doses or clinical alerts.</p>
            <p className="text-xs text-slate-500 mt-1">All assigned patients are currently on track with their medication regimens.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {alerts.map((al) => {
              const isChat = al.type === 'CHAT_MESSAGE';
              const isRefill = al.type === 'REFILL_NEEDED';
              return (
                <div key={al.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/20 transition-colors">
                  <div className="flex items-start sm:items-center gap-3.5">
                    <div
                      className={`p-2.5 rounded-xl shrink-0 ${
                        isChat
                          ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20'
                          : isRefill
                          ? al.severity === 'CRITICAL'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : al.severity === 'CRITICAL'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}
                    >
                      {isChat ? (
                        <MessageSquare className="w-5 h-5" />
                      ) : isRefill ? (
                        <Package className="w-5 h-5" />
                      ) : al.severity === 'CRITICAL' ? (
                        <XCircle className="w-5 h-5" />
                      ) : (
                        <AlertTriangle className="w-5 h-5" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-white text-sm">{al.title}</span>
                        {al.patient_employee_id && (
                          <span className="font-mono text-[10px] text-teal-400 font-semibold bg-teal-500/10 px-1.5 py-0.5 rounded border border-teal-500/20">
                            {al.patient_employee_id}
                          </span>
                        )}
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            isChat
                              ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                              : isRefill
                              ? al.severity === 'CRITICAL'
                                ? 'bg-rose-500/20 text-rose-300'
                                : 'bg-amber-500/20 text-amber-300'
                              : al.severity === 'CRITICAL'
                              ? 'bg-rose-500/20 text-rose-300'
                              : 'bg-amber-500/20 text-amber-300'
                          }`}
                        >
                          {isChat ? 'LIVE MESSAGE' : isRefill ? (al.severity === 'CRITICAL' ? 'CRITICAL REFILL' : 'REFILL NEEDED') : al.severity}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">{al.message}</p>
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        {formatTimestamp(al.timestamp)}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center flex-wrap">
                    <button
                      onClick={() => handleMarkAlertRead(al.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-xs transition-colors border border-slate-700/60"
                      title="Mark this notification as read"
                    >
                      <Check className="w-3 h-3 text-amber-400" />
                      <span>Mark read</span>
                    </button>
                    {isChat ? (
                      <button
                        onClick={() => handleOpenChat(al)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition-colors shadow-sm shadow-teal-500/10"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        <span>Open Live Chat</span>
                      </button>
                    ) : isRefill ? (
                      <Link
                        to="/caregiver/adherence-reports"
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 font-semibold text-xs transition-colors"
                      >
                        <span>View Adherence & Refill</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    ) : (
                      <Link
                        to={`/caregiver/patients/${al.patient_id}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 font-semibold text-xs transition-colors"
                      >
                        View Patient
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}

          </div>
        )}
      </div>

      {/* Direct Caregiver-Patient Live Chat Drawer */}
      <ChatDrawer
        isOpen={isChatOpen}
        onClose={() => {
          setIsChatOpen(false);
          fetchAlerts(false);
        }}
        targetUser={selectedChatPatient}
      />
    </div>
  );
};

export default CaregiverAlerts;
