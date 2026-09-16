import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp,
  Pill,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Loader2,
  AlertCircle,
  Package,
  Search,
  ArrowRight,
  ShieldAlert,
  Info,
  CalendarDays,
  UserCheck,
} from 'lucide-react';
import medicationService from '../../api/medicationService';

export const RefillPredictions = () => {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterUrgency, setFilterUrgency] = useState('ALL'); // 'ALL' | 'CRITICAL' | 'LOW_STOCK' | 'INSUFFICIENT'

  const loadPredictions = async () => {
    setIsLoading(true);
    setError('');
    try {
      const res = await medicationService.getRefillPredictions();
      setData(res);
    } catch (err) {
      console.error('Failed to load refill predictions:', err);
      setError(
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        'Unable to calculate refill predictions. Please verify backend connectivity.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPredictions();
  }, []);

  const predictions = data?.predictions || [];

  const filteredPredictions = predictions.filter((item) => {
    // Urgency / status filter
    if (filterUrgency === 'CRITICAL' && item.urgency_level !== 'CRITICAL') return false;
    if (filterUrgency === 'LOW_STOCK' && !['CRITICAL', 'LOW_STOCK'].includes(item.urgency_level)) return false;
    if (filterUrgency === 'INSUFFICIENT' && item.status !== 'INSUFFICIENT_DATA') return false;

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const name = (item.medicine_name || '').toLowerCase();
      const form = (item.dosage_form || '').toLowerCase();
      const doctor = (item.doctor_name || '').toLowerCase();
      return name.includes(q) || form.includes(q) || doctor.includes(q);
    }
    return true;
  });

  const criticalCount = predictions.filter((p) => p.urgency_level === 'CRITICAL').length;
  const lowStockCount = predictions.filter((p) => p.urgency_level === 'LOW_STOCK').length;
  const goodCount = predictions.filter((p) => p.urgency_level === 'GOOD').length;
  const insufficientCount = predictions.filter((p) => p.status === 'INSUFFICIENT_DATA').length;

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const getUrgencyBadge = (urgency) => {
    switch (urgency) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <ShieldAlert className="w-3.5 h-3.5" />
            CRITICAL (≤ 3 days)
          </span>
        );
      case 'LOW_STOCK':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5" />
            LOW STOCK (≤ 7 days)
          </span>
        );
      case 'MODERATE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/15 text-sky-400 border border-sky-500/30">
            <Clock className="w-3.5 h-3.5" />
            MODERATE (≤ 14 days)
          </span>
        );
      case 'GOOD':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" />
            SUFFICIENT SUPPLY
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6 w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
              <TrendingUp className="w-5 h-5" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white">Refill Predictions</h2>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Dynamic medication stock projections calculated strictly from your active schedules and recorded intake
          </p>
        </div>
        <button
          type="button"
          onClick={loadPredictions}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl border border-slate-700 shadow-sm transition-colors shrink-0 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Recalculate Predictions</span>
        </button>
      </div>

      {/* Summary KPI Cards */}
      {!isLoading && predictions.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
              <Package className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-white">{predictions.length}</div>
              <div className="text-xs text-slate-400 font-medium">Monitored Medicines</div>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-rose-400">{criticalCount}</div>
              <div className="text-xs text-slate-400 font-medium">Critical Refills (≤ 3d)</div>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-amber-400">{lowStockCount}</div>
              <div className="text-xs text-slate-400 font-medium">Refill Soon (≤ 7d)</div>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-emerald-400">{goodCount}</div>
              <div className="text-xs text-slate-400 font-medium">Sufficient Supply</div>
            </div>
          </div>
        </div>
      )}

      {/* Filter / Search Controls */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-slate-900/60 border border-slate-800 rounded-2xl p-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-thin">
          <button
            type="button"
            onClick={() => setFilterUrgency('ALL')}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
              filterUrgency === 'ALL'
                ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30 font-semibold'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
            }`}
          >
            All Medications ({predictions.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterUrgency('CRITICAL')}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
              filterUrgency === 'CRITICAL'
                ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30 font-semibold'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
            }`}
          >
            Critical (≤ 3d)
          </button>
          <button
            type="button"
            onClick={() => setFilterUrgency('LOW_STOCK')}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
              filterUrgency === 'LOW_STOCK'
                ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
            }`}
          >
            Refill Soon (≤ 7d)
          </button>
          {insufficientCount > 0 && (
            <button
              type="button"
              onClick={() => setFilterUrgency('INSUFFICIENT')}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
                filterUrgency === 'INSUFFICIENT'
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
              }`}
            >
              Incomplete Data ({insufficientCount})
            </button>
          )}
        </div>

        <div className="relative min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search medicine, doctor..."
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
            onClick={loadPredictions}
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
          <p className="text-xs text-slate-400">Computing live dynamic refill calculations from database...</p>
        </div>
      ) : predictions.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center mx-auto text-teal-400">
            <TrendingUp className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-white">No active medication records.</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Add your medications with their prescribed quantities and intake schedules to view automated dynamic refill predictions.
            </p>
          </div>
          <div className="pt-2">
            <Link
              to="/medications"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-400 hover:bg-teal-300 text-slate-950 font-bold text-xs rounded-xl shadow-md transition-colors"
            >
              <Pill className="w-4 h-4" />
              <span>Add Medication & Schedule</span>
            </Link>
          </div>
        </div>
      ) : filteredPredictions.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center space-y-2">
          <p className="text-sm font-medium text-slate-300">No matching refill predictions found.</p>
          <p className="text-xs text-slate-500">
            Adjust your search keywords or switch to the &ldquo;All Medications&rdquo; tab.
          </p>
        </div>
      ) : (
        /* Predictions Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredPredictions.map((pred) => {
            const isInsufficient = pred.status === 'INSUFFICIENT_DATA';
            const isEnded = pred.status === 'ENDED';
            const isValid = pred.status === 'VALID';

            // Progress bar calculations
            const startingStock = pred.current_stock || 1;
            const remainingStock = pred.estimated_remaining_quantity !== null ? pred.estimated_remaining_quantity : 0;
            const stockPct = Math.min(100, Math.max(0, Math.round((remainingStock / startingStock) * 100)));

            return (
              <div
                key={pred.medicine_id}
                className={`bg-slate-900/70 border rounded-2xl p-5 space-y-4 transition-all hover:border-slate-700 shadow-lg ${
                  isInsufficient
                    ? 'border-amber-500/30 bg-amber-950/10'
                    : isEnded
                    ? 'border-slate-800 opacity-75'
                    : pred.urgency_level === 'CRITICAL'
                    ? 'border-rose-500/40'
                    : 'border-slate-800'
                }`}
              >
                {/* Card Top: Medicine Title & Badge */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 shrink-0">
                      <Pill className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-base font-bold text-white">{pred.medicine_name}</h4>
                      <div className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                        <span>
                          {pred.strength ? `${pred.strength} ${pred.unit || ''}` : ''}
                        </span>
                        <span>•</span>
                        <span className="capitalize">{pred.dosage_form || 'Tablet'}</span>
                        {pred.doctor_name && (
                          <>
                            <span>•</span>
                            <span className="text-teal-400/90 font-medium">Dr. {pred.doctor_name}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {isValid && getUrgencyBadge(pred.urgency_level)}
                  {isEnded && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
                      Ended
                    </span>
                  )}
                </div>

                {/* Case 1: Valid Prediction */}
                {isValid && (
                  <div className="space-y-3 pt-1">
                    {/* Stock Indicator Progress Bar */}
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className="text-slate-400">Estimated Remaining Supply:</span>
                        <span className="font-mono font-bold text-white">
                          {pred.estimated_remaining_quantity}{' '}
                          <span className="text-slate-400 font-normal text-[11px]">
                            / {pred.current_stock} units ({stockPct}%)
                          </span>
                        </span>
                      </div>
                      <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                        <div
                          className={`h-full rounded-full transition-all ${
                            pred.urgency_level === 'CRITICAL'
                              ? 'bg-rose-500'
                              : pred.urgency_level === 'LOW_STOCK'
                              ? 'bg-amber-400'
                              : 'bg-teal-400'
                          }`}
                          style={{ width: `${stockPct}%` }}
                        />
                      </div>
                    </div>

                    {/* Calculated Metrics Breakdown */}
                    <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/80">
                      <div className="bg-slate-950/60 rounded-xl p-2.5 border border-slate-800/60">
                        <div className="text-[10px] uppercase font-semibold text-slate-400">Daily Usage</div>
                        <div className="text-sm font-bold text-slate-100 font-mono mt-0.5">
                          {pred.daily_consumption}{' '}
                          <span className="text-[10px] text-slate-400 font-normal">units/day</span>
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          {pred.doses_per_day}x daily ({pred.dose_quantity_per_intake} ea)
                        </div>
                      </div>

                      <div className="bg-slate-950/60 rounded-xl p-2.5 border border-slate-800/60">
                        <div className="text-[10px] uppercase font-semibold text-slate-400">Days Remaining</div>
                        <div className={`text-sm font-bold font-mono mt-0.5 ${
                          pred.urgency_level === 'CRITICAL' ? 'text-rose-400' : 'text-teal-300'
                        }`}>
                          {pred.estimated_remaining_days} Days
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          {pred.doses_taken_count} doses taken
                        </div>
                      </div>

                      <div className="bg-slate-950/60 rounded-xl p-2.5 border border-slate-800/60">
                        <div className="text-[10px] uppercase font-semibold text-slate-400">Predicted Refill</div>
                        <div className="text-xs font-bold text-white font-mono mt-1">
                          {formatDate(pred.predicted_refill_date)}
                        </div>
                        <div className="text-[10px] text-teal-400 font-medium mt-0.5">
                          Target date
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Case 2: Insufficient Data Alert */}
                {isInsufficient && (
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-2">
                    <div className="flex items-center gap-2 text-amber-300 font-semibold text-xs">
                      <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                      <span>Refill prediction unavailable — insufficient medication data.</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      {pred.status_message || 'Missing required dosage intake schedule or stock quantity parameters.'}
                    </p>
                    <div className="pt-1">
                      <Link
                        to="/medications"
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-400 hover:text-teal-300"
                      >
                        <span>Update Medication Stock & Schedule</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                )}

                {/* Case 3: Ended Medication */}
                {isEnded && (
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
                    <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5 text-slate-400" />
                      <span>Medication already ended</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Regimen completed on {formatDate(pred.end_date)}. No future refill is required.
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default RefillPredictions;
