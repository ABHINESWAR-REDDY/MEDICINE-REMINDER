import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  CalendarCheck,
  Clock,
  Plus,
  Edit2,
  Trash2,
  X,
  Loader2,
  AlertCircle,
  CheckCircle,
  Pill,
  Calendar,
} from 'lucide-react';
import medicationService from '../../api/medicationService';
import EmptyState from '../common/EmptyState';

const SCHEDULE_FREQUENCIES = [
  { id: 'ONCE_DAILY', label: 'Once Daily', defaultTimes: ['08:00'] },
  { id: 'TWICE_DAILY', label: 'Twice Daily', defaultTimes: ['08:00', '20:00'] },
  { id: 'THREE_TIMES_DAILY', label: 'Three Times Daily', defaultTimes: ['08:00', '14:00', '20:00'] },
  { id: 'FOUR_TIMES_DAILY', label: 'Four Times Daily', defaultTimes: ['08:00', '12:00', '16:00', '20:00'] },
  { id: 'CUSTOM', label: 'Custom Times', defaultTimes: ['09:00'] },
];

export const Schedule = () => {
  let locationSearch = '';
  try {
    const loc = useLocation();
    locationSearch = loc?.search || '';
  } catch {
    locationSearch = typeof window !== 'undefined' ? window.location?.search || '' : '';
  }

  const [schedules, setSchedules] = useState([]);
  const [medicines, setMedicines] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [selectedMedicineId, setSelectedMedicineId] = useState('');
  const [frequencyType, setFrequencyType] = useState('TWICE_DAILY');
  const [scheduledTimes, setScheduledTimes] = useState(['08:00', '20:00']);
  const [doseQuantity, setDoseQuantity] = useState('1.0');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const [schedData, medsData] = await Promise.all([
        medicationService.listSchedules(),
        medicationService.listMedicines(true), // active medicines
      ]);
      setSchedules(schedData);
      setMedicines(medsData);

      // Check if medicine_id was passed in URL
      const searchParams = new URLSearchParams(locationSearch);
      const urlMedId = searchParams.get('medicine_id');
      if (urlMedId) {
        const found = medsData.find((m) => String(m.id) === String(urlMedId));
        if (found) {
          openAddModal(found.id);
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load schedule data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

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

  const unscheduledMedicines = medicines.filter((m) => !schedules.some((s) => s.medicine_id === m.id));

  const openAddModal = (presetMedId = null) => {
    setEditingSchedule(null);
    let targetId = '';
    if (presetMedId) {
      targetId = presetMedId.toString();
    } else if (unscheduledMedicines.length > 0) {
      targetId = unscheduledMedicines[0].id.toString();
    } else if (medicines.length > 0) {
      targetId = medicines[0].id.toString();
    }
    setSelectedMedicineId(targetId);
    setFrequencyType('TWICE_DAILY');
    setScheduledTimes(['08:00', '20:00']);
    setDoseQuantity('1.0');
    setStartDate(new Date().toISOString().split('T')[0]);
    setEndDate('');
    setModalError('');
    setIsModalOpen(true);
  };

  const openEditModal = (sched) => {
    setEditingSchedule(sched);
    setSelectedMedicineId(sched.medicine_id.toString());
    setFrequencyType(sched.frequency_type);
    setScheduledTimes(Array.isArray(sched.scheduled_times) ? sched.scheduled_times : ['08:00']);
    setDoseQuantity(sched.dose_quantity.toString());
    setStartDate(sched.start_date);
    setEndDate(sched.end_date || '');
    setModalError('');
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingSchedule(null);
    setModalError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedMedicineId) {
      setModalError('Please select a medication.');
      return;
    }
    const numDoseQty = parseFloat(doseQuantity);
    if (isNaN(numDoseQty) || numDoseQty <= 0) {
      setModalError('Dose quantity must be greater than zero.');
      return;
    }
    if (scheduledTimes.length === 0) {
      setModalError('At least one intake time is required.');
      return;
    }
    if (endDate && endDate < startDate) {
      setModalError('End date cannot be before start date.');
      return;
    }

    setIsSubmitting(true);
    setModalError('');

    try {
      const payload = {
        frequency_type: frequencyType,
        times_per_day: scheduledTimes.length,
        scheduled_times: scheduledTimes,
        dose_quantity: numDoseQty,
        start_date: startDate,
        end_date: endDate || null,
      };

      if (editingSchedule) {
        await medicationService.updateSchedule(editingSchedule.id, payload);
        setSuccessMsg('Dosage schedule updated successfully!');
      } else {
        await medicationService.createMedicineSchedule(parseInt(selectedMedicineId, 10), payload);
        setSuccessMsg('Dosage schedule created successfully!');
      }

      closeModal();
      await loadData();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setModalError(err.response?.data?.detail || err.message || 'Failed to save dosage schedule.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id, medName) => {
    if (!window.confirm(`Are you sure you want to delete this schedule for "${medName || 'medication'}"?`)) {
      return;
    }

    try {
      await medicationService.deleteSchedule(id);
      setSuccessMsg('Schedule deleted successfully.');
      await loadData();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete schedule.');
    }
  };

  const formatFrequencyLabel = (freq) => {
    switch (freq) {
      case 'ONCE_DAILY':
        return 'Once Daily';
      case 'TWICE_DAILY':
        return 'Twice Daily';
      case 'THREE_TIMES_DAILY':
        return '3 Times Daily';
      case 'FOUR_TIMES_DAILY':
        return '4 Times Daily';
      default:
        return 'Custom';
    }
  };

  return (
    <div className="space-y-6 w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Adherence & Schedule</h2>
          <p className="text-sm text-slate-400 mt-1">
            Track daily medication intake times, adherence routines, and scheduled dosages
          </p>
        </div>
        <button
          type="button"
          onClick={() => openAddModal()}
          disabled={medicines.length === 0}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-400 hover:bg-teal-300 text-slate-950 font-semibold text-xs rounded-xl shadow-sm transition-colors shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Plus className="w-4 h-4" />
          <span>Add Schedule</span>
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

      {/* Unscheduled Medications Section (Added in Medications side bar) */}
      {unscheduledMedicines.length > 0 && !isLoading && (
        <div className="p-5 rounded-2xl bg-slate-900/90 border border-teal-500/30 space-y-3 shadow-lg">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
                <Pill className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-white">
                Medicines Added in Medications Side Bar ({unscheduledMedicines.length} Pending Intake Routine)
              </h3>
            </div>
            <span className="text-[11px] text-teal-300/80 font-medium">
              Configure daily times for your added medicines
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
            {unscheduledMedicines.map((med) => (
              <div
                key={med.id}
                className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-teal-500/40 flex items-center justify-between gap-3 shadow-md transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400">
                    <Clock className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">{med.name}</div>
                    <div className="text-[10px] text-teal-300 font-mono">
                      {med.dosage_amount} {med.dosage_unit} · {med.medicine_form}
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => openAddModal(med.id)}
                  className="px-3 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow-md shadow-teal-500/10 transition-colors shrink-0"
                >
                  Schedule Intake
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Content Area */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <Loader2 className="w-6 h-6 animate-spin text-teal-400" />
        </div>
      ) : schedules.length === 0 && unscheduledMedicines.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
          <EmptyState
            icon={CalendarCheck}
            title="No scheduled intakes yet."
            description={
              medicines.length === 0
                ? 'Add your first medication under Medications to configure daily intake schedules.'
                : 'Create your dosage intake schedule to track daily medication timing routines.'
            }
            actionText={medicines.length > 0 ? 'Add Schedule' : undefined}
            onAction={medicines.length > 0 ? () => openAddModal() : undefined}
          />
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.length > 0 && (
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
              Active Dosage Intake Routines ({schedules.length})
            </h3>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {schedules.map((sched) => {
            const med = sched.medicine;
            return (
              <div
                key={sched.id}
                className="bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 space-y-4 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
                      <Clock className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm text-white">
                        {med ? med.name : `Medicine #${sched.medicine_id}`}
                      </h3>
                      {med && (
                        <p className="text-xs text-teal-300 font-mono mt-0.5">
                          {med.dosage_amount} {med.dosage_unit} • {med.medicine_form}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-teal-500/10 text-teal-300 border border-teal-500/20">
                      {formatFrequencyLabel(sched.frequency_type)}
                    </span>
                    <button
                      type="button"
                      onClick={() => openEditModal(sched)}
                      className="p-1.5 text-slate-400 hover:text-teal-300 hover:bg-slate-800 rounded-lg transition-colors"
                      title="Edit Schedule"
                      aria-label="Edit Schedule"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(sched.id, med?.name)}
                      className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                      title="Delete Schedule"
                      aria-label="Delete Schedule"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Scheduled Times List */}
                <div className="space-y-1.5">
                  <span className="text-[11px] text-slate-400 font-medium block">Daily Intake Times:</span>
                  <div className="flex flex-wrap gap-2">
                    {Array.isArray(sched.scheduled_times) &&
                      sched.scheduled_times.map((timeStr, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-950/70 border border-slate-800 text-xs font-mono text-slate-200 font-semibold"
                        >
                          <Clock className="w-3 h-3 text-teal-400" />
                          <span>{timeStr}</span>
                        </span>
                      ))}
                  </div>
                </div>

                {/* Footer details */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>Starts: {sched.start_date}</span>
                  </div>
                  <div>
                    <span>Dose: {sched.dose_quantity} unit(s)</span>
                  </div>
                </div>
              </div>
            );
          })}
          </div>
        </div>
      )}

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-white">
                {editingSchedule ? 'Edit Dosage Schedule' : 'Create Dosage Schedule'}
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
                <label htmlFor="schedMed" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Select Medication <span className="text-teal-400">*</span>
                </label>
                <select
                  id="schedMed"
                  disabled={Boolean(editingSchedule)}
                  value={selectedMedicineId}
                  onChange={(e) => setSelectedMedicineId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors disabled:opacity-60"
                >
                  {medicines.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.dosage_amount} {m.dosage_unit})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="schedFreq" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Frequency <span className="text-teal-400">*</span>
                  </label>
                  <select
                    id="schedFreq"
                    value={frequencyType}
                    onChange={(e) => handleFrequencyChange(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  >
                    {SCHEDULE_FREQUENCIES.map((f) => (
                      <option key={f.id} value={f.id}>{f.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="schedDoseQty" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Dose Per Intake <span className="text-teal-400">*</span>
                  </label>
                  <input
                    id="schedDoseQty"
                    type="number"
                    step="any"
                    required
                    value={doseQuantity}
                    onChange={(e) => setDoseQuantity(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
              </div>

              {/* Scheduled Times */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Daily Scheduled Times (24-Hour Format)
                </label>
                <div className="flex flex-wrap gap-2 items-center">
                  {scheduledTimes.map((timeVal, idx) => (
                    <div key={idx} className="flex items-center gap-1">
                      <input
                        type="time"
                        required
                        value={timeVal}
                        onChange={(e) => handleTimeChange(idx, e.target.value)}
                        className="px-2.5 py-1.5 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-teal-500"
                      />
                      {frequencyType === 'CUSTOM' && scheduledTimes.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeCustomTime(idx)}
                          className="text-slate-500 hover:text-rose-400 p-0.5"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                  {frequencyType === 'CUSTOM' && (
                    <button
                      type="button"
                      onClick={addCustomTime}
                      className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl transition-colors font-medium"
                    >
                      + Add Time
                    </button>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="schedStart" className="block text-xs font-medium text-slate-300 mb-1.5">
                    Start Date <span className="text-teal-400">*</span>
                  </label>
                  <input
                    id="schedStart"
                    type="date"
                    required
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
                <div>
                  <label htmlFor="schedEnd" className="block text-xs font-medium text-slate-300 mb-1.5">
                    End Date (Optional)
                  </label>
                  <input
                    id="schedEnd"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  />
                </div>
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
                    <span>{editingSchedule ? 'Update Schedule' : 'Save Schedule'}</span>
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

export default Schedule;
