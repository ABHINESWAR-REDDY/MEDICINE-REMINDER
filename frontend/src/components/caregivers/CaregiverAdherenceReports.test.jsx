import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import CaregiverAdherenceReports from './CaregiverAdherenceReports';
import caregiverService from '../../api/caregiverService';

vi.mock('../../api/caregiverService', () => ({
  default: {
    getAdherenceReports: vi.fn(),
    getPatientAdherenceReport: vi.fn(),
  },
  caregiverService: {
    getAdherenceReports: vi.fn(),
    getPatientAdherenceReport: vi.fn(),
  },
}));

describe('CaregiverAdherenceReports Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading state initially', async () => {
    caregiverService.getAdherenceReports.mockImplementation(() => new Promise(() => {}));

    render(
      <BrowserRouter>
        <CaregiverAdherenceReports />
      </BrowserRouter>
    );

    expect(screen.getByText(/Aggregating live adherence metrics for assigned patients.../i)).toBeInTheDocument();
  });

  it('renders empty state when caregiver has zero assigned patients', async () => {
    caregiverService.getAdherenceReports.mockResolvedValue({
      caregiver_id: 2,
      period_days: 30,
      total_assigned_patients: 0,
      overall_adherence_percentage: 100.0,
      overall_adherence_status: 'Good',
      high_risk_count: 0,
      needs_attention_count: 0,
      good_standing_count: 0,
      reports: [],
    });

    render(
      <BrowserRouter>
        <CaregiverAdherenceReports />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No patients are currently assigned to you.')).toBeInTheDocument();
      expect(screen.getByText(/Once an administrator assigns patients to your caregiver account/i)).toBeInTheDocument();
    });
  });

  it('renders real database adherence records across assigned patients', async () => {
    caregiverService.getAdherenceReports.mockResolvedValue({
      caregiver_id: 2,
      period_days: 30,
      total_assigned_patients: 2,
      overall_adherence_percentage: 84.0,
      overall_adherence_status: 'Needs Attention',
      high_risk_count: 1,
      needs_attention_count: 0,
      good_standing_count: 1,
      reports: [
        {
          patient_id: 10,
          employee_id: 'PT000010',
          name: 'Alice Johnson',
          email: 'alice@example.com',
          account_created_at: '2026-08-01T10:00:00Z',
          adherence_percentage: 92.0,
          adherence_status: 'Good',
          total_expected_doses: 25,
          taken_count: 23,
          missed_count: 1,
          skipped_count: 1,
          active_medications_count: 2,
        },
        {
          patient_id: 11,
          employee_id: 'PT000011',
          name: 'Bob Smith',
          email: 'bob@example.com',
          account_created_at: '2026-08-05T10:00:00Z',
          adherence_percentage: 76.0,
          adherence_status: 'High Risk',
          total_expected_doses: 25,
          taken_count: 19,
          missed_count: 4,
          skipped_count: 2,
          active_medications_count: 1,
        },
      ],
    });

    render(
      <BrowserRouter>
        <CaregiverAdherenceReports />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
      expect(screen.getByText('Bob Smith')).toBeInTheDocument();
      expect(screen.getByText('92% — Good')).toBeInTheDocument();
      expect(screen.getByText('76% — High Risk')).toBeInTheDocument();
      expect(screen.getByText('84%')).toBeInTheDocument(); // Overall Group Adherence
    });

    // Test search filter
    const searchInput = screen.getByPlaceholderText(/Search patient by name/i);
    fireEvent.change(searchInput, { target: { value: 'Alice' } });
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
    expect(screen.queryByText('Bob Smith')).not.toBeInTheDocument();
  });

  it('loads detailed patient report when clicking View Detailed Report', async () => {
    caregiverService.getAdherenceReports.mockResolvedValue({
      caregiver_id: 2,
      period_days: 30,
      total_assigned_patients: 1,
      overall_adherence_percentage: 92.0,
      overall_adherence_status: 'Good',
      high_risk_count: 0,
      needs_attention_count: 0,
      good_standing_count: 1,
      reports: [
        {
          patient_id: 10,
          employee_id: 'PT000010',
          name: 'Alice Johnson',
          email: 'alice@example.com',
          account_created_at: '2026-08-01T10:00:00Z',
          adherence_percentage: 92.0,
          adherence_status: 'Good',
          total_expected_doses: 25,
          taken_count: 23,
          missed_count: 1,
          skipped_count: 1,
          active_medications_count: 1,
        },
      ],
    });

    caregiverService.getPatientAdherenceReport.mockResolvedValue({
      patient: {
        id: 10,
        employee_id: 'PT000010',
        name: 'Alice Johnson',
        email: 'alice@example.com',
        account_created_at: '2026-08-01T10:00:00Z',
      },
      period_days: 30,
      adherence_summary: {
        patient_id: 10,
        period_days: 30,
        adherence_percentage: 92.0,
        adherence_status: 'Good',
        total_expected_doses: 25,
        taken_count: 23,
        missed_count: 1,
        skipped_count: 1,
      },
      medication_breakdown: [
        {
          medicine_id: 5,
          medicine_name: 'Metformin',
          strength: 500,
          unit: 'mg',
          dosage_form: 'TABLET',
          total_expected: 25,
          taken_count: 23,
          missed_count: 1,
          skipped_count: 1,
          adherence_percentage: 92.0,
          current_stock: 40,
          estimated_remaining_days: 20,
          refill_status: 'VALID',
        },
      ],
      recent_dose_events: [
        {
          id: 101,
          medicine_id: 5,
          medicine_name: 'Metformin',
          scheduled_time: '2026-08-22T08:00:00Z',
          actual_time: '2026-08-22T08:05:00Z',
          status: 'TAKEN',
          dose_quantity: 1.0,
        },
      ],
      refill_predictions: [],
    });

    render(
      <BrowserRouter>
        <CaregiverAdherenceReports />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
    });

    const detailBtn = screen.getByRole('button', { name: /View Detailed Report/i });
    fireEvent.click(detailBtn);

    expect(await screen.findByText('Medication-Specific Compliance & Refill Status')).toBeInTheDocument();
    const metformins = await screen.findAllByText('Metformin');
    expect(metformins.length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText('20 days left (40 units)')).toBeInTheDocument();
  });


  it('handles API error state with retry button', async () => {
    caregiverService.getAdherenceReports.mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <CaregiverAdherenceReports />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
    });
  });
});
