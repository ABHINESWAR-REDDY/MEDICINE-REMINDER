import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Pill, Shield, LogOut, User, Bell, MessageSquare, ChevronRight, Check, CheckCheck, AlertTriangle, AlertCircle, Info, X, Package } from 'lucide-react';


import ThemeToggle from '../common/ThemeToggle';
import { caregiverService } from '../../api/caregiverService';
import { chatService } from '../../api/chatService';
import { notificationService } from '../../api/notificationService';
import ChatDrawer from '../chat/ChatDrawer';

export const Header = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const [alerts, setAlerts] = useState([]);
  const [patientNotifications, setPatientNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [pollError, setPollError] = useState(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [activeChatUser, setActiveChatUser] = useState(null);
  const dropdownRef = useRef(null);

  const formatAlertTime = (timestamp) => {
    if (!timestamp) return '';
    let str = typeof timestamp === 'string' ? timestamp : String(timestamp);
    if (!str.endsWith('Z') && !/[+-]\d{2}(:\d{2})?$/.test(str)) {
      str = `${str}Z`;
    }
    const d = new Date(str);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Poll for notifications and unread counts
  useEffect(() => {
    if (!isAuthenticated || !user) return;

    let isMounted = true;

    const checkNotifications = async () => {
      try {
        if (user.role === 'CAREGIVER') {
          const alertList = await caregiverService.getAlerts();
          if (isMounted && Array.isArray(alertList)) {
            setAlerts(alertList);
            setUnreadCount(alertList.length);
            setPollError(null);
          }
        } else if (user.role === 'PATIENT') {
          const [notifs, unreadRes] = await Promise.all([
            notificationService.getNotifications(),
            notificationService.getUnreadCount(),
          ]);
          if (isMounted) {
            setPatientNotifications(Array.isArray(notifs) ? notifs : []);
            setUnreadCount(unreadRes?.unread_count || 0);
            setPollError(null);
          }
        }
      } catch (err) {
        if (isMounted) {
          console.error('Notification polling error:', err);
          const errorMsg = err.response?.data?.detail?.message || err.response?.data?.detail || err.message || 'Failed to update notifications';
          setPollError(typeof errorMsg === 'string' ? errorMsg : 'Connection error');
        }
      }
    };

    checkNotifications();
    const interval = setInterval(checkNotifications, 5000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isAuthenticated, user?.role]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getRoleBadgeStyle = (role) => {
    switch (role) {
      case 'ADMIN':
        return 'bg-purple-500/10 text-purple-300 border-purple-500/30';
      case 'CAREGIVER':
        return 'bg-blue-500/10 text-blue-300 border-blue-500/30';
      default:
        return 'bg-teal-500/10 text-teal-300 border-teal-500/30';
    }
  };

  const handleOpenChatFromNotification = async (al) => {
    try {
      await caregiverService.markAlertRead(al.id);
      setAlerts((prev) => prev.filter((a) => a.id !== al.id));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      // Ignore
    }
    setIsDropdownOpen(false);
    if (al.type === 'CHAT_MESSAGE') {
      setActiveChatUser({
        id: al.patient_id,
        user_id: al.patient_id,
        name: al.patient_name,
        employee_id: al.patient_employee_id,
        role: 'PATIENT',
      });
      setIsChatOpen(true);
    } else if (al.type === 'REFILL_NEEDED') {
      navigate('/caregiver/adherence-reports');
    } else {
      navigate('/caregiver/alerts');
    }
  };

  const handleMarkCaregiverAlertRead = async (e, alertId) => {
    if (e) e.stopPropagation();
    try {
      await caregiverService.markAlertRead(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to mark alert as read:', err);
    }
  };

  const handleMarkAllCaregiverAlertsRead = async (e) => {
    if (e) e.stopPropagation();
    try {
      await caregiverService.markAllAlertsRead();
      setAlerts([]);
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all alerts as read:', err);
    }
  };

  const handlePatientNotificationClick = async (notif) => {
    if (!notif.is_read) {
      try {
        await notificationService.markAsRead(notif.id);
        setPatientNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch (e) {
        // Ignore
      }
    }
    setIsDropdownOpen(false);
    navigate('/patient/alerts');
  };

  const handleMarkAllPatientNotificationsRead = async () => {
    try {
      await notificationService.markAllAsRead();
      setPatientNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (e) {
      // Ignore
    }
  };

  return (
    <>
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-30 px-6 py-4 transition-colors duration-200">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Brand Identity */}
          <Link to="/" className="flex items-center gap-3 group shrink-0">
            <div className="flex items-center justify-center h-10 w-10 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 group-hover:border-teal-500/40 transition-colors">
              <Pill className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-white">PillSync</h1>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Intelligent Medicine Reminder & Medication Tracking Platform
              </p>
            </div>
          </Link>

          {/* Right: Authenticated User Controls & Theme Switcher */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2 sm:gap-3">
                {/* Live Notification Bell for Caregiver or Patient */}
                {(user.role === 'CAREGIVER' || user.role === 'PATIENT') && (
                  <div className="relative" ref={dropdownRef}>
                    <button
                      onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                      aria-label="Notifications"
                      className={`relative p-2 rounded-xl border transition-colors ${
                        unreadCount > 0
                          ? 'bg-amber-500/10 text-amber-300 border-amber-500/30 hover:bg-amber-500/20'
                          : 'bg-slate-800/60 text-slate-300 border-slate-700/60 hover:bg-slate-800'
                      }`}
                    >
                      <Bell className="w-4 h-4" />
                      {unreadCount > 0 && (
                        <span className="absolute -top-1 -right-1 flex h-4 w-4">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-4 w-4 bg-rose-500 text-white text-[9px] font-bold items-center justify-center">
                            {unreadCount > 9 ? '9+' : unreadCount}
                          </span>
                        </span>
                      )}
                    </button>

                    {/* Notification Dropdown Panel */}
                    {isDropdownOpen && (
                      <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden z-50 animate-in fade-in-50 zoom-in-95">
                        {user.role === 'CAREGIVER' ? (
                          <>
                            <div className="p-3.5 border-b border-slate-800 bg-slate-950/80 flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Bell className="w-4 h-4 text-amber-400" />
                                <span className="text-xs font-bold text-white">Supervision Notifications</span>
                              </div>
                              <div className="flex items-center gap-2">
                                {alerts.length > 0 && (
                                  <button
                                    onClick={handleMarkAllCaregiverAlertsRead}
                                    className="text-[10px] text-amber-400 hover:text-amber-300 font-semibold flex items-center gap-1 transition-colors"
                                    title="Mark all notifications as read"
                                  >
                                    <CheckCheck className="w-3 h-3" />
                                    <span>Mark all read</span>
                                  </button>
                                )}
                                <span className="text-[10px] font-semibold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
                                  {alerts.length} active
                                </span>
                              </div>
                            </div>

                            <div className="max-h-72 overflow-y-auto divide-y divide-slate-800/60">
                              {pollError && alerts.length === 0 ? (
                                <div className="p-5 text-center text-xs text-rose-400 bg-rose-500/5">
                                  <AlertTriangle className="w-6 h-6 mx-auto text-rose-400 mb-1.5" />
                                  <p className="font-semibold">{pollError}</p>
                                </div>
                              ) : alerts.length === 0 ? (
                                <div className="p-6 text-center text-xs text-slate-400">
                                  <Bell className="w-6 h-6 mx-auto text-slate-600 mb-1" />
                                  <p>No active alerts or unread messages</p>
                                </div>
                              ) : (
                                alerts.slice(0, 5).map((al) => {
                                  const isChat = al.type === 'CHAT_MESSAGE';
                                  const isRefill = al.type === 'REFILL_NEEDED';
                                  return (
                                    <div
                                      key={al.id}
                                      onClick={() => handleOpenChatFromNotification(al)}
                                      className="p-3 hover:bg-slate-800/40 cursor-pointer transition-colors flex items-start gap-2.5 group"
                                    >
                                      <div
                                        className={`p-1.5 rounded-lg shrink-0 mt-0.5 ${
                                          isChat
                                            ? 'bg-teal-500/20 text-teal-300'
                                            : isRefill
                                            ? al.severity === 'CRITICAL'
                                              ? 'bg-rose-500/20 text-rose-300'
                                              : 'bg-amber-500/20 text-amber-300'
                                            : al.severity === 'CRITICAL'
                                            ? 'bg-rose-500/20 text-rose-300'
                                            : 'bg-amber-500/20 text-amber-300'
                                        }`}
                                      >
                                        {isChat ? (
                                          <MessageSquare className="w-3.5 h-3.5" />
                                        ) : isRefill ? (
                                          <Package className="w-3.5 h-3.5" />
                                        ) : (
                                          <Bell className="w-3.5 h-3.5" />
                                        )}
                                      </div>
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-1">
                                          <span className="text-xs font-bold text-white truncate">{al.title}</span>
                                          <span
                                            className={`text-[9px] font-bold px-1.5 py-0.2 rounded shrink-0 ${
                                              isChat
                                                ? 'bg-teal-500/20 text-teal-300'
                                                : isRefill
                                                ? al.severity === 'CRITICAL'
                                                  ? 'bg-rose-500/20 text-rose-300'
                                                  : 'bg-amber-500/20 text-amber-300'
                                                : al.severity === 'CRITICAL'
                                                ? 'bg-rose-500/20 text-rose-300'
                                                : 'bg-amber-500/20 text-amber-300'
                                            }`}
                                          >
                                            {isChat ? 'LIVE CHAT' : isRefill ? (al.severity === 'CRITICAL' ? 'CRITICAL REFILL' : 'REFILL NEEDED') : al.severity}
                                          </span>
                                        </div>
                                        <p className="text-[11px] text-slate-300 truncate mt-0.5">{al.message}</p>
                                        <div className="flex items-center justify-between mt-1">
                                          <span className="text-[9px] text-slate-500 block">
                                            {formatAlertTime(al.timestamp)}
                                          </span>
                                          <button
                                            type="button"
                                            onClick={(e) => handleMarkCaregiverAlertRead(e, al.id)}
                                            className="text-[10px] text-slate-400 hover:text-amber-300 font-medium flex items-center gap-1 transition-colors px-1.5 py-0.5 rounded hover:bg-slate-800"
                                            title="Mark as read"
                                          >
                                            <Check className="w-2.5 h-2.5" />
                                            <span>Mark read</span>
                                          </button>
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })

                              )}
                            </div>

                            <div className="p-2.5 border-t border-slate-800 bg-slate-950/60 text-center">
                              <Link
                                to="/caregiver/alerts"
                                onClick={() => setIsDropdownOpen(false)}
                                className="text-xs text-teal-400 hover:text-teal-300 font-semibold inline-flex items-center gap-1"
                              >
                                <span>View All Alerts Hub</span>
                                <ChevronRight className="w-3 h-3" />
                              </Link>
                            </div>
                          </>
                        ) : (

                          /* Patient Notifications Dropdown */
                          <>
                            <div className="p-3.5 border-b border-slate-800 bg-slate-950/80 flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Bell className="w-4 h-4 text-teal-400" />
                                <span className="text-xs font-bold text-white">Medication Notifications</span>
                              </div>
                              <div className="flex items-center gap-2">
                                {unreadCount > 0 && (
                                  <button
                                    onClick={handleMarkAllPatientNotificationsRead}
                                    className="text-[10px] text-teal-400 hover:text-teal-300 font-semibold flex items-center gap-1"
                                  >
                                    <CheckCheck className="w-3 h-3" />
                                    <span>Mark all read</span>
                                  </button>
                                )}
                                <span className="text-[10px] font-semibold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
                                  {unreadCount} unread
                                </span>
                              </div>
                            </div>

                            <div className="max-h-72 overflow-y-auto divide-y divide-slate-800/60">
                              {pollError && patientNotifications.length === 0 ? (
                                <div className="p-5 text-center text-xs text-rose-400 bg-rose-500/5">
                                  <AlertTriangle className="w-6 h-6 mx-auto text-rose-400 mb-1.5" />
                                  <p className="font-semibold">{pollError}</p>
                                </div>
                              ) : patientNotifications.length === 0 ? (
                                <div className="p-6 text-center text-xs text-slate-400">
                                  <Bell className="w-6 h-6 mx-auto text-slate-600 mb-1" />
                                  <p>No medication alerts or reminders</p>
                                  <p className="text-[11px] text-slate-500 mt-1">You are all caught up on your doses!</p>
                                </div>
                              ) : (
                                patientNotifications.slice(0, 5).map((notif) => {
                                  const isMissed = notif.type === 'MISSED_DOSE';
                                  return (
                                    <div
                                      key={notif.id}
                                      onClick={() => handlePatientNotificationClick(notif)}
                                      className={`p-3 hover:bg-slate-800/40 cursor-pointer transition-colors flex items-start gap-2.5 ${
                                        !notif.is_read ? 'bg-slate-800/30' : ''
                                      }`}
                                    >
                                      <div
                                        className={`p-1.5 rounded-lg shrink-0 mt-0.5 ${
                                          isMissed
                                            ? 'bg-amber-500/20 text-amber-300'
                                            : 'bg-teal-500/20 text-teal-300'
                                        }`}
                                      >
                                        {isMissed ? <AlertTriangle className="w-3.5 h-3.5" /> : <Bell className="w-3.5 h-3.5" />}
                                      </div>
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-1">
                                          <span className="text-xs font-bold text-white truncate">{notif.title}</span>
                                          <div className="flex items-center gap-1.5 shrink-0">
                                            {!notif.is_read && (
                                              <span className="w-2 h-2 rounded-full bg-teal-400"></span>
                                            )}
                                            <span
                                              className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                                                isMissed
                                                  ? 'bg-amber-500/20 text-amber-300'
                                                  : 'bg-teal-500/20 text-teal-300'
                                              }`}
                                            >
                                              {isMissed ? 'MISSED' : 'REMINDER'}
                                            </span>
                                          </div>
                                        </div>
                                        <p className="text-[11px] text-slate-300 truncate mt-0.5">{notif.message}</p>
                                        <span className="text-[9px] text-slate-500 block mt-0.5">
                                          {formatAlertTime(notif.created_at)}
                                        </span>
                                      </div>
                                    </div>
                                  );
                                })
                              )}
                            </div>

                            <div className="p-2.5 border-t border-slate-800 bg-slate-950/60 text-center">
                              <Link
                                to="/patient/alerts"
                                onClick={() => setIsDropdownOpen(false)}
                                className="text-xs text-teal-400 hover:text-teal-300 font-semibold inline-flex items-center gap-1"
                              >
                                <span>View All Alerts Hub</span>
                                <ChevronRight className="w-3 h-3" />
                              </Link>
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Profile Link */}
                <Link
                  to="/profile"
                  className="flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl bg-slate-800/60 border border-slate-700/60 hover:bg-slate-800 hover:border-slate-600 transition-colors text-xs"
                >
                  <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-teal-500/20 text-teal-300 shrink-0">
                    <User className="w-3.5 h-3.5" />
                  </div>
                  <div className="text-left hidden sm:block">
                    <span className="font-medium text-slate-200 block leading-tight">{user.name}</span>
                    <span
                      className={`inline-flex items-center gap-0.5 text-[10px] font-semibold uppercase px-1.5 py-0.2 rounded border ${getRoleBadgeStyle(
                        user.role
                      )}`}
                    >
                      <Shield className="w-2.5 h-2.5" />
                      {user.role}
                    </span>
                  </div>
                </Link>

                <button
                  onClick={handleLogout}
                  title="Sign out"
                  aria-label="Sign out"
                  className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-800/80 hover:bg-rose-500/10 text-slate-300 hover:text-rose-300 border border-slate-700 hover:border-rose-500/30 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden md:inline">Sign out</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium bg-teal-400 text-slate-950 hover:bg-teal-300 transition-colors"
                >
                  Sign in
                </Link>
              </div>
            )}

            {/* Theme Switcher at TOP-RIGHT */}
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Direct Caregiver-Patient Chat Drawer from Notification */}
      <ChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        targetUser={activeChatUser}
      />
    </>
  );
};

export default Header;
