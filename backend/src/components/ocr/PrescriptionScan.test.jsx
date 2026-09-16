import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import PrescriptionScan from './PrescriptionScan';
import { ocrService } from '../../api/ocrService';

// Mock OCR API Service
vi.mock('../../api/ocrService', () => ({
  ocrService: {
    scanPrescription: vi.fn(),
    confirmPrescription: vi.fn(),
    searchReferenceMedicines: vi.fn(),
  },
}));

describe('PrescriptionScan Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () =>
    render(
      <BrowserRouter>
        <PrescriptionScan />
      </BrowserRouter>
    );

  it('renders initial idle empty upload state', () => {
    renderComponent();

    expect(screen.getByText('Scan & Import Prescription')).toBeInTheDocument();
    expect(screen.getByText('Upload prescription document')).toBeInTheDocument();
    expect(screen.getByText(/Upload a prescription to extract medication details/i)).toBeInTheDocument();
  });

  it('rejects oversized files > 10MB', () => {
    renderComponent();

    const largeFile = new File(['dummy content'], 'large.png', {
      type: 'image/png',
    });
    // Override file size for test
    Object.defineProperty(largeFile, 'size', { value: 11 * 1024 * 1024 });

    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [largeFile] } });

    expect(screen.getByText(/File size exceeds the 10 MB limit/i)).toBeInTheDocument();
  });

  it('rejects unsupported file extensions', () => {
    renderComponent();

    const invalidFile = new File(['dummy content'], 'script.exe', {
      type: 'application/x-msdownload',
    });

    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [invalidFile] } });

    expect(screen.getByText(/Unsupported file format/i)).toBeInTheDocument();
  });

  it('processes valid file and transitions to review screen with confidence badge', async () => {
    const mockOCRResponse = {
      medication: {
        medicine_name: { value: 'Amoxicillin', source: 'ocr', confidence: 0.95 },
        strength: { value: '500', source: 'ocr', confidence: 0.90 },
        unit: { value: 'mg', source: 'ocr', confidence: 0.90 },
        dosage_form: { value: 'Tablet', source: 'ocr', confidence: 0.85 },
        instructions: { value: 'Take after food', source: 'ocr', confidence: 0.85 },
        start_date: { value: '2026-08-18', source: 'ocr', confidence: 0.80 },
        end_date: { value: null, source: 'not_detected', confidence: 0.0 },
      },
      raw_text: 'Amoxicillin 500 mg Tablet\nTake after food',
      cleaned_text: 'Amoxicillin 500 mg Tablet\nTake after food',
      fields: {
        medicine_name: 'Amoxicillin',
        dosage_amount: 500.0,
        dosage_unit: 'mg',
        dosage_form: 'TABLET',
        instructions: 'Take after food',
        start_date: '2026-08-18',
        expiry_date: null,
      },
      match: {
        matched_name: 'Amoxicillin',
        confidence: 0.95,
        confidence_level: 'HIGH',
        candidates: [{ dataset_name: 'Amoxicillin', confidence: 0.95, match_type: 'EXACT' }],
      },
      confidence_score: 0.95,
      confidence_level: 'HIGH',
    };

    ocrService.scanPrescription.mockResolvedValueOnce(mockOCRResponse);

    renderComponent();

    const validFile = new File(['fake-png-bytes'], 'prescription.png', {
      type: 'image/png',
    });

    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [validFile] } });

    // Should show review screen after API resolves with medication fields
    await waitFor(() => {
      expect(screen.getByText(/Match Confidence: HIGH/i)).toBeInTheDocument();
      expect(screen.getByDisplayValue('Amoxicillin')).toBeInTheDocument();
      expect(screen.getByDisplayValue('500')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Take after food')).toBeInTheDocument();
    });
  });

  it('allows editing fields and submitting confirmation', async () => {
    const mockOCRResponse = {
      medication: {
        medicine_name: { value: 'Amoxicillin', source: 'ocr', confidence: 0.94 },
        strength: { value: '500', source: 'ocr', confidence: 0.90 },
        unit: { value: 'mg', source: 'ocr', confidence: 0.90 },
        dosage_form: { value: 'TABLET', source: 'ocr', confidence: 0.85 },
        instructions: { value: 'Take after meals', source: 'ocr', confidence: 0.85 },
        start_date: { value: '2026-08-18', source: 'ocr', confidence: 0.80 },
        end_date: { value: null, source: 'not_detected', confidence: 0.0 },
      },
      raw_text: 'Amoxicilin 500 mg',
      fields: {
        medicine_name: 'Amoxicillin',
        dosage_amount: 500.0,
        dosage_unit: 'mg',
        dosage_form: 'TABLET',
        instructions: 'Take after meals',
      },
      match: {
        matched_name: 'Amoxicillin',
        confidence: 0.94,
        confidence_level: 'HIGH',
      },
      confidence_score: 0.94,
      confidence_level: 'HIGH',
    };

    ocrService.scanPrescription.mockResolvedValueOnce(mockOCRResponse);
    ocrService.confirmPrescription.mockResolvedValueOnce({
      success: true,
      medicine_id: 42,
    });

    renderComponent();

    const validFile = new File(['fake-png-bytes'], 'prescription.png', {
      type: 'image/png',
    });
    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.getByDisplayValue('Amoxicillin')).toBeInTheDocument();
    });

    // Click confirm button
    const confirmBtn = screen.getByRole('button', {
      name: /Confirm & Save to My Medications/i,
    });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(ocrService.confirmPrescription).toHaveBeenCalledTimes(1);
      expect(screen.getByText('Prescription Successfully Imported!')).toBeInTheDocument();
    });
  });
});

