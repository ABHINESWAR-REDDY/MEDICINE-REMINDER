import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  History,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Pill,
  Calendar,
  RefreshCw,
  Loader2,
  AlertCircle,
  ArrowRight,
  Filter,
} from 'lucide-react';
import medicationService from '../../api/medicationService';
import { formatLocalDateTime, formatLocalDate } from '../../utils/dateTime';

export const MedicationHistory = () => {
  const { t } = useTranslation();
  const [history, setHistory] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const loadHistory = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await medicationService.getMedicationHistory();
      setHistory(data?.history || []);
      setTotalRecords(data?.total_records || 0);
    } catch (err) {
      console.error('Failed to load patient medication history:', err);
      setError(
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        'Unable to load medication history from database. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const filteredHistory = history.filter((item) => {
    // Status filter
    if (statusFilter !== 'ALL') {
      const itemStatus = (item.status || '').toUpperCase();
      if (itemStatus !== statusFilter) {
        return false;
      }
    }

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const medName = (item.medicine_name || '').toLowerCase();
      const form = (item.dosage_form || '').toLowerCase();
      const instructions = (item.instructions || '').toLowerCase();
      const status = (item.status || '').toLowerCase();
      return medName.includes(q) || form.includes(q) || instructions.includes(q) || status.includes(q);
    }

    return true;
  });

  const getStatusBadge = (status) => {
    const s = (status || '').toUpperCase();
    switch (s) {
      case 'TAKEN':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            TAKEN
          </span>
        );
      case 'MISSED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3.5 h-3.5 shrink-0" />
            MISSED
          </span>
        );
      case 'SKIPPED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            SKIPPED
          </span>
        );
      case 'SCHEDULED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/15 text-sky-400 border border-sky-500/30">
            <Clock className="w-3.5 h-3.5 shrink-0" />
            SCHEDULED
          </span>
        );
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-teal-500/15 text-teal-400 border border-teal-500/30">
            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            ACTIVE REGIMEN
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            {s || 'LOGGED'}
          </span>
        );
    }
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return '—';
    return formatLocalDateTime(isoString, { hour12: true }) || isoString;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return formatLocalDate(dateString) || dateString;
  };

  const statusTabs = [
    { id: 'ALL', label: t('medications.allHistory', 'All History') },
    { id: 'TAKEN', label: t('medications.takenDoses', 'Taken Doses') },
    { id: 'MISSED', label: t('medications.missedDoses', 'Missed Doses') },
    { id: 'SKIPPED', label: t('medications.skippedDoses', 'Skipped Doses') },
    { id: 'SCHEDULED', label: t('medications.scheduledDoses', 'Scheduled Doses') },
  ];

  return (
    <div className="space-y-6 w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
              <History className="w-5 h-5" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white">{t('nav.viewMedicationHistory')}</h2>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            {t('medications.subtitle')}
          </p>
        </div>
        <button
          type="button"
          onClick={loadHistory}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl border border-slate-700 shadow-sm transition-colors shrink-0 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>{t('common.refresh')}</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-slate-900/60 border border-slate-800 rounded-2xl p-3">
        {/* Status Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-thin">
          {statusTabs.map((tab) => {
            const isActive = statusFilter === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setStatusFilter(tab.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30 font-semibold'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Search Box */}
        <div className="relative min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('medications.searchPlaceholder', 'Search by medicine name...')}
            className="w-full pl-9 pr-4 py-1.5 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
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
            onClick={loadHistory}
            className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 rounded-lg text-xs font-semibold transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Main Content Area */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-3">
          <Loader2 className="w-7 h-7 animate-spin text-teal-400" />
          <p className="text-xs text-slate-400">Loading your real medication records from database...</p>
        </div>
      ) : history.length === 0 ? (
        /* Empty State: No medication history available */
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center mx-auto text-teal-400">
            <History className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-white">No medication history available.</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              You do not have any recorded medication intake records or active medication prescriptions in the system yet.
            </p>
          </div>
          <div className="pt-2 flex items-center justify-center gap-3">
            <Link
              to="/medications"
              className="inline-flex items-center gap-2 px-4 py-2 bg-teal-400 hover:bg-teal-300 text-slate-950 font-bold text-xs rounded-xl shadow-md transition-colors"
            >
              <Pill className="w-3.5 h-3.5" />
              <span>Add Medication</span>
            </Link>
            <Link
              to="/schedule"
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl border border-slate-700 transition-colors"
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>View Daily Schedule</span>
            </Link>
          </div>
        </div>
      ) : filteredHistory.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center space-y-2">
          <p className="text-sm font-medium text-slate-300">No matching records found.</p>
          <p className="text-xs text-slate-500">
            Try adjusting your search criteria or changing the status filter tab.
          </p>
        </div>
      ) : (
        /* History Table & Cards */
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
            <div className="text-xs font-semibold text-slate-300">
              Showing {filteredHistory.length} of {totalRecords} Medication History Events
            </div>
            <span className="text-[11px] text-slate-500 font-medium">Chronological order</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/40 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Medicine & Form</th>
                  <th className="py-3.5 px-4">Strength & Unit</th>
                  <th className="py-3.5 px-4">Schedule / Instructions</th>
                  <th className="py-3.5 px-4">Regimen Period</th>
                  <th className="py-3.5 px-4">Dose Date & Time</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Actual Taken Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs text-slate-300">
                {filteredHistory.map((item, index) => {
                  return (
                    <tr
                      key={item.id ? `dose-${item.id}` : `med-${item.medicine_id}-${index}`}
                      className="hover:bg-slate-800/30 transition-colors group"
                    >
                      {/* Medicine Name & Form */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2.5">
                          <div className="p-1.5 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20 group-hover:bg-teal-500/20 transition-colors">
                            <Pill className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="font-semibold text-white">{item.medicine_name}</div>
                            <div className="text-[11px] text-slate-400">{item.dosage_form || 'TABLET'}</div>
                          </div>
                        </div>
                      </td>

                      {/* Strength & Unit */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="font-mono text-slate-200 font-medium">
                          {item.strength !== null && item.strength !== undefined ? item.strength : '—'}{' '}
                          <span className="text-teal-400 text-[11px]">{item.unit || ''}</span>
                        </span>
                      </td>

                      {/* Schedule / Instructions */}
                      <td className="py-3.5 px-4 max-w-xs">
                        <div className="space-y-0.5">
                          {item.schedule_description && (
                            <div className="text-slate-200 font-medium flex items-center gap-1">
                              <Clock className="w-3 h-3 text-slate-400 shrink-0" />
                              <span>{item.schedule_description}</span>
                            </div>
                          )}
                          {item.instructions ? (
                            <div className="text-[11px] text-slate-400 line-clamp-2">
                              {item.instructions}
                            </div>
                          ) : (
                            <div className="text-[11px] text-slate-500 italic">No instructions specified</div>
                          )}
                        </div>
                      </td>

                      {/* Regimen Period */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="text-[11px] text-slate-300">
                          <span>{formatDate(item.start_date)}</span>
                          <span className="text-slate-500 mx-1">→</span>
                          <span>{item.end_date ? formatDate(item.end_date) : 'Ongoing'}</span>
                        </div>
                      </td>

                      {/* Dose Date/Time */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="font-mono text-[11px] text-slate-200">
                          {item.scheduled_time ? formatDateTime(item.scheduled_time) : (
                            <span className="text-slate-500 italic">Regimen start: {formatDate(item.start_date)}</span>
                          )}
                        </div>
                      </td>

                      {/* Dose Status */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {getStatusBadge(item.status)}
                      </td>

                      {/* Actual Taken Time */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {item.actual_time ? (
                          <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
                            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                            <span>{formatDateTime(item.actual_time)}</span>
                          </div>
                        ) : (
                          <span className="text-slate-500 text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default MedicationHistory;
