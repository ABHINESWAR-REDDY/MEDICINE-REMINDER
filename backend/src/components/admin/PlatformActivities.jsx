import React, { useState, useEffect, useCallback } from 'react';
import { adminService } from '../../api/adminService';
import {
  Activity,
  Search,
  Filter,
  RefreshCw,
  Loader2,
  Calendar,
  AlertCircle,
  Shield,
  User,
  Users,
  ChevronLeft,
  ChevronRight,
  Clock,
  Info,
} from 'lucide-react';

export const PlatformActivities = () => {
  const [activities, setActivities] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [targetTypeFilter, setTargetTypeFilter] = useState('');
  const [dateRange, setDateRange] = useState('ALL');

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);

  const calculateDateBounds = (range) => {
    const now = new Date();
    if (range === 'TODAY') {
      const start = new Date(now.setHours(0, 0, 0, 0)).toISOString();
      return { start_date: start, end_date: new Date().toISOString() };
    } else if (range === '7D') {
      const start = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
      return { start_date: start, end_date: new Date().toISOString() };
    } else if (range === '30D') {
      const start = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      return { start_date: start, end_date: new Date().toISOString() };
    }
    return { start_date: null, end_date: null };
  };

  const fetchActivities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { start_date, end_date } = calculateDateBounds(dateRange);
      const params = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
      };

      if (search.trim()) params.search = search.trim();
      if (roleFilter) params.role = roleFilter;
      if (actionFilter) params.action = actionFilter;
      if (targetTypeFilter) params.target_type = targetTypeFilter;
      if (start_date) params.start_date = start_date;
      if (end_date) params.end_date = end_date;

      const data = await adminService.getPlatformActivities(params);
      setActivities(data?.items || []);
      setTotal(data?.total || 0);
    } catch (err) {
      const errorMsg =
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        err.message ||
        'Failed to load platform activities.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, roleFilter, actionFilter, targetTypeFilter, dateRange]);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchActivities();
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  const getRoleBadge = (role) => {
    const r = (role || 'SYSTEM').toUpperCase();
    if (r === 'ADMIN') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
          <Shield className="w-3 h-3" /> Admin
        </span>
      );
    } else if (r === 'CAREGIVER') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">
          <Users className="w-3 h-3" /> Caregiver
        </span>
      );
    } else if (r === 'PATIENT') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
          <User className="w-3 h-3" /> Patient
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-700/50 text-slate-300 border border-slate-600/30">
        System
      </span>
    );
  };

  const getActionBadge = (action) => {
    const act = (action || '').toUpperCase();
    let colorClass = 'bg-slate-800 text-slate-300 border-slate-700';

    if (act.includes('APPROV') || act.includes('TAKEN') || act.includes('ACTIVAT') || act.includes('CREATED')) {
      colorClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    } else if (act.includes('REJECT') || act.includes('DEACTIVAT') || act.includes('DELET') || act.includes('REVOK')) {
      colorClass = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
    } else if (act.includes('MISSED') || act.includes('SKIPPED') || act.includes('WARNING')) {
      colorClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    } else if (act.includes('ASSIGN') || act.includes('UPDATE') || act.includes('RECONCILE')) {
      colorClass = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
    }

    return (
      <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-mono font-medium border ${colorClass}`}>
        {action}
      </span>
    );
  };

  const formatTimestamp = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Platform Activities</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">
              Live Audit Log
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time audit trail of administrative actions, medication changes, dose tracking, and clinical events.
          </p>
        </div>
        <button
          onClick={() => {
            setPage(1);
            fetchActivities();
          }}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by actor name, email, action, or target..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2.5 bg-teal-600 hover:bg-teal-500 text-white rounded-xl text-xs font-semibold transition-colors"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-800/60">
          {/* Role Filter */}
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <span>Role:</span>
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-950/60 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="">All Roles</option>
              <option value="ADMIN">Admin</option>
              <option value="CAREGIVER">Caregiver</option>
              <option value="PATIENT">Patient</option>
              <option value="SYSTEM">System</option>
            </select>
          </div>

          {/* Date Range Filter */}
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <span>Date Range:</span>
            <select
              value={dateRange}
              onChange={(e) => {
                setDateRange(e.target.value);
                setPage(1);
              }}
              className="bg-slate-950/60 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="ALL">All Time</option>
              <option value="TODAY">Today</option>
              <option value="7D">Last 7 Days</option>
              <option value="30D">Last 30 Days</option>
            </select>
          </div>

          {/* Target Type Filter */}
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>Target:</span>
            <select
              value={targetTypeFilter}
              onChange={(e) => {
                setTargetTypeFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-950/60 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="">All Targets</option>
              <option value="User">User</option>
              <option value="Medicine">Medicine</option>
              <option value="MedicationDose">MedicationDose</option>
              <option value="Prescription">Prescription</option>
              <option value="CaregiverPatientAssignment">Assignment</option>
              <option value="ChatMessage">ChatMessage</option>
              <option value="SystemSetting">SystemSetting</option>
            </select>
          </div>

          {/* Active filter clear */}
          {(search || roleFilter || targetTypeFilter || dateRange !== 'ALL') && (
            <button
              onClick={() => {
                setSearch('');
                setRoleFilter('');
                setActionFilter('');
                setTargetTypeFilter('');
                setDateRange('ALL');
                setPage(1);
              }}
              className="text-xs text-teal-400 hover:text-teal-300 underline ml-auto"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Content State Handling */}
      {loading && activities.length === 0 ? (
        <div className="flex items-center justify-center min-h-[350px] bg-slate-900/40 border border-slate-800/80 rounded-2xl">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
            <p className="text-slate-400 text-sm">Loading real-time platform activities...</p>
          </div>
        </div>
      ) : error ? (
        <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 space-y-3">
          <div className="flex items-center gap-2 font-semibold">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchActivities}
            className="px-4 py-2 bg-rose-500/20 hover:bg-rose-500/30 rounded-xl text-xs font-semibold text-rose-300 transition-colors"
          >
            Try Again
          </button>
        </div>
      ) : activities.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/40 border border-slate-800/80 rounded-2xl space-y-3">
          <Activity className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-300">No platform activities found.</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            {search || roleFilter || targetTypeFilter || dateRange !== 'ALL'
              ? 'No activity records match your filter criteria. Try adjusting the search term or date range.'
              : 'No activities have been recorded in the database yet. Platform actions will appear here dynamically as users interact.'}
          </p>
        </div>
      ) : (
        /* Activity Table */
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 font-semibold uppercase tracking-wider">
                  <th className="py-3.5 px-4">Actor</th>
                  <th className="py-3.5 px-4">Action</th>
                  <th className="py-3.5 px-4">Target</th>
                  <th className="py-3.5 px-4">Description / Details</th>
                  <th className="py-3.5 px-4 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {activities.map((act) => (
                  <tr key={act.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white">{act.actor_name}</span>
                          {getRoleBadge(act.actor_role)}
                        </div>
                        {act.actor_email && (
                          <span className="text-[11px] text-slate-400">{act.actor_email}</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      {getActionBadge(act.action)}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="text-slate-300 font-mono text-[11px]">
                        {act.target_type}
                        {act.target_id ? ` #${act.target_id}` : ''}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="space-y-1">
                        <p className="text-slate-200">{act.description}</p>
                        {act.details && Object.keys(act.details).length > 0 && (
                          <div className="text-[10px] font-mono text-slate-500 truncate max-w-xs">
                            {JSON.stringify(act.details)}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5 text-slate-400">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        <span>{formatTimestamp(act.created_at)}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 border-t border-slate-800 bg-slate-950/40 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <span>Showing</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-slate-200 focus:outline-none focus:border-teal-500"
              >
                <option value={10}>10</option>
                <option value={15}>15</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
              <span>per page</span>
              <span className="text-slate-500">|</span>
              <span>Total: <strong className="text-slate-200">{total}</strong> activities</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-slate-400">
                Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1 || loading}
                  className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages || loading}
                  className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlatformActivities;
