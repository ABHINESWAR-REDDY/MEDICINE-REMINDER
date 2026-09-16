import React, { useState, useEffect, useCallback } from 'react';
import { adminService } from '../../api/adminService';
import {
  BarChart3,
  TrendingUp,
  Users,
  Pill,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Loader2,
  Calendar,
  FileText,
  MessageSquare,
  Bell,
  Activity,
  ShieldCheck,
  Percent,
} from 'lucide-react';

export const PlatformAnalytics = () => {
  const [period, setPeriod] = useState('30d');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [showCustomModal, setShowCustomModal] = useState(false);

  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { period };
      if (period === 'custom' && customStart) {
        params.start_date = new Date(customStart).toISOString();
        if (customEnd) {
          params.end_date = new Date(customEnd).toISOString();
        }
      }
      const data = await adminService.getPlatformAnalytics(params);
      setAnalytics(data);
    } catch (err) {
      const errorMsg =
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        err.message ||
        'Failed to load platform analytics.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [period, customStart, customEnd]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const handlePeriodChange = (newPeriod) => {
    if (newPeriod === 'custom') {
      setShowCustomModal(true);
    } else {
      setPeriod(newPeriod);
    }
  };

  const handleApplyCustomDates = (e) => {
    e.preventDefault();
    if (customStart) {
      setPeriod('custom');
      setShowCustomModal(false);
    }
  };

  // Safe percentage helper preventing NaN or value || 100 bugs
  const formatPercent = (val) => {
    if (val === null || val === undefined || isNaN(val)) return '0.0%';
    return `${Number(val).toFixed(1)}%`;
  };

  const hasAnyData =
    analytics &&
    (analytics.users?.total_patients > 0 ||
      analytics.users?.total_caregivers > 0 ||
      analytics.medications?.total_active_medications > 0 ||
      analytics.medications?.scheduled_doses_in_period > 0 ||
      analytics.prescriptions?.total_prescriptions > 0 ||
      analytics.notifications?.total_notifications > 0 ||
      analytics.chat?.total_messages > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Platform Analytics</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">
              Live Database Aggregation
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            System-level clinical adherence patterns, medication tracking volume, caregiver supervision, and operational trends.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Period Selector Tabs */}
          <div className="inline-flex rounded-xl bg-slate-900 border border-slate-800 p-1">
            <button
              onClick={() => handlePeriodChange('today')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                period === 'today'
                  ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Today
            </button>
            <button
              onClick={() => handlePeriodChange('7d')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                period === '7d'
                  ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              7 Days
            </button>
            <button
              onClick={() => handlePeriodChange('30d')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                period === '30d'
                  ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              30 Days
            </button>
            <button
              onClick={() => handlePeriodChange('90d')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                period === '90d'
                  ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              90 Days
            </button>
            <button
              onClick={() => handlePeriodChange('custom')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                period === 'custom'
                  ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Custom
            </button>
          </div>

          <button
            onClick={fetchAnalytics}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Custom Date Filter Modal */}
      {showCustomModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">Select Custom Date Range</h3>
            <form onSubmit={handleApplyCustomDates} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Start Date</label>
                <input
                  type="date"
                  required
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-teal-500"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">End Date</label>
                <input
                  type="date"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-teal-500"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCustomModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-xl font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white text-xs rounded-xl font-semibold"
                >
                  Apply Filter
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Content Rendering */}
      {loading && !analytics ? (
        <div className="flex items-center justify-center min-h-[400px] bg-slate-900/40 border border-slate-800/80 rounded-2xl">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
            <p className="text-slate-400 text-sm">Aggregating platform database metrics...</p>
          </div>
        </div>
      ) : error ? (
        <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 space-y-3">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="w-5 h-5" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchAnalytics}
            className="px-4 py-2 bg-rose-500/20 hover:bg-rose-500/30 rounded-xl text-xs font-semibold text-rose-300 transition-colors"
          >
            Try Again
          </button>
        </div>
      ) : !hasAnyData ? (
        <div className="p-12 text-center bg-slate-900/40 border border-slate-800/80 rounded-2xl space-y-3">
          <BarChart3 className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-300">No analytics data available for the selected period.</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Zero activity or medication events match the chosen date range. Choose a wider date range or log clinical actions to view live analytics.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Top Level KPI Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Overall Platform Adherence */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Platform Adherence</span>
                <TrendingUp className="w-5 h-5 text-teal-400" />
              </div>
              <div className="mt-3 text-3xl font-extrabold text-white">
                {formatPercent(analytics.adherence?.overall_adherence_percentage)}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                Taken / (Taken + Missed) in period
              </div>
            </div>

            {/* Total Patients */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Total Patients</span>
                <Users className="w-5 h-5 text-blue-400" />
              </div>
              <div className="mt-3 text-3xl font-extrabold text-white">
                {analytics.users?.total_patients ?? 0}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {analytics.users?.new_patients_in_period ?? 0} new in period ({analytics.users?.active_patients ?? 0} active)
              </div>
            </div>

            {/* Total Caregivers */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Caregiver Network</span>
                <ShieldCheck className="w-5 h-5 text-purple-400" />
              </div>
              <div className="mt-3 text-3xl font-extrabold text-white">
                {analytics.users?.total_caregivers ?? 0}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {analytics.users?.active_caregivers ?? 0} active, {analytics.users?.pending_caregivers ?? 0} pending review
              </div>
            </div>

            {/* Active Medications Tracked */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Active Medications</span>
                <Pill className="w-5 h-5 text-emerald-400" />
              </div>
              <div className="mt-3 text-3xl font-extrabold text-white">
                {analytics.medications?.total_active_medications ?? 0}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {analytics.medications?.total_tracked_medications ?? 0} total created
              </div>
            </div>
          </div>

          {/* Section 1: Adherence & Medication Intake Details */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Dose Status Distribution */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <Activity className="w-5 h-5 text-teal-400" />
                  <h2>Dose Intake Breakdown</h2>
                </div>
                <span className="text-xs text-slate-400">
                  Total in period: <strong className="text-white">{analytics.medications?.scheduled_doses_in_period ?? 0}</strong>
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-center">
                  <div className="text-xs font-medium text-emerald-400 uppercase">Taken</div>
                  <div className="text-2xl font-bold text-white mt-1">
                    {analytics.medications?.taken_doses ?? 0}
                  </div>
                </div>
                <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-center">
                  <div className="text-xs font-medium text-rose-400 uppercase">Missed</div>
                  <div className="text-2xl font-bold text-white mt-1">
                    {analytics.medications?.missed_doses ?? 0}
                  </div>
                </div>
                <div className="p-3.5 bg-amber-500/10 border border-amber-500/20 rounded-xl text-center">
                  <div className="text-xs font-medium text-amber-400 uppercase">Skipped</div>
                  <div className="text-2xl font-bold text-white mt-1">
                    {analytics.medications?.skipped_doses ?? 0}
                  </div>
                </div>
              </div>

              {/* Visual Proportion Bar */}
              {(() => {
                const taken = analytics.medications?.taken_doses ?? 0;
                const missed = analytics.medications?.missed_doses ?? 0;
                const skipped = analytics.medications?.skipped_doses ?? 0;
                const totalDoses = taken + missed + skipped;
                if (totalDoses === 0) return null;

                const takenPct = ((taken / totalDoses) * 100).toFixed(1);
                const missedPct = ((missed / totalDoses) * 100).toFixed(1);
                const skippedPct = ((skipped / totalDoses) * 100).toFixed(1);

                return (
                  <div className="space-y-1.5 pt-2">
                    <div className="h-3 w-full bg-slate-950 rounded-full overflow-hidden flex">
                      <div style={{ width: `${takenPct}%` }} className="bg-emerald-500 transition-all" title={`Taken: ${takenPct}%`} />
                      <div style={{ width: `${missedPct}%` }} className="bg-rose-500 transition-all" title={`Missed: ${missedPct}%`} />
                      <div style={{ width: `${skippedPct}%` }} className="bg-amber-500 transition-all" title={`Skipped: ${skippedPct}%`} />
                    </div>
                    <div className="flex justify-between text-[11px] text-slate-500">
                      <span>Taken ({takenPct}%)</span>
                      <span>Missed ({missedPct}%)</span>
                      <span>Skipped ({skippedPct}%)</span>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Patient Adherence Risk Cohorts */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <Percent className="w-5 h-5 text-purple-400" />
                  <h2>Patient Adherence Cohorts</h2>
                </div>
                <span className="text-xs text-slate-400">Risk Segmentation</span>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                    <div>
                      <div className="text-xs font-semibold text-white">Good Adherence (≥ 80%)</div>
                      <div className="text-[11px] text-slate-400">Patients on track with prescribed schedule</div>
                    </div>
                  </div>
                  <span className="text-lg font-bold text-emerald-400">
                    {analytics.adherence?.good_adherence_patients ?? 0}
                  </span>
                </div>

                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                    <div>
                      <div className="text-xs font-semibold text-white">Needs Attention (50% - 79%)</div>
                      <div className="text-[11px] text-slate-400">Moderate adherence risk requiring reminder follow-up</div>
                    </div>
                  </div>
                  <span className="text-lg font-bold text-amber-400">
                    {analytics.adherence?.needs_attention_patients ?? 0}
                  </span>
                </div>

                <div className="flex items-center justify-between p-3 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-400" />
                    <div>
                      <div className="text-xs font-semibold text-white">High Risk (&lt; 50%)</div>
                      <div className="text-[11px] text-slate-400">Severe risk of treatment failure</div>
                    </div>
                  </div>
                  <span className="text-lg font-bold text-rose-400">
                    {analytics.adherence?.high_risk_patients ?? 0}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Caregivers & Supervision Network */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Caregiver Network */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
              <div className="flex items-center gap-2 text-white font-semibold pb-3 border-b border-slate-800">
                <Users className="w-5 h-5 text-teal-400" />
                <h2>Caregiver Supervision</h2>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Active Patient Assignments:</span>
                  <span className="font-bold text-white">{analytics.caregivers?.active_assignments ?? 0}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Caregivers with Patients:</span>
                  <span className="font-bold text-white">{analytics.caregivers?.caregivers_with_assignments ?? 0}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Unassigned Active Patients:</span>
                  <span className="font-bold text-amber-400">{analytics.caregivers?.unassigned_patients ?? 0}</span>
                </div>
              </div>
            </div>

            {/* OCR & Prescriptions */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
              <div className="flex items-center gap-2 text-white font-semibold pb-3 border-b border-slate-800">
                <FileText className="w-5 h-5 text-blue-400" />
                <h2>Prescriptions & OCR</h2>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Prescriptions Uploaded:</span>
                  <span className="font-bold text-white">{analytics.prescriptions?.total_prescriptions ?? 0}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">OCR Jobs Queued:</span>
                  <span className="font-bold text-white">{analytics.prescriptions?.total_ocr_jobs ?? 0}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Successful Extractions:</span>
                  <span className="font-bold text-emerald-400">{analytics.prescriptions?.successful_extractions ?? 0}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Failed Extractions:</span>
                  <span className="font-bold text-rose-400">{analytics.prescriptions?.failed_extractions ?? 0}</span>
                </div>
              </div>
            </div>

            {/* Notifications & Messaging */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
              <div className="flex items-center gap-2 text-white font-semibold pb-3 border-b border-slate-800">
                <Bell className="w-5 h-5 text-purple-400" />
                <h2>Alerts & Messaging</h2>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Total Notifications:</span>
                  <span className="font-bold text-white">{analytics.notifications?.total_notifications ?? 0}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Unread Alert Queue:</span>
                  <span className="font-bold text-amber-400">{analytics.notifications?.unread_notifications ?? 0}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Direct Chat Messages:</span>
                  <span className="font-bold text-white">{analytics.chat?.total_messages ?? 0}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Patient / Caregiver Messages:</span>
                  <span className="font-bold text-white">
                    {analytics.chat?.patient_messages ?? 0} / {analytics.chat?.caregiver_messages ?? 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlatformAnalytics;
