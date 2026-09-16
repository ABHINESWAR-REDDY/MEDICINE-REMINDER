import React, { useState, useEffect } from 'react';
import { FileText, Plus, Edit2, Trash2, X, Loader2, AlertCircle, CheckCircle, Calendar, UserCheck } from 'lucide-react';
import medicationService from '../../api/medicationService';
import EmptyState from '../common/EmptyState';

export const Prescriptions = () => {
  const [prescriptions, setPrescriptions] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRx, setEditingRx] = useState(null);
  const [prescriptionNumber, setPrescriptionNumber] = useState('');
  const [doctorName, setDoctorName] = useState('');
  const [issueDate, setIssueDate] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [status, setStatus] = useState('ACTIVE');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');

  const loadPrescriptions = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await medicationService.listPrescriptions(statusFilter || null);
      setPrescriptions(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load prescriptions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPrescriptions();
  }, [statusFilter]);

  const openAddModal = () => {
    setEditingRx(null);
    setPrescriptionNumber('');
    setDoctorName('');
    setIssueDate('');
    setExpiryDate('');
    setStatus('ACTIVE');
    setNotes('');
    setModalError('');
    setIsModalOpen(true);
  };

  const openEditModal = (rx) => {
    setEditingRx(rx);
    setPrescriptionNumber(rx.prescription_number || '');
    setDoctorName(rx.doctor_name || '');
    setIssueDate(rx.issue_date || '');
    setExpiryDate(rx.expiry_date || '');
    setStatus(rx.status || 'ACTIVE');
    setNotes(rx.notes || '');
    setModalError('');
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingRx(null);
    setModalError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (issueDate && expiryDate && expiryDate < issueDate) {
      setModalError('Expiry date cannot be before issue date.');
      return;
    }

    setIsSubmitting(true);
    setModalError('');
    try {
      const payload = {
        prescription_number: prescriptionNumber.trim() || null,
        doctor_name: doctorName.trim() || null,
        issue_date: issueDate || null,
        expiry_date: expiryDate || null,
        status: status,
        notes: notes.trim() || null,
      };

      if (editingRx) {
        await medicationService.updatePrescription(editingRx.id, payload);
        setSuccessMsg('Prescription updated successfully!');
      } else {
        await medicationService.createPrescription(payload);
        setSuccessMsg('Prescription added successfully!');
      }
      closeModal();
      await loadPrescriptions();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setModalError(err.response?.data?.detail || err.message || 'Failed to save prescription.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id, rxNumber) => {
    const label = rxNumber || 'this prescription';
    if (!window.confirm(`Are you sure you want to delete ${label}?`)) {
      return;
    }

    try {
      await medicationService.deletePrescription(id);
      setSuccessMsg('Prescription deleted successfully.');
      await loadPrescriptions();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete prescription.');
    }
  };

  const getStatusBadge = (rxStatus) => {
    switch (rxStatus) {
      case 'ACTIVE':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'EXPIRED':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'CANCELLED':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className="space-y-6 w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Prescriptions</h2>
          <p className="text-sm text-slate-400 mt-1">
            Manage provider prescription records, validity terms, and doctor instructions
          </p>
        </div>
        <button
          type="button"
          onClick={openAddModal}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-400 hover:bg-teal-300 text-slate-950 font-semibold text-xs rounded-xl shadow-sm transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Add Prescription</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2">
        {['', 'ACTIVE', 'EXPIRED', 'CANCELLED'].map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setStatusFilter(tab)}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-colors ${
              statusFilter === tab
                ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30'
                : 'text-slate-400 hover:bg-slate-900 border border-transparent'
            }`}
          >
            {tab === '' ? 'All Prescriptions' : tab.charAt(0) + tab.slice(1).toLowerCase()}
          </button>
        ))}
      </div>

      {/* Global Alerts */}
      {successMsg && (
        <div role="status" className="p-3.5 rounded-xl text-xs flex items-center gap-2 bg-teal-500/10 border border-teal-500/20 text-teal-300">
          <CheckCircle className="w-4 h-4 text-teal-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div role="alert" className="p-3.5 rounded-xl text-xs flex items-center gap-2 bg-rose-500/10 border border-rose-500/20 text-rose-300">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Content Area */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <Loader2 className="w-6 h-6 animate-spin text-teal-400" />
        </div>
      ) : prescriptions.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
          <EmptyState
            icon={FileText}
            title="No prescriptions added yet."
            description="Add your clinical prescription details to link medicines with verified provider recommendations."
            actionText="Add Prescription"
            onAction={openAddModal}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {prescriptions.map((rx) => (
            <div
              key={rx.id}
              className="bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 space-y-4 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm text-white">
                      {rx.prescription_number || `Prescription #${rx.id}`}
                    </h3>
                    {rx.doctor_name && (
                      <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                        <UserCheck className="w-3 h-3 text-slate-500" />
                        <span>{rx.doctor_name}</span>
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getStatusBadge(rx.status)}`}>
                    {rx.status}
                  </span>
                  <button
                    type="button"
                    onClick={() => openEditModal(rx)}
                    className="p-1.5 text-slate-400 hover:text-teal-300 hover:bg-slate-800 rounded-lg transition-colors"
                    title="Edit Prescription"
                    aria-label={`Edit ${rx.prescription_number || rx.id}`}
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(rx.id, rx.prescription_number)}
                    className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                    title="Delete Prescription"
                    aria-label={`Delete ${rx.prescription_number || rx.id}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {rx.notes && (
                <p className="text-xs text-slate-400 leading-relaxed pl-1">{rx.notes}</p>
              )}

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <div className="flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  <span>Issued: {rx.issue_date || '—'}</span>
                </div>
                <div>
                  <span>Expires: {rx.expiry_date || 'No expiration'}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-white">
                {editingRx ? 'Edit Prescription' : 'Add New Prescription'}
              </h3>
              <button
                type="button"
                onClick={closeModal}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {modalError && (
              <div role="alert" className="p-3 rounded-xl text-xs flex items-center gap-2 bg-rose-500/10 border border-rose-500/20 text-rose-300">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="rxNum" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Rx / Number
                  </label>
                  <input
                    id="rxNum"
                    type="text"
                    value={prescriptionNumber}
                    onChange={(e) => setPrescriptionNumber(e.target.value)}
                    placeholder="e.g. RX-99401"
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
                <div>
                  <label htmlFor="rxDoc" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Doctor / Prescriber
                  </label>
                  <input
                    id="rxDoc"
                    type="text"
                    value={doctorName}
                    onChange={(e) => setDoctorName(e.target.value)}
                    placeholder="e.g. Dr. Smith"
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="rxIssue" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Issue Date
                  </label>
                  <input
                    id="rxIssue"
                    type="date"
                    value={issueDate}
                    onChange={(e) => setIssueDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
                <div>
                  <label htmlFor="rxExpiry" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Expiry Date
                  </label>
                  <input
                    id="rxExpiry"
                    type="date"
                    value={expiryDate}
                    onChange={(e) => setExpiryDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="rxStatus" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Prescription Status
                </label>
                <select
                  id="rxStatus"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="EXPIRED">EXPIRED</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </div>

              <div>
                <label htmlFor="rxNotes" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Notes & Refill Instructions
                </label>
                <textarea
                  id="rxNotes"
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. 3 refills remaining, take with food"
                  className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-teal-400 hover:bg-teal-300 text-slate-950 font-semibold text-xs rounded-xl shadow-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>{editingRx ? 'Update Prescription' : 'Save Prescription'}</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Prescriptions;
