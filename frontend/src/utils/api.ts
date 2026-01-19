import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/authStore';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token;

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized - token expired or invalid
    if (error.response?.status === 401) {
      const refreshToken = useAuthStore.getState().refreshToken;

      // Try to refresh token if available
      if (refreshToken && originalRequest && !originalRequest._retry) {
        originalRequest._retry = true;

        try {
          const response = await axios.post(
            `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/auth/refresh`,
            { refresh_token: refreshToken }
          );

          const { access_token, refresh_token } = response.data;

          useAuthStore.getState().setTokens({
            access_token,
            refresh_token,
            token_type: 'Bearer',
          });

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, logout user
          useAuthStore.getState().logout();
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }

      // No refresh token or retry already attempted
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }

    // Handle other errors
    const errorMessage = getErrorMessage(error);
    console.error('API Error:', errorMessage);

    return Promise.reject(error);
  }
);

// Helper to extract error message
function getErrorMessage(error: AxiosError): string {
  if (error.response?.data) {
    const data = error.response.data as Record<string, unknown>;
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.message === 'string') return data.message;
    if (typeof data.error === 'string') return data.error;
  }

  if (error.message) return error.message;

  return 'An unexpected error occurred';
}

// Typed request helpers
export const apiGet = <T>(url: string, params?: Record<string, unknown>) =>
  api.get<T>(url, { params });

export const apiPost = <T>(url: string, data?: unknown) =>
  api.post<T>(url, data);

export const apiPut = <T>(url: string, data?: unknown) =>
  api.put<T>(url, data);

export const apiPatch = <T>(url: string, data?: unknown) =>
  api.patch<T>(url, data);

export const apiDelete = <T>(url: string) => api.delete<T>(url);

// API endpoints
export const endpoints = {
  // Auth
  auth: {
    login: '/auth/login',
    callback: '/auth/callback',
    refresh: '/auth/refresh',
    logout: '/auth/logout',
    me: '/auth/me',
  },

  // Users
  users: {
    profile: '/users/profile',
    settings: '/users/settings',
    zones: '/users/zones',
  },

  // Activities
  activities: {
    list: '/activities',
    get: (id: number) => `/activities/${id}`,
    sync: '/activities/sync',
    streams: (id: number) => `/activities/${id}/streams`,
    stats: '/activities/stats',
  },

  // Training Plans
  plans: {
    list: '/plans',
    get: (id: number) => `/plans/${id}`,
    create: '/plans',
    update: (id: number) => `/plans/${id}`,
    delete: (id: number) => `/plans/${id}`,
    active: '/plans/active',
    generate: '/plans/generate',
  },

  // Workouts
  workouts: {
    list: '/workouts',
    get: (id: number) => `/workouts/${id}`,
    create: '/workouts',
    update: (id: number) => `/workouts/${id}`,
    delete: (id: number) => `/workouts/${id}`,
    upcoming: '/workouts/upcoming',
    calendar: '/workouts/calendar',
  },

  // Fitness metrics (using /metrics endpoint)
  fitness: {
    metrics: '/metrics',
    history: '/metrics',  // List metrics with date filters
    current: '/metrics/current',
    calculate: '/metrics/calculate',
    summary: '/metrics/summary',
    zones: '/metrics/zones',
  },

  // Dashboard
  dashboard: {
    stats: '/dashboard/stats',
    summary: '/dashboard/summary',
  },

  // Strava
  strava: {
    authorize: '/auth/strava/login/redirect',
    callback: '/auth/strava/callback',
    sync: '/activities/sync',
    status: '/auth/me',
  },
};

// Extend AxiosRequestConfig to include _retry
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}

export default api;
