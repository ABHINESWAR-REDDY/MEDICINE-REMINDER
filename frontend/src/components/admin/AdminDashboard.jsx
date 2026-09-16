import React, { useState, useEffect } from 'react';
import { adminService } from '../../api/adminService';
import {
  Users,
  UserCheck,
  Clock,
  ShieldCheck,
  Pill,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react';

export const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const statsData = await adminService.getDashboard();
      setStats(statsData);
    } catch (err) {
      const errorMsg =
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        err.message ||
        'Failed to load system dashboard.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
          <p className="text-slate-400 text-sm">Loading system metrics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400">
        <p className="font-semibold">{error}</p>
        <button
          onClick={fetchDashboardData}
          className="mt-3 px-4 py-2 bg-rose-500/20 rounded-xl text-xs font-semibold hover:bg-rose-500/30"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System Administration</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time multi-role governance, caregiver approvals, and platform health.
          </p>
        </div>
        <button
          onClick={fetchDashboardData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Metrics
        </button>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Total Patients</span>
            <Users className="w-5 h-5 text-teal-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-white">{stats?.total_patients || 0}</div>
          <div className="mt-1 text-xs text-slate-400">Registered patient accounts</div>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Total Caregivers</span>
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-white">{stats?.total_caregivers || 0}</div>
          <div className="mt-1 text-xs text-slate-400">
            {stats?.active_caregivers || 0} active · {stats?.inactive_caregivers || 0} inactive
          </div>
        </div>

        <div className="p-5 bg-slate-900/60 border border-amber-500/20 rounded-2xl relative overflow-hidden bg-amber-500/5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-amber-400 tracking-wider">Pending Approvals</span>
            <Clock className="w-5 h-5 text-amber-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-amber-300">{stats?.pending_caregivers || 0}</div>
          <div className="mt-1 text-xs text-amber-400/80">Require administrative review</div>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Active Assignments</span>
            <UserCheck className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-white">{stats?.active_assignments || 0}</div>
          <div className="mt-1 text-xs text-slate-400">Caregiver-patient links</div>
        </div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-teal-500/10 flex items-center justify-center text-teal-400">
            <Pill className="w-5 h-5" />
          </div>
          <div>
            <div className="text-lg font-bold text-white">{stats?.total_medicines || 0}</div>
            <div className="text-xs text-slate-400">Tracked Medications</div>
          </div>
        </div>

        <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <div className="text-lg font-bold text-white">{stats?.today_doses_taken || 0}</div>
            <div className="text-xs text-slate-400">Doses Taken Today</div>
          </div>
        </div>

        <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400">
            <XCircle className="w-5 h-5" />
          </div>
          <div>
            <div className="text-lg font-bold text-white">{stats?.today_doses_missed || 0}</div>
            <div className="text-xs text-slate-400">Doses Missed Today</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
