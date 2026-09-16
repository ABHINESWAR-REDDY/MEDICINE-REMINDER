import React from 'react';
import { Link, useLocation } from 'react-router-dom';
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
} from 'lucide-react';

export const Sidebar = () => {
  const { user } = useAuth();
  const location = useLocation();
  const currentPath = location.pathname;
  const role = user?.role?.toUpperCase() || 'PATIENT';

  let navItems = [];

  if (role === 'ADMIN') {
    navItems = [
      { name: 'Admin Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
      { name: 'Caregiver Approvals', path: '/admin/caregivers', icon: ShieldCheck },
      { name: 'Patient Management', path: '/admin/patients', icon: Users },
      { name: 'Patient Assignments', path: '/admin/assignments', icon: UserPlus },
      { name: 'Platform Activities', path: '/admin/activities', icon: Activity },
      { name: 'Notification Settings', path: '/admin/notification-settings', icon: Bell },
      { name: 'Platform Analytics', path: '/admin/analytics', icon: BarChart3 },
      { name: 'System Operations', path: '/admin/system', icon: Server },
      { name: 'Audit Logs', path: '/admin/audit-logs', icon: ClipboardList },
      { name: 'User Profile', path: '/profile', icon: User },
    ];
  } else if (role === 'CAREGIVER') {
    navItems = [
      { name: 'Caregiver Dashboard', path: '/caregiver/dashboard', icon: LayoutDashboard },
      { name: 'My Patients', path: '/caregiver/patients', icon: Users },
      { name: 'View Adherence Reports', path: '/caregiver/adherence-reports', icon: BarChart3 },
      { name: 'Clinical Alerts', path: '/caregiver/alerts', icon: Bell },
      { name: 'User Profile', path: '/profile', icon: User },
    ];
  } else {

    // PATIENT navigation
    navItems = [
      { name: 'Dashboard', path: '/', icon: LayoutDashboard },
      { name: 'Scan Prescription', path: '/ocr', icon: ScanLine },
      { name: 'Medications', path: '/medications', icon: Pill },
      { name: 'View Medication History', path: '/patient/medication-history', icon: History },
      { name: 'View Refill Predictions', path: '/patient/refill-predictions', icon: TrendingUp },
      { name: 'Conditions', path: '/conditions', icon: Activity },
      { name: 'Prescriptions', path: '/prescriptions', icon: FileText },
      { name: 'Schedule', path: '/schedule', icon: CalendarCheck },
      { name: 'User Profile', path: '/profile', icon: User },
    ];
  }


  return (
    <aside className="w-64 shrink-0 border-r border-slate-800 bg-slate-900/50 flex flex-col justify-between p-4 min-h-[calc(100vh-73px)]">
      <div className="space-y-6">
        <div>
          <div className="flex items-center justify-between px-3 mb-2">
            <h2 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              {role === 'ADMIN' ? 'Admin Portal' : role === 'CAREGIVER' ? 'Caregiver Portal' : 'Patient Portal'}
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
                  key={item.name}
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
