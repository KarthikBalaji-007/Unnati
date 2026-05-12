/**
 * api.js
 * Axios service layer – all calls to the FastAPI backend.
 * Base URL is proxied via Vite's dev proxy to http://localhost:8000.
 */

import axios from 'axios';
import { getAuthToken } from './auth';

const api = axios.create({
  timeout: 300000,   // 5 min – first run downloads model + heavy video processing
  headers: { 'Accept': 'application/json' },
});

// ─── Interceptors ─────────────────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      'Unknown error';
    const wrapped = new Error(message);
    wrapped.status = err.response?.status;
    wrapped.data = err.response?.data;
    return Promise.reject(wrapped);
  }
);

// ─── Health ───────────────────────────────────────────────────────────────────
export const checkHealth = () => api.get('/api/health');

// ─── Upload ───────────────────────────────────────────────────────────────────
/**
 * Upload a video file. Returns { file_id, filename, size_bytes, message }.
 * @param {File} file
 * @param {(progress: number) => void} onProgress
 */
export const uploadVideo = (file, onProgress) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/api/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });
};

// ─── Process ──────────────────────────────────────────────────────────────────
/**
 * Trigger AI analysis on an uploaded video.
 * @param {string} fileId
 * @param {string} testType  'T3' | 'T4' | 'T5' | 'T8' | 'T9'
 * @param {object|null} athleteInfo  { name, age, gender, location? }
 */
export const processVideo = (fileId, testType, athleteInfo = null) =>
  api.post('/api/process', {
    file_id: fileId,
    test_type: testType,
    athlete_info: athleteInfo,
  });

// ─── Results ──────────────────────────────────────────────────────────────────
/** List all sessions, newest first. */
export const getSessions = (limit = 50) => api.get('/api/sessions', { params: { limit } });

/** Get full result detail for a specific session. */
export const getResult = (sessionId) => api.get(`/api/results/${sessionId}`);

/** Delete a session. */
export const deleteSession = (sessionId) => api.delete(`/api/sessions/${sessionId}`);

// ─── Auth ──────────────────────────────────────────────────────────────────────
export const registerUser = (payload) => api.post('/api/auth/register', payload);
export const loginUser = (payload) => api.post('/api/auth/login', payload);
export const getCurrentUser = () => api.get('/api/auth/me');
export const logoutUser = () => api.post('/api/auth/logout');
export const requestPasswordReset = (payload) => api.post('/api/auth/forgot-password/request', payload);
export const confirmPasswordReset = (payload) => api.post('/api/auth/forgot-password/confirm', payload);
export const getAuthSessions = () => api.get('/api/auth/sessions');
export const revokeAuthSession = (sessionId) => api.delete(`/api/auth/sessions/${sessionId}`);
export const revokeAllAuthSessions = (keepCurrent = true) =>
  api.post(`/api/auth/sessions/revoke-all?keep_current=${keepCurrent}`);

// ─── Athlete linking ───────────────────────────────────────────────────────────
export const getMyAthlete = () => api.get('/api/my-athlete');
export const linkAthlete = (athleteId) => api.post(`/api/athletes/link/${athleteId}`);

// ─── Coach dashboard ───────────────────────────────────────────────────────────
export const getCoachOverview = () => api.get('/api/coach/overview');
export const getCoachRecentSessions = (limit = 20) => api.get('/api/coach/recent-sessions', { params: { limit } });

export default api;
