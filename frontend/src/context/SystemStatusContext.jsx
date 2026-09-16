import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { fetchHealthStatus } from '../api/healthService';

const SystemStatusContext = createContext(null);

export const SystemStatusProvider = ({ children }) => {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);

  const checkHealth = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchHealthStatus();
      setHealthData(data);
      setError(null);
    } catch (err) {
      setHealthData(null);
      if (err.response) {
        setError(`Backend responded with error: ${err.response.status} ${err.response.statusText}`);
      } else if (err.request) {
        setError('Cannot reach backend API. Connection refused or server offline.');
      } else {
        setError(err.message || 'Unknown network error occurred.');
      }
    } finally {
      setLoading(false);
      setLastChecked(new Date());
    }
  }, []);

  // Periodic health polling (every 30 seconds)
  useEffect(() => {
    checkHealth();
    const interval = setInterval(() => {
      checkHealth();
    }, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return (
    <SystemStatusContext.Provider
      value={{
        healthData,
        loading,
        error,
        lastChecked,
        refresh: checkHealth,
      }}
    >
      {children}
    </SystemStatusContext.Provider>
  );
};

export const useSystemStatus = () => {
  const context = useContext(SystemStatusContext);
  if (!context) {
    throw new Error('useSystemStatus must be used within a SystemStatusProvider');
  }
  return context;
};
