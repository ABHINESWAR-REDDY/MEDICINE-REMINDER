import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import CaregiverDashboard, { extractErrorMessage } from './CaregiverDashboard';
import { caregiverService } from '../../api/caregiverService';

vi.mock('../../api/caregiverService', () => ({
  caregiverService: {
    getDashboard: vi.fn(),
    getAlerts: vi.fn(),
  },
}));

describe('CaregiverDashboard Component & Resilience', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders assigned patients and supervision metrics', async () => {
    vi.mocked(caregiverService.getDashboard).mockResolvedValue({
      total_assigned_patients: 2,
      today_doses_scheduled: 6,
      today_doses_taken: 4,
      today_doses_missed: 1,
      today_doses_pending: 1,
      overall_adherence_percentage: 80.0,
      overall_adherence_status: 'Needs Attention',
      patients: [
        {
          id: 5,
          name: 'John Doe',
          email: 'john@example.com',
          medications_count: 3,
          today_doses_total: 4,
          today_doses_taken: 3,
          today_doses_missed: 1,
          adherence_percentage: 75.0,
          adherence_status: 'Needs Attention',
        },
      ],
    });

    vi.mocked(caregiverService.getAlerts).mockResolvedValue([
      {
        id: 'alert_1',
        patient_id: 5,
        patient_name: 'John Doe',
        severity: 'WARNING',
        title: 'Missed Dose: Metformin',
        message: 'Patient John Doe missed the 08:00 UTC scheduled dose.',
        timestamp: '2026-08-20T08:00:00Z',
      },
    ]);

    render(
      <BrowserRouter>
        <CaregiverDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Caregiver Supervision Portal')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
      expect(screen.getByText('Missed Dose: Metformin:')).toBeInTheDocument();
      expect(screen.getByText('80%')).toBeInTheDocument();
    });
  });

  it('renders live chat message alert with direct Live Chat button', async () => {
    vi.mocked(caregiverService.getDashboard).mockResolvedValue({
      total_assigned_patients: 1,
      today_doses_scheduled: 2,
      today_doses_taken: 2,
      today_doses_missed: 0,
      today_doses_pending: 0,
      overall_adherence_percentage: 100.0,
      overall_adherence_status: 'Good',
      patients: [
        {
          id: 7,
          name: 'Alice Cooper',
          email: 'alice@example.com',
          medications_count: 2,
          today_doses_total: 2,
          today_doses_taken: 2,
          today_doses_missed: 0,
          adherence_percentage: 100.0,
          adherence_status: 'Good',
        },
      ],
    });

    vi.mocked(caregiverService.getAlerts).mockResolvedValue([
      {
        id: 'chat_msg_10',
        patient_id: 7,
        patient_name: 'Alice Cooper',
        severity: 'INFO',
        type: 'CHAT_MESSAGE',
        title: 'New Message from Alice Cooper',
        message: 'You have received a message from this patient: "I took my morning medicine."',
        timestamp: '2026-08-21T10:00:00Z',
      },
    ]);

    render(
      <BrowserRouter>
        <CaregiverDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/New Message from Alice Cooper/i)).toBeInTheDocument();
      expect(screen.getByText(/You have received a message from this patient/i)).toBeInTheDocument();
      expect(screen.getByText('LIVE MESSAGE')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Live Chat/i })).toBeInTheDocument();
    });
  });

  it('renders dashboard successfully even when getAlerts rejects (Promise.allSettled resilience)', async () => {
    vi.mocked(caregiverService.getDashboard).mockResolvedValue({
      total_assigned_patients: 1,
      today_doses_scheduled: 2,
      today_doses_taken: 2,
      today_doses_missed: 0,
      today_doses_pending: 0,
      overall_adherence_percentage: 100.0,
      overall_adherence_status: 'Good',
      patients: [
        {
          id: 12,
          name: 'Resilient Patient',
          email: 'resilient@example.com',
          medications_count: 1,
          today_doses_total: 2,
          today_doses_taken: 2,
          today_doses_missed: 0,
          adherence_percentage: 100.0,
          adherence_status: 'Good',
        },
      ],
    });

    vi.mocked(caregiverService.getAlerts).mockRejectedValue(new Error('Network error on alerts'));

    render(
      <BrowserRouter>
        <CaregiverDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Caregiver Supervision Portal')).toBeInTheDocument();
      expect(screen.getByText('Resilient Patient')).toBeInTheDocument();
      expect(screen.getByText(/Could not update clinical alerts/i)).toBeInTheDocument();
    });
  });

  it('correctly handles and renders 0% adherence instead of defaulting to 100%', async () => {
    vi.mocked(caregiverService.getDashboard).mockResolvedValue({
      total_assigned_patients: 1,
      today_doses_scheduled: 4,
      today_doses_taken: 0,
      today_doses_missed: 4,
      today_doses_pending: 0,
      overall_adherence_percentage: 0.0,
      overall_adherence_status: 'High Risk',
      patients: [
        {
          id: 20,
          name: 'Zero Adherence Patient',
          email: 'zero@example.com',
          medications_count: 2,
          today_doses_total: 4,
          today_doses_taken: 0,
          today_doses_missed: 4,
          adherence_percentage: 0.0,
          adherence_status: 'High Risk',
        },
      ],
    });
    vi.mocked(caregiverService.getAlerts).mockResolvedValue([]);

    render(
      <BrowserRouter>
        <CaregiverDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('0%')).toBeInTheDocument();
      expect(screen.getByText('0% (High Risk)')).toBeInTheDocument();
    });
  });

  it('renders clean empty state when no patients are assigned without demo/mock data', async () => {
    vi.mocked(caregiverService.getDashboard).mockResolvedValue({
      total_assigned_patients: 0,
      today_doses_scheduled: 0,
      today_doses_taken: 0,
      today_doses_missed: 0,
      today_doses_pending: 0,
      overall_adherence_percentage: 100.0,
      overall_adherence_status: 'Good',
      patients: [],
    });
    vi.mocked(caregiverService.getAlerts).mockResolvedValue([]);

    render(
      <BrowserRouter>
        <CaregiverDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No patients are currently assigned to you.')).toBeInTheDocument();
    });
  });

  it('correctly extracts both string and object error details', () => {
    // 1. String detail
    const err1 = { response: { data: { detail: 'Custom string error' } } };
    expect(extractErrorMessage(err1)).toBe('Custom string error');

    // 2. Object detail with message
    const err2 = { response: { data: { detail: { message: 'Object error message' } } } };
    expect(extractErrorMessage(err2)).toBe('Object error message');

    // 3. Fallback
    expect(extractErrorMessage(null, 'Default fallback')).toBe('Default fallback');
  });
});
