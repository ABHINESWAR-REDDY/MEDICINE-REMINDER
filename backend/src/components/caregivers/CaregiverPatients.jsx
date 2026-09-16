import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { caregiverService } from '../../api/caregiverService';
import {
  Users,
  Search,
  ChevronRight,
  Loader2,
  RefreshCw,
  Activity,
  Pill,
} from 'lucide-react';

export const CaregiverPatients = () => {
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchPatients = async () => {
    setLoading(true);
    try {
      const data = await caregiverService.getPatients();
      setPatients(data);
    } catch (err) {
      console.error('Failed to load assigned patients:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, []);

  const filtered = patients.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Assigned Patients</h1>
          <p className="text-sm text-slate-400 mt-1">Supervise medication schedules and adherence records.</p>
        </div>
        <button
          onClick={fetchPatients}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="relative w-full sm:w-72">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Search assigned patients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
        />
      </div>

      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin mx-auto mb-2" />
            <p className="text-xs text-slate-400">Loading patients...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Users className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm font-medium">No assigned patients found.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-5">
            {filtered.map((pt) => (
              <div
                key={pt.id}
                className="p-5 bg-slate-950/70 border border-slate-800/80 rounded-2xl flex flex-col justify-between space-y-4 hover:border-slate-700 transition-colors"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-bold text-white text-base leading-tight">{pt.name}</h3>
                      <span className="font-mono text-[10px] text-teal-400 font-semibold bg-teal-500/10 px-1.5 py-0.5 rounded border border-teal-500/20 inline-block mt-1">
                        {pt.employee_id || `PT${String(pt.id).padStart(6, '0')}`}
                      </span>
                      <p className="text-xs text-slate-400 mt-1">{pt.email}</p>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        pt.adherence_status === 'Good'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : pt.adherence_status === 'Needs Attention'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                      }`}
                    >
                      {pt.adherence_percentage}%
                    </span>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800/60">
                      <span className="text-[10px] text-slate-500 uppercase block">Medications</span>
                      <span className="font-bold text-white">{pt.medications_count} Active</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800/60">
                      <span className="text-[10px] text-slate-500 uppercase block">Today Taken</span>
                      <span className="font-bold text-emerald-400">
                        {pt.today_doses_taken}/{pt.today_doses_total}
                      </span>
                    </div>
                  </div>
                </div>

                <Link
                  to={`/caregiver/patients/${pt.id}`}
                  className="w-full py-2 px-3 rounded-xl bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 font-semibold text-xs transition-colors flex items-center justify-center gap-1.5"
                >
                  <span>Inspect Medical Profile</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CaregiverPatients;
