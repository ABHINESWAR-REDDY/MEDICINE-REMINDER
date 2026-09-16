import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PatientManagement from './PatientManagement';
import { adminService } from '../../api/adminService';

vi.mock('../../api/adminService', () => ({
  adminService: {
    getPatients: vi.fn(),
    togglePatientActive: vi.fn(),
  },
}));

describe('PatientManagement Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders dynamic patient list from live database records with exact account creation date', async () => {
    vi.mocked(adminService.getPatients).mockResolvedValue([
      {
        id: 1,
        name: 'Alice Patient',
        email: 'alice.patient@example.com',
        role: 'PATIENT',
        is_active: true,
        approval_status: 'APPROVED',
        created_at: '2026-08-17T14:56:49Z',
        assigned_caregiver_id: 10,
        assigned_caregiver_name: 'Dr. Gregory House',
        medications_count: 3,
      },
      {
        id: 2,
        name: 'Bob Unassigned',
        email: 'bob@example.com',
        role: 'PATIENT',
        is_active: false,
        approval_status: 'APPROVED',
        created_at: '2026-08-18T10:00:00Z',
        assigned_caregiver_id: null,
        assigned_caregiver_name: null,
        medications_count: 0,
      },
    ]);

    render(<PatientManagement />);

    await waitFor(() => {
      expect(screen.getByText('Patient Directory & Management')).toBeInTheDocument();
      expect(screen.getByText('Total Patients: 2')).toBeInTheDocument();
      expect(screen.getByText('Alice Patient')).toBeInTheDocument();
      expect(screen.getByText('alice.patient@example.com')).toBeInTheDocument();
      expect(screen.getByText('17-08-2026')).toBeInTheDocument();
      expect(screen.getByText('Dr. Gregory House')).toBeInTheDocument();
      expect(screen.getByText('3 medications')).toBeInTheDocument();
      expect(screen.getByText('Bob Unassigned')).toBeInTheDocument();
      expect(screen.getByText('No caregiver assigned')).toBeInTheDocument();
      expect(screen.getByText('0 medications')).toBeInTheDocument();
    });
  });

  it('renders clean empty state when database returns no patients', async () => {
    vi.mocked(adminService.getPatients).mockResolvedValue([]);

    render(<PatientManagement />);

    await waitFor(() => {
      expect(screen.getByText('No registered patients found.')).toBeInTheDocument();
      expect(screen.getByText('Total Patients: 0')).toBeInTheDocument();
    });
  });

  it('filters by status tab dynamically calling backend API', async () => {
    vi.mocked(adminService.getPatients).mockResolvedValue([]);

    render(<PatientManagement />);

    await waitFor(() => {
      expect(screen.getByText('No registered patients found.')).toBeInTheDocument();
    });

    const activeTab = screen.getByRole('button', { name: 'ACTIVE' });
    fireEvent.click(activeTab);

    await waitFor(() => {
      expect(adminService.getPatients).toHaveBeenCalledWith('ACTIVE', '');
    });
  });

  it('displays user-friendly error state with retry button on API failure', async () => {
    vi.mocked(adminService.getPatients).mockRejectedValue(new Error('Network Error'));

    render(<PatientManagement />);

    await waitFor(() => {
      expect(screen.getByText('Network Error')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument();
    });
  });
});
