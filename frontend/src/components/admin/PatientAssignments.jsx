import React, { useState, useEffect } from 'react';
import { adminService } from '../../api/adminService';
import {
  UserPlus,
  UserCheck,
  Trash2,
  Loader2,
  RefreshCw,
  Search,
  Shield,
  User,
  AlertCircle,
  CheckCircle2,
  Users,
} from 'lucide-react';

export const PatientAssignments = () => {
  const [assignments, setAssignments] = useState([]);
  const [caregivers, setCaregivers] = useState([]);
  const [patients, setPatients] = useState([]);
  const [caregiverId, setCaregiverId] = useState('');
  const [patientId, setPatientId] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [assignmentsData, caregiversData, patientsData] = await Promise.all([
        adminService.getAssignments(),
        adminService.getCaregivers('APPROVED'),
        adminService.getPatients(),
      ]);
      setAssignments(assignmentsData || []);
      setCaregivers(caregiversData || []);
      setPatients(patientsData || []);
    } catch (err) {
      console.error('Failed to load assignment data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Compute live assigned patient count per caregiver
  const getCaregiverAssignedCount = (cgId) => {
    return assignments.filter((a) => a.caregiver_id === cgId).length;
  };

  // 1. Available Caregivers: Only show caregivers who have NOT reached the 5-patient limit
  const availableCaregivers = caregivers.filter((cg) => getCaregiverAssignedCount(cg.id) < 5);

  // 2. Available Patients: Only show patients who are NOT currently assigned to any caregiver
  const assignedPatientIds = new Set(assignments.map((a) => a.patient_id));
  const availablePatients = patients.filter((p) => !assignedPatientIds.has(p.id));

  const selectedCaregiver = availableCaregivers.find((c) => c.id === parseInt(caregiverId, 10)) || caregivers.find((c) => c.id === parseInt(caregiverId, 10));
  const selectedCaregiverCount = selectedCaregiver ? getCaregiverAssignedCount(selectedCaregiver.id) : 0;
  const isCaregiverAtMaxCapacity = selectedCaregiverCount >= 5;

  const handleAssign = async (e) => {
    e.preventDefault();
    if (!caregiverId || !patientId) return;

    if (isCaregiverAtMaxCapacity) {
      setMessage({
        type: 'error',
        text: `Caregiver ${selectedCaregiver?.name} has reached the maximum capacity limit of 5 assigned patients.`,
      });
      return;
    }

    setCreating(true);
    setMessage(null);
    try {
      const res = await adminService.assignPatient(parseInt(caregiverId, 10), parseInt(patientId, 10));
      setMessage({ type: 'success', text: res.message || 'Patient assigned successfully.' });
      setCaregiverId('');
      setPatientId('');
      fetchData();
    } catch (err) {
      const errorText =
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        'Assignment failed. Please check the requirements.';
      setMessage({ type: 'error', text: errorText });
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id) => {
    if (!window.confirm('Are you sure you want to revoke this patient assignment?')) return;
    try {
      await adminService.revokeAssignment(id);
      setMessage({ type: 'success', text: 'Assignment revoked successfully.' });
      fetchData();
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to revoke assignment.' });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Patient-Caregiver Assignments</h1>
          <p className="text-sm text-slate-400 mt-1">
            Link registered patients to approved caregiver supervisors. (Maximum 5 patients per caregiver)
          </p>
        </div>
        <button
          onClick={fetchData}
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
          <div className="flex items-center gap-2">
            {message.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{message.text}</span>
          </div>
          <button onClick={() => setMessage(null)} className="text-slate-400 hover:text-white font-bold ml-3">✕</button>
        </div>
      )}

      {/* Assignment Creation Form */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-teal-400" />
            Assign Patient to Caregiver
          </h2>
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/20">
            Policy: Max 5 Patients per Caregiver
          </span>
        </div>

        <form onSubmit={handleAssign} className="grid grid-cols-1 md:grid-cols-12 gap-4">
          {/* Caregiver Selection Dropdown */}
          <div className="md:col-span-5">
            <label htmlFor="caregiverSelect" className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Select Caregiver
            </label>
            <select
              id="caregiverSelect"
              required
              value={caregiverId}
              onChange={(e) => setCaregiverId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-teal-500 transition-colors"
            >
              <option value="">
                {availableCaregivers.length === 0
                  ? '-- No Available Caregivers (All full at 5/5) --'
                  : `-- Choose Approved Caregiver (${availableCaregivers.length} available) --`}
              </option>
              {availableCaregivers.map((cg) => {
                const assignedCount = getCaregiverAssignedCount(cg.id);
                const empId = cg.employee_id || `CG${String(cg.id).padStart(6, '0')}`;
                return (
                  <option key={cg.id} value={cg.id}>
                    {cg.name} ({empId}) — {assignedCount}/5 patients assigned
                  </option>
                );
              })}
            </select>

            {/* Selected Caregiver Live Capacity Indicator */}
            {selectedCaregiver && (
              <div className="mt-2 flex items-center justify-between text-[11px] px-1">
                <span className="text-slate-400">
                  ID: <strong className="font-mono text-teal-300">{selectedCaregiver.employee_id || `CG${String(selectedCaregiver.id).padStart(6, '0')}`}</strong>
                </span>
                <span
                  className={`font-semibold ${
                    isCaregiverAtMaxCapacity ? 'text-rose-400' : 'text-emerald-400'
                  }`}
                >
                  Capacity: {selectedCaregiverCount}/5 assigned ({5 - selectedCaregiverCount} slots left)
                </span>
              </div>
            )}
          </div>

          {/* Patient Selection Dropdown */}
          <div className="md:col-span-4">
            <label htmlFor="patientSelect" className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Select Patient
            </label>
            <select
              id="patientSelect"
              required
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-teal-500 transition-colors"
            >
              <option value="">
                {patients.length === 0
                  ? 'No patients available'
                  : availablePatients.length === 0
                  ? 'No patients available'
                  : `-- Choose Registered Patient (${availablePatients.length} unassigned) --`}
              </option>
              {availablePatients.map((p) => {
                const empId = p.employee_id || `PT${String(p.id).padStart(6, '0')}`;
                return (
                  <option key={p.id} value={p.id}>
                    {p.name} ({empId}) — {p.email}
                  </option>
                );
              })}
            </select>
          </div>

          {/* Action Button */}
          <div className="md:col-span-3 flex items-end">
            <button
              type="submit"
              disabled={creating || !caregiverId || !patientId || isCaregiverAtMaxCapacity || availablePatients.length === 0}
              className="w-full py-2.5 px-4 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-teal-500/10"
            >
              {creating ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Assigning...</span>
                </>
              ) : (
                <>
                  <UserCheck className="w-3.5 h-3.5" />
                  <span>Create Assignment</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Active Assignments Table */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Users className="w-4 h-4 text-teal-400" />
            Active Assignments ({assignments.length})
          </h2>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin mx-auto mb-2" />
            <p className="text-xs text-slate-400">Loading assignments...</p>
          </div>
        ) : assignments.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <UserCheck className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm font-medium">No active caregiver-patient assignments.</p>
            <p className="text-xs text-slate-500 mt-1">Use the form above to assign a patient to a caregiver.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Caregiver</th>
                  <th className="py-3.5 px-4 font-semibold">Caregiver Email</th>
                  <th className="py-3.5 px-4 font-semibold">Patient</th>
                  <th className="py-3.5 px-4 font-semibold">Patient Email</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {assignments.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-3 px-4">
                      <div>
                        <span className="font-semibold text-white block leading-tight">{a.caregiver_name}</span>
                        <span className="font-mono text-[10px] text-blue-400 font-semibold bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20 inline-block mt-0.5">
                          {a.caregiver_employee_id || `CG${String(a.caregiver_id).padStart(6, '0')}`}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{a.caregiver_email}</td>
                    <td className="py-3 px-4">
                      <div>
                        <span className="font-semibold text-teal-300 block leading-tight">{a.patient_name}</span>
                        <span className="font-mono text-[10px] text-teal-400 font-semibold bg-teal-500/10 px-1.5 py-0.5 rounded border border-teal-500/20 inline-block mt-0.5">
                          {a.patient_employee_id || `PT${String(a.patient_id).padStart(6, '0')}`}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{a.patient_email}</td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleRevoke(a.id)}
                        className="px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 font-semibold text-xs transition-colors"
                      >
                        Revoke
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

export default PatientAssignments;
