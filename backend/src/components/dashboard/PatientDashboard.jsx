import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Pill,
  Calendar,
  Clock,
  Activity,
  FileText,
  Loader2,
  ChevronRight,
  ShieldCheck,
  ScanLine,
  ArrowRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Bell,
  MessageSquare,
  User,
  Shield,
  RefreshCw,
} from 'lucide-react';
import medicationService from '../../api/medicationService';
import { doseService } from '../../api/doseService';
import authService from '../../api/authService';
import { notificationService } from '../../api/notificationService';
import EmptyState from '../common/EmptyState';
import ChatDrawer from '../chat/ChatDrawer';

export const formatScheduledTime = (scheduledTimeStr) => {
  if (!scheduledTimeStr) return '';
  const timeMatch = scheduledTimeStr.match(/T(\d{2}):(\d{2})/);
  if (timeMatch) {
    return `${timeMatch[1]}:${timeMatch[2]}`;
  }
  return scheduledTimeStr;
};

export const formatTakenAtTime = (actualTimeStr) => {
  if (!actualTimeStr) return '';
  let dateStr = typeof actualTimeStr === 'string' ? actualTimeStr : String(actualTimeStr);
  if (!dateStr.endsWith('Z') && !/[+-]\d{2}(:\d{2})?$/.test(dateStr)) {
    dateStr = `${dateStr}Z`;
  }
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

export const PatientDashboard = ({ user }) => {
  const [profile, setProfile] = useState(user);
  const [medicines, setMedicines] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [conditions, setConditions] = useState([]);
  const [prescriptions, setPrescriptions] = useState([]);
  const [todayDoses, setTodayDoses] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [adherence, setAdherence] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const [freshUser, meds, scheds, conds, rxs, doses, adh, notifs] = await Promise.all([
        Promise.resolve(authService?.getMe ? authService.getMe() : null).catch(() => null),
        Promise.resolve(medicationService?.listMedicines ? medicationService.listMedicines(true) : []).catch(() => []),
        Promise.resolve(medicationService?.listSchedules ? medicationService.listSchedules(true) : []).catch(() => []),
        Promise.resolve(medicationService?.listConditions ? medicationService.listConditions() : []).catch(() => []),
        Promise.resolve(medicationService?.listPrescriptions ? medicationService.listPrescriptions('ACTIVE') : []).catch(() => []),
        Promise.resolve(doseService?.getTodayDoses ? doseService.getTodayDoses() : []).catch(() => []),
        Promise.resolve(doseService?.getAdherence ? doseService.getAdherence(30) : null).catch(() => null),
        Promise.resolve(notificationService?.getNotifications ? notificationService.getNotifications() : []).catch(() => []),
      ]);
      if (freshUser) {
        setProfile(freshUser);
      }
      setMedicines(Array.isArray(meds) ? meds : []);
      setSchedules(Array.isArray(scheds) ? scheds : []);
      setConditions(Array.isArray(conds) ? conds : []);
      setPrescriptions(Array.isArray(rxs) ? rxs : []);
      setTodayDoses(Array.isArray(doses) ? doses : []);
      setNotifications(Array.isArray(notifs) ? notifs : []);
      setAdherence(adh);
    } catch (err) {
      console.error('Failed to load patient dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleTakeDose = async (doseId) => {
    setActionLoading(doseId);
    try {
      await doseService.markDoseTaken(doseId);
      loadDashboardData();
    } catch (err) {
      console.error('Failed to mark dose taken:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSkipDose = async (doseId) => {
    setActionLoading(doseId);
    try {
      await doseService.markDoseSkipped(doseId);
      loadDashboardData();
    } catch (err) {
      console.error('Failed to skip dose:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const activeUser = profile || user;
  const caregiverName = activeUser?.assigned_caregiver_name;
  const caregiverEmpId = activeUser?.assigned_caregiver_employee_id;
  const caregiverEmail = activeUser?.assigned_caregiver_email;

  return (
    <div className="space-y-6 w-full">
      {/* Patient Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h2 className="text-2xl font-bold tracking-tight text-white">
              Welcome, {activeUser?.name || 'Patient'}
            </h2>
            <span className="font-mono text-xs text-teal-400 font-semibold bg-teal-500/10 px-2 py-0.5 rounded-md border border-teal-500/20">
              {activeUser?.employee_id || (activeUser?.id ? `PT${String(activeUser.id).padStart(6, '0')}` : '')}
            </span>
            {caregiverName && (
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-300 bg-blue-500/10 px-2.5 py-0.5 rounded-md border border-blue-500/20">
                <span>Caregiver: <strong>{caregiverName}</strong></span>
                <span className="font-mono text-[10px] text-blue-400 font-bold">({caregiverEmpId || 'CG'})</span>
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Patient Portal — Manage your medication inventory, dosage schedules, and health records.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/ocr"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-teal-500 hover:bg-teal-400 text-slate-950 shadow-lg shadow-teal-500/10 transition-colors"
          >
            <ScanLine className="w-4 h-4" />
            <span>Scan Prescription</span>
          </Link>
          <span className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border bg-teal-500/10 text-teal-300 border-teal-500/30">
            <ShieldCheck className="w-3.5 h-3.5" />
            Patient Portal
          </span>
        </div>
      </div>

      {/* Assigned Caregiver Card & Direct Chat Action */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-lg shrink-0">
            {caregiverName ? caregiverName.charAt(0).toUpperCase() : <User className="w-6 h-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Supervising Caregiver:</span>
              {caregiverName ? (
                <>
                  <span className="text-sm font-bold text-white">{caregiverName}</span>
                  <span className="font-mono text-xs text-blue-400 font-bold bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                    {caregiverEmpId || 'CG Assigned'}
                  </span>
                </>
              ) : (
                <span className="text-xs text-slate-500 italic">No Caregiver Assigned Yet</span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {caregiverName
                ? `${caregiverEmail || 'Caregiver Supervisor'} · Authorized to monitor your doses & adherence`
                : 'Contact system administrator if you require an approved caregiver supervisor'}
            </p>
          </div>
        </div>

        {caregiverName ? (
          <button
            onClick={() => setIsChatOpen(true)}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition-all shadow-lg shadow-teal-500/10 shrink-0"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-slate-950 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-slate-950"></span>
            </span>
            <MessageSquare className="w-4 h-4" />
            <span>Live Chat with Caregiver</span>
          </button>
        ) : (
          <button
            disabled
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 text-slate-500 font-medium text-xs cursor-not-allowed shrink-0"
          >
            <MessageSquare className="w-4 h-4" />
            <span>Chat Unavailable</span>
          </button>
        )}
      </div>

      {/* Active Medication Alerts & Reminders Hub Card */}
      {notifications.length > 0 && (
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center">
                <Bell className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>Medication Reminders & Alerts</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-300 border border-teal-500/20">
                    {notifications.filter((n) => !n.is_read).length} Unread
                  </span>
                </h3>
              </div>
            </div>
            <Link
              to="/patient/alerts"
              className="text-xs text-teal-400 hover:text-teal-300 font-semibold inline-flex items-center gap-1"
            >
              <span>View All Alerts Hub</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {notifications.slice(0, 2).map((notif) => {
              const isMissed = notif.type === 'MISSED_DOSE';
              return (
                <div
                  key={notif.id}
                  className={`p-3.5 rounded-xl border flex items-start gap-3 transition-colors ${
                    isMissed
                      ? 'bg-amber-500/5 border-amber-500/20'
                      : 'bg-slate-950/60 border-slate-800/80'
                  }`}
                >
                  <div
                    className={`p-2 rounded-lg shrink-0 mt-0.5 ${
                      isMissed ? 'bg-amber-500/10 text-amber-400' : 'bg-teal-500/10 text-teal-400'
                    }`}
                  >
                    {isMissed ? <AlertTriangle className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-xs font-bold text-white truncate">{notif.title}</span>
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.2 rounded shrink-0 ${
                          isMissed ? 'bg-amber-500/20 text-amber-300' : 'bg-teal-500/20 text-teal-300'
                        }`}
                      >
                        {isMissed ? 'MISSED DOSE' : 'REMINDER'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300 mt-0.5 line-clamp-2">{notif.message}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick Action Hero Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-teal-950/40 via-slate-900/80 to-slate-900/60 border border-teal-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 shrink-0">
            <ScanLine className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Have a new medical prescription?</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              Use our intelligent OCR scanner to upload images or PDFs. Medication names, dosages, and frequencies are automatically extracted and verified.
            </p>
          </div>
        </div>
        <Link
          to="/ocr"
          className="shrink-0 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold flex items-center gap-2 border border-slate-700 transition-colors"
        >
          <span>Scan Document</span>
          <ArrowRight className="w-3.5 h-3.5 text-teal-400" />
        </Link>
      </div>

      {/* Real Live Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Link
          to="/medications"
          className="p-4 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-colors space-y-1 block"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400">Active Medicines</span>
            <Pill className="w-4 h-4 text-teal-400" />
          </div>
          <p className="text-2xl font-bold text-white font-mono">{(medicines || []).length}</p>
        </Link>

        <Link
          to="/schedule"
          className="p-4 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-colors space-y-1 block"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400">Intake Schedules</span>
            <Calendar className="w-4 h-4 text-sky-400" />
          </div>
          <p className="text-2xl font-bold text-white font-mono">{(schedules || []).length}</p>
        </Link>

        <Link
          to="/conditions"
          className="p-4 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-colors space-y-1 block"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400">Conditions</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white font-mono">{(conditions || []).length}</p>
        </Link>

        <Link
          to="/prescriptions"
          className="p-4 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-colors space-y-1 block"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400">Prescriptions</span>
            <FileText className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold text-white font-mono">{(prescriptions || []).length}</p>
        </Link>
      </div>

      {/* Adherence Overview Bar */}
      {adherence && (
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div>
              <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">30-Day Medication Adherence</span>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-2xl font-bold text-white">{adherence.adherence_percentage}%</span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                    adherence.adherence_status === 'Good'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : adherence.adherence_status === 'Needs Attention'
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}
                >
                  {adherence.adherence_status}
                </span>
              </div>
            </div>
            <div className="text-xs text-slate-400">
              <span className="text-emerald-400 font-semibold">{adherence.taken_count} taken</span> ·{' '}
              <span className="text-rose-400 font-semibold">{adherence.missed_count} missed</span> ·{' '}
              <span className="text-slate-400">{adherence.skipped_count} skipped</span>
            </div>
          </div>
          <div className="w-full h-2.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                adherence.adherence_percentage >= 90
                  ? 'bg-emerald-400'
                  : adherence.adherence_percentage >= 75
                  ? 'bg-amber-400'
                  : 'bg-rose-400'
              }`}
              style={{ width: `${Math.min(100, adherence.adherence_percentage)}%` }}
            />
          </div>
        </div>
      )}

      {/* Today's Dose Tracker Section */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-teal-400" />
              Today's Scheduled Medication Doses
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Track and confirm your daily medication intake</p>
          </div>
          <button
            onClick={loadDashboardData}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {isLoading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin mx-auto mb-2" />
            <p className="text-xs text-slate-400">Loading today's doses...</p>
          </div>
        ) : todayDoses.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <CheckCircle2 className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm font-medium">No doses scheduled for today.</p>
            <p className="text-xs text-slate-500 mt-1">Create an intake schedule to start tracking doses.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {todayDoses.map((dose) => (
              <div key={dose.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/20">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-teal-500/10 text-teal-400">
                    <Pill className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-white">{dose.medicine_name}</div>
                    <div className="text-xs text-slate-400">
                      {dose.dosage_amount ? `${dose.dosage_amount} ${dose.dosage_unit || ''}` : ''} · {dose.medicine_form || ''}
                      {dose.instructions && <span className="ml-2 italic text-slate-500">"{dose.instructions}"</span>}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-3">
                  <div className="text-left sm:text-right text-xs">
                    <div className="text-slate-200 font-semibold">
                      {formatScheduledTime(dose.scheduled_time)}
                    </div>
                    {dose.actual_time && (
                      <div className="text-[10px] text-emerald-400">
                        Taken at {formatTakenAtTime(dose.actual_time)}
                      </div>
                    )}
                  </div>

                  {dose.status === 'SCHEDULED' ? (
                    <div className="inline-flex items-center gap-2">
                      <button
                        onClick={() => handleTakeDose(dose.id)}
                        disabled={actionLoading === dose.id}
                        className="px-3 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-md shadow-emerald-500/10 transition-colors disabled:opacity-50"
                      >
                        {actionLoading === dose.id ? 'Saving...' : 'Mark as Taken'}
                      </button>
                      <button
                        onClick={() => handleSkipDose(dose.id)}
                        disabled={actionLoading === dose.id}
                        className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-colors disabled:opacity-50"
                      >
                        Skip
                      </button>
                    </div>
                  ) : (
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                        dose.status === 'TAKEN'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : dose.status === 'MISSED'
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      {dose.status}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Direct Caregiver Communication Chat Drawer */}
      <ChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        targetUser={
          caregiverName
            ? {
                id: activeUser?.assigned_caregiver_id,
                user_id: activeUser?.assigned_caregiver_id,
                name: caregiverName,
                employee_id: caregiverEmpId,
                email: caregiverEmail,
                role: 'CAREGIVER',
              }
            : null
        }
      />
    </div>
  );
};

export default PatientDashboard;
