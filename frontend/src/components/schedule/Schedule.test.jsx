import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Schedule from './Schedule';
import medicationService from '../../api/medicationService';

vi.mock('../../api/medicationService', () => ({
  default: {
    listSchedules: vi.fn(),
    listMedicines: vi.fn(),
    createMedicineSchedule: vi.fn(),
    updateSchedule: vi.fn(),
    deleteSchedule: vi.fn(),
  },
  medicationService: {
    listSchedules: vi.fn(),
    listMedicines: vi.fn(),
    createMedicineSchedule: vi.fn(),
    updateSchedule: vi.fn(),
    deleteSchedule: vi.fn(),
  },
}));

describe('Schedule Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    medicationService.listMedicines.mockResolvedValue([]);
  });

  it('renders empty state when no schedules exist', async () => {
    medicationService.listSchedules.mockResolvedValueOnce([]);

    render(<Schedule />);

    await waitFor(() => {
      expect(screen.getByText(/No scheduled intakes yet/i)).toBeInTheDocument();
    });
  });

  it('renders schedules loaded from database', async () => {
    medicationService.listSchedules.mockResolvedValueOnce([
      {
        id: 1,
        medicine_id: 10,
        frequency_type: 'TWICE_DAILY',
        times_per_day: 2,
        scheduled_times: ['08:00', '20:00'],
        dose_quantity: 1.0,
        start_date: '2026-08-17',
        is_active: true,
        medicine: {
          id: 10,
          name: 'Metformin',
          dosage_amount: 500,
          dosage_unit: 'mg',
          medicine_form: 'TABLET',
        },
      },
    ]);

    render(<Schedule />);

    await waitFor(() => {
      expect(screen.getByText('Metformin')).toBeInTheDocument();
      expect(screen.getByText('Twice Daily')).toBeInTheDocument();
      expect(screen.getByText('08:00')).toBeInTheDocument();
      expect(screen.getByText('20:00')).toBeInTheDocument();
    });
  });
});
