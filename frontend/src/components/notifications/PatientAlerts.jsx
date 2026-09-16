import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Bell,
  AlertTriangle,
  CheckCircle2,
  CheckCheck,
  Clock,
  Loader2,
  RefreshCw,
  Filter,
  Calendar,
  Pill,
  ChevronRight,
  Info,
} from 'lucide-react';
import { notificationService } from '../../api/notificationService';

import { formatLocalDateTime, formatLocalTime } from '../../utils/dateTime';

export const PatientAlerts = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [actionLoading, setActionLoading] = useState(null);

  const formatAlertTime = (timestamp) => {
    return formatLocalDateTime(timestamp, { hour12: true });
  };

  const fetchNotifications = async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const data = await notificationService.getNotifications();
      setNotifications(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      console.error('Failed to load patient notifications:', err);
      const msg = err.response?.data?.detail?.message || err.response?.data?.detail || err.message || 'Failed to load notifications';
      setError(typeof msg === 'string' ? msg : 'Failed to load notifications');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications(true);
    const interval = setInterval(() => {
      fetchNotifications(false);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleMarkAsRead = async (id) => {
    setActionLoading(id);
    try {
      await notificationService.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      console.error('Failed to mark notification read:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleMarkAllRead = async () => {
    setActionLoading('all');
    try {
      await notificationService.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      console.error('Failed to mark all read:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const filteredNotifications = notifications.filter((n) => {
    if (activeFilter === 'UNREAD') return !n.is_read;
    if (activeFilter === 'MEDICATION REMINDERS') return n.type === 'MEDICATION_REMINDER';
    if (activeFilter === 'MISSED DOSES') return n.type === 'MISSED_DOSE';
    return true;
  });

  const unreadTotal = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">Medication Alerts & Reminders</h1>
            {unreadTotal > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-500/10 text-teal-300 border border-teal-500/30">
                {unreadTotal} Unread
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time reminders for upcoming scheduled doses and clinical alerts for missed intakes.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          {unreadTotal > 0 && (
            <button
              onClick={handleMarkAllRead}
              disabled={actionLoading === 'all'}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold transition-colors shadow-lg shadow-teal-500/10 disabled:opacity-50"
            >
              {actionLoading === 'all' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <CheckCheck className="w-3.5 h-3.5" />
              )}
              <span>Mark All as Read</span>
            </button>
          )}

          <button
            onClick={() => fetchNotifications(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-slate-800">
        {['ALL', 'UNREAD', 'MEDICATION REMINDERS', 'MISSED DOSES'].map((tab) => {
          const isSelected = activeFilter === tab;
          const count =
            tab === 'ALL'
              ? notifications.length
              : tab === 'UNREAD'
              ? unreadTotal
              : tab === 'MEDICATION REMINDERS'
              ? notifications.filter((n) => n.type === 'MEDICATION_REMINDER').length
              : notifications.filter((n) => n.type === 'MISSED_DOSE').length;

          return (
            <button
              key={tab}
              onClick={() => setActiveFilter(tab)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 border whitespace-nowrap ${
                isSelected
                  ? 'bg-teal-500 text-slate-950 border-teal-400 shadow-md shadow-teal-500/10'
                  : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              <span>{tab}</span>
              <span
                className={`px-1.5 py-0.2 text-[10px] rounded-full font-mono ${
                  isSelected ? 'bg-slate-950/30 text-slate-950 font-extrabold' : 'bg-slate-800 text-slate-400'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Alerts List Container */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Bell className="w-4 h-4 text-teal-400" />
            <span>Alerts Feed ({filteredNotifications.length})</span>
          </h2>
          <span className="text-[11px] text-slate-500">Auto-refreshing every 5s</span>
        </div>

        {error && notifications.length === 0 ? (
          <div className="p-8 text-center text-rose-400 bg-rose-500/10 border border-rose-500/20 m-4 rounded-xl">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-rose-400" />
            <p className="text-sm font-semibold">{error}</p>
            <button
              onClick={() => fetchNotifications(true)}
              className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-semibold transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        ) : loading && notifications.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin mx-auto mb-2" />
            <p className="text-xs">Loading medication notifications...</p>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Bell className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm font-medium text-slate-300">
              {notifications.length === 0
                ? 'No new medication alerts.'
                : activeFilter === 'UNREAD'
                ? 'No unread medication alerts.'
                : activeFilter === 'MISSED DOSES'
                ? 'No missed doses recorded.'
                : activeFilter === 'MEDICATION REMINDERS'
                ? 'No active medication reminders.'
                : 'No new medication alerts.'}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Your medication schedules and dose intake will generate alerts automatically here.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {filteredNotifications.map((notif) => {
              const isMissed = notif.type === 'MISSED_DOSE';
              return (
                <div
                  key={notif.id}
                  className={`p-4.5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-colors hover:bg-slate-800/20 ${
                    !notif.is_read ? 'bg-slate-800/30' : ''
                  }`}
                >
                  <div className="flex items-start gap-3.5">
                    <div
                      className={`p-2.5 rounded-xl shrink-0 mt-0.5 border ${
                        isMissed
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : 'bg-teal-500/10 text-teal-400 border-teal-500/20'
                      }`}
                    >
                      {isMissed ? <AlertTriangle className="w-5 h-5" /> : <Bell className="w-5 h-5" />}
                    </div>

                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-white text-sm">{notif.title}</span>
                        {!notif.is_read && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded-full border border-teal-500/20">
                            <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse"></span>
                            UNREAD
                          </span>
                        )}
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            isMissed ? 'bg-amber-500/20 text-amber-300' : 'bg-teal-500/20 text-teal-300'
                          }`}
                        >
                          {isMissed ? 'MISSED DOSE' : 'REMINDER'}
                        </span>
                      </div>

                      <p className="text-xs text-slate-300 mt-1 leading-relaxed">{notif.message}</p>

                      <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-1.5">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span>{formatAlertTime(notif.created_at)}</span>
                        </span>
                        {notif.medicine_name && (
                          <span className="flex items-center gap-1 text-slate-400 font-medium">
                            <Pill className="w-3 h-3 text-teal-400" />
                            <span>{notif.medicine_name}</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    {!notif.is_read && (
                      <button
                        onClick={() => handleMarkAsRead(notif.id)}
                        disabled={actionLoading === notif.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
                      >
                        {actionLoading === notif.id ? (
                          <Loader2 className="w-3 h-3 animate-spin text-teal-400" />
                        ) : (
                          <CheckCircle2 className="w-3 h-3 text-teal-400" />
                        )}
                        <span>Mark as Read</span>
                      </button>
                    )}

                    <Link
                      to="/schedule"
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 text-xs font-semibold transition-colors border border-teal-500/20"
                    >
                      <span>View Schedule</span>
                      <ChevronRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientAlerts;
