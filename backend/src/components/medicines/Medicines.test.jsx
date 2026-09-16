import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Medicines from './Medicines';
import medicationService from '../../api/medicationService';

vi.mock('../../api/medicationService', () => ({
  default: {
    listMedicines: vi.fn(),
    listConditions: vi.fn(),
    listPrescriptions: vi.fn(),
    createMedicine: vi.fn(),
    updateMedicine: vi.fn(),
    deactivateMedicine: vi.fn(),
    deleteMedicine: vi.fn(),
    createMedicineSchedule: vi.fn(),
  },
  medicationService: {
    listMedicines: vi.fn(),
    listConditions: vi.fn(),
    listPrescriptions: vi.fn(),
    createMedicine: vi.fn(),
    updateMedicine: vi.fn(),
    deactivateMedicine: vi.fn(),
    deleteMedicine: vi.fn(),
    createMedicineSchedule: vi.fn(),
  },
}));

describe('Medicines Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    medicationService.listConditions.mockResolvedValue([]);
    medicationService.listPrescriptions.mockResolvedValue([]);
  });

  it('renders empty state when no medicines exist in database', async () => {
    medicationService.listMedicines.mockResolvedValueOnce([]);

    render(<Medicines />);

    await waitFor(() => {
      expect(screen.getByText(/No medicines added yet/i)).toBeInTheDocument();
    });
  });

  it('renders medicines returned from database query', async () => {
    medicationService.listMedicines.mockResolvedValueOnce([
      {
        id: 10,
        name: 'Lisinopril',
        dosage_amount: 10,
        dosage_unit: 'mg',
        quantity: 30,
        medicine_form: 'TABLET',
        instructions: 'Take in the morning',
        start_date: '2026-08-17',
        is_active: true,
      },
    ]);

    render(<Medicines />);

    await waitFor(() => {
      expect(screen.getByText('Lisinopril')).toBeInTheDocument();
      expect(screen.getByText('10 mg')).toBeInTheDocument();
      expect(screen.getByText('Qty: 30')).toBeInTheDocument();
      expect(screen.getByText('Starts: 17-08-2026')).toBeInTheDocument();
    });
  });

  it('renders Add New Medication modal with exact title and creates medicine with schedule', async () => {
    medicationService.listMedicines.mockResolvedValue([]);
    medicationService.createMedicine.mockResolvedValueOnce({
      id: 99,
      name: 'Metformin',
      dosage_amount: 500,
      dosage_unit: 'mg',
      quantity: 60,
      medicine_form: 'TABLET',
      start_date: '2026-08-18',
    });
    medicationService.createMedicineSchedule.mockResolvedValueOnce({
      id: 501,
      medicine_id: 99,
      frequency_type: 'TWICE_DAILY',
    });

    render(<Medicines />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Add Medication/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Add Medication/i }));

    // Verify modal title is EXACTLY 'Add New Medication'
    expect(screen.getByRole('heading', { level: 3, name: 'Add New Medication' })).toBeInTheDocument();

    // Fill form
    fireEvent.change(screen.getByLabelText(/Medicine Name/i), { target: { value: 'Metformin' } });
    fireEvent.change(screen.getByLabelText(/Dosage Strength/i), { target: { value: '500' } });
    fireEvent.change(screen.getByLabelText(/Units on Hand/i), { target: { value: '60' } });

    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /Save Medication/i }));

    await waitFor(() => {
      expect(medicationService.createMedicine).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Metformin',
          dosage_amount: 500,
          quantity: 60,
        })
      );
      expect(medicationService.createMedicineSchedule).toHaveBeenCalledWith(
        99,
        expect.objectContaining({
          frequency_type: 'TWICE_DAILY',
          times_per_day: 2,
        })
      );
    });
  });

  it('displays user-friendly session expired error on 401 save response', async () => {
    medicationService.listMedicines.mockResolvedValue([]);
    medicationService.createMedicine.mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Could not validate credentials.' } },
    });

    render(<Medicines />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Add Medication/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Add Medication/i }));

    fireEvent.change(screen.getByLabelText(/Medicine Name/i), { target: { value: 'Metformin' } });
    fireEvent.change(screen.getByLabelText(/Dosage Strength/i), { target: { value: '500' } });
    fireEvent.change(screen.getByLabelText(/Units on Hand/i), { target: { value: '60' } });

    fireEvent.click(screen.getByRole('button', { name: /Save Medication/i }));

    await waitFor(() => {
      expect(screen.getByText('Your session has expired. Please log in again.')).toBeInTheDocument();
      expect(screen.queryByText('Could not validate credentials.')).not.toBeInTheDocument();
    });
  });

  it('displays user-friendly permission error on 403 save response', async () => {
    medicationService.listMedicines.mockResolvedValue([]);
    medicationService.createMedicine.mockRejectedValueOnce({
      response: { status: 403, data: { detail: 'Insufficient permissions to access this resource.' } },
    });

    render(<Medicines />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Add Medication/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Add Medication/i }));

    fireEvent.change(screen.getByLabelText(/Medicine Name/i), { target: { value: 'Metformin' } });
    fireEvent.change(screen.getByLabelText(/Dosage Strength/i), { target: { value: '500' } });
    fireEvent.change(screen.getByLabelText(/Units on Hand/i), { target: { value: '60' } });

    fireEvent.click(screen.getByRole('button', { name: /Save Medication/i }));

    await waitFor(() => {
      expect(screen.getByText('You do not have permission to add medication.')).toBeInTheDocument();
    });
  });
});
