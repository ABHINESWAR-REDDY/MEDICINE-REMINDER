import React, { useState, useEffect } from 'react';
import { Activity, Plus, Edit2, Trash2, X, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import medicationService from '../../api/medicationService';
import EmptyState from '../common/EmptyState';
import { formatLocalDate } from '../../utils/dateTime';

export const Conditions = () => {
  const [conditions, setConditions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCondition, setEditingCondition] = useState(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');

  const loadConditions = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await medicationService.listConditions();
      setConditions(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load conditions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConditions();
  }, []);

  const openAddModal = () => {
    setEditingCondition(null);
    setName('');
    setDescription('');
    setModalError('');
    setIsModalOpen(true);
  };

  const openEditModal = (cond) => {
    setEditingCondition(cond);
    setName(cond.name);
    setDescription(cond.description || '');
    setModalError('');
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingCondition(null);
    setName('');
    setDescription('');
    setModalError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setModalError('Condition name is required.');
      return;
    }

    setIsSubmitting(true);
    setModalError('');
    try {
      if (editingCondition) {
        await medicationService.updateCondition(editingCondition.id, {
          name: name.trim(),
          description: description.trim() || null,
        });
        setSuccessMsg('Condition updated successfully!');
      } else {
        await medicationService.createCondition({
          name: name.trim(),
          description: description.trim() || null,
        });
        setSuccessMsg('Condition added successfully!');
      }
      closeModal();
      await loadConditions();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setModalError(err.response?.data?.detail || err.message || 'Failed to save condition.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id, condName) => {
    if (!window.confirm(`Are you sure you want to delete condition "${condName}"?`)) {
      return;
    }

    try {
      await medicationService.deleteCondition(id);
      setSuccessMsg('Condition deleted successfully.');
      await loadConditions();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete condition.');
    }
  };

  return (
    <div className="space-y-6 w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Conditions & Diseases</h2>
          <p className="text-sm text-slate-400 mt-1">
            Track diagnosed medical conditions to associate with prescribed treatments
          </p>
        </div>
        <button
          type="button"
          onClick={openAddModal}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-400 hover:bg-teal-300 text-slate-950 font-semibold text-xs rounded-xl shadow-sm transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Add Condition</span>
        </button>
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
      ) : conditions.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
          <EmptyState
            icon={Activity}
            title="No conditions added yet."
            description="Add your diagnosed medical conditions (e.g. Hypertension, Diabetes) to link them with your medications."
            actionText="Add Condition"
            onAction={openAddModal}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {conditions.map((cond) => (
            <div
              key={cond.id}
              className="bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 space-y-3 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
                    <Activity className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-sm text-white">{cond.name}</h3>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => openEditModal(cond)}
                    className="p-1.5 text-slate-400 hover:text-teal-300 hover:bg-slate-800 rounded-lg transition-colors"
                    title="Edit Condition"
                    aria-label={`Edit ${cond.name}`}
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(cond.id, cond.name)}
                    className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                    title="Delete Condition"
                    aria-label={`Delete ${cond.name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {cond.description ? (
                <p className="text-xs text-slate-400 leading-relaxed pl-1">{cond.description}</p>
              ) : (
                <p className="text-[11px] text-slate-500 italic pl-1">No additional description recorded.</p>
              )}

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
                <span>Created {formatLocalDate(cond.created_at)}</span>
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
                {editingCondition ? 'Edit Condition' : 'Add New Condition'}
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
              <div>
                <label htmlFor="condName" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Condition / Disease Name <span className="text-teal-400">*</span>
                </label>
                <input
                  id="condName"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Hypertension, Type 2 Diabetes"
                  className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                />
              </div>

              <div>
                <label htmlFor="condDesc" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Description / Notes (Optional)
                </label>
                <textarea
                  id="condDesc"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Clinical notes, diagnostic details, severity level..."
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
                  disabled={isSubmitting || !name.trim()}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-teal-400 hover:bg-teal-300 text-slate-950 font-semibold text-xs rounded-xl shadow-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>{editingCondition ? 'Update Condition' : 'Save Condition'}</span>
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

export default Conditions;
