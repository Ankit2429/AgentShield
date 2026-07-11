import axios from 'axios';

// Connect to the FastAPI backend. In development, this defaults to localhost:8000.
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Check backend health and readiness.
 */
export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

/**
 * Fetch live operational dashboard metrics and recent decisions.
 */
export const getDashboard = async () => {
  const response = await api.get('/dashboard');
  return response.data;
};

/**
 * Fetch all tracked agent profiles with optional filtering.
 */
export const getAgents = async (params = {}) => {
  const response = await api.get('/agents', { params });
  return response.data;
};

/**
 * Fetch a list of replay sessions with optional filtering.
 */
export const getReplays = async (params = {}) => {
  const response = await api.get('/replay', { params });
  return response.data;
};

/**
 * Fetch the full ordered replay timeline for a specific session.
 */
export const getReplaySession = async (sessionId) => {
  const response = await api.get(`/replay/${sessionId}`);
  return response.data;
};

/**
 * Submit a simulated AI message to be analyzed by the security engines.
 */
export const analyzeMessage = async (payload) => {
  const response = await api.post('/analyze', payload);
  return response.data;
};

export default api;
