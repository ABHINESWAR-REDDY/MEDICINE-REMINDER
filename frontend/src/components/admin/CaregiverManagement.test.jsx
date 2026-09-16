import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import CaregiverManagement from './CaregiverManagement';
import { adminService } from '../../api/adminService';

vi.mock('../../api/adminService', () => ({
  adminService: {
    getCaregivers: vi.fn(),
    approveCaregiver: vi.fn(),
    rejectCaregiver: vi.fn(),
    activateCaregiver: vi.fn(),
    deactivateCaregiver: vi.fn(),
  },
}));

describe('CaregiverManagement Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders real database caregivers with exact account creation date', async () => {
    vi.mocked(adminService.getCaregivers).mockResolvedValue([
      {
        id: 42,
        name: 'Dr. Gregory House',
        email: 'house@princeton.edu',
        role: 'CAREGIVER',
        approval_status: 'PENDING',
        is_active: false,
        assigned_patients_count: 0,
        created_at: '2026-08-18T14:32:45Z',
      },
    ]);

    render(<CaregiverManagement />);

    await waitFor(() => {
      expect(screen.getByText('Caregiver Directory & Approvals')).toBeInTheDocument();
      expect(screen.getByText('Dr. Gregory House')).toBeInTheDocument();
      expect(screen.getByText('house@princeton.edu')).toBeInTheDocument();
      expect(screen.getByText('18-08-2026')).toBeInTheDocument();
      expect(screen.getByText('Account Created')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument();
    });
  });

  it('renders clean empty state when no caregivers exist', async () => {
    vi.mocked(adminService.getCaregivers).mockResolvedValue([]);

    render(<CaregiverManagement />);

    await waitFor(() => {
      expect(screen.getByText('No caregivers found.')).toBeInTheDocument();
    });
  });

  it('filters by status tab dynamically calling backend API', async () => {
    vi.mocked(adminService.getCaregivers).mockResolvedValue([]);

    render(<CaregiverManagement />);

    await waitFor(() => {
      expect(screen.getByText('No caregivers found.')).toBeInTheDocument();
    });

    const pendingTab = screen.getByRole('button', { name: 'PENDING' });
    fireEvent.click(pendingTab);

    await waitFor(() => {
      expect(adminService.getCaregivers).toHaveBeenCalledWith('PENDING');
      expect(screen.getByText('No pending caregiver registrations.')).toBeInTheDocument();
    });
  });

  it('approves caregiver and displays email notification message', async () => {
    vi.mocked(adminService.getCaregivers).mockResolvedValue([
      {
        id: 42,
        name: 'Dr. Gregory House',
        email: 'house@princeton.edu',
        role: 'CAREGIVER',
        approval_status: 'PENDING',
        is_active: false,
        assigned_patients_count: 0,
        created_at: '2026-08-18T14:32:45Z',
      },
    ]);
    vi.mocked(adminService.approveCaregiver).mockResolvedValue({
      success: true,
      status: 'APPROVED',
      message: 'Caregiver Dr. Gregory House approved and notification email sent.',
      email_notification: 'SENT',
    });

    render(<CaregiverManagement />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));

    await waitFor(() => {
      expect(adminService.approveCaregiver).toHaveBeenCalledWith(42);
      expect(screen.getByText('Caregiver Dr. Gregory House approved and notification email sent.')).toBeInTheDocument();
    });
  });
});
