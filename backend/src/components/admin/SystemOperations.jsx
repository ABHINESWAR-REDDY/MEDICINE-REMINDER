import React, { useState, useEffect } from 'react';
import { adminService } from '../../api/adminService';
import {
  Activity,
  Database,
  Server,
  Bell,
  MessageSquare,
  ShieldCheck,
  RefreshCw,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Play,
  RotateCw,
  Sparkles,
  ClipboardCheck,
} from 'lucide-react';

export const SystemOperations = () => {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Operation state
  const [operating, setOperating] = useState(null);
  const [operationResult, setOperationResult] = useState(null);
  const [operationError, setOperationError] = useState(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminService.getSystemHealth();
      setHealth(data);
    } catch (err) {
      const errorMsg =
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        err.message ||
        'Failed to fetch system health status.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const handleRunOperation = async (opType, apiCall) => {
    setOperating(opType);
    setOperationResult(null);
    setOperationError(null);
    try {
      const res = await apiCall();
      setOperationResult(res);
      fetchHealth(); // refresh health after operation
    } catch (err) {
      const errorMsg =
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        err.message ||
        'Operation execution failed.';
      setOperationError(errorMsg);
    } finally {
      setOperating(null);
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || 'ERROR').toUpperCase();
    if (s === 'HEALTHY' || s === 'CONNECTED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" /> Healthy
        </span>
      );
    } else if (s === 'DEGRADED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-3 h-3" /> Degraded
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <XCircle className="w-3 h-3" /> Error
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">System Operations</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">
              Live Health & Controls
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Monitor real-time subsystem connectivity and execute safe administrative reconciliation tasks.
          </p>
        </div>

        <button
          onClick={fetchHealth}
          disabled={loading || operating !== null}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Run Health Diagnostics
        </button>
      </div>

      {/* Operation Feedback Banners */}
      {operationResult && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-start justify-between gap-3 text-emerald-400 text-sm">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold">{operationResult.message}</div>
              {operationResult.details?.issues && operationResult.details.issues.length > 0 && (
                <ul className="mt-1 list-disc list-inside text-xs text-emerald-300">
                  {operationResult.details.issues.map((iss, i) => (
                    <li key={i}>{iss}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <button
            onClick={() => setOperationResult(null)}
            className="text-xs font-bold text-emerald-400 hover:text-emerald-300"
          >
            Dismiss
          </button>
        </div>
      )}

      {operationError && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl flex items-center justify-between gap-3 text-rose-400 text-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span>{operationError}</span>
          </div>
          <button
            onClick={() => setOperationError(null)}
            className="text-xs font-bold text-rose-400 hover:text-rose-300"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 1. System Health Diagnostics Grid */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Subsystem Health Diagnostics
        </h2>

        {loading && !health ? (
          <div className="flex items-center justify-center min-h-[250px] bg-slate-900/40 border border-slate-800/80 rounded-2xl">
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
              <p className="text-slate-400 text-sm">Pinging subsystems & measuring latencies...</p>
            </div>
          </div>
        ) : error ? (
          <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 space-y-3">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="w-5 h-5" />
              <span>{error}</span>
            </div>
            <button
              onClick={fetchHealth}
              className="px-4 py-2 bg-rose-500/20 hover:bg-rose-500/30 rounded-xl text-xs font-semibold text-rose-300"
            >
              Retry Check
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Database Component */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-semibold text-sm">
                  <Database className="w-4 h-4 text-blue-400" />
                  <span>Database Engine</span>
                </div>
                {getStatusBadge(health?.components?.database?.status)}
              </div>
              <p className="text-xs text-slate-300">
                {health?.components?.database?.message || 'PostgreSQL database connection.'}
              </p>
              {health?.components?.database?.latency_ms !== undefined && (
                <div className="text-[11px] text-slate-500 font-mono">
                  Latency: {health.components.database.latency_ms} ms
                </div>
              )}
            </div>

            {/* Backend API Component */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-semibold text-sm">
                  <Server className="w-4 h-4 text-teal-400" />
                  <span>Backend REST API</span>
                </div>
                {getStatusBadge(health?.components?.backend_api?.status)}
              </div>
              <p className="text-xs text-slate-300">
                {health?.components?.backend_api?.message || 'FastAPI worker processes.'}
              </p>
              {health?.components?.backend_api?.latency_ms !== undefined && (
                <div className="text-[11px] text-slate-500 font-mono">
                  Latency: {health.components.backend_api.latency_ms} ms
                </div>
              )}
            </div>

            {/* Notification Subsystem */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-semibold text-sm">
                  <Bell className="w-4 h-4 text-amber-400" />
                  <span>Notification Engine</span>
                </div>
                {getStatusBadge(health?.components?.notifications?.status)}
              </div>
              <p className="text-xs text-slate-300">
                {health?.components?.notifications?.message || 'Alert queue and dispatch.'}
              </p>
              {health?.components?.notifications?.details?.unread_count !== undefined && (
                <div className="text-[11px] text-slate-500">
                  Unread Alerts: {health.components.notifications.details.unread_count}
                </div>
              )}
            </div>

            {/* Direct Messaging Subsystem */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-semibold text-sm">
                  <MessageSquare className="w-4 h-4 text-purple-400" />
                  <span>Direct Messaging</span>
                </div>
                {getStatusBadge(health?.components?.chat?.status)}
              </div>
              <p className="text-xs text-slate-300">
                {health?.components?.chat?.message || 'Chat messages and conversations.'}
              </p>
            </div>

            {/* Authentication Subsystem */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-3 sm:col-span-2 lg:col-span-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-semibold text-sm">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Authentication & RBAC Security</span>
                </div>
                {getStatusBadge(health?.components?.authentication?.status)}
              </div>
              <p className="text-xs text-slate-300">
                {health?.components?.authentication?.message || 'JWT signing and role-based access controls.'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 2. Safe Administrative Operations Panel */}
      <div className="space-y-3 pt-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Safe Administrative Operations
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Operation 1: Reconcile Overdue Doses */}
          <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-white font-semibold text-sm">
                <RotateCw className="w-4 h-4 text-teal-400" />
                <h3>Reconcile Overdue Doses</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Scans all active medication doses across the platform and transitions past overdue scheduled doses to MISSED status idempotently.
              </p>
            </div>

            <button
              onClick={() => handleRunOperation('reconcile_doses', adminService.reconcileDoses)}
              disabled={operating !== null}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold shadow-lg shadow-teal-500/20 disabled:opacity-50 transition-all"
            >
              {operating === 'reconcile_doses' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Run Dose Reconciliation
            </button>
          </div>

          {/* Operation 2: Reconcile Notifications */}
          <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-white font-semibold text-sm">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <h3>Refresh Notification State</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Triggers proactive reminder and refill alert calculations across all active patient accounts according to current platform rules.
              </p>
            </div>

            <button
              onClick={() => handleRunOperation('reconcile_notifs', adminService.reconcileNotifications)}
              disabled={operating !== null}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold disabled:opacity-50 transition-all"
            >
              {operating === 'reconcile_notifs' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Refresh Notifications
            </button>
          </div>

          {/* Operation 3: Data Consistency Check */}
          <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-white font-semibold text-sm">
                <ClipboardCheck className="w-4 h-4 text-purple-400" />
                <h3>Run Consistency Check</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Executes read-only diagnostic validation across patient schedules, dosage templates, and caregiver assignment records.
              </p>
            </div>

            <button
              onClick={() => handleRunOperation('consistency_check', adminService.runConsistencyCheck)}
              disabled={operating !== null}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/20 disabled:opacity-50 transition-all"
            >
              {operating === 'consistency_check' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Run Diagnostic Scan
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemOperations;
