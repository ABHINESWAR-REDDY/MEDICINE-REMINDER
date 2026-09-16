import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Pill,
  Plus,
  Edit2,
  Trash2,
  X,
  Loader2,
  AlertCircle,
  CheckCircle,
  Calendar,
  Clock,
  Activity,
  FileText,
  PowerOff,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import medicationService from '../../api/medicationService';
import EmptyState from '../common/EmptyState';

const DOSAGE_UNITS = ['mg', 'mcg', 'g', 'ml', 'tablet', 'capsule', 'drop', 'unit'];
const MEDICINE_FORMS = ['TABLET', 'CAPSULE', 'SYRUP', 'INJECTION', 'DROPS', 'CREAM', 'OTHER'];
const SCHEDULE_FREQUENCIES = [
  { id: 'ONCE_DAILY', label: 'Once Daily', defaultTimes: ['08:00'] },
  { id: 'TWICE_DAILY', label: 'Twice Daily', defaultTimes: ['08:00', '20:00'] },
  { id: 'THREE_TIMES_DAILY', label: 'Three Times Daily', defaultTimes: ['08:00', '14:00', '20:00'] },
  { id: 'FOUR_TIMES_DAILY', label: 'Four Times Daily', defaultTimes: ['08:00', '12:00', '16:00', '20:00'] },
  { id: 'CUSTOM', label: 'Custom Times', defaultTimes: ['09:00'] },
];

/**
 * Format ISO YYYY-MM-DD date string to DD-MM-YYYY for user presentation
 */
const formatDisplayDate = (dateStr) => {
  if (!dateStr) return '';
  const match = String(dateStr).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) {
    return `${match[3]}-${match[2]}-${match[1]}`;
  }
  return dateStr;
};

/**
 * Clean user-friendly error formatting adhering to Phase 2 error guidelines
 */
const formatErrorMessage = (err, fallback = 'Failed to save medication record.') => {
  if (err?.response) {
    const status = err.response.status;
    const detail = err.response.data?.detail;

    if (status === 401) {
      return 'Your session has expired. Please log in again.';
    }
    if (status === 403) {
      return 'You do not have permission to add medication.';
    }
    if (status === 422) {
      if (typeof detail === 'string') {
        return detail;
      }
      if (Array.isArray(detail) && detail.length > 0) {
        return detail.map((d) => d.msg.replace('Value error, ', '')).join('. ');
      }
      return 'Please review the highlighted fields and try again.';
    }
    if (status >= 500) {
      return 'Unable to save medication. Please try again.';
    }
    if (typeof detail === 'string') {
      return detail;
    }
  }
  return err?.message || fallback;
};

export const Medicines = () => {
  const { t } = useTranslation();
  const [medicines, setMedicines] = useState([]);
  const [conditions, setConditions] = useState([]);
  const [prescriptions, setPrescriptions] = useState([]);
  const [statusFilter, setStatusFilter] = useState('active'); // 'active' | 'all'
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMed, setEditingMed] = useState(null);

  // Form Fields
  const [name, setName] = useState('');
  const [dosageAmount, setDosageAmount] = useState('');
  const [dosageUnit, setDosageUnit] = useState('mg');
  const [quantity, setQuantity] = useState('');
  const [medicineForm, setMedicineForm] = useState('TABLET');
  const [instructions, setInstructions] = useState('');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState('');
  const [conditionId, setConditionId] = useState('');
  const [prescriptionId, setPrescriptionId] = useState('');

  // Schedule configuration inside Add modal
  const [createScheduleNow, setCreateScheduleNow] = useState(true);
  const [frequencyType, setFrequencyType] = useState('TWICE_DAILY');
  const [scheduledTimes, setScheduledTimes] = useState(['08:00', '20:00']);
  const [doseQuantity, setDoseQuantity] = useState('1.0');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');

  // Direct Schedule Modal State for specific medicine card
  const [schedulingMed, setSchedulingMed] = useState(null);
  const [scheduleModalError, setScheduleModalError] = useState('');
  const [isSchedulingSubmitting, setIsSchedulingSubmitting] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const [medsData, condsData, rxData] = await Promise.all([
        medicationService.listMedicines(statusFilter === 'active' ? true : null),
        medicationService.listConditions(),
        medicationService.listPrescriptions(),
      ]);
      setMedicines(medsData);
      setConditions(condsData);
      setPrescriptions(rxData);
    } catch (err) {
      setError(formatErrorMessage(err, 'Failed to load medication records.'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const handleFrequencyChange = (freqId) => {
    setFrequencyType(freqId);
    const found = SCHEDULE_FREQUENCIES.find((f) => f.id === freqId);
    if (found) {
      setScheduledTimes(found.defaultTimes);
    }
  };

  const handleTimeChange = (index, value) => {
    const newTimes = [...scheduledTimes];
    newTimes[index] = value;
    setScheduledTimes(newTimes);
  };

  const addCustomTime = () => {
    setScheduledTimes([...scheduledTimes, '12:00']);
  };

  const removeCustomTime = (index) => {
    if (scheduledTimes.length <= 1) return;
    setScheduledTimes(scheduledTimes.filter((_, i) => i !== index));
  };

  const openScheduleModal = (med) => {
    setSchedulingMed(med);
    setFrequencyType('TWICE_DAILY');
    setScheduledTimes(['08:00', '20:00']);
    setDoseQuantity('1.0');
    setStartDate(med.start_date || new Date().toISOString().split('T')[0]);
    setEndDate(med.end_date || '');
    setScheduleModalError('');
  };

  const closeScheduleModal = () => {
    setSchedulingMed(null);
    setScheduleModalError('');
  };

  const handleDirectScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!schedulingMed) return;

    const numDoseQty = parseFloat(doseQuantity);
    if (isNaN(numDoseQty) || numDoseQty <= 0) {
      setScheduleModalError('Dose per intake must be greater than zero.');
      return;
    }
    if (!scheduledTimes || scheduledTimes.length === 0) {
      setScheduleModalError('Please specify at least one daily scheduled time.');
      return;
    }
    if (endDate && endDate < startDate) {
      setScheduleModalError('End date cannot be before start date.');
      return;
    }

    setIsSchedulingSubmitting(true);
    setScheduleModalError('');

    try {
      await medicationService.createMedicineSchedule(schedulingMed.id, {
        frequency_type: frequencyType,
        times_per_day: scheduledTimes.length,
        scheduled_times: scheduledTimes,
        dose_quantity: numDoseQty,
        start_date: startDate,
        end_date: endDate || null,
      });

      setSuccessMsg(`Dosage intake routine configured for "${schedulingMed.name}"!`);
      closeScheduleModal();
      await loadData();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setScheduleModalError(formatErrorMessage(err, 'Failed to save dosage schedule.'));
    } finally {
      setIsSchedulingSubmitting(false);
    }
  };

  const openAddModal = () => {
    setEditingMed(null);
    setName('');
    setDosageAmount('');
    setDosageUnit('mg');
    setQuantity('');
    setMedicineForm('TABLET');
    setInstructions('');
    setStartDate(new Date().toISOString().split('T')[0]);
    setEndDate('');
    setConditionId('');
    setPrescriptionId('');
    setCreateScheduleNow(true);
    setFrequencyType('TWICE_DAILY');
    setScheduledTimes(['08:00', '20:00']);
    setDoseQuantity('1.0');
    setModalError('');
    setIsModalOpen(true);
  };

  const openEditModal = (med) => {
    setEditingMed(med);
    setName(med.name);
    setDosageAmount(med.dosage_amount.toString());
    setDosageUnit(med.dosage_unit);
    setQuantity(med.quantity.toString());
    setMedicineForm(med.medicine_form);
    setInstructions(med.instructions || '');
    setStartDate(med.start_date);
    setEndDate(med.end_date || '');
    setConditionId(med.condition_id ? med.condition_id.toString() : '');
    setPrescriptionId(med.prescription_id ? med.prescription_id.toString() : '');
    setCreateScheduleNow(false);
    setModalError('');
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingMed(null);
    setModalError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setModalError('Medicine name is required.');
      return;
    }
    const numDose = parseFloat(dosageAmount);
    if (isNaN(numDose) || numDose <= 0) {
      setModalError('Dosage amount must be greater than zero.');
      return;
    }
    const numQty = parseInt(quantity, 10);
    if (isNaN(numQty) || numQty <= 0) {
      setModalError('Quantity must be greater than zero.');
      return;
    }
    if (endDate && endDate < startDate) {
      setModalError('End date cannot be before start date.');
      return;
    }
    if (!editingMed && createScheduleNow) {
      const numDoseQty = parseFloat(doseQuantity);
      if (isNaN(numDoseQty) || numDoseQty <= 0) {
        setModalError('Dose per intake must be greater than zero.');
        return;
      }
      if (!scheduledTimes || scheduledTimes.length === 0) {
        setModalError('Please specify at least one daily scheduled time.');
        return;
      }
    }

    setIsSubmitting(true);
    setModalError('');

    try {
      const payload = {
        name: name.trim(),
        dosage_amount: numDose,
        dosage_unit: dosageUnit,
        quantity: numQty,
        medicine_form: medicineForm,
        instructions: instructions.trim() || null,
        start_date: startDate,
        end_date: endDate || null,
        condition_id: conditionId ? parseInt(conditionId, 10) : null,
        prescription_id: prescriptionId ? parseInt(prescriptionId, 10) : null,
      };

      if (editingMed) {
        await medicationService.updateMedicine(editingMed.id, payload);
        setSuccessMsg('Medication updated successfully!');
      } else {
        const createdMed = await medicationService.createMedicine(payload);

        // Optionally attach initial schedule
        if (createScheduleNow && scheduledTimes.length > 0) {
          const numDoseQty = parseFloat(doseQuantity) || 1.0;
          try {
            await medicationService.createMedicineSchedule(createdMed.id, {
              frequency_type: frequencyType,
              times_per_day: scheduledTimes.length,
              scheduled_times: scheduledTimes,
              dose_quantity: numDoseQty,
              start_date: startDate,
              end_date: endDate || null,
            });
          } catch (schedErr) {
            // Atomic transaction rollback: delete partially created medicine if schedule creation fails
            try {
              await medicationService.deleteMedicine(createdMed.id);
            } catch {
              // Ignore cleanup error
            }
            throw schedErr;
          }
        }
        setSuccessMsg('Medication and dosage schedule created successfully!');
      }

      closeModal();
      await loadData();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setModalError(formatErrorMessage(err, 'Unable to save medication. Please try again.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeactivate = async (med) => {
    if (!window.confirm(`Are you sure you want to discontinue / deactivate "${med.name}"?`)) {
      return;
    }

    try {
      await medicationService.deactivateMedicine(med.id);
      setSuccessMsg(`"${med.name}" deactivated successfully.`);
      await loadData();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(formatErrorMessage(err, 'Failed to deactivate medication.'));
    }
  };

  const handleDelete = async (med) => {
    if (!window.confirm(`Permanently delete medication "${med.name}" and all attached schedules?`)) {
      return;
    }

    try {
      await medicationService.deleteMedicine(med.id);
      setSuccessMsg(`"${med.name}" deleted successfully.`);
      await loadData();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(formatErrorMessage(err, 'Failed to delete medication.'));
    }
  };

  return (
    <div className="space-y-6 w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">{t('medications.title')}</h2>
          <p className="text-sm text-slate-400 mt-1">
            {t('medications.subtitle')}
          </p>
        </div>
        <button
          type="button"
          onClick={openAddModal}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-400 hover:bg-teal-300 text-slate-950 font-semibold text-xs rounded-xl shadow-sm transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>{t('medications.addMedication')}</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setStatusFilter('active')}
          className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-colors ${
            statusFilter === 'active'
              ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30'
              : 'text-slate-400 hover:bg-slate-900 border border-transparent'
          }`}
        >
          {t('common.active')} {t('nav.medications')}
        </button>
        <button
          type="button"
          onClick={() => setStatusFilter('all')}
          className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-colors ${
            statusFilter === 'all'
              ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30'
              : 'text-slate-400 hover:bg-slate-900 border border-transparent'
          }`}
        >
          {t('common.all')} {t('nav.medications')}
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
      ) : medicines.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
          <EmptyState
            icon={Pill}
            title="No medicines added yet."
            description="Add your prescribed medicines, dosages, and dosage intake timings to start tracking your treatments."
            actionText="Add Medication"
            onAction={openAddModal}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {medicines.map((med) => (
            <div
              key={med.id}
              className={`bg-slate-900/60 border rounded-2xl p-5 space-y-4 transition-colors ${
                med.is_active ? 'border-slate-800 hover:border-slate-700/80' : 'border-slate-800/40 opacity-75'
              }`}
            >
              {/* Card Top */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
                    <Pill className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                      <span>{med.name}</span>
                      <span className="text-xs text-teal-300 font-mono font-normal">
                        {med.dosage_amount} {med.dosage_unit}
                      </span>
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 font-medium">
                        {med.medicine_form}
                      </span>
                      <span className="text-[10px] text-slate-400">Qty: {med.quantity}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  {med.is_active ? (
                    <button
                      type="button"
                      onClick={() => handleDeactivate(med)}
                      className="p-1.5 text-slate-400 hover:text-amber-400 hover:bg-slate-800 rounded-lg transition-colors"
                      title="Deactivate / Discontinue Medicine"
                      aria-label={`Deactivate ${med.name}`}
                    >
                      <PowerOff className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <span className="text-[10px] font-semibold text-slate-500 px-2 py-0.5 rounded-md bg-slate-800/80">
                      Discontinued
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => openEditModal(med)}
                    className="p-1.5 text-slate-400 hover:text-teal-300 hover:bg-slate-800 rounded-lg transition-colors"
                    title="Edit Medicine"
                    aria-label={`Edit ${med.name}`}
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(med)}
                    className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                    title="Delete Medicine"
                    aria-label={`Delete ${med.name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Instructions */}
              {med.instructions && (
                <p className="text-xs text-slate-400 leading-relaxed pl-1">{med.instructions}</p>
              )}

              {/* Badges: Condition & Prescription */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {med.condition && (
                  <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/20 font-medium">
                    <Activity className="w-3 h-3 text-teal-400" />
                    <span>{med.condition.name}</span>
                  </span>
                )}
                {med.prescription && (
                  <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg bg-purple-500/10 text-purple-300 border border-purple-500/20 font-medium">
                    <FileText className="w-3 h-3 text-purple-400" />
                    <span>{med.prescription.prescription_number || `Rx #${med.prescription.id}`}</span>
                  </span>
                )}
              </div>

              {/* Schedule Info */}
              <div>
                {med.schedules && med.schedules.length > 0 ? (
                  <div className="flex flex-wrap items-center gap-1.5 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-teal-400" />
                      <span>Intake Times:</span>
                    </span>
                    {med.schedules.flatMap((s) => s.scheduled_times || []).map((t, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded-md bg-teal-500/10 border border-teal-500/20 text-teal-300 font-mono text-[10px] font-bold"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-amber-500/5 border border-amber-500/10">
                    <span className="text-[11px] text-amber-400/90 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-amber-400" />
                      <span>No schedule configured</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => openScheduleModal(med)}
                      className="px-2.5 py-1 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-[11px] shadow-sm transition-colors cursor-pointer flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Schedule</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Footer Timeline */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <div className="flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  <span>Starts: {formatDisplayDate(med.start_date)}</span>
                </div>
                {med.end_date && <span>Ends: {formatDisplayDate(med.end_date)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Direct Schedule Intake Modal */}
      {schedulingMed && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl my-8">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <Clock className="w-5 h-5 text-teal-400" />
                  <span>Configure Intake Schedule</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Set daily intake timings for <strong>{schedulingMed.name}</strong> ({schedulingMed.dosage_amount} {schedulingMed.dosage_unit})
                </p>
              </div>
              <button
                type="button"
                onClick={closeScheduleModal}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {scheduleModalError && (
              <div role="alert" className="p-3 rounded-xl text-xs flex items-center gap-2 bg-rose-500/10 border border-rose-500/20 text-rose-300">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{scheduleModalError}</span>
              </div>
            )}

            <form onSubmit={handleDirectScheduleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Daily Intake Frequency <span className="text-teal-400">*</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {SCHEDULE_FREQUENCIES.map((freq) => {
                    const isSelected = frequencyType === freq.id;
                    return (
                      <button
                        key={freq.id}
                        type="button"
                        onClick={() => handleFrequencyChange(freq.id)}
                        className={`p-2.5 rounded-xl border text-xs font-medium text-left transition-all ${
                          isSelected
                            ? 'bg-teal-500/10 border-teal-500/40 text-teal-300 ring-1 ring-teal-500/30'
                            : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <div className="font-semibold text-slate-200">{freq.label}</div>
                        <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                          {freq.defaultTimes.join(', ')}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-medium text-slate-300">
                    Intake Times (24h format) <span className="text-teal-400">*</span>
                  </label>
                  {frequencyType === 'CUSTOM' && (
                    <button
                      type="button"
                      onClick={addCustomTime}
                      className="text-[11px] text-teal-400 hover:text-teal-300 font-semibold flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      Add Time
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {scheduledTimes.map((time, idx) => (
                    <div key={idx} className="flex items-center gap-1 bg-slate-950/80 border border-slate-800 rounded-xl px-2.5 py-1.5">
                      <Clock className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                      <input
                        type="time"
                        required
                        value={time}
                        onChange={(e) => handleTimeChange(idx, e.target.value)}
                        className="bg-transparent text-xs text-slate-200 font-mono focus:outline-none"
                      />
                      {frequencyType === 'CUSTOM' && scheduledTimes.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeCustomTime(idx)}
                          className="text-slate-500 hover:text-rose-400 p-0.5"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Dose Per Intake <span className="text-teal-400">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.1"
                    required
                    value={doseQuantity}
                    onChange={(e) => setDoseQuantity(e.target.value)}
                    placeholder="1.0"
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Start Date <span className="text-teal-400">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={closeScheduleModal}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSchedulingSubmitting}
                  className="inline-flex items-center gap-2 px-5 py-2 bg-teal-400 hover:bg-teal-300 text-slate-950 font-bold text-xs rounded-xl shadow-md transition-colors disabled:opacity-50"
                >
                  {isSchedulingSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Schedule Routine</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl my-8">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-white">
                {editingMed ? 'Edit Medication' : 'Add New Medication'}
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
                <label htmlFor="medName" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Medicine Name <span className="text-teal-400">*</span>
                </label>
                <input
                  id="medName"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Metformin, Lisinopril, Amoxicillin"
                  className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label htmlFor="medDosage" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Dosage Strength <span className="text-teal-400">*</span>
                  </label>
                  <input
                    id="medDosage"
                    type="number"
                    step="any"
                    required
                    value={dosageAmount}
                    onChange={(e) => setDosageAmount(e.target.value)}
                    placeholder="e.g. 500"
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
                <div>
                  <label htmlFor="medUnit" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Unit <span className="text-teal-400">*</span>
                  </label>
                  <select
                    id="medUnit"
                    value={dosageUnit}
                    onChange={(e) => setDosageUnit(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  >
                    {DOSAGE_UNITS.map((u) => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="medForm" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Form <span className="text-teal-400">*</span>
                  </label>
                  <select
                    id="medForm"
                    value={medicineForm}
                    onChange={(e) => setMedicineForm(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  >
                    {MEDICINE_FORMS.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="medQty" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Units on Hand (Qty) <span className="text-teal-400">*</span>
                  </label>
                  <input
                    id="medQty"
                    type="number"
                    required
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    placeholder="e.g. 60"
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
              </div>

              {/* Dynamic Dropdowns loaded from user database */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="medCond" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Linked Condition (Optional)
                  </label>
                  <select
                    id="medCond"
                    value={conditionId}
                    onChange={(e) => setConditionId(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  >
                    <option value="">None / Unassigned</option>
                    {conditions.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="medRx" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Linked Prescription (Optional)
                  </label>
                  <select
                    id="medRx"
                    value={prescriptionId}
                    onChange={(e) => setPrescriptionId(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  >
                    <option value="">None / Unassigned</option>
                    {prescriptions.map((rx) => (
                      <option key={rx.id} value={rx.id}>
                        {rx.prescription_number || `Rx #${rx.id}`} {rx.doctor_name ? `(${rx.doctor_name})` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="medStart" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Start Date <span className="text-teal-400">*</span>
                  </label>
                  <input
                    id="medStart"
                    type="date"
                    required
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
                <div>
                  <label htmlFor="medEnd" className="block text-xs font-medium text-slate-300 mb-1.5">
                    End Date (Optional)
                  </label>
                  <input
                    id="medEnd"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="medInst" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Instructions & Guidance
                </label>
                <textarea
                  id="medInst"
                  rows={2}
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="e.g. Take 1 tablet daily with a meal and plenty of water"
                  className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                />
              </div>

              {/* Initial Schedule Configuration */}
              {!editingMed && (
                <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-slate-200 flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={createScheduleNow}
                        onChange={(e) => setCreateScheduleNow(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-teal-400 focus:ring-teal-500/30"
                      />
                      <span>Create dosage schedule now</span>
                    </label>
                    {createScheduleNow && (
                      <span className="text-[11px] text-teal-400 font-medium">Auto-configured</span>
                    )}
                  </div>

                  {createScheduleNow && (
                    <div className="space-y-3 pt-2 border-t border-slate-800/80">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[11px] font-medium text-slate-400 mb-1">
                            Intake Frequency
                          </label>
                          <select
                            value={frequencyType}
                            onChange={(e) => handleFrequencyChange(e.target.value)}
                            className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-teal-500"
                          >
                            {SCHEDULE_FREQUENCIES.map((f) => (
                              <option key={f.id} value={f.id}>{f.label}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="block text-[11px] font-medium text-slate-400 mb-1">
                            Dose Per Intake
                          </label>
                          <input
                            type="number"
                            step="any"
                            value={doseQuantity}
                            onChange={(e) => setDoseQuantity(e.target.value)}
                            className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-teal-500"
                          />
                        </div>
                      </div>

                      {/* Scheduled Times Pickers */}
                      <div>
                        <label className="block text-[11px] font-medium text-slate-400 mb-1.5">
                          Daily Scheduled Times (24h)
                        </label>
                        <div className="flex flex-wrap gap-2 items-center">
                          {scheduledTimes.map((t, idx) => (
                            <div key={idx} className="flex items-center gap-1">
                              <input
                                type="time"
                                required
                                value={t}
                                onChange={(e) => handleTimeChange(idx, e.target.value)}
                                className="px-2 py-1 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-teal-500"
                              />
                              {frequencyType === 'CUSTOM' && scheduledTimes.length > 1 && (
                                <button
                                  type="button"
                                  onClick={() => removeCustomTime(idx)}
                                  className="text-slate-500 hover:text-rose-400 p-0.5"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              )}
                            </div>
                          ))}
                          {frequencyType === 'CUSTOM' && (
                            <button
                              type="button"
                              onClick={addCustomTime}
                              className="px-2 py-1 text-[11px] bg-slate-800 hover:bg-slate-750 text-slate-300 rounded-lg transition-colors"
                            >
                              + Add Time
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

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
                    <span>{editingMed ? 'Update Medication' : 'Save Medication'}</span>
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

export default Medicines;
