import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import NotificationSettings from './NotificationSettings';
import { adminService } from '../../api/adminService';

vi.mock('../../api/adminService', () => ({
  adminService: {
    getNotificationSettings: vi.fn(),
    updateNotificationSettings: vi.fn(),
  },
}));

describe('NotificationSettings Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders persistent notification settings from database', async () => {
    vi.mocked(adminService.getNotificationSettings).mockResolvedValue({
      patient_medication_reminders_enabled: true,
      patient_missed_dose_alerts_enabled: true,
      patient_refill_alerts_enabled: false,
      patient_polling_interval_seconds: 30,
      caregiver_missed_dose_alerts_enabled: true,
      caregiver_refill_alerts_enabled: true,
      caregiver_adherence_risk_alerts_enabled: true,
      caregiver_patient_chat_alerts_enabled: true,
      system_security_alerts_enabled: true,
      system_operational_alerts_enabled: true,
      updated_at: '2026-08-24T12:00:00Z',
      updated_by: 'Super Admin (admin@pillsync.com)',
    });

    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Notification Settings')).toBeInTheDocument();
      expect(screen.getByText('Patient Notifications')).toBeInTheDocument();
      expect(screen.getByText('Caregiver Notifications')).toBeInTheDocument();
      expect(screen.getByText('System Notifications')).toBeInTheDocument();
      expect(screen.getByText(/Super Admin/)).toBeInTheDocument();
    });
  });

  it('toggles a setting and saves successfully to database', async () => {
    vi.mocked(adminService.getNotificationSettings).mockResolvedValue({
      patient_medication_reminders_enabled: true,
      patient_missed_dose_alerts_enabled: true,
      patient_refill_alerts_enabled: true,
      patient_polling_interval_seconds: 30,
      caregiver_missed_dose_alerts_enabled: true,
      caregiver_refill_alerts_enabled: true,
      caregiver_adherence_risk_alerts_enabled: true,
      caregiver_patient_chat_alerts_enabled: true,
      system_security_alerts_enabled: true,
      system_operational_alerts_enabled: true,
      updated_at: '2026-08-24T12:00:00Z',
      updated_by: 'Super Admin',
    });

    vi.mocked(adminService.updateNotificationSettings).mockResolvedValue({
      patient_medication_reminders_enabled: false,
      updated_at: '2026-08-24T12:05:00Z',
      updated_by: 'Super Admin',
    });

    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Notification Settings')).toBeInTheDocument();
    });

    const switches = screen.getAllByRole('switch');
    expect(switches.length).toBeGreaterThan(0);

    // Click first toggle
    fireEvent.click(switches[0]);

    // Submit save
    const saveBtn = screen.getByRole('button', { name: /Save Configuration/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(adminService.updateNotificationSettings).toHaveBeenCalled();
      expect(screen.getByText(/Notification settings have been successfully saved/i)).toBeInTheDocument();
    });
  });

  it('displays user-friendly error state on failure', async () => {
    vi.mocked(adminService.getNotificationSettings).mockRejectedValue(new Error('Permission Denied'));

    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Permission Denied')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
    });
  });
});
