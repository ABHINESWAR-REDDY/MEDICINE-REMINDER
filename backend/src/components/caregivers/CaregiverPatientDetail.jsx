import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { caregiverService } from '../../api/caregiverService';
import {
  User,
  Pill,
  CalendarCheck,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowLeft,
  Loader2,
  RefreshCw,
  Activity,
  MessageSquare,
} from 'lucide-react';
import ChatDrawer from '../chat/ChatDrawer';

const formatScheduledTime = (scheduledTimeStr) => {
  if (!scheduledTimeStr) return '';
  const timeMatch = scheduledTimeStr.match(/T(\d{2}):(\d{2})/);
  if (timeMatch) {
    return `${timeMatch[1]}:${timeMatch[2]}`;
  }
  return scheduledTimeStr;
};

const formatTakenAtTime = (actualTimeStr) => {
  if (!actualTimeStr) return '';
  let dateStr = actualTimeStr;
  if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('-')) {
    dateStr = `${dateStr}Z`;
  }
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
};

export const CaregiverPatientDetail = () => {
  const { patientId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  const fetchDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await caregiverService.getPatientDetail(patientId);
      setData(res);
    } catch (err) {
      console.error('Failed to load patient detail:', err);
      setError(err.response?.data?.detail?.message || 'Access Denied: You are not authorized to view this patient.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [patientId]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
          <p className="text-slate-400 text-sm">Loading patient profile & dose history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 max-w-lg mx-auto mt-10">
        <h2 className="text-lg font-bold mb-2">Unauthorized Patient Access</h2>
        <p className="text-sm mb-4">{error}</p>
        <Link
          to="/caregiver/dashboard"
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          Return to Caregiver Portal
        </Link>
      </div>
    );
  }

  const { patient, medications, today_doses, adherence_30_days, adherence_7_days } = data;

  return (
    <div className="space-y-6">
      {/* Back Link & Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            to="/caregiver/dashboard"
            className="p-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-white tracking-tight">{patient.name}</h1>
              <span className="font-mono text-xs text-teal-400 font-semibold bg-teal-500/10 px-2 py-0.5 rounded-md border border-teal-500/20">
                {patient.employee_id || `PT${String(patient.id).padStart(6, '0')}`}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{patient.email} · Assigned Patient Profile</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsChatOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold transition-colors shadow-lg shadow-teal-500/10"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-slate-950 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-slate-950"></span>
            </span>
            <MessageSquare className="w-4 h-4" />
            <span>Live Chat with Patient</span>
          </button>
          <button
            onClick={fetchDetail}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Adherence Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">30-Day Adherence</span>
            <Activity className="w-5 h-5 text-teal-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-teal-300">
            {adherence_30_days?.adherence_percentage}%
          </div>
          <div className="mt-1 text-xs text-slate-400">
            Status: <span className="font-semibold text-white">{adherence_30_days?.adherence_status}</span> · {adherence_30_days?.taken_count} taken, {adherence_30_days?.missed_count} missed
          </div>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">7-Day Adherence</span>
            <Activity className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-indigo-300">
            {adherence_7_days?.adherence_percentage}%
          </div>
          <div className="mt-1 text-xs text-slate-400">
            Status: <span className="font-semibold text-white">{adherence_7_days?.adherence_status}</span> · {adherence_7_days?.taken_count} taken, {adherence_7_days?.missed_count} missed
          </div>
        </div>
      </div>

      {/* Today's Dose Tracker */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <CalendarCheck className="w-4 h-4 text-teal-400" />
            Today's Scheduled Doses ({today_doses.length})
          </h2>
        </div>

        {today_doses.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            No medication doses scheduled for today.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {today_doses.map((dose) => (
              <div key={dose.id} className="p-4 flex items-center justify-between hover:bg-slate-800/20">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400">
                    <Pill className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-white">{dose.medicine_name}</div>
                    <div className="text-xs text-slate-400">
                      {dose.dosage_amount ? `${dose.dosage_amount} ${dose.dosage_unit || ''}` : ''} · {dose.medicine_form || ''}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right text-xs">
                    <div className="text-slate-300 font-medium">
                      {formatScheduledTime(dose.scheduled_time)}
                    </div>
                    {dose.actual_time && (
                      <div className="text-[10px] text-emerald-400">
                        Taken at {formatTakenAtTime(dose.actual_time)}
                      </div>
                    )}
                  </div>
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                      dose.status === 'TAKEN'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : dose.status === 'MISSED'
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        : dose.status === 'SKIPPED'
                        ? 'bg-slate-800 text-slate-400 border-slate-700'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    {dose.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Medication Regimen List */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Pill className="w-4 h-4 text-indigo-400" />
            Active Medications ({medications.length})
          </h2>
        </div>
        <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {medications.map((m) => (
            <div key={m.id} className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-2">
              <div className="font-bold text-white text-sm">{m.name}</div>
              <div className="text-xs text-slate-400">
                {m.dosage_amount ? `${m.dosage_amount} ${m.dosage_unit || ''}` : ''} · {m.medicine_form || ''}
              </div>
              {m.instructions && (
                <div className="text-xs text-slate-400 italic bg-slate-900 p-2 rounded-lg border border-slate-800">
                  "{m.instructions}"
                </div>
              )}
              {m.schedules && m.schedules.length > 0 && (
                <div className="text-xs text-teal-400 font-medium">
                  Times: {m.schedules.map((s) => (s.scheduled_times || []).join(', ')).join('; ')}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Direct Caregiver-Patient Chat Drawer */}
      <ChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        targetUser={patient}
      />
    </div>
  );
};

export default CaregiverPatientDetail;
