import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Sparkles,
  Clock,
  Calendar,
  User,
  Pill,
  RefreshCw,
  ArrowRight,
  Eye,
  EyeOff,
  Plus,
  Trash2,
  ScanLine,
} from 'lucide-react';
import { ocrService } from '../../api/ocrService';

export const PrescriptionScan = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // Workflow states: 'idle' | 'processing' | 'review' | 'success'
  const [workflowState, setWorkflowState] = useState('idle');
  const [processingStep, setProcessingStep] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [showRawText, setShowRawText] = useState(false);
  const [rawText, setRawText] = useState('');
  const [matchData, setMatchData] = useState(null);
  const [confidenceScore, setConfidenceScore] = useState(0.0);
  const [confidenceLevel, setConfidenceLevel] = useState('LOW');

  // Editable Draft Form State (Zero hardcoded defaults)
  const [form, setForm] = useState({
    // Medication
    name: '',
    dosageAmount: '',
    dosageUnit: '',
    medicineForm: '',
    quantity: '',
    instructions: '',
    startDate: '',
    endDate: '',

    // Optional Schedule
    createSchedule: true,
    frequencyType: '',
    doseQuantity: '',
    scheduledTimes: [],
  });

  const [newTimeInput, setNewTimeInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    setErrorMsg(null);

    // Validate size (10 MB)
    if (file.size > 10 * 1024 * 1024) {
      setErrorMsg('File size exceeds the 10 MB limit.');
      return;
    }

    // Validate type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf'];
    if (!allowedTypes.includes(file.type.toLowerCase())) {
      setErrorMsg('Unsupported file format. Please upload PNG, JPG, or PDF.');
      return;
    }

    setSelectedFile(file);
    startOCRProcess(file);
  };

  const pollingIntervalRef = React.useRef(null);

  const cleanupPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };

  React.useEffect(() => {
    return () => cleanupPolling();
  }, []);

  const formatApiError = (err, fallbackMsg) => {
    if (!err) return fallbackMsg;
    if (!err.response) {
      if (err.message === 'Network Error' || err.code === 'ERR_NETWORK') {
        return 'Unable to connect to the PillSync server. Please check your network connection.';
      }
      return err.message || fallbackMsg;
    }

    const data = err.response.data;
    const detail = data?.detail || data?.error;
    const errorCode = typeof detail === 'object' ? detail?.code : data?.code;
    const errorMessage = typeof detail === 'object' ? detail?.message : (typeof detail === 'string' ? detail : null);

    // Map structured error codes to safe user-friendly messages
    if (errorCode === 'OCR_MODEL_NOT_READY') {
      return errorMessage || 'Handwriting OCR model is currently initializing. Please try again shortly.';
    }
    if (errorCode === 'OCR_ENGINE_FAILURE') {
      return errorMessage || 'OCR processing failed. Please try a clearer prescription image.';
    }
    if (errorCode === 'DETECTOR_FAILURE') {
      return errorMessage || 'Medicine region detector failed. Please try a clearer prescription image.';
    }
    if (errorCode === 'PDF_PROCESSING_FAILURE') {
      return errorMessage || 'Unable to read this PDF. Please upload a valid prescription PDF.';
    }
    if (errorCode === 'NO_TEXT_DETECTED') {
      return errorMessage || 'No readable text was detected. Please upload a clearer prescription.';
    }
    if (errorCode === 'REFERENCE_MATCHING_FAILURE') {
      return errorMessage || 'Prescription text was extracted, but medicine matching is unavailable. You can review the extracted information manually.';
    }
    if (errorCode === 'FILE_INVALID') {
      return errorMessage || 'Invalid prescription file.';
    }
    if (errorCode === 'OCR_JOB_TIMEOUT') {
      return errorMessage || 'Prescription scanning timed out. Please try again.';
    }

    // Status code checks
    const status = err.response.status;
    if (status === 401) return 'Your session has expired. Please log in again.';
    if (status === 403) return 'You do not have permission to scan prescriptions.';
    if (status === 413) return 'File size exceeds the 10 MB limit.';
    if (errorMessage) return errorMessage;
    if (status === 422) return 'Prescription file could not be processed. Please check file format and clarity.';
    if (status === 500) return 'Prescription processing failed on the server. Please try again.';

    return fallbackMsg;
  };

  const populateDraftFromOCR = (response) => {
    const med = response.medication || {};
    const fields = response.fields || {};
    const match = response.match || {};
    const topCandidate = (match.candidates && match.candidates[0]?.dataset_name) || (response.medicine_candidates && response.medicine_candidates[0]?.dataset_name);

    // 1. Medicine Name
    const resolvedName = med.medicine_name?.value || fields.medicine_name || match.matched_name || topCandidate || fields.detected_raw_medicine_name || '';
    
    // 2. Strength / Dosage Amount
    const resolvedStrength = med.strength?.value || (fields.dosage_amount !== null && fields.dosage_amount !== undefined ? String(fields.dosage_amount) : (fields.strength ? String(fields.strength).replace(/[^\d.]/g, '') : ''));
    
    // 3. Unit
    const resolvedUnit = med.unit?.value || fields.dosage_unit || '';
    
    // 4. Dosage Form
    const resolvedForm = med.dosage_form?.value || fields.dosage_form || '';
    
    // 5. Instructions
    const resolvedInstructions = med.instructions?.value || fields.instructions || '';
    
    // 6. Start Date (Do NOT default to today)
    const resolvedStartDate = med.start_date?.value || fields.start_date || '';
    
    // 7. End Date
    const resolvedEndDate = med.end_date?.value || fields.expiry_date || '';

    setRawText(response.raw_text || '');
    setMatchData(response.match || null);
    
    // Confidence score based on medicine match
    const matchScore = match.confidence !== undefined ? match.confidence : (response.confidence_score || 0.0);
    setConfidenceScore(matchScore);
    setConfidenceLevel(match.confidence_level || response.confidence_level || 'LOW');

    setForm({
      name: resolvedName,
      dosageAmount: resolvedStrength,
      dosageUnit: resolvedUnit,
      medicineForm: resolvedForm ? resolvedForm.toUpperCase() : '',
      quantity: fields.quantity !== null && fields.quantity !== undefined ? String(fields.quantity) : '',
      instructions: resolvedInstructions,
      startDate: resolvedStartDate,
      endDate: resolvedEndDate,

      createSchedule: Boolean(fields.frequency || (Array.isArray(fields.scheduled_times) && fields.scheduled_times.length > 0)),
      frequencyType: fields.frequency || '',
      doseQuantity: fields.dose_quantity ? String(fields.dose_quantity) : '',
      scheduledTimes: Array.isArray(fields.scheduled_times) ? fields.scheduled_times : [],
    });

    setWorkflowState('review');
  };


  const startOCRProcess = async (file) => {
    cleanupPolling();
    setWorkflowState('processing');
    setProcessingStep('Uploading prescription...');
    setErrorMsg(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const initResponse = await ocrService.scanPrescription(formData);

      // Check if asynchronous job response
      if (initResponse.job_id) {
        const jobId = initResponse.job_id;
        setProcessingStep('Analyzing prescription...');

        const startTime = Date.now();
        const MAX_POLL_TIME_MS = 5 * 60 * 1000; // 5 minutes max on CPU

        pollingIntervalRef.current = setInterval(async () => {
          try {
            if (Date.now() - startTime > MAX_POLL_TIME_MS) {
              cleanupPolling();
              setErrorMsg('Prescription scanning timed out. Please try again.');
              setWorkflowState('idle');
              return;
            }

            const jobStatus = await ocrService.getPrescriptionJob(jobId);

            if (jobStatus.status === 'processing') {
              if (jobStatus.stage === 'detecting_regions') {
                setProcessingStep('Detecting medicine regions...');
              } else if (jobStatus.stage === 'reading_text') {
                setProcessingStep('Reading handwritten medicine text...');
              } else if (jobStatus.stage === 'matching_reference') {
                setProcessingStep('Preparing results...');
              } else {
                setProcessingStep(jobStatus.progress_message || 'Analyzing prescription...');
              }
            } else if (jobStatus.status === 'completed') {
              cleanupPolling();
              setProcessingStep('Extraction complete');
              if (jobStatus.result) {
                populateDraftFromOCR(jobStatus.result);
              } else {
                setErrorMsg('OCR completed but returned no result data.');
                setWorkflowState('idle');
              }
            } else if (jobStatus.status === 'failed') {
              cleanupPolling();
              const err = jobStatus.error || {};
              setErrorMsg(err.message || 'Prescription OCR failed.');
              setWorkflowState('idle');
            }
          } catch (pollErr) {
            console.error('Polling error:', pollErr);
          }
        }, 1500);

      } else if (initResponse.fields) {
        // Direct synchronous response fallback
        populateDraftFromOCR(initResponse);
      } else {
        throw new Error('Unexpected response from prescription scanner.');
      }

    } catch (err) {
      cleanupPolling();
      console.error('OCR Extraction Error:', err);
      const userMessage = formatApiError(err, 'Failed to process prescription image.');
      setErrorMsg(userMessage);
      setWorkflowState('idle');
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleAddTime = () => {
    if (!newTimeInput) return;
    if (!form.scheduledTimes.includes(newTimeInput)) {
      setForm((prev) => ({
        ...prev,
        scheduledTimes: [...prev.scheduledTimes, newTimeInput].sort(),
      }));
    }
    setNewTimeInput('');
  };

  const handleRemoveTime = (timeToRemove) => {
    setForm((prev) => ({
      ...prev,
      scheduledTimes: prev.scheduledTimes.filter((t) => t !== timeToRemove),
    }));
  };

  const handleSelectCandidate = (candidateName) => {
    setForm((prev) => ({
      ...prev,
      name: candidateName,
    }));
  };

  const handleConfirmAndSave = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setErrorMsg('Medicine name is required.');
      return;
    }
    if (!form.dosageAmount || Number(form.dosageAmount) <= 0) {
      setErrorMsg('Please specify a valid dosage amount.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const payload = {
        create_prescription: false,
        prescription_number: null,
        doctor_name: null,
        issue_date: null,
        expiry_date: null,
        notes: null,

        name: form.name.trim(),
        dosage_amount: parseFloat(form.dosageAmount),
        dosage_unit: (form.dosageUnit || 'MG').toUpperCase(),
        medicine_form: (form.medicineForm || 'TABLET').toUpperCase(),
        quantity: parseInt(form.quantity, 10) || 30,
        instructions: form.instructions || null,
        start_date: form.startDate || new Date().toISOString().split('T')[0],
        end_date: form.endDate || null,

        create_schedule: form.createSchedule,
        frequency_type: form.frequencyType || 'ONCE_DAILY',
        dose_quantity: parseFloat(form.doseQuantity) || 1.0,
        scheduled_times: form.scheduledTimes.length > 0 ? form.scheduledTimes : ['08:00'],
      };

      await ocrService.confirmPrescription(payload);
      setWorkflowState('success');
    } catch (err) {

      console.error('Confirmation Error:', err);
      const userMessage = formatApiError(err, 'Failed to save confirmed medication.');
      setErrorMsg(userMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    cleanupPolling();
    setSelectedFile(null);
    setRawText('');
    setMatchData(null);
    setConfidenceScore(0.0);
    setConfidenceLevel('LOW');
    setErrorMsg(null);
    setWorkflowState('idle');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-teal-400 font-medium text-xs tracking-wider uppercase">
            <ScanLine className="w-4 h-4" />
            <span>Prescription OCR & AI Normalization</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1">
            Scan & Import Prescription
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Upload prescription images or PDFs to automatically extract medication details verified against our reference database.
          </p>
        </div>
      </div>

      {/* Global Error Notice */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold">Notice:</span> {errorMsg}
          </div>
        </div>
      )}

      {/* WORKFLOW STATE 1: IDLE / UPLOAD */}
      {workflowState === 'idle' && (
        <div className="space-y-6">
          <div
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            className="border-2 border-dashed border-slate-700 hover:border-teal-500/50 bg-slate-900/40 hover:bg-slate-900/70 transition-all rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer group"
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.pdf"
              className="hidden"
              onChange={handleFileChange}
            />

            <div className="w-16 h-16 rounded-2xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 group-hover:scale-105 transition-transform mb-4 shadow-lg shadow-teal-500/5">
              <UploadCloud className="w-8 h-8" />
            </div>

            <h3 className="text-base font-semibold text-white">
              Upload prescription document
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              Drag and drop your file here, or click to browse from your device.
            </p>

            <div className="flex items-center gap-3 mt-6 text-[11px] text-slate-400 bg-slate-800/60 px-4 py-2 rounded-full border border-slate-700/60">
              <span>Supported: PNG, JPG, JPEG, PDF</span>
              <span>•</span>
              <span>Max size: 10 MB</span>
            </div>
          </div>

          {/* Empty State Banner */}
          <div className="p-6 rounded-2xl bg-slate-900/30 border border-slate-800/80 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-teal-400 shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-slate-200">
                AI Clinical Normalization Knowledge Base
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Upload a prescription to extract medication details. Every extraction is matched against 50,000+ reference records to normalize spelling variations, forms, and strengths before user confirmation.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* WORKFLOW STATE 2: REAL-TIME PROCESSING */}
      {workflowState === 'processing' && (
        <div className="p-12 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col items-center justify-center text-center space-y-6">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 animate-pulse">
              <RefreshCw className="w-8 h-8 animate-spin" />
            </div>
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-white">
              Processing Prescription Document
            </h3>
            <p className="text-xs text-teal-400 font-medium">{processingStep}</p>
            <p className="text-[11px] text-slate-500 mt-2">
              File: {selectedFile?.name} ({(selectedFile?.size / 1024).toFixed(1)} KB)
            </p>
          </div>
        </div>
      )}

      {/* WORKFLOW STATE 3: REVIEW & CORRECTION */}
      {workflowState === 'review' && (
        <form onSubmit={handleConfirmAndSave} className="space-y-6">
          {/* Top Status & Confidence Bar */}
          <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div
                className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 border ${
                  confidenceLevel === 'HIGH'
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                    : confidenceLevel === 'MEDIUM'
                    ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                    : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                }`}
              >
                {confidenceLevel === 'HIGH' ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5" />
                )}
                <span>
                  Match Confidence: {confidenceLevel} ({Math.round(confidenceScore * 100)}%)
                </span>
              </div>
              <span className="text-xs text-slate-400">
                File: <span className="text-slate-200">{selectedFile?.name}</span>
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowRawText(!showRawText)}
                className="text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/50 flex items-center gap-1.5 transition-colors"
              >
                {showRawText ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                <span>{showRawText ? 'Hide Raw OCR' : 'Inspect Raw OCR'}</span>
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="text-xs text-slate-400 hover:text-rose-300 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/50 transition-colors"
              >
                Scan Another
              </button>
            </div>
          </div>

          {/* Raw Text Drawer */}
          {showRawText && (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 space-y-1">
              <div className="text-[11px] text-slate-400 font-sans uppercase font-semibold">
                Extracted Raw OCR Text
              </div>
              <pre className="whitespace-pre-wrap leading-relaxed text-slate-300 max-h-48 overflow-y-auto">
                {rawText || 'No text extracted.'}
              </pre>
            </div>
          )}

          {/* Confidence Warnings */}
          {confidenceLevel === 'MEDIUM' && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5 text-amber-300 text-xs">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Review Suggested:</span> The medicine name had a spelling variation matched to{' '}
                <span className="font-bold underline">{form.name}</span>. Please verify and confirm before saving.
              </div>
            </div>
          )}

          {confidenceLevel === 'LOW' && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Low Match Confidence:</span> Medicine not found with high certainty in reference dataset. Please manually inspect and edit all fields below.
              </div>
            </div>
          )}

          {/* Candidate Suggestions */}
          {matchData && matchData.candidates && matchData.candidates.length > 1 && (
            <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Reference Dataset Suggestions:
              </div>
              <div className="flex flex-wrap gap-2">
                {matchData.candidates.map((cand, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSelectCandidate(cand.dataset_name)}
                    className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${
                      form.name === cand.dataset_name
                        ? 'bg-teal-500/20 text-teal-300 border-teal-500/40 font-semibold'
                        : 'bg-slate-800 text-slate-300 border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    {cand.dataset_name} ({Math.round(cand.confidence * 100)}%)
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Medication Details Form */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-white font-semibold text-sm border-b border-slate-800 pb-3">
              <Pill className="w-4 h-4 text-teal-400" />
              <span>Medication Details</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div className="sm:col-span-2">
                <label className="block text-slate-400 font-medium mb-1">
                  Medicine Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  name="name"
                  required
                  value={form.name}
                  onChange={handleInputChange}
                  placeholder="e.g. Amoxicillin"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white font-medium focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">Dosage Form</label>
                <select
                  name="medicineForm"
                  value={form.medicineForm}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                >
                  <option value="">Select form (or leave blank)</option>
                  <option value="TABLET">Tablet</option>
                  <option value="CAPSULE">Capsule</option>
                  <option value="SYRUP">Syrup</option>
                  <option value="DROPS">Drops</option>
                  <option value="INJECTION">Injection</option>
                  <option value="CREAM">Cream</option>
                  <option value="OTHER">Other / Inhaler</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">
                  Strength / Dosage Amount <span className="text-rose-400">*</span>
                </label>
                <input
                  type="number"
                  step="any"
                  name="dosageAmount"
                  required
                  value={form.dosageAmount}
                  onChange={handleInputChange}
                  placeholder="e.g. 500"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">Unit</label>
                <select
                  name="dosageUnit"
                  value={form.dosageUnit}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                >
                  <option value="">Select unit</option>
                  <option value="mg">mg</option>
                  <option value="g">g</option>
                  <option value="mcg">mcg</option>
                  <option value="ml">ml</option>
                  <option value="tablet">tablet</option>
                  <option value="capsule">capsule</option>
                  <option value="drop">drop</option>
                  <option value="unit">unit / IU</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">Quantity (Stock)</label>
                <input
                  type="number"
                  name="quantity"
                  value={form.quantity}
                  onChange={handleInputChange}
                  placeholder="e.g. 30"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div className="sm:col-span-3">
                <label className="block text-slate-400 font-medium mb-1">Instructions / Directions</label>
                <input
                  type="text"
                  name="instructions"
                  value={form.instructions}
                  onChange={handleInputChange}
                  placeholder="e.g. Take after food with water"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">Start Date</label>
                <input
                  type="date"
                  name="startDate"
                  value={form.startDate}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">End Date (Optional)</label>
                <input
                  type="date"
                  name="endDate"
                  value={form.endDate}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                />
              </div>
            </div>
          </div>


          {/* Section 3: Dosage Schedule */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-white font-semibold text-sm">
                <Clock className="w-4 h-4 text-teal-400" />
                <span>Dosage Schedule</span>
              </div>
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400">
                <input
                  type="checkbox"
                  name="createSchedule"
                  checked={form.createSchedule}
                  onChange={handleInputChange}
                  className="rounded border-slate-700 bg-slate-800 text-teal-500 focus:ring-teal-500/20"
                />
                <span>Create Medication Schedule</span>
              </label>
            </div>

            {form.createSchedule && (
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-slate-400 font-medium mb-1">Frequency</label>
                    <select
                      name="frequencyType"
                      value={form.frequencyType}
                      onChange={handleInputChange}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                    >
                      <option value="ONCE_DAILY">Once Daily</option>
                      <option value="TWICE_DAILY">Twice Daily</option>
                      <option value="THREE_TIMES_DAILY">Three Times Daily</option>
                      <option value="FOUR_TIMES_DAILY">Four Times Daily</option>
                      <option value="CUSTOM">Custom / As Needed</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-400 font-medium mb-1">Dose Quantity per Intake</label>
                    <input
                      type="number"
                      step="any"
                      name="doseQuantity"
                      value={form.doseQuantity}
                      onChange={handleInputChange}
                      placeholder="1.0"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Scheduled Times (24h format)</label>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    {form.scheduledTimes.map((time, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1.5 bg-slate-800 border border-slate-700 text-teal-300 px-3 py-1 rounded-full text-xs font-mono"
                      >
                        {time}
                        <button
                          type="button"
                          onClick={() => handleRemoveTime(time)}
                          className="text-slate-400 hover:text-rose-300"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="time"
                      value={newTimeInput}
                      onChange={(e) => setNewTimeInput(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-white text-xs focus:outline-none focus:border-teal-500"
                    />
                    <button
                      type="button"
                      onClick={handleAddTime}
                      className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs flex items-center gap-1 border border-slate-700 transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Time</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={handleReset}
              disabled={isSubmitting}
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-slate-700 bg-slate-800/60 hover:bg-slate-800 text-slate-300 text-xs font-medium transition-colors"
            >
              Cancel / Start Over
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-teal-500/10 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Saving to Medications...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Confirm & Save to My Medications</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* WORKFLOW STATE 4: SUCCESS CONFIRMATION */}
      {workflowState === 'success' && (
        <div className="p-8 rounded-2xl bg-slate-900/80 border border-emerald-500/30 flex flex-col items-center justify-center text-center space-y-4 shadow-xl shadow-emerald-500/5">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-2">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-white">Prescription Successfully Imported!</h2>
          <p className="text-xs text-slate-300 max-w-md">
            The medication <span className="font-semibold text-teal-300">{form.name}</span> has been securely saved to your patient profile in PostgreSQL.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-4">
            <button
              type="button"
              onClick={() => navigate('/medications')}
              className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <span>View My Medications</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => navigate('/schedule')}
              className="px-5 py-2.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium transition-colors"
            >
              View Schedule
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="px-5 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 hover:bg-slate-800 text-slate-400 hover:text-white text-xs transition-colors"
            >
              Scan Another Prescription
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PrescriptionScan;
