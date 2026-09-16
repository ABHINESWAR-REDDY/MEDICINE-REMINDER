import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import SystemOperations from './SystemOperations';
import { adminService } from '../../api/adminService';

vi.mock('../../api/adminService', () => ({
  adminService: {
    getSystemHealth: vi.fn(),
    reconcileDoses: vi.fn(),
    reconcileNotifications: vi.fn(),
    runConsistencyCheck: vi.fn(),
  },
}));

describe('SystemOperations Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders system health diagnostics for all subsystems', async () => {
    vi.mocked(adminService.getSystemHealth).mockResolvedValue({
      status: 'HEALTHY',
      timestamp: '2026-08-24T12:00:00Z',
      components: {
        database: { status: 'HEALTHY', latency_ms: 1.2, message: 'Database connection active.' },
        backend_api: { status: 'HEALTHY', latency_ms: 0.8, message: 'API running normally.' },
        notifications: { status: 'HEALTHY', message: 'Notification queue online.', details: { unread_count: 5 } },
        chat: { status: 'HEALTHY', message: 'Chat engine online.' },
        authentication: { status: 'HEALTHY', message: 'JWT authentication active.' },
      },
    });

    render(<SystemOperations />);

    await waitFor(() => {
      expect(screen.getByText('System Operations')).toBeInTheDocument();
      expect(screen.getByText('Database Engine')).toBeInTheDocument();
      expect(screen.getByText('Backend REST API')).toBeInTheDocument();
      expect(screen.getByText('Notification Engine')).toBeInTheDocument();
      expect(screen.getByText('Direct Messaging')).toBeInTheDocument();
      expect(screen.getByText('Authentication & RBAC Security')).toBeInTheDocument();
    });
  });

  it('executes dose reconciliation operation safely and renders feedback message', async () => {
    vi.mocked(adminService.getSystemHealth).mockResolvedValue({
      status: 'HEALTHY',
      components: {
        database: { status: 'HEALTHY', latency_ms: 1.0 },
      },
    });

    vi.mocked(adminService.reconcileDoses).mockResolvedValue({
      success: true,
      message: 'Dose reconciliation completed successfully. 3 overdue doses transitioned to MISSED.',
      details: { reconciled_count: 3 },
    });

    render(<SystemOperations />);

    await waitFor(() => {
      expect(screen.getByText('System Operations')).toBeInTheDocument();
    });

    const reconcileBtn = screen.getByRole('button', { name: /Run Dose Reconciliation/i });
    fireEvent.click(reconcileBtn);

    await waitFor(() => {
      expect(adminService.reconcileDoses).toHaveBeenCalled();
      expect(screen.getByText(/Dose reconciliation completed successfully/i)).toBeInTheDocument();
    });
  });

  it('displays user-friendly error state with retry on failure', async () => {
    vi.mocked(adminService.getSystemHealth).mockRejectedValue(new Error('Diagnostic Check Failed'));

    render(<SystemOperations />);

    await waitFor(() => {
      expect(screen.getByText('Diagnostic Check Failed')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Retry Check' })).toBeInTheDocument();
    });
  });
});
