import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import ForgotPassword from './components/auth/ForgotPassword';
import Layout from './components/layout/Layout';
import Dashboard from './components/dashboard/Dashboard';
import Profile from './components/profile/Profile';
import Medicines from './components/medicines/Medicines';
import Conditions from './components/conditions/Conditions';
import Prescriptions from './components/prescriptions/Prescriptions';
import Schedule from './components/schedule/Schedule';
import PrescriptionScan from './components/ocr/PrescriptionScan';
import PatientAlerts from './components/notifications/PatientAlerts';
import MedicationHistory from './components/medications/MedicationHistory';
import RefillPredictions from './components/medications/RefillPredictions';
import AIAssistantPage from './components/ai/AIAssistantPage';


// Admin Components
import AdminDashboard from './components/admin/AdminDashboard';
import CaregiverManagement from './components/admin/CaregiverManagement';
import PatientManagement from './components/admin/PatientManagement';
import PatientAssignments from './components/admin/PatientAssignments';
import AuditLogs from './components/admin/AuditLogs';
import PlatformActivities from './components/admin/PlatformActivities';
import NotificationSettings from './components/admin/NotificationSettings';
import PlatformAnalytics from './components/admin/PlatformAnalytics';
import SystemOperations from './components/admin/SystemOperations';

// Caregiver Components
import CaregiverDashboard from './components/caregivers/CaregiverDashboard';
import CaregiverPatients from './components/caregivers/CaregiverPatients';
import CaregiverPatientDetail from './components/caregivers/CaregiverPatientDetail';
import CaregiverAlerts from './components/caregivers/CaregiverAlerts';
import CaregiverAdherenceReports from './components/caregivers/CaregiverAdherenceReports';


function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />

            {/* Shared / Dynamic Dashboard Route */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Dashboard />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* AI Healthcare Assistant Studio Route */}
            <Route
              path="/ai-assistant"
              element={
                <ProtectedRoute>
                  <Layout>
                    <AIAssistantPage />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Patient Specific Routes */}
            <Route
              path="/medications"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <Medicines />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/patient/medication-history"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <MedicationHistory />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/medications/history"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <MedicationHistory />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/patient/refill-predictions"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <RefillPredictions />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/medications/refills"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <RefillPredictions />
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/conditions"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <Conditions />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/prescriptions"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <Prescriptions />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/ocr"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <PrescriptionScan />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/schedule"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <Schedule />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/patient/alerts"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <PatientAlerts />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/alerts"
              element={
                <ProtectedRoute allowedRoles={['PATIENT']}>
                  <Layout>
                    <PatientAlerts />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Caregiver Routes */}
            <Route
              path="/caregiver/dashboard"
              element={
                <ProtectedRoute allowedRoles={['CAREGIVER']}>
                  <Layout>
                    <CaregiverDashboard />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/caregiver/patients"
              element={
                <ProtectedRoute allowedRoles={['CAREGIVER']}>
                  <Layout>
                    <CaregiverPatients />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/caregiver/patients/:patientId"
              element={
                <ProtectedRoute allowedRoles={['CAREGIVER']}>
                  <Layout>
                    <CaregiverPatientDetail />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/caregiver/alerts"
              element={
                <ProtectedRoute allowedRoles={['CAREGIVER']}>
                  <Layout>
                    <CaregiverAlerts />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/caregiver/adherence-reports"
              element={
                <ProtectedRoute allowedRoles={['CAREGIVER']}>
                  <Layout>
                    <CaregiverAdherenceReports />
                  </Layout>
                </ProtectedRoute>
              }
            />


            {/* Admin Routes */}
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Layout>
                    <AdminDashboard />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/caregivers"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Layout>
                    <CaregiverManagement />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/patients"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Layout>
                    <PatientManagement />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/assignments"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Layout>
                    <PatientAssignments />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/audit-logs"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Layout>
                    <AuditLogs />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/activities"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Layout>
                    <PlatformActivities />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/notification-settings"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Layout>
                    <NotificationSettings />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/analytics"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Layout>
                    <PlatformAnalytics />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/system"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Layout>
                    <SystemOperations />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Shared Profile & Settings Route */}
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Profile />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Profile />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
