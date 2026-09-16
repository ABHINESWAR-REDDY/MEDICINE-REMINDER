import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PlatformAnalytics from './PlatformAnalytics';
import { adminService } from '../../api/adminService';

vi.mock('../../api/adminService', () => ({
  adminService: {
    getPlatformAnalytics: vi.fn(),
  },
}));

describe('PlatformAnalytics Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders live platform analytics metrics and zero adherence correctly', async () => {
    vi.mocked(adminService.getPlatformAnalytics).mockResolvedValue({
      period: '30d',
      start_date: '2026-07-25T00:00:00Z',
      end_date: '2026-08-24T00:00:00Z',
      users: {
        total_patients: 12,
        total_caregivers: 4,
        active_patients: 10,
        active_caregivers: 3,
        pending_caregivers: 1,
        rejected_caregivers: 0,
        new_patients_in_period: 2,
        new_caregivers_in_period: 1,
      },
      medications: {
        total_active_medications: 15,
        total_tracked_medications: 18,
        scheduled_doses_in_period: 40,
        taken_doses: 35,
        missed_doses: 5,
        skipped_doses: 0,
      },
      adherence: {
        overall_adherence_percentage: 87.5,
        good_adherence_patients: 8,
        needs_attention_patients: 2,
        high_risk_patients: 0,
      },
      caregivers: {
        active_assignments: 8,
        caregivers_with_assignments: 3,
        unassigned_patients: 2,
      },
      prescriptions: {
        total_prescriptions: 6,
        total_ocr_jobs: 6,
        successful_extractions: 5,
        failed_extractions: 1,
      },
      notifications: {
        total_notifications: 45,
        unread_notifications: 3,
        patient_notifications: 35,
        caregiver_alerts: 10,
        missed_dose_notifications: 5,
        refill_notifications: 2,
        chat_notifications: 8,
      },
      chat: {
        total_messages: 24,
        patient_messages: 14,
        caregiver_messages: 10,
        unread_messages: 1,
      },
    });

    render(<PlatformAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Platform Analytics')).toBeInTheDocument();
      expect(screen.getByText('87.5%')).toBeInTheDocument();
      expect(screen.getByText('Dose Intake Breakdown')).toBeInTheDocument();
      expect(screen.getByText('Patient Adherence Cohorts')).toBeInTheDocument();
      expect(screen.getByText('Caregiver Supervision')).toBeInTheDocument();
      expect(screen.getByText('Prescriptions & OCR')).toBeInTheDocument();
    });
  });

  it('renders exact 0.0% adherence when no doses were taken', async () => {
    vi.mocked(adminService.getPlatformAnalytics).mockResolvedValue({
      period: '30d',
      users: { total_patients: 1, total_caregivers: 0 },
      medications: { total_active_medications: 1, scheduled_doses_in_period: 2, taken_doses: 0, missed_doses: 2 },
      adherence: { overall_adherence_percentage: 0.0, good_adherence_patients: 0, high_risk_patients: 1 },
      caregivers: {},
      prescriptions: {},
      notifications: {},
      chat: {},
    });

    render(<PlatformAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('0.0%')).toBeInTheDocument();
    });
  });

  it('switches date range period tabs and triggers backend query', async () => {
    vi.mocked(adminService.getPlatformAnalytics).mockResolvedValue({
      period: '7d',
      users: { total_patients: 5 },
      medications: {},
      adherence: { overall_adherence_percentage: 90.0 },
      caregivers: {},
      prescriptions: {},
      notifications: {},
      chat: {},
    });

    render(<PlatformAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Platform Analytics')).toBeInTheDocument();
    });

    const sevenDaysBtn = screen.getByRole('button', { name: '7 Days' });
    fireEvent.click(sevenDaysBtn);

    await waitFor(() => {
      expect(adminService.getPlatformAnalytics).toHaveBeenCalledWith({ period: '7d' });
    });
  });

  it('displays user-friendly error state with retry on failure', async () => {
    vi.mocked(adminService.getPlatformAnalytics).mockRejectedValue(new Error('Analytics computation failed'));

    render(<PlatformAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Analytics computation failed')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument();
    });
  });
});
