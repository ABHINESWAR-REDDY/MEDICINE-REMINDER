import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import PatientAlerts from './PatientAlerts';
import { notificationService } from '../../api/notificationService';

vi.mock('../../api/notificationService', () => ({
  notificationService: {
    getNotifications: vi.fn(),
    getUnreadCount: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
  },
}));

describe('PatientAlerts Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders alerts hub with notifications, filter tabs, and severity badges', async () => {
    vi.mocked(notificationService.getNotifications).mockResolvedValue([
      {
        id: 1,
        user_id: 3,
        type: 'MEDICATION_REMINDER',
        title: 'Medication Reminder: Metformin 500mg',
        message: 'Your scheduled dose of Metformin 500mg is due at 08:00 PM.',
        severity: 'INFO',
        medicine_name: 'Metformin 500mg',
        is_read: false,
        created_at: '2026-08-21T14:30:00Z',
      },
      {
        id: 2,
        user_id: 3,
        type: 'MISSED_DOSE',
        title: 'Missed Dose: Amoxicillin 250mg',
        message: 'You missed your scheduled 09:00 AM dose of Amoxicillin 250mg.',
        severity: 'WARNING',
        medicine_name: 'Amoxicillin 250mg',
        is_read: true,
        created_at: '2026-08-21T03:30:00Z',
      },
    ]);

    render(
      <BrowserRouter>
        <PatientAlerts />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Medication Alerts & Reminders')).toBeInTheDocument();
      expect(screen.getByText('Medication Reminder: Metformin 500mg')).toBeInTheDocument();
      expect(screen.getByText('Missed Dose: Amoxicillin 250mg')).toBeInTheDocument();
      expect(screen.getByText('1 Unread')).toBeInTheDocument();
    });
  });

  it('filters notifications by tabs and supports marking single notification as read', async () => {
    vi.mocked(notificationService.getNotifications).mockResolvedValue([
      {
        id: 1,
        user_id: 3,
        type: 'MEDICATION_REMINDER',
        title: 'Medication Reminder: Metformin 500mg',
        message: 'Your scheduled dose of Metformin 500mg is due at 08:00 PM.',
        severity: 'INFO',
        is_read: false,
        created_at: '2026-08-21T14:30:00Z',
      },
      {
        id: 2,
        user_id: 3,
        type: 'MISSED_DOSE',
        title: 'Missed Dose: Amoxicillin 250mg',
        message: 'You missed your scheduled 09:00 AM dose of Amoxicillin 250mg.',
        severity: 'WARNING',
        is_read: false,
        created_at: '2026-08-21T03:30:00Z',
      },
    ]);
    vi.mocked(notificationService.markAsRead).mockResolvedValue({ success: true });

    render(
      <BrowserRouter>
        <PatientAlerts />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Medication Reminder: Metformin 500mg')).toBeInTheDocument();
    });

    // Switch to MISSED DOSES tab
    const missedTab = screen.getByRole('button', { name: /MISSED DOSES/i });
    fireEvent.click(missedTab);

    expect(screen.getByText('Missed Dose: Amoxicillin 250mg')).toBeInTheDocument();
    expect(screen.queryByText('Medication Reminder: Metformin 500mg')).not.toBeInTheDocument();

    // Mark as read
    const markReadBtn = screen.getByRole('button', { name: /Mark as Read/i });
    fireEvent.click(markReadBtn);

    await waitFor(() => {
      expect(notificationService.markAsRead).toHaveBeenCalledWith(2);
    });
  });

  it('displays empty state message when patient has no notifications', async () => {
    vi.mocked(notificationService.getNotifications).mockResolvedValue([]);

    render(
      <BrowserRouter>
        <PatientAlerts />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No new medication alerts.')).toBeInTheDocument();
      expect(screen.getByText(/Your medication schedules and dose intake will generate alerts automatically here/i)).toBeInTheDocument();
    });
  });
});

