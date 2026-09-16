import React, { useState, useEffect } from 'react';
import { adminService } from '../../api/adminService';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Power,
  PowerOff,
  UserPlus,
  Loader2,
  RefreshCw,
  Search,
  Calendar,
} from 'lucide-react';

export const CaregiverManagement = () => {
  const [caregivers, setCaregivers] = useState([]);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [message, setMessage] = useState(null);

  const fetchCaregivers = async () => {
    setLoading(true);
    try {
      const filter = statusFilter === 'ALL' ? null : statusFilter;
      const data = await adminService.getCaregivers(filter);
      setCaregivers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load caregivers:', err);
      setCaregivers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCaregivers();
  }, [statusFilter]);

  const handleApprove = async (id, name) => {
    setActionLoading(id);
    try {
      const res = await adminService.approveCaregiver(id);
      setMessage({
        type: 'success',
        text: res?.message || `Caregiver ${name} approved and notification email sent.`
      });
      fetchCaregivers();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail?.message || 'Failed to approve.' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id, name) => {
    if (!window.confirm(`Reject caregiver ${name}?`)) return;
    setActionLoading(id);
    try {
      const res = await adminService.rejectCaregiver(id);
      setMessage({
        type: 'success',
        text: res?.message || `Caregiver ${name} rejected and notification email sent.`
      });
      fetchCaregivers();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail?.message || 'Failed to reject.' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleActive = async (cg) => {
    setActionLoading(cg.id);
    try {
      if (cg.is_active) {
        await adminService.deactivateCaregiver(cg.id);
        setMessage({ type: 'success', text: `Caregiver ${cg.name} deactivated.` });
      } else {
        await adminService.activateCaregiver(cg.id);
        setMessage({ type: 'success', text: `Caregiver ${cg.name} activated.` });
      }
      fetchCaregivers();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail?.message || 'Action failed.' });
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
      case 'PENDING':
        return 'No pending caregiver registrations.';
      case 'APPROVED':
        return 'No approved caregivers found.';
      case 'REJECTED':
        return 'No rejected caregivers found.';
      case 'ACTIVE':
        return 'No active caregivers found.';
      case 'INACTIVE':
        return 'No inactive caregivers found.';
      case 'ALL':
      default:
        return 'No caregivers found.';
    }
  };

  const filtered = caregivers.filter((c) =>
    (c.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (c.email || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Caregiver Directory & Approvals</h1>
          <p className="text-sm text-slate-400 mt-1">Manage healthcare professional credentials, approvals, and access.</p>
        </div>
        <button
          onClick={fetchCaregivers}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

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

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="flex items-center gap-1.5 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800 w-full sm:w-auto overflow-x-auto">
          {['ALL', 'PENDING', 'APPROVED', 'REJECTED', 'ACTIVE', 'INACTIVE'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                statusFilter === st
                  ? 'bg-teal-500 text-slate-950 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search caregivers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin mx-auto mb-2" />
            <p className="text-xs text-slate-400">Loading caregivers...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <ShieldCheck className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm font-medium">{getEmptyStateMessage()}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Caregiver</th>
                  <th className="py-3.5 px-4 font-semibold">Email</th>
                  <th className="py-3.5 px-4 font-semibold">Account Created</th>
                  <th className="py-3.5 px-4 font-semibold">Approval</th>
                  <th className="py-3.5 px-4 font-semibold">Active Status</th>
                  <th className="py-3.5 px-4 font-semibold">Assigned Patients</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filtered.map((cg) => (
                  <tr key={cg.id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-3 px-4">
                      <div>
                        <span className="font-semibold text-white block leading-tight">{cg.name}</span>
                        <span className="font-mono text-[10px] text-blue-400 font-semibold bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20 inline-block mt-0.5">
                          {cg.employee_id || `CG${String(cg.id).padStart(6, '0')}`}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{cg.email}</td>
                    <td className="py-3 px-4 text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        <span>{formatAccountCreatedDate(cg.created_at)}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                          cg.approval_status === 'APPROVED'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : cg.approval_status === 'REJECTED'
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        }`}
                      >
                        {cg.approval_status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                          cg.is_active
                            ? 'bg-teal-500/10 text-teal-400 border-teal-500/20'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {cg.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-medium">{cg.assigned_patients_count} patients</td>
                    <td className="py-3 px-4 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        {cg.approval_status === 'PENDING' && (
                          <>
                            <button
                              onClick={() => handleApprove(cg.id, cg.name)}
                              disabled={actionLoading === cg.id}
                              className="px-2.5 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleReject(cg.id, cg.name)}
                              disabled={actionLoading === cg.id}
                              className="px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs"
                            >
                              Reject
                            </button>
                          </>
                        )}
                        {cg.approval_status === 'APPROVED' && (
                          <button
                            onClick={() => handleToggleActive(cg)}
                            disabled={actionLoading === cg.id}
                            className={`p-1.5 rounded-lg text-xs font-semibold transition-colors ${
                              cg.is_active
                                ? 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/20'
                                : 'bg-teal-500/10 hover:bg-teal-500/20 text-teal-400 border border-teal-500/20'
                            }`}
                            title={cg.is_active ? 'Deactivate account' : 'Activate account'}
                          >
                            {cg.is_active ? <PowerOff className="w-3.5 h-3.5" /> : <Power className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>
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

export default CaregiverManagement;
