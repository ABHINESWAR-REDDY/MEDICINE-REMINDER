import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import MedicationHistory from './MedicationHistory';
import medicationService from '../../api/medicationService';

vi.mock('../../api/medicationService', () => ({
  default: {
    getMedicationHistory: vi.fn(),
  },
  medicationService: {
    getMedicationHistory: vi.fn(),
  },
}));

describe('MedicationHistory Component - Real Data Adherence Log', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading state initially', async () => {
    medicationService.getMedicationHistory.mockImplementation(
      () => new Promise(() => {})
    );

    render(
      <BrowserRouter>
        <MedicationHistory />
      </BrowserRouter>
    );

    expect(screen.getByText(/Loading your real medication records from database.../i)).toBeInTheDocument();
  });

  it('renders exact empty state when patient has zero medication history records', async () => {
    medicationService.getMedicationHistory.mockResolvedValue({
      patient_id: 1,
      total_records: 0,
      history: [],
    });

    render(
      <BrowserRouter>
        <MedicationHistory />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No medication history available.')).toBeInTheDocument();
      expect(screen.getByText(/You do not have any recorded medication intake records/i)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Add Medication/i })).toBeInTheDocument();
    });
  });

  it('renders real database medication history events with status badges and timestamps', async () => {
    medicationService.getMedicationHistory.mockResolvedValue({
      patient_id: 5,
      total_records: 3,
      history: [
        {
          id: 101,
          dose_id: 101,
          medicine_id: 10,
          medicine_name: 'Metformin HCl',
          strength: 500,
          unit: 'mg',
          dosage_form: 'TABLET',
          instructions: 'Take with evening meal',
          schedule_description: 'Twice Daily (08:00, 20:00)',
          dose_quantity: 1.0,
          start_date: '2026-08-01',
          end_date: null,
          is_active: true,
          scheduled_time: '2026-08-22T08:00:00Z',
          actual_time: '2026-08-22T08:05:00Z',
          status: 'TAKEN',
        },
        {
          id: 102,
          dose_id: 102,
          medicine_id: 10,
          medicine_name: 'Metformin HCl',
          strength: 500,
          unit: 'mg',
          dosage_form: 'TABLET',
          instructions: 'Take with evening meal',
          schedule_description: 'Twice Daily (08:00, 20:00)',
          dose_quantity: 1.0,
          start_date: '2026-08-01',
          end_date: null,
          is_active: true,
          scheduled_time: '2026-08-21T20:00:00Z',
          actual_time: null,
          status: 'MISSED',
        },
        {
          id: 103,
          dose_id: 103,
          medicine_id: 11,
          medicine_name: 'Amoxicillin',
          strength: 250,
          unit: 'mg',
          dosage_form: 'CAPSULE',
          instructions: 'Take after food',
          schedule_description: 'Once Daily (09:00)',
          dose_quantity: 1.0,
          start_date: '2026-08-15',
          end_date: '2026-08-25',
          is_active: true,
          scheduled_time: '2026-08-23T09:00:00Z',
          actual_time: null,
          status: 'SCHEDULED',
        },
      ],
    });

    render(
      <BrowserRouter>
        <MedicationHistory />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('Metformin HCl').length).toBeGreaterThan(0);
      expect(screen.getByText('Amoxicillin')).toBeInTheDocument();
      expect(screen.getByText('TAKEN')).toBeInTheDocument();
      expect(screen.getByText('MISSED')).toBeInTheDocument();
      expect(screen.getByText('SCHEDULED')).toBeInTheDocument();
      expect(screen.getByText(/Showing 3 of 3 Medication History Events/i)).toBeInTheDocument();
    });

    // Test filter tabs
    fireEvent.click(screen.getByRole('button', { name: 'Taken Doses' }));
    expect(screen.getAllByText('Metformin HCl').length).toBeGreaterThan(0);
    expect(screen.queryByText('Amoxicillin')).not.toBeInTheDocument();

    // Test search filter
    fireEvent.click(screen.getByRole('button', { name: 'All History' }));
    const searchInput = screen.getByPlaceholderText(/Search by medicine name/i);
    fireEvent.change(searchInput, { target: { value: 'Amoxicillin' } });
    expect(screen.getByText('Amoxicillin')).toBeInTheDocument();
    expect(screen.queryByText('Metformin HCl')).not.toBeInTheDocument();
  });

  it('handles error state with retry functionality', async () => {
    medicationService.getMedicationHistory.mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <MedicationHistory />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
    });
  });
});
