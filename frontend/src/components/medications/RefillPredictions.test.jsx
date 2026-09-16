import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import RefillPredictions from './RefillPredictions';
import medicationService from '../../api/medicationService';

const mockGetRefillPredictions = vi.fn();

vi.mock('../../api/medicationService', () => ({
  default: {
    getRefillPredictions: (...args) => mockGetRefillPredictions(...args),
  },
  medicationService: {
    getRefillPredictions: (...args) => mockGetRefillPredictions(...args),
  },
}));

describe('RefillPredictions Component - Dynamic Real Calculations', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders loading state initially', async () => {
    mockGetRefillPredictions.mockImplementation(
      () => new Promise(() => {})
    );

    render(
      <BrowserRouter>
        <RefillPredictions />
      </BrowserRouter>
    );

    expect(screen.getByText(/Computing live dynamic refill calculations from database.../i)).toBeInTheDocument();
  });

  it('renders empty state when patient has no active medications', async () => {
    mockGetRefillPredictions.mockResolvedValue({
      patient_id: 2,
      generated_at: '2026-08-22T22:30:00Z',
      total_medications: 0,
      valid_predictions_count: 0,
      insufficient_data_count: 0,
      predictions: [],
    });

    render(
      <BrowserRouter>
        <RefillPredictions />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No active medication records.')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Add Medication & Schedule/i })).toBeInTheDocument();
    });
  });

  it('renders dynamic refill calculations, urgency badges, and insufficient data alerts correctly', async () => {
    mockGetRefillPredictions.mockResolvedValue({
      patient_id: 3,
      generated_at: '2026-08-22T22:30:00Z',
      total_medications: 3,
      valid_predictions_count: 2,
      insufficient_data_count: 1,
      predictions: [
        {
          medicine_id: 1,
          medicine_name: 'Metformin HCl',
          strength: 500,
          unit: 'mg',
          dosage_form: 'TABLET',
          instructions: 'Take twice daily',
          start_date: '2026-08-01',
          end_date: null,
          is_active: true,
          status: 'VALID',
          status_message: 'Refill predicted dynamically from active schedule and intake history.',
          current_stock: 60,
          daily_consumption: 2.0,
          doses_per_day: 2,
          dose_quantity_per_intake: 1.0,
          doses_taken_count: 10,
          doses_missed_count: 1,
          estimated_remaining_quantity: 50.0,
          estimated_remaining_days: 25,
          predicted_refill_date: '2026-09-16',
          urgency_level: 'GOOD',
          prescription_id: 1,
          doctor_name: 'Sarah Connor',
        },
        {
          medicine_id: 2,
          medicine_name: 'Atorvastatin',
          strength: 20,
          unit: 'mg',
          dosage_form: 'TABLET',
          instructions: 'Once daily at night',
          start_date: '2026-08-01',
          end_date: null,
          is_active: true,
          status: 'VALID',
          status_message: 'Refill predicted dynamically from active schedule and intake history.',
          current_stock: 10,
          daily_consumption: 1.0,
          doses_per_day: 1,
          dose_quantity_per_intake: 1.0,
          doses_taken_count: 8,
          doses_missed_count: 0,
          estimated_remaining_quantity: 2.0,
          estimated_remaining_days: 2,
          predicted_refill_date: '2026-08-24',
          urgency_level: 'CRITICAL',
          prescription_id: null,
          doctor_name: null,
        },
        {
          medicine_id: 3,
          medicine_name: 'Ibuprofen As Needed',
          strength: 400,
          unit: 'mg',
          dosage_form: 'TABLET',
          instructions: null,
          start_date: '2026-08-01',
          end_date: null,
          is_active: true,
          status: 'INSUFFICIENT_DATA',
          status_message: 'Refill prediction unavailable — insufficient medication data (no active schedule configured).',
          current_stock: 30,
          daily_consumption: null,
          doses_per_day: null,
          dose_quantity_per_intake: null,
          doses_taken_count: null,
          doses_missed_count: null,
          estimated_remaining_quantity: null,
          estimated_remaining_days: null,
          predicted_refill_date: null,
          urgency_level: null,
          prescription_id: null,
          doctor_name: null,
        },
      ],
    });

    render(
      <BrowserRouter>
        <RefillPredictions />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Summary cards
      expect(screen.getByText('Monitored Medicines')).toBeInTheDocument();
      expect(screen.getByText('Critical Refills (≤ 3d)')).toBeInTheDocument();

      // Medicine cards
      expect(screen.getByText('Metformin HCl')).toBeInTheDocument();
      expect(screen.getByText(/Dr. Sarah Connor/i)).toBeInTheDocument();
      expect(screen.getByText('25 Days')).toBeInTheDocument();
      expect(screen.getByText('SUFFICIENT SUPPLY')).toBeInTheDocument();

      // Critical medicine
      expect(screen.getByText('Atorvastatin')).toBeInTheDocument();
      expect(screen.getByText('2 Days')).toBeInTheDocument();
      expect(screen.getByText('CRITICAL (≤ 3 days)')).toBeInTheDocument();

      // Insufficient data medicine
      expect(screen.getByText('Ibuprofen As Needed')).toBeInTheDocument();
      expect(screen.getByText('Refill prediction unavailable — insufficient medication data.')).toBeInTheDocument();
    });

    // Test filter by Critical tab
    fireEvent.click(screen.getByRole('button', { name: 'Critical (≤ 3d)' }));
    expect(screen.getByText('Atorvastatin')).toBeInTheDocument();
    expect(screen.queryByText('Metformin HCl')).not.toBeInTheDocument();
  });
});
