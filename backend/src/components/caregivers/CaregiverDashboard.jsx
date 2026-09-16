import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { caregiverService } from '../../api/caregiverService';
import {
  Users,
  CheckCircle2,
  XCircle,
  Clock,
  Activity,
  Bell,
  ChevronRight,
  Loader2,
  RefreshCw,
  AlertTriangle,
  MessageSquare,
} from 'lucide-react';
import ChatDrawer from '../chat/ChatDrawer';

export const extractErrorMessage = (err, fallback = 'An unexpected error occurred.') => {
  if (!err) return fallback;
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim().length > 0) {
    return detail;
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string' && detail.message.trim().length > 0) {
      return detail.message;
    }
  }
  const dataMsg = err.response?.data?.message;
  if (typeof dataMsg === 'string' && dataMsg.trim().length > 0) {
    return dataMsg;
  }
  if (typeof err.message === 'string' && err.message.trim().length > 0) {
    return err.message;
  }
  return fallback;
};

export const CaregiverDashboard = () => {
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [alertsError, setAlertsError] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [selectedChatPatient, setSelectedChatPatient] = useState(null);

  const isFetchingRef = useRef(false);
  const dataRef = useRef(null);
  dataRef.current = data;

  const fetchDashboard = async (showLoading = true) => {
    // Avoid multiple overlapping fetch cycles
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;

    if (showLoading && !dataRef.current) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }

    try {
      const [dashRes, alertsRes] = await Promise.allSettled([
        caregiverService.getDashboard(),
        caregiverService.getAlerts(),
      ]);

      if (dashRes.status === 'fulfilled' && dashRes.value) {
        setData(dashRes.value);
        setError(null);
      } else if (dashRes.status === 'rejected') {
        console.error('Failed to load caregiver dashboard:', dashRes.reason);
        // Only show full-page error if there's no existing dashboard data
        if (!dataRef.current) {
          setError(extractErrorMessage(dashRes.reason, 'Failed to load caregiver supervision dashboard.'));
        }
      }

      if (alertsRes.status === 'fulfilled') {
        setAlerts(Array.isArray(alertsRes.value) ? alertsRes.value : []);
        setAlertsError(null);
      } else if (alertsRes.status === 'rejected') {
        console.error('Failed to load caregiver alerts:', alertsRes.reason);
        setAlertsError(extractErrorMessage(alertsRes.reason, 'Failed to load clinical alerts.'));
      }
    } catch (err) {
      console.error('Unexpected error in caregiver fetch:', err);
      if (!dataRef.current) {
        setError(extractErrorMessage(err, 'Failed to load caregiver supervision dashboard.'));
      }
    } finally {
      if (showLoading) setLoading(false);
      setRefreshing(false);
      isFetchingRef.current = false;
    }
  };

  useEffect(() => {
    fetchDashboard(true);

    // Poll at a safe 20-second interval to avoid database lock contention and overhead
    const interval = setInterval(() => {
      fetchDashboard(false);
    }, 20000);

    return () => clearInterval(interval);
  }, []);

  const handleOpenChatForPatient = (pt) => {
    setSelectedChatPatient(pt);
    setIsChatOpen(true);
  };

  const handleOpenChatFromAlert = (al) => {
    setSelectedChatPatient({
      id: al.patient_id,
      user_id: al.patient_id,
      name: al.patient_name,
      employee_id: al.patient_employee_id,
      role: 'PATIENT',
    });
    setIsChatOpen(true);
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
          <p className="text-slate-400 text-sm">Loading supervision data...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400">
        <p className="font-semibold">{error}</p>
        <button
          onClick={() => fetchDashboard(true)}
          className="mt-3 px-4 py-2 bg-rose-500/20 rounded-xl text-xs font-semibold hover:bg-rose-500/30"
        >
          Try Again
        </button>
      </div>
    );
  }

  const overallAdh = data?.overall_adherence_percentage;
  const hasAdhData = overallAdh !== undefined && overallAdh !== null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Caregiver Supervision Portal</h1>
          <p className="text-sm text-slate-400 mt-1">
            Monitor medication adherence, dose intake, and real-time patient communications.
          </p>
        </div>
        <button
          onClick={() => fetchDashboard(false)}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold self-start transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Assigned Patients</span>
            <Users className="w-5 h-5 text-teal-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-white">{data?.total_assigned_patients ?? 0}</div>
          <div className="mt-1 text-xs text-slate-400">Under your care</div>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Doses Scheduled</span>
            <Clock className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-white">{data?.today_doses_scheduled ?? 0}</div>
          <div className="mt-1 text-xs text-slate-400">Total doses today</div>
        </div>

        <div className="p-5 bg-slate-900/60 border border-emerald-500/20 rounded-2xl bg-emerald-500/5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-emerald-400 tracking-wider">Doses Taken</span>
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-emerald-300">{data?.today_doses_taken ?? 0}</div>
          <div className="mt-1 text-xs text-emerald-400/80">Confirmed taken</div>
        </div>

        <div className="p-5 bg-slate-900/60 border border-rose-500/20 rounded-2xl bg-rose-500/5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-rose-400 tracking-wider">Missed Doses</span>
            <XCircle className="w-5 h-5 text-rose-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-rose-300">{data?.today_doses_missed ?? 0}</div>
          <div className="mt-1 text-xs text-rose-400/80">Requires attention</div>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Overall Adherence</span>
            <Activity className="w-5 h-5 text-teal-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-teal-300">
            {hasAdhData ? `${overallAdh}%` : 'No data'}
          </div>
          <div className="mt-1 text-xs text-slate-400">
            Status: {data?.overall_adherence_status || 'Good'}
          </div>
        </div>
      </div>

      {/* Alerts Error Banner if Alerts Call Failed Separately */}
      {alertsError && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl flex items-center justify-between text-xs text-amber-300">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>Could not update clinical alerts: {alertsError}</span>
          </div>
          <button
            onClick={() => fetchDashboard(false)}
            className="px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 rounded font-semibold text-amber-200"
          >
            Retry Alerts
          </button>
        </div>
      )}

      {/* Clinical & Messaging Alerts Box */}
      {(alerts || []).length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold text-amber-300 flex items-center gap-2">
              <Bell className="w-4 h-4 text-amber-400" />
              Active Clinical & Live Alerts ({alerts.length})
            </h2>
            <Link to="/caregiver/alerts" className="text-xs text-amber-400 hover:underline font-semibold">
              View All Alerts →
            </Link>
          </div>
          <div className="space-y-2">
            {alerts.slice(0, 4).map((al) => {
              const isChat = al.type === 'CHAT_MESSAGE';
              return (
                <div
                  key={al.id}
                  className={`p-3 bg-slate-900/80 border rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs transition-colors ${
                    isChat ? 'border-teal-500/40 bg-teal-950/20' : 'border-amber-500/20'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {isChat && <MessageSquare className="w-4 h-4 text-teal-400 shrink-0" />}
                    <div>
                      <span className="font-semibold text-white mr-2">{al.title}:</span>
                      <span className="text-slate-300">{al.message}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isChat
                          ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                          : al.severity === 'CRITICAL'
                          ? 'bg-rose-500/20 text-rose-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {isChat ? 'LIVE MESSAGE' : al.severity}
                    </span>
                    {isChat && (
                      <button
                        onClick={() => handleOpenChatFromAlert(al)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-[11px] transition-colors shadow-sm"
                      >
                        <MessageSquare className="w-3 h-3" />
                        <span>Live Chat</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Assigned Patients Table */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">My Supervised Patients</h2>
            <p className="text-xs text-slate-400 mt-0.5">Click a patient to inspect detailed schedules and dose history</p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">
            {data?.patients?.length ?? 0} Patients
          </span>
        </div>

        {!data?.patients || data.patients.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Users className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm font-medium">No patients are currently assigned to you.</p>
            <p className="text-xs text-slate-500 mt-1">Please contact your administrator to assign patients.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Patient Name</th>
                  <th className="py-3.5 px-4 font-semibold">Email</th>
                  <th className="py-3.5 px-4 font-semibold">Medications</th>
                  <th className="py-3.5 px-4 font-semibold">Today's Doses</th>
                  <th className="py-3.5 px-4 font-semibold">Missed Doses</th>
                  <th className="py-3.5 px-4 font-semibold">30-Day Adherence</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {data.patients.map((pt) => {
                  const hasUnreadChat = alerts.some((a) => a.type === 'CHAT_MESSAGE' && a.patient_id === pt.id);
                  const patientAdh = pt.adherence_percentage;
                  const hasPatientAdh = patientAdh !== undefined && patientAdh !== null;

                  return (
                    <tr key={pt.id} className="hover:bg-slate-800/20 transition-colors">
                      <td className="py-3 px-4">
                        <div>
                          <span className="font-semibold text-white block leading-tight">{pt.name}</span>
                          <span className="font-mono text-[10px] text-teal-400 font-semibold bg-teal-500/10 px-1.5 py-0.5 rounded border border-teal-500/20 inline-block mt-0.5">
                            {pt.employee_id || `PT${String(pt.id).padStart(6, '0')}`}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-300">{pt.email}</td>
                      <td className="py-3 px-4 text-slate-300">{pt.medications_count ?? 0} meds</td>
                      <td className="py-3 px-4 text-slate-300">
                        <span className="text-emerald-400 font-semibold">{pt.today_doses_taken ?? 0}</span> / {pt.today_doses_total ?? 0} taken
                      </td>
                      <td className="py-3 px-4">
                        {(pt.today_doses_missed ?? 0) > 0 ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                            {pt.today_doses_missed} Missed
                          </span>
                        ) : (
                          <span className="text-slate-500 text-xs">0</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {hasPatientAdh ? (
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                              pt.adherence_status === 'Good'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : pt.adherence_status === 'Needs Attention'
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            }`}
                          >
                            {patientAdh}% ({pt.adherence_status || 'Good'})
                          </span>
                        ) : (
                          <span className="text-slate-500 text-xs">No adherence data</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenChatForPatient(pt)}
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-semibold text-xs transition-colors ${
                              hasUnreadChat
                                ? 'bg-teal-500 text-slate-950 font-bold hover:bg-teal-400 shadow-md shadow-teal-500/20 animate-pulse'
                                : 'bg-blue-500/10 hover:bg-blue-500/20 text-blue-300'
                            }`}
                          >
                            <MessageSquare className="w-3.5 h-3.5" />
                            <span>{hasUnreadChat ? 'Chat (New)' : 'Chat'}</span>
                          </button>
                          <Link
                            to={`/caregiver/patients/${pt.id}`}
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 font-semibold text-xs transition-colors"
                          >
                            <span>Inspect</span>
                            <ChevronRight className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Direct Caregiver-Patient Chat Drawer */}
      <ChatDrawer
        isOpen={isChatOpen}
        onClose={() => {
          setIsChatOpen(false);
          fetchDashboard(false);
        }}
        targetUser={selectedChatPatient}
      />
    </div>
  );
};

export default CaregiverDashboard;
