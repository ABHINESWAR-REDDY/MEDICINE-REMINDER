import React from 'react';
import { Users, UserPlus } from 'lucide-react';
import EmptyState from '../common/EmptyState';

export const Caregivers = () => {
  return (
    <div className="space-y-6 w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Caregivers & Patients</h2>
          <p className="text-sm text-slate-400 mt-1">
            Manage supervised care assignments, linked family members, and access permissions
          </p>
        </div>
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-400 hover:bg-teal-300 text-slate-950 font-semibold text-xs rounded-xl shadow-sm transition-colors shrink-0"
        >
          <UserPlus className="w-4 h-4" />
          <span>Invite Caregiver</span>
        </button>
      </div>

      {/* Clean Content Area */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
        <EmptyState
          icon={Users}
          title="No caregiver connections yet"
          description="Assigned caregivers and supervised patient profiles will appear here once connected."
          actionText="Connect Caregiver"
        />
      </div>
    </div>
  );
};

export default Caregivers;
