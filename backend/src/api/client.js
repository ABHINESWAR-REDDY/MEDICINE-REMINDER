import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL !== undefined 
  ? import.meta.env.VITE_API_BASE_URL 
  : '';

export const TOKEN_STORAGE_KEY = 'pillsync_auth_token';

const apiClient = axios.create({
  baseURL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});


// Attach Authorization Bearer token and handle multipart FormData properly
apiClient.interceptors.request.use(
  (config) => {
    try {
      const token = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (token && typeof token === 'string' && token.trim().length > 0) {
        const trimmedToken = token.trim();
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${trimmedToken}`;
        config.headers['Authorization'] = `Bearer ${trimmedToken}`;
        if (typeof config.headers.set === 'function') {
          config.headers.set('Authorization', `Bearer ${trimmedToken}`);
        }
      }
    } catch {
      // In non-browser or storage restricted environments, ignore
    }

    // When uploading FormData (multipart files), delete Content-Type to let browser set boundary
    if (config.data instanceof FormData && config.headers) {
      if (typeof config.headers.delete === 'function') {
        config.headers.delete('Content-Type');
      } else {
        delete config.headers['Content-Type'];
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 unauthorized errors by cleaning expired tokens and redirecting to login
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const isAuthEndpoint = error.config?.url?.includes('/api/v1/auth/login');
      if (!isAuthEndpoint) {
        try {
          localStorage.removeItem(TOKEN_STORAGE_KEY);
        } catch {
          // ignore
        }
        if (
          typeof window !== 'undefined' &&
          window.location &&
          window.location.pathname !== '/login' &&
          !(typeof process !== 'undefined' && process.env && process.env.NODE_ENV === 'test')
        ) {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

