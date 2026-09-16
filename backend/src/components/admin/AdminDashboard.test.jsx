import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import AdminDashboard from './AdminDashboard';
import { adminService } from '../../api/adminService';

vi.mock('../../api/adminService', () => ({
  adminService: {
    getDashboard: vi.fn(),
  },
}));

describe('AdminDashboard Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders live system metrics and summary cards', async () => {
    vi.mocked(adminService.getDashboard).mockResolvedValue({
      total_patients: 15,
      total_caregivers: 4,
      pending_caregivers: 3,
      active_caregivers: 1,
      inactive_caregivers: 3,
      active_assignments: 8,
      total_medicines: 24,
      today_doses_total: 10,
      today_doses_taken: 8,
      today_doses_missed: 2,
    });

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('System Administration')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument();
      expect(screen.getByText('Pending Approvals')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('Active Assignments')).toBeInTheDocument();
      expect(screen.getByText('Tracked Medications')).toBeInTheDocument();
      expect(screen.getByText('Doses Taken Today')).toBeInTheDocument();
      expect(screen.getByText('Doses Missed Today')).toBeInTheDocument();
    });

    // Ensure individual caregiver approval list/table is not rendered on Admin Dashboard
    expect(screen.queryByText('Pending Caregiver Registrations')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Reject/i })).not.toBeInTheDocument();
  });
});
