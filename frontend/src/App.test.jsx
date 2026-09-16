import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';
import authService from './api/authService';
import medicationService from './api/medicationService';
import { doseService } from './api/doseService';
import { adminService } from './api/adminService';
import { caregiverService } from './api/caregiverService';

vi.mock('./api/medicationService', () => ({
  default: {
    listMedicines: vi.fn().mockResolvedValue([]),
    listSchedules: vi.fn().mockResolvedValue([]),
    listConditions: vi.fn().mockResolvedValue([]),
    listPrescriptions: vi.fn().mockResolvedValue([]),
  },
  medicationService: {
    listMedicines: vi.fn().mockResolvedValue([]),
    listSchedules: vi.fn().mockResolvedValue([]),
    listConditions: vi.fn().mockResolvedValue([]),
    listPrescriptions: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('./api/doseService', () => ({
  doseService: {
    getTodayDoses: vi.fn().mockResolvedValue([]),
    getAdherence: vi.fn().mockResolvedValue({
      adherence_percentage: 100,
      adherence_status: 'Good',
      taken_count: 0,
      missed_count: 0,
      skipped_count: 0,
    }),
    markDoseTaken: vi.fn(),
    markDoseSkipped: vi.fn(),
  },
}));

vi.mock('./api/adminService', () => ({
  adminService: {
    getDashboard: vi.fn().mockResolvedValue({
      total_patients: 10,
      total_caregivers: 2,
      pending_caregivers: 0,
      active_caregivers: 2,
      inactive_caregivers: 0,
      active_assignments: 5,
      total_medicines: 20,
      today_doses_total: 8,
      today_doses_taken: 8,
      today_doses_missed: 0,
    }),
    getPendingCaregivers: vi.fn().mockResolvedValue([]),
    getCaregivers: vi.fn().mockResolvedValue([]),
    getAssignments: vi.fn().mockResolvedValue([]),
    getAuditLogs: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('./api/caregiverService', () => ({
  caregiverService: {
    getDashboard: vi.fn().mockResolvedValue({
      total_assigned_patients: 1,
      today_doses_scheduled: 2,
      today_doses_taken: 2,
      today_doses_missed: 0,
      today_doses_pending: 0,
      overall_adherence_percentage: 100,
      overall_adherence_status: 'Good',
      patients: [],
    }),
    getPatients: vi.fn().mockResolvedValue([]),
    getAlerts: vi.fn().mockResolvedValue([]),
    getPatientDetail: vi.fn(),
  },
}));

vi.mock('./api/notificationService', () => ({
  default: {
    getNotifications: vi.fn().mockResolvedValue([]),
    getUnreadCount: vi.fn().mockResolvedValue({ unread_count: 0 }),
    markAsRead: vi.fn().mockResolvedValue({}),
    markAllAsRead: vi.fn().mockResolvedValue({}),
  },
  notificationService: {
    getNotifications: vi.fn().mockResolvedValue([]),
    getUnreadCount: vi.fn().mockResolvedValue({ unread_count: 0 }),
    markAsRead: vi.fn().mockResolvedValue({}),
    markAllAsRead: vi.fn().mockResolvedValue({}),
  },
}));

describe('PillSync Application Routing and Role-Based Dashboards', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    window.history.pushState({}, 'Home', '/');
  });

  it('redirects unauthenticated users to the Login page when no token is present', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Welcome Back to PillSync|Sign in/i })).toBeInTheDocument();
      expect(screen.getByLabelText('Email Address')).toBeInTheDocument();
      expect(screen.getByLabelText('Password')).toBeInTheDocument();
    });
  });

  it('renders Patient Dashboard when user has PATIENT role', async () => {
    localStorage.setItem('pillsync_auth_token', 'valid_jwt_token');
    vi.spyOn(authService, 'getMe').mockResolvedValue({
      id: 10,
      name: 'Naveen Kumar',
      email: 'naveen@example.com',
      role: 'PATIENT',
      is_active: true,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Welcome, Naveen Kumar/i })).toBeInTheDocument();
      expect(screen.getAllByText(/Patient Portal/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Today's Scheduled Medication Doses/i)).toBeInTheDocument();
      expect(screen.getByText('View Medication History')).toBeInTheDocument();
      expect(screen.getByText('View Refill Predictions')).toBeInTheDocument();
      expect(screen.queryByText('View Adherence Reports')).not.toBeInTheDocument();
    });
  });

  it('renders Caregiver Dashboard when user has CAREGIVER role', async () => {
    localStorage.setItem('pillsync_auth_token', 'valid_jwt_token');
    vi.spyOn(authService, 'getMe').mockResolvedValue({
      id: 11,
      name: 'Caregiver Clara',
      email: 'clara.caregiver@example.com',
      role: 'CAREGIVER',
      is_active: true,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Caregiver Supervision Portal')).toBeInTheDocument();
      expect(screen.getByText('My Supervised Patients')).toBeInTheDocument();
      expect(screen.getByText('View Adherence Reports')).toBeInTheDocument();
      expect(screen.queryByText('View Medication History')).not.toBeInTheDocument();
      expect(screen.queryByText('View Refill Predictions')).not.toBeInTheDocument();
    });
  });

  it('renders Admin Dashboard when user has ADMIN role', async () => {
    localStorage.setItem('pillsync_auth_token', 'valid_jwt_token');
    vi.spyOn(authService, 'getMe').mockResolvedValue({
      id: 12,
      name: 'Admin Arthur',
      email: 'arthur.admin@example.com',
      role: 'ADMIN',
      is_active: true,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('System Administration')).toBeInTheDocument();
      expect(screen.getByText('Pending Approvals')).toBeInTheDocument();
      expect(screen.queryByText('Pending Caregiver Registrations')).not.toBeInTheDocument();
      expect(screen.queryByText('View Medication History')).not.toBeInTheDocument();
      expect(screen.queryByText('View Refill Predictions')).not.toBeInTheDocument();
      expect(screen.queryByText('View Adherence Reports')).not.toBeInTheDocument();
    });
  });
});


