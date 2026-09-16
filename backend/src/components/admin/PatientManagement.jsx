import React, { useState, useEffect } from 'react';
import { adminService } from '../../api/adminService';
import {
  Users,
  User,
  Power,
  PowerOff,
  Pill,
  Loader2,
  RefreshCw,
  Search,
  Calendar,
  ShieldAlert,
  UserCheck,
  UserX,
} from 'lucide-react';

export const PatientManagement = () => {
  const [patients, setPatients] = useState([]);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const fetchPatients = async () => {
    setLoading(true);
    setError(null);
    try {
      const filter = statusFilter === 'ALL' ? null : statusFilter;
      const data = await adminService.getPatients(filter, searchQuery);
      setPatients(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load patients:', err);
      const errorMsg =
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        err.message ||
        'Failed to load patients.';
      setError(errorMsg);
      setPatients([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, [statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchPatients();
  };

  const handleToggleActive = async (patient) => {
    setActionLoading(patient.id);
    setMessage(null);
    try {
      const res = await adminService.togglePatientActive(patient.id);
      setMessage({
        type: 'success',
        text: res.message || `Patient ${patient.name} status updated successfully.`,
      });
      fetchPatients();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail?.message || 'Failed to update patient status.',
      });
    } finally {
      setActionLoading(null);
    }
  };

  const formatAccountCreatedDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      const d = new Date(dateString);
      if (isNaN(d.getTime())) return 'N/A';
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const year = d.getFullYear();
      return `${day}-${month}-${year}`;
    } catch {
      return 'N/A';
    }
  };

  const getEmptyStateMessage = () => {
    switch (statusFilter) {
      case 'ACTIVE':
        return 'No active registered patients found.';
      case 'INACTIVE':
        return 'No inactive registered patients found.';
      case 'ALL':
      default:
        return 'No registered patients found.';
    }
  };

  // Client-side search refinement if typing without pressing enter
  const filteredPatients = patients.filter((p) =>
    (p.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.email || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.assigned_caregiver_name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">Patient Directory & Management</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">
              Total Patients: {patients.length}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Live database overview of registered patient accounts, caregiver supervision, and medication tracking.
          </p>
        </div>
        <button
          onClick={fetchPatients}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold self-start transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Notifications */}
      {message && (
        <div
          className={`p-4 rounded-xl text-xs font-medium border flex items-center justify-between ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
          }`}
        >
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="flex items-center gap-1.5 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800 w-full sm:w-auto overflow-x-auto">
          {['ALL', 'ACTIVE', 'INACTIVE'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                statusFilter === st
                  ? 'bg-teal-500 text-slate-950 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search patients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
          />
        </form>
      </div>

      {/* Main Table Container */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin mx-auto mb-2" />
            <p className="text-xs text-slate-400">Loading patients from database...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center bg-rose-500/5 border-rose-500/20 text-rose-400">
            <ShieldAlert className="w-10 h-10 mx-auto text-rose-400 mb-2" />
            <p className="text-sm font-semibold">{error}</p>
            <button
              onClick={fetchPatients}
              className="mt-3 px-4 py-2 bg-rose-500/20 hover:bg-rose-500/30 rounded-xl text-xs font-semibold text-rose-300 transition-colors"
            >
              Try Again
            </button>
          </div>
        ) : filteredPatients.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Users className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm font-medium">{getEmptyStateMessage()}</p>
            <p className="text-xs text-slate-500 mt-1">No database records match current criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Patient</th>
                  <th className="py-3.5 px-4 font-semibold">Email</th>
                  <th className="py-3.5 px-4 font-semibold">Account Created</th>
                  <th className="py-3.5 px-4 font-semibold">Account Status</th>
                  <th className="py-3.5 px-4 font-semibold">Assigned Caregiver</th>
                  <th className="py-3.5 px-4 font-semibold">Medications</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredPatients.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center text-teal-400 font-bold text-xs border border-slate-700">
                          {p.name ? p.name.charAt(0).toUpperCase() : 'P'}
                        </div>
                        <div>
                          <span className="font-semibold text-white block leading-tight">{p.name}</span>
                          <span className="font-mono text-[10px] text-teal-400 font-semibold bg-teal-500/10 px-1.5 py-0.5 rounded border border-teal-500/20 inline-block mt-0.5">
                            {p.employee_id || `PT${String(p.id).padStart(6, '0')}`}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{p.email}</td>
                    <td className="py-3 px-4 text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        <span>{formatAccountCreatedDate(p.created_at)}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                          p.is_active
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        }`}
                      >
                        {p.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {p.assigned_caregiver_name ? (
                        <div>
                          <div className="flex items-center gap-1.5 text-indigo-300 font-medium">
                            <UserCheck className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                            <span className="font-semibold text-white">{p.assigned_caregiver_name}</span>
                          </div>
                          <span className="font-mono text-[10px] text-blue-400 font-semibold bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20 inline-block mt-1">
                            {p.assigned_caregiver_employee_id || (p.assigned_caregiver_id ? `CG${String(p.assigned_caregiver_id).padStart(6, '0')}` : '')}
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-500 italic">No caregiver assigned</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <Pill className="w-3.5 h-3.5 text-teal-400" />
                        <span className="font-medium">{p.medications_count} medications</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleToggleActive(p)}
                        disabled={actionLoading === p.id}
                        className={`p-1.5 rounded-lg text-xs font-semibold transition-colors ${
                          p.is_active
                            ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20'
                            : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20'
                        }`}
                        title={p.is_active ? 'Deactivate account' : 'Activate account'}
                      >
                        {p.is_active ? <PowerOff className="w-3.5 h-3.5" /> : <Power className="w-3.5 h-3.5" />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientManagement;
