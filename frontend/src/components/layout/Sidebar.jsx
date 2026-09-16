import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  User,
  Pill,
  CalendarCheck,
  Activity,
  FileText,
  ScanLine,
  Users,
  Bell,
  ShieldCheck,
  UserPlus,
  ClipboardList,
  History,
  TrendingUp,
  BarChart3,
  Sliders,
  Settings,
  Server,
  Bot,
} from 'lucide-react';

export const Sidebar = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const location = useLocation();
  const currentPath = location.pathname;
  const role = user?.role?.toUpperCase() || 'PATIENT';

  let navItems = [];

  if (role === 'ADMIN') {
    navItems = [
      { name: t('nav.adminPortal'), path: '/admin/dashboard', icon: LayoutDashboard },
      { name: t('nav.aiAssistant'), path: '/ai-assistant', icon: Bot },
      { name: t('nav.caregiverApprovals'), path: '/admin/caregivers', icon: ShieldCheck },
      { name: t('nav.patientManagement'), path: '/admin/patients', icon: Users },
      { name: t('nav.patientAssignments'), path: '/admin/assignments', icon: UserPlus },
      { name: t('nav.platformActivities'), path: '/admin/activities', icon: Activity },
      { name: t('nav.notificationSettings'), path: '/admin/notification-settings', icon: Bell },
      { name: t('nav.platformAnalytics'), path: '/admin/analytics', icon: BarChart3 },
      { name: t('nav.systemOperations'), path: '/admin/system', icon: Server },
      { name: t('nav.auditLogs'), path: '/admin/audit-logs', icon: ClipboardList },
      { name: t('nav.userProfile'), path: '/profile', icon: User },
    ];
  } else if (role === 'CAREGIVER') {
    navItems = [
      { name: t('nav.caregiverPortal'), path: '/caregiver/dashboard', icon: LayoutDashboard },
      { name: t('nav.aiAssistant'), path: '/ai-assistant', icon: Bot },
      { name: t('nav.myPatients'), path: '/caregiver/patients', icon: Users },
      { name: t('nav.viewAdherenceReports'), path: '/caregiver/adherence-reports', icon: BarChart3 },
      { name: t('nav.clinicalAlerts'), path: '/caregiver/alerts', icon: Bell },
      { name: t('nav.userProfile'), path: '/profile', icon: User },
    ];
  } else {
    // PATIENT navigation
    navItems = [
      { name: t('nav.dashboard'), path: '/', icon: LayoutDashboard },
      { name: t('nav.aiAssistant'), path: '/ai-assistant', icon: Bot },
      { name: t('nav.scanPrescription'), path: '/ocr', icon: ScanLine },
      { name: t('nav.medications'), path: '/medications', icon: Pill },
      { name: t('nav.viewMedicationHistory'), path: '/patient/medication-history', icon: History },
      { name: t('nav.viewRefillPredictions'), path: '/patient/refill-predictions', icon: TrendingUp },
      { name: t('nav.conditions'), path: '/conditions', icon: Activity },
      { name: t('nav.prescriptions'), path: '/prescriptions', icon: FileText },
      { name: t('nav.schedule'), path: '/schedule', icon: CalendarCheck },
      { name: t('nav.userProfile'), path: '/profile', icon: User },
    ];
  }

  const getPortalTitle = () => {
    if (role === 'ADMIN') return t('nav.adminPortal');
    if (role === 'CAREGIVER') return t('nav.caregiverPortal');
    return t('nav.patientPortal');
  };

  return (
    <aside className="w-64 shrink-0 border-r border-slate-800 bg-slate-900/50 flex flex-col justify-between p-4 min-h-[calc(100vh-73px)]">
      <div className="space-y-6">
        <div>
          <div className="flex items-center justify-between px-3 mb-2">
            <h2 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              {getPortalTitle()}
            </h2>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-400 border border-teal-500/20 font-medium">
              {role}
            </span>
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const isActive = currentPath === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-teal-500/10 text-teal-300 border border-teal-500/20'
                      : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                  }`}
                >
                  <item.icon className={`w-4 h-4 ${isActive ? 'text-teal-400' : 'text-slate-400'}`} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
