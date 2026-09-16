import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Prescriptions from './Prescriptions';
import medicationService from '../../api/medicationService';

vi.mock('../../api/medicationService', () => ({
  default: {
    listPrescriptions: vi.fn(),
    createPrescription: vi.fn(),
    updatePrescription: vi.fn(),
    deletePrescription: vi.fn(),
  },
  medicationService: {
    listPrescriptions: vi.fn(),
    createPrescription: vi.fn(),
    updatePrescription: vi.fn(),
    deletePrescription: vi.fn(),
  },
}));

describe('Prescriptions Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no prescriptions exist', async () => {
    medicationService.listPrescriptions.mockResolvedValueOnce([]);

    render(<Prescriptions />);

    await waitFor(() => {
      expect(screen.getByText(/No prescriptions added yet/i)).toBeInTheDocument();
    });
  });

  it('renders loaded prescription from database', async () => {
    medicationService.listPrescriptions.mockResolvedValueOnce([
      {
        id: 1,
        prescription_number: 'RX-7701',
        doctor_name: 'Dr. House',
        issue_date: '2026-08-01',
        expiry_date: '2026-12-31',
        status: 'ACTIVE',
        notes: 'Take with water',
      },
    ]);

    render(<Prescriptions />);

    await waitFor(() => {
      expect(screen.getByText('RX-7701')).toBeInTheDocument();
      expect(screen.getByText('Dr. House')).toBeInTheDocument();
      expect(screen.getByText('ACTIVE')).toBeInTheDocument();
    });
  });
});
