import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart3,
  Users,
  Search,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Pill,
  ChevronRight,
  TrendingUp,
  Package,
  Calendar,
  X,
  ShieldAlert,
  UserCheck,
  FileText,
} from 'lucide-react';
import caregiverService from '../../api/caregiverService';

const PERIOD_OPTIONS = [
  { days: 1, label: 'Today (24h)' },
  { days: 7, label: 'Last 7 Days' },
  { days: 30, label: 'Last 30 Days' },
  { days: 90, label: 'Last 90 Days' },
];

export const CaregiverAdherenceReports = () => {
  const [selectedPeriod, setSelectedPeriod] = useState(30);
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL' | 'GOOD' | 'NEEDS_ATTENTION' | 'HIGH_RISK'

  // Patient Detail Modal State
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [patientDetail, setPatientDetail] = useState(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');

  const loadReports = async (days = selectedPeriod) => {
    setIsLoading(true);
    setError('');
    try {
      const res = await caregiverService.getAdherenceReports(days);
      setData(res);
    } catch (err) {
      console.error('Failed to load caregiver adherence reports:', err);
      setError(
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        'Unable to load adherence reports from database. Please verify your connection.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReports(selectedPeriod);
  }, [selectedPeriod]);

  const loadPatientDetail = async (patientId, days = selectedPeriod) => {
    setSelectedPatientId(patientId);
    setIsDetailLoading(true);
    setDetailError('');
    try {
      const res = await caregiverService.getPatientAdherenceReport(patientId, days);
      setPatientDetail(res);
    } catch (err) {
      console.error('Failed to load patient adherence detail:', err);
      setDetailError(
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        'Unable to load detailed patient adherence report.'
      );
    } finally {
      setIsDetailLoading(false);
    }
  };

  const closePatientDetail = () => {
    setSelectedPatientId(null);
    setPatientDetail(null);
    setDetailError('');
  };

  const reports = data?.reports || [];

  const filteredReports = reports.filter((item) => {
    // Status category filter
    if (statusFilter === 'GOOD' && item.adherence_status !== 'Good') return false;
    if (statusFilter === 'NEEDS_ATTENTION' && item.adherence_status !== 'Needs Attention') return false;
    if (statusFilter === 'HIGH_RISK' && item.adherence_status !== 'High Risk') return false;

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const name = (item.name || '').toLowerCase();
      const email = (item.email || '').toLowerCase();
      const empId = (item.employee_id || '').toLowerCase();
      return name.includes(q) || email.includes(q) || empId.includes(q);
    }
    return true;
  });

  const getAdherenceBadge = (status, percentage) => {
    if (status === 'Good') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5" />
          {percentage}% — Good
        </span>
      );
    }
    if (status === 'Needs Attention') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
          <AlertTriangle className="w-3.5 h-3.5" />
          {percentage}% — Needs Attention
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
        <XCircle className="w-3.5 h-3.5" />
        {percentage}% — High Risk
      </span>
    );
  };

  const formatDate = (isoString) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6 w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <BarChart3 className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Patient Adherence Reports</h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Clinical adherence metrics, dosage intake compliance, and real-time refill tracking for your assigned patients
          </p>
        </div>

        {/* Date Filter & Refresh */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-1 flex items-center gap-1">
            {PERIOD_OPTIONS.map((opt) => {
              const isSelected = selectedPeriod === opt.days;
              return (
                <button
                  key={opt.days}
                  type="button"
                  onClick={() => setSelectedPeriod(opt.days)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    isSelected
                      ? 'bg-teal-500 text-slate-950 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={() => loadReports(selectedPeriod)}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl border border-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* KPI Overview Summary */}
      {!isLoading && data && data.total_assigned_patients > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-white">{data.total_assigned_patients}</div>
              <div className="text-xs text-slate-400 font-medium">Assigned Patients Monitored</div>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-teal-400">{data.overall_adherence_percentage}%</div>
              <div className="text-xs text-slate-400 font-medium">Overall Group Adherence</div>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-emerald-400">{data.good_standing_count}</div>
              <div className="text-xs text-slate-400 font-medium">Good Standing (≥ 90%)</div>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-rose-400">{data.high_risk_count}</div>
              <div className="text-xs text-slate-400 font-medium">High Risk Patients (&lt; 75%)</div>
            </div>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-slate-900/60 border border-slate-800 rounded-2xl p-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-thin">
          <button
            type="button"
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
              statusFilter === 'ALL'
                ? 'bg-blue-500/15 text-blue-300 border border-blue-500/30 font-semibold'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
            }`}
          >
            All Patients ({reports.length})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('HIGH_RISK')}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
              statusFilter === 'HIGH_RISK'
                ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30 font-semibold'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
            }`}
          >
            High Risk (&lt; 75%)
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('NEEDS_ATTENTION')}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
              statusFilter === 'NEEDS_ATTENTION'
                ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
            }`}
          >
            Needs Attention (75–89%)
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('GOOD')}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
              statusFilter === 'GOOD'
                ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
            }`}
          >
            Good Standing (≥ 90%)
          </button>
        </div>

        <div className="relative min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search patient by name, ID, email..."
            className="w-full pl-9 pr-4 py-1.5 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-colors"
          />
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div role="alert" className="p-4 rounded-2xl text-xs flex items-center justify-between bg-rose-500/10 border border-rose-500/20 text-rose-300">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => loadReports(selectedPeriod)}
            className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 rounded-lg text-xs font-semibold transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Main Reports Table */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-3">
          <Loader2 className="w-7 h-7 animate-spin text-teal-400" />
          <p className="text-xs text-slate-400">Aggregating live adherence metrics for assigned patients...</p>
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto text-blue-400">
            <Users className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-white">No patients are currently assigned to you.</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Once an administrator assigns patients to your caregiver account, their real-time adherence and medication reports will appear here.
            </p>
          </div>
          <div className="pt-2">
            <Link
              to="/caregiver/dashboard"
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl border border-slate-700 transition-colors"
            >
              <span>Back to Dashboard</span>
            </Link>
          </div>
        </div>
      ) : filteredReports.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center space-y-2">
          <p className="text-sm font-medium text-slate-300">No matching patient adherence records found.</p>
          <p className="text-xs text-slate-500">
            Try adjusting your search criteria or switching the adherence category tab.
          </p>
        </div>
      ) : (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
            <div className="text-xs font-semibold text-slate-300">
              Assigned Patients Adherence Compliance — {PERIOD_OPTIONS.find((o) => o.days === selectedPeriod)?.label}
            </div>
            <span className="text-[11px] text-slate-500 font-medium">Real-time database analytics</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/40 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Patient</th>
                  <th className="py-3.5 px-4">Adherence Rate</th>
                  <th className="py-3.5 px-4">Compliance Status</th>
                  <th className="py-3.5 px-4 text-center">Taken</th>
                  <th className="py-3.5 px-4 text-center">Missed</th>
                  <th className="py-3.5 px-4 text-center">Skipped</th>
                  <th className="py-3.5 px-4 text-center">Active Meds</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs text-slate-300">
                {filteredReports.map((patient) => {
                  return (
                    <tr
                      key={patient.patient_id}
                      className="hover:bg-slate-800/30 transition-colors group"
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-xs">
                            {patient.name.charAt(0)}
                          </div>
                          <div>
                            <div className="font-semibold text-white group-hover:text-blue-300 transition-colors">
                              {patient.name}
                            </div>
                            <div className="text-[11px] text-slate-400 font-mono">
                              {patient.employee_id} • {patient.email}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="space-y-1 min-w-[120px]">
                          <div className="flex items-center justify-between text-xs font-mono font-bold">
                            <span className="text-white">{patient.adherence_percentage}%</span>
                            <span className="text-slate-500 font-normal text-[10px]">
                              {patient.taken_count}/{patient.total_expected_doses}
                            </span>
                          </div>
                          <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
                            <div
                              className={`h-full rounded-full transition-all ${
                                patient.adherence_percentage >= 90
                                  ? 'bg-emerald-400'
                                  : patient.adherence_percentage >= 75
                                  ? 'bg-amber-400'
                                  : 'bg-rose-500'
                              }`}
                              style={{ width: `${patient.adherence_percentage}%` }}
                            />
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {getAdherenceBadge(patient.adherence_status, patient.adherence_percentage)}
                      </td>

                      <td className="py-3.5 px-4 text-center font-mono font-bold text-emerald-400">
                        {patient.taken_count}
                      </td>

                      <td className="py-3.5 px-4 text-center font-mono font-bold text-rose-400">
                        {patient.missed_count}
                      </td>

                      <td className="py-3.5 px-4 text-center font-mono font-bold text-amber-400">
                        {patient.skipped_count}
                      </td>

                      <td className="py-3.5 px-4 text-center font-mono text-slate-200">
                        {patient.active_medications_count}
                      </td>

                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => loadPatientDetail(patient.patient_id, selectedPeriod)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 font-semibold text-xs transition-colors border border-teal-500/20"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>View Detailed Report</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Patient Adherence Deep-Dive Modal */}
      {selectedPatientId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6 space-y-6 shadow-2xl my-8">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
                  <BarChart3 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">
                    {patientDetail?.patient?.name || 'Patient Adherence Report'}
                  </h3>
                  <p className="text-xs text-slate-400">
                    Comprehensive compliance log, medication-wise analytics, and refill predictions
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={closePatientDetail}
                className="text-slate-400 hover:text-slate-200 p-1.5 rounded-xl hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {isDetailLoading ? (
              <div className="py-20 text-center space-y-3">
                <Loader2 className="w-8 h-8 text-teal-400 animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Loading patient report details from database...</p>
              </div>
            ) : detailError ? (
              <div role="alert" className="p-4 rounded-xl text-xs bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-center justify-between">
                <span>{detailError}</span>
                <button
                  type="button"
                  onClick={() => loadPatientDetail(selectedPatientId, selectedPeriod)}
                  className="px-3 py-1 bg-rose-500/20 text-rose-200 rounded-lg text-xs font-semibold"
                >
                  Retry
                </button>
              </div>
            ) : patientDetail ? (
              <div className="space-y-6">
                {/* Patient Summary Card */}
                <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-base">{patientDetail.patient.name}</span>
                      <span className="font-mono text-xs text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded border border-teal-500/20">
                        {patientDetail.patient.employee_id}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      <span>{patientDetail.patient.email}</span>
                      <span className="mx-2">•</span>
                      <span>Account Created: {formatDate(patientDetail.patient.account_created_at)}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-xs text-slate-400">Window Compliance</div>
                      <div className="text-xl font-bold font-mono text-white">
                        {patientDetail.adherence_summary.adherence_percentage}%
                      </div>
                    </div>
                    {getAdherenceBadge(
                      patientDetail.adherence_summary.adherence_status,
                      patientDetail.adherence_summary.adherence_percentage
                    )}
                  </div>
                </div>

                {/* Dosage Counts Breakdown */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Total Expected</div>
                    <div className="text-lg font-bold text-white font-mono mt-0.5">
                      {patientDetail.adherence_summary.total_expected_doses}
                    </div>
                  </div>
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
                    <div className="text-[10px] text-emerald-400 uppercase font-semibold">Taken Doses</div>
                    <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">
                      {patientDetail.adherence_summary.taken_count}
                    </div>
                  </div>
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
                    <div className="text-[10px] text-rose-400 uppercase font-semibold">Missed Doses</div>
                    <div className="text-lg font-bold text-rose-400 font-mono mt-0.5">
                      {patientDetail.adherence_summary.missed_count}
                    </div>
                  </div>
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
                    <div className="text-[10px] text-amber-400 uppercase font-semibold">Skipped Doses</div>
                    <div className="text-lg font-bold text-amber-400 font-mono mt-0.5">
                      {patientDetail.adherence_summary.skipped_count}
                    </div>
                  </div>
                </div>

                {/* Medication-Specific Adherence Breakdown */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <Pill className="w-4 h-4 text-teal-400" />
                    <span>Medication-Specific Compliance & Refill Status</span>
                  </h4>

                  {patientDetail.medication_breakdown.length === 0 ? (
                    <div className="p-4 bg-slate-950/40 border border-slate-800 rounded-xl text-center text-xs text-slate-500">
                      No medication records found for this patient.
                    </div>
                  ) : (
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-slate-800 bg-slate-950 text-[10px] font-semibold text-slate-400 uppercase">
                            <th className="py-2.5 px-3">Medication</th>
                            <th className="py-2.5 px-3">Strength</th>
                            <th className="py-2.5 px-3 text-center">Taken / Expected</th>
                            <th className="py-2.5 px-3">Compliance %</th>
                            <th className="py-2.5 px-3">Stock / Refill Days</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50 text-slate-300">
                          {patientDetail.medication_breakdown.map((m) => (
                            <tr key={m.medicine_id} className="hover:bg-slate-800/20">
                              <td className="py-2.5 px-3 font-semibold text-white">{m.medicine_name}</td>
                              <td className="py-2.5 px-3 font-mono text-slate-400">
                                {m.strength} {m.unit}
                              </td>
                              <td className="py-2.5 px-3 text-center font-mono">
                                <span className="text-emerald-400 font-bold">{m.taken_count}</span> / {m.total_expected}
                              </td>
                              <td className="py-2.5 px-3 font-mono font-bold">
                                <span
                                  className={
                                    m.adherence_percentage >= 90
                                      ? 'text-emerald-400'
                                      : m.adherence_percentage >= 75
                                      ? 'text-amber-400'
                                      : 'text-rose-400'
                                  }
                                >
                                  {m.adherence_percentage}%
                                </span>
                              </td>
                              <td className="py-2.5 px-3 whitespace-nowrap">
                                {m.estimated_remaining_days !== null && m.estimated_remaining_days !== undefined ? (
                                  <span
                                    className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                                      m.estimated_remaining_days <= 3
                                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                        : m.estimated_remaining_days <= 7
                                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                        : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                    }`}
                                  >
                                    {m.estimated_remaining_days} days left ({m.current_stock} units)
                                  </span>
                                ) : (
                                  <span className="text-slate-500 text-[11px] italic">
                                    {m.refill_status || 'No refill data'}
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Recent Dose Intake Log */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-400" />
                    <span>Recent Intake History in Period (Last 50 doses)</span>
                  </h4>

                  {patientDetail.recent_dose_events.length === 0 ? (
                    <div className="p-4 bg-slate-950/40 border border-slate-800 rounded-xl text-center text-xs text-slate-500">
                      No dose activity recorded during this period.
                    </div>
                  ) : (
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl max-h-48 overflow-y-auto divide-y divide-slate-800/40">
                      {patientDetail.recent_dose_events.map((d) => (
                        <div key={d.id} className="p-2.5 flex items-center justify-between text-xs hover:bg-slate-800/20">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white">{d.medicine_name}</span>
                            <span className="text-slate-500 font-mono text-[11px]">
                              {formatDateTime(d.scheduled_time)}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            {d.status === 'TAKEN' && (
                              <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Taken {d.actual_time ? `(${formatDateTime(d.actual_time)})` : ''}
                              </span>
                            )}
                            {d.status === 'MISSED' && (
                              <span className="inline-flex items-center gap-1 text-rose-400 font-semibold text-[11px]">
                                <XCircle className="w-3.5 h-3.5" />
                                Missed
                              </span>
                            )}
                            {d.status === 'SKIPPED' && (
                              <span className="inline-flex items-center gap-1 text-amber-400 font-semibold text-[11px]">
                                <AlertTriangle className="w-3.5 h-3.5" />
                                Skipped
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};

export default CaregiverAdherenceReports;
