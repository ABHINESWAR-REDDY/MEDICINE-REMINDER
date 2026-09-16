import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Conditions from './Conditions';
import medicationService from '../../api/medicationService';

vi.mock('../../api/medicationService', () => ({
  default: {
    listConditions: vi.fn(),
    createCondition: vi.fn(),
    updateCondition: vi.fn(),
    deleteCondition: vi.fn(),
  },
  medicationService: {
    listConditions: vi.fn(),
    createCondition: vi.fn(),
    updateCondition: vi.fn(),
    deleteCondition: vi.fn(),
  },
}));

describe('Conditions Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no conditions are returned from database', async () => {
    medicationService.listConditions.mockResolvedValueOnce([]);

    render(<Conditions />);

    await waitFor(() => {
      expect(screen.getByText(/No conditions added yet/i)).toBeInTheDocument();
    });
  });

  it('renders loaded conditions from database and allows creation', async () => {
    medicationService.listConditions
      .mockResolvedValueOnce([
        { id: 1, name: 'Hypertension', description: 'High BP', created_at: '2026-08-17T12:00:00Z' },
      ])
      .mockResolvedValueOnce([
        { id: 1, name: 'Hypertension', description: 'High BP', created_at: '2026-08-17T12:00:00Z' },
        { id: 2, name: 'Diabetes Type 2', description: 'Metabolic', created_at: '2026-08-17T12:05:00Z' },
      ]);
    medicationService.createCondition.mockResolvedValueOnce({
      id: 2,
      name: 'Diabetes Type 2',
      description: 'Metabolic',
    });

    render(<Conditions />);

    await waitFor(() => {
      expect(screen.getByText('Hypertension')).toBeInTheDocument();
    });

    // Open modal
    fireEvent.click(screen.getByRole('button', { name: /Add Condition/i }));
    expect(screen.getByLabelText(/Condition \/ Disease Name/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Condition \/ Disease Name/i), {
      target: { value: 'Diabetes Type 2' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Save Condition/i }));

    await waitFor(() => {
      expect(medicationService.createCondition).toHaveBeenCalledWith({
        name: 'Diabetes Type 2',
        description: null,
      });
      expect(screen.getByText(/Condition added successfully!/i)).toBeInTheDocument();
    });
  });
});
