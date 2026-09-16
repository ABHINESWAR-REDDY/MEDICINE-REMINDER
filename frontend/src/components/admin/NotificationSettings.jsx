import React, { useState, useEffect } from 'react';
import { adminService } from '../../api/adminService';
import { formatLocalDateTime } from '../../utils/dateTime';
import {
  Bell,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Loader2,
  Save,
  RotateCcw,
  Shield,
  User,
  Users,
  Settings,
  Clock,
} from 'lucide-react';

export const NotificationSettings = () => {
  const [settings, setSettings] = useState({
    // Patient Notifications
    patient_medication_reminders_enabled: true,
    patient_missed_dose_alerts_enabled: true,
    patient_refill_alerts_enabled: true,
    patient_polling_interval_seconds: 30,

    // Caregiver Notifications
    caregiver_missed_dose_alerts_enabled: true,
    caregiver_refill_alerts_enabled: true,
    caregiver_adherence_risk_alerts_enabled: true,
    caregiver_patient_chat_alerts_enabled: true,

    // System Notifications
    system_security_alerts_enabled: true,
    system_operational_alerts_enabled: true,
  });

  const [metadata, setMetadata] = useState({
    updated_at: null,
    updated_by: null,
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchSettings = async () => {
    setLoading(true);
    setError(null);
    setSaveSuccess(false);
    try {
      const data = await adminService.getNotificationSettings();
      if (data) {
        setSettings({
          patient_medication_reminders_enabled: data.patient_medication_reminders_enabled ?? true,
          patient_missed_dose_alerts_enabled: data.patient_missed_dose_alerts_enabled ?? true,
          patient_refill_alerts_enabled: data.patient_refill_alerts_enabled ?? true,
          patient_polling_interval_seconds: data.patient_polling_interval_seconds ?? 30,
          caregiver_missed_dose_alerts_enabled: data.caregiver_missed_dose_alerts_enabled ?? true,
          caregiver_refill_alerts_enabled: data.caregiver_refill_alerts_enabled ?? true,
          caregiver_adherence_risk_alerts_enabled: data.caregiver_adherence_risk_alerts_enabled ?? true,
          caregiver_patient_chat_alerts_enabled: data.caregiver_patient_chat_alerts_enabled ?? true,
          system_security_alerts_enabled: data.system_security_alerts_enabled ?? true,
          system_operational_alerts_enabled: data.system_operational_alerts_enabled ?? true,
        });
        setMetadata({
          updated_at: data.updated_at,
          updated_by: data.updated_by,
        });
      }
    } catch (err) {
      const errorMsg =
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        err.message ||
        'Failed to load platform notification settings.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleToggle = (field) => {
    setSettings((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
    setSaveSuccess(false);
  };

  const handleNumberChange = (field, val) => {
    const num = parseInt(val, 10);
    setSettings((prev) => ({
      ...prev,
      [field]: isNaN(num) ? 30 : num,
    }));
    setSaveSuccess(false);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      const updated = await adminService.updateNotificationSettings(settings);
      setMetadata({
        updated_at: updated.updated_at,
        updated_by: updated.updated_by,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err) {
      const errorMsg =
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        err.message ||
        'Failed to save notification settings.';
      setError(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const handleResetToDefaults = () => {
    setSettings({
      patient_medication_reminders_enabled: true,
      patient_missed_dose_alerts_enabled: true,
      patient_refill_alerts_enabled: true,
      patient_polling_interval_seconds: 30,
      caregiver_missed_dose_alerts_enabled: true,
      caregiver_refill_alerts_enabled: true,
      caregiver_adherence_risk_alerts_enabled: true,
      caregiver_patient_chat_alerts_enabled: true,
      system_security_alerts_enabled: true,
      system_operational_alerts_enabled: true,
    });
    setSaveSuccess(false);
  };

  const formatTimestamp = (isoStr) => {
    if (!isoStr) return null;
    return formatLocalDateTime(isoStr, { hour12: true }) || isoStr;
  };

  if (loading && !metadata.updated_at && !error) {
    return (
      <div className="flex items-center justify-center min-h-[400px] bg-slate-900/40 border border-slate-800/80 rounded-2xl">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
          <p className="text-slate-400 text-sm">Loading persistent notification settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Notification Settings</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">
              Persistent DB Configuration
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Configure platform-wide automated notification generation rules for patients, caregivers, and administrative subsystems.
          </p>
        </div>

        <button
          onClick={fetchSettings}
          disabled={loading || saving}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Reload Settings
        </button>
      </div>

      {/* Success / Error Banners */}
      {saveSuccess && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-center gap-3 text-emerald-400 text-sm">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>Notification settings have been successfully saved and persisted in the database.</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl flex items-center justify-between gap-3 text-rose-400 text-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchSettings}
            className="px-3 py-1.5 bg-rose-500/20 hover:bg-rose-500/30 rounded-xl text-xs font-semibold text-rose-300"
          >
            Retry
          </button>
        </div>
      )}

      {/* Settings Form */}
      <form onSubmit={handleSave} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 1. Patient Notifications Section */}
          <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center gap-2.5 text-white font-semibold text-base pb-3 border-b border-slate-800">
                <User className="w-5 h-5 text-blue-400" />
                <h2>Patient Notifications</h2>
              </div>
              <p className="text-xs text-slate-400">
                Control reminders and alert generation dispatched to patient dashboards and alerts feed.
              </p>

              <div className="space-y-4 pt-2">
                {/* Medication Reminders Toggle */}
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="space-y-0.5">
                    <label className="text-xs font-medium text-slate-200 block cursor-pointer">
                      Medication Reminders
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Dispatches reminders when medication schedules are due.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.patient_medication_reminders_enabled}
                    onClick={() => handleToggle('patient_medication_reminders_enabled')}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      settings.patient_medication_reminders_enabled ? 'bg-teal-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        settings.patient_medication_reminders_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                {/* Missed-Dose Alerts Toggle */}
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="space-y-0.5">
                    <label className="text-xs font-medium text-slate-200 block cursor-pointer">
                      Missed-Dose Alerts
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Flags overdue scheduled doses as missed with warnings.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.patient_missed_dose_alerts_enabled}
                    onClick={() => handleToggle('patient_missed_dose_alerts_enabled')}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      settings.patient_missed_dose_alerts_enabled ? 'bg-teal-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        settings.patient_missed_dose_alerts_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                {/* Refill Alerts Toggle */}
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="space-y-0.5">
                    <label className="text-xs font-medium text-slate-200 block cursor-pointer">
                      Refill Notifications
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Predictive warnings when remaining pill supply is low.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.patient_refill_alerts_enabled}
                    onClick={() => handleToggle('patient_refill_alerts_enabled')}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      settings.patient_refill_alerts_enabled ? 'bg-teal-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        settings.patient_refill_alerts_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                {/* Polling Interval Input */}
                <div className="p-3 bg-slate-950/40 rounded-xl border border-slate-800/60 space-y-2">
                  <label className="text-xs font-medium text-slate-200 block">
                    Patient Polling Interval (Seconds)
                  </label>
                  <input
                    type="number"
                    min="5"
                    max="300"
                    value={settings.patient_polling_interval_seconds}
                    onChange={(e) => handleNumberChange('patient_polling_interval_seconds', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-teal-500"
                  />
                  <p className="text-[10px] text-slate-500">
                    Recommended: 30s. Range: 5s to 300s.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 2. Caregiver Notifications Section */}
          <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center gap-2.5 text-white font-semibold text-base pb-3 border-b border-slate-800">
                <Users className="w-5 h-5 text-teal-400" />
                <h2>Caregiver Notifications</h2>
              </div>
              <p className="text-xs text-slate-400">
                Supervisory alerts and escalation triggers sent to assigned caregivers.
              </p>

              <div className="space-y-4 pt-2">
                {/* Caregiver Missed Dose Alerts */}
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="space-y-0.5">
                    <label className="text-xs font-medium text-slate-200 block cursor-pointer">
                      Missed-Dose Alerts
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Alerts caregiver when assigned patient misses intake.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.caregiver_missed_dose_alerts_enabled}
                    onClick={() => handleToggle('caregiver_missed_dose_alerts_enabled')}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      settings.caregiver_missed_dose_alerts_enabled ? 'bg-teal-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        settings.caregiver_missed_dose_alerts_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                {/* Caregiver Refill Alerts */}
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="space-y-0.5">
                    <label className="text-xs font-medium text-slate-200 block cursor-pointer">
                      Refill Alerts
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Notifies caregiver when patient medications need restock.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.caregiver_refill_alerts_enabled}
                    onClick={() => handleToggle('caregiver_refill_alerts_enabled')}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      settings.caregiver_refill_alerts_enabled ? 'bg-teal-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        settings.caregiver_refill_alerts_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                {/* Caregiver Adherence-Risk Alerts */}
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="space-y-0.5">
                    <label className="text-xs font-medium text-slate-200 block cursor-pointer">
                      Adherence-Risk Alerts
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Warns caregiver when patient 30-day adherence drops &lt; 75%.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.caregiver_adherence_risk_alerts_enabled}
                    onClick={() => handleToggle('caregiver_adherence_risk_alerts_enabled')}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      settings.caregiver_adherence_risk_alerts_enabled ? 'bg-teal-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        settings.caregiver_adherence_risk_alerts_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                {/* Patient Chat Alerts */}
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="space-y-0.5">
                    <label className="text-xs font-medium text-slate-200 block cursor-pointer">
                      Patient Chat Alerts
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Delivers real-time indicators for unread patient messages.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.caregiver_patient_chat_alerts_enabled}
                    onClick={() => handleToggle('caregiver_patient_chat_alerts_enabled')}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      settings.caregiver_patient_chat_alerts_enabled ? 'bg-teal-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        settings.caregiver_patient_chat_alerts_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* 3. System & Administrative Notifications */}
          <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center gap-2.5 text-white font-semibold text-base pb-3 border-b border-slate-800">
                <Shield className="w-5 h-5 text-purple-400" />
                <h2>System Notifications</h2>
              </div>
              <p className="text-xs text-slate-400">
                Operational and security health alerts for administrators.
              </p>

              <div className="space-y-4 pt-2">
                {/* Security Notifications */}
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="space-y-0.5">
                    <label className="text-xs font-medium text-slate-200 block cursor-pointer">
                      Administrative / Security Alerts
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Flags authentication anomalies and role authorization events.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.system_security_alerts_enabled}
                    onClick={() => handleToggle('system_security_alerts_enabled')}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      settings.system_security_alerts_enabled ? 'bg-teal-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        settings.system_security_alerts_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                {/* System Operational Alerts */}
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="space-y-0.5">
                    <label className="text-xs font-medium text-slate-200 block cursor-pointer">
                      Operational Health Alerts
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Dispatches alerts on database latency or subsystem errors.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.system_operational_alerts_enabled}
                    onClick={() => handleToggle('system_operational_alerts_enabled')}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      settings.system_operational_alerts_enabled ? 'bg-teal-500' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        settings.system_operational_alerts_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                {/* Audit and Metadata Information */}
                {metadata.updated_at && (
                  <div className="p-3 bg-purple-500/5 rounded-xl border border-purple-500/10 space-y-1">
                    <div className="flex items-center gap-1.5 text-[11px] text-purple-300 font-semibold">
                      <Clock className="w-3.5 h-3.5" />
                      <span>Last Persistent Update</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      {formatTimestamp(metadata.updated_at)}
                    </p>
                    {metadata.updated_by && (
                      <p className="text-[10px] text-slate-500 truncate">
                        By: {metadata.updated_by}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-xs text-slate-400">
            Changes saved here are committed to PostgreSQL and take effect immediately across all client sessions.
          </div>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button
              type="button"
              onClick={handleResetToDefaults}
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors flex-1 sm:flex-initial"
            >
              <RotateCcw className="w-4 h-4" />
              Reset Defaults
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold shadow-lg shadow-teal-500/20 disabled:opacity-50 transition-all flex-1 sm:flex-initial"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Configuration
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default NotificationSettings;
