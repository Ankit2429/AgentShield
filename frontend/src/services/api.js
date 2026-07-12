import axios from 'axios';

const _rawApiUrl = process.env.REACT_APP_API_URL || 'https://agentshield-backend-yl6q.onrender.com';
const API_BASE_URL = _rawApiUrl.replace(/\/+$/, '');

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: attach access token to outgoing calls
api.interceptors.request.use(
  (config) => {
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
      config.headers['Authorization'] = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: handle expired access tokens via refresh rotation
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Suppress validation triggers or non-401 authentication errors
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url.includes('/auth/login')) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        isRefreshing = false;
        // Broadcast custom event to logout the UI
        window.dispatchEvent(new Event('auth_required'));
        return Promise.reject(error);
      }

      try {
        // Run refresh token rotation
        const res = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token } = res.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);

        api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        originalRequest.headers['Authorization'] = `Bearer ${access_token}`;

        processQueue(null, access_token);
        isRefreshing = false;

        return api(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        isRefreshing = false;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.dispatchEvent(new Event('auth_required'));
        return Promise.reject(refreshErr);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Log in to the backend platform.
 */
export const loginUser = async (email, password) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  
  const response = await api.post('/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
  const { access_token, refresh_token } = response.data;
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('refresh_token', refresh_token);
  return response.data;
};

/**
 * Log out and revoke active tokens.
 */
export const logoutUser = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  try {
    if (refreshToken) {
      await api.post('/auth/logout', { refresh_token: refreshToken });
    }
  } catch (err) {
    console.warn('[API] Token revocation warning on logout:', err);
  } finally {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.dispatchEvent(new Event('auth_required'));
  }
};

/**
 * Fetch authenticated caller context metadata.
 */
export const getCurrentUser = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

/**
 * Check backend health.
 */
export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

/**
 * Fetch dashboard stats.
 */
export const getDashboard = async () => {
  const response = await api.get('/dashboard');
  return response.data;
};

/**
 * Fetch list of agents.
 */
export const getAgents = async (params = {}) => {
  const response = await api.get('/agents', { params });
  return response.data;
};

/**
 * Fetch list of replays.
 */
export const getReplays = async (params = {}) => {
  const response = await api.get('/replay', { params });
  return response.data;
};

/**
 * Fetch a single replay session.
 */
export const getReplaySession = async (sessionId) => {
  const response = await api.get(`/replay/${sessionId}`);
  return response.data;
};

/**
 * Run a simulation query.
 */
export const analyzeMessage = async (payload) => {
  const response = await api.post('/analyze', payload);
  return response.data;
};

// Singleton WebSocket client manager
let socket = null;
const listeners = new Set();

export const subscribeToEvents = (callback) => {
  listeners.add(callback);

  if (!socket) {
    const token = localStorage.getItem('access_token');
    // Enforce authenticated query parameter
    const wsUrl = `${API_BASE_URL.replace(/^http/, 'ws')}/api/v1/ws?token=${encodeURIComponent(token || '')}`;
    console.log('[WS] Establishing authenticated link to:', wsUrl);

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('[WS] Live SOC link online.');
      const pingInterval = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send('ping');
        } else {
          clearInterval(pingInterval);
        }
      }, 30000);
    };

    socket.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const message = JSON.parse(event.data);
        listeners.forEach((cb) => {
          try {
            cb(message);
          } catch (e) {
            console.error('[WS] Listener error:', e);
          }
        });
      } catch (err) {
        // Suppress ping pong text message logs
      }
    };

    socket.onclose = (event) => {
      console.log(`[WS] Connection closed (code: ${event.code}). Attempting reconnect in 3s...`);
      socket = null;
      setTimeout(() => {
        if (listeners.size > 0 && localStorage.getItem('access_token')) {
          const dummy = () => {};
          subscribeToEvents(dummy);
          listeners.delete(dummy);
        }
      }, 3000);
    };

    socket.onerror = (err) => {
      console.error('[WS] Connection error:', err);
    };
  }

  return () => {
    listeners.delete(callback);
    if (listeners.size === 0 && socket) {
      socket.close();
      socket = null;
    }
  };
};

export default api;
