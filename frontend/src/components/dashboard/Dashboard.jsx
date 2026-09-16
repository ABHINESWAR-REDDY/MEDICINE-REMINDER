import React from 'react';
import { useAuth } from '../../context/AuthContext';
import PatientDashboard from './PatientDashboard';
import CaregiverDashboard from '../caregivers/CaregiverDashboard';
import AdminDashboard from '../admin/AdminDashboard';

export const Dashboard = () => {
  const { user } = useAuth();
  const role = user?.role?.toUpperCase();

  switch (role) {
    case 'ADMIN':
      return <AdminDashboard user={user} />;
    case 'CAREGIVER':
      return <CaregiverDashboard user={user} />;
    case 'PATIENT':
    default:
      return <PatientDashboard user={user} />;
  }
};

export default Dashboard;
