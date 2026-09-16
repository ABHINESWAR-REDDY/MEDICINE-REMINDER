import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PlatformActivities from './PlatformActivities';
import { adminService } from '../../api/adminService';

vi.mock('../../api/adminService', () => ({
  adminService: {
    getPlatformActivities: vi.fn(),
  },
}));

describe('PlatformActivities Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders platform activities table with live database records', async () => {
    vi.mocked(adminService.getPlatformActivities).mockResolvedValue({
      total: 2,
      limit: 15,
      offset: 0,
      items: [
        {
          id: 1,
          actor_id: 10,
          actor_name: 'Dr. Gregory House',
          actor_email: 'house@pillsync.com',
          actor_role: 'ADMIN',
          action: 'CAREGIVER_APPROVED',
          target_type: 'User',
          target_id: 5,
          description: 'Approved caregiver registration for John Doe.',
          details: { name: 'John Doe' },
          created_at: '2026-08-24T12:00:00Z',
        },
        {
          id: 2,
          actor_id: 20,
          actor_name: 'Alice Patient',
          actor_email: 'alice@pillsync.com',
          actor_role: 'PATIENT',
          action: 'DOSE_TAKEN',
          target_type: 'MedicationDose',
          target_id: 101,
          description: 'Marked scheduled dose #101 as TAKEN.',
          details: { patient_id: 20 },
          created_at: '2026-08-24T12:15:00Z',
        },
      ],
    });

    render(<PlatformActivities />);

    await waitFor(() => {
      expect(screen.getByText('Platform Activities')).toBeInTheDocument();
      expect(screen.getByText('Dr. Gregory House')).toBeInTheDocument();
      expect(screen.getByText('house@pillsync.com')).toBeInTheDocument();
      expect(screen.getByText('CAREGIVER_APPROVED')).toBeInTheDocument();
      expect(screen.getByText('Approved caregiver registration for John Doe.')).toBeInTheDocument();

      expect(screen.getByText('Alice Patient')).toBeInTheDocument();
      expect(screen.getByText('alice@pillsync.com')).toBeInTheDocument();
      expect(screen.getByText('DOSE_TAKEN')).toBeInTheDocument();
      expect(screen.getByText('Marked scheduled dose #101 as TAKEN.')).toBeInTheDocument();
    });
  });

  it('renders clean empty state when no activities exist', async () => {
    vi.mocked(adminService.getPlatformActivities).mockResolvedValue({
      total: 0,
      limit: 15,
      offset: 0,
      items: [],
    });

    render(<PlatformActivities />);

    await waitFor(() => {
      expect(screen.getByText('No platform activities found.')).toBeInTheDocument();
    });
  });

  it('displays user-friendly error state with retry on API failure', async () => {
    vi.mocked(adminService.getPlatformActivities).mockRejectedValue(new Error('Network Connection Failed'));

    render(<PlatformActivities />);

    await waitFor(() => {
      expect(screen.getByText('Network Connection Failed')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument();
    });
  });
});
