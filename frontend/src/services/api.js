import axios from 'axios';

const _rawApiUrl = process.env.REACT_APP_API_URL;
if (!_rawApiUrl) {
  console.warn("REACT_APP_API_URL environment variable is missing!");
}
const API_BASE_URL = (_rawApiUrl || 'http://localhost:8000').replace(/\/+$/, '');

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
 *
 * Uses a raw axios call (NOT the shared `api` instance) to guarantee that:
 * 1. The global Content-Type: application/json default never overrides the
 *    form-encoded body required by OAuth2PasswordRequestForm.
 * 2. The Authorization interceptor never attaches a stale Bearer token to
 *    the login request itself.
 */
export const loginUser = async (email, password) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  // Log the exact URL in DevTools so we can confirm the endpoint during debugging
  const loginUrl = `${API_BASE_URL}/api/v1/auth/login`;
  console.log('[AUTH] loginUser -> POST', loginUrl);

  const response = await axios.post(loginUrl, formData.toString(), {
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

/**
 * Trigger the demo data seeder (DEMO_MODE only, Admin role required).
 * @param {boolean} force - If true, re-seeds even if sessions exist.
 */
export const seedDemoData = async (force = false) => {
  const response = await api.post(`/demo/seed${force ? '?force=true' : ''}`);
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// WebSocket Singleton — exponential-backoff reconnect
// ─────────────────────────────────────────────────────────────────────────────

const listeners = new Set();

// Internal state — never exported
let _socket = null;            // the live WebSocket instance
let _reconnectTimer = null;    // pending setTimeout handle (prevents duplicate timers)
let _pingInterval = null;      // keepalive ping interval handle
let _retryDelay = 1000;        // current backoff delay in ms
let _intentionalClose = false; // true when the app deliberately closes the socket

const _BACKOFF_STEPS = [1000, 2000, 4000, 8000, 15000]; // ms

/** Advance backoff delay to the next step, capped at 15 s. */
function _nextBackoff() {
  const idx = _BACKOFF_STEPS.indexOf(_retryDelay);
  _retryDelay = (idx >= 0 && idx < _BACKOFF_STEPS.length - 1)
    ? _BACKOFF_STEPS[idx + 1]
    : 15000;
}

/** Reset backoff to 1 s after a successful connection. */
function _resetBackoff() {
  _retryDelay = 1000;
}

/** Cancel any pending reconnect timer. */
function _clearReconnectTimer() {
  if (_reconnectTimer !== null) {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = null;
  }
}

/** Stop the keepalive ping interval and clear its reference. */
function _clearPing() {
  if (_pingInterval !== null) {
    clearInterval(_pingInterval);
    _pingInterval = null;
  }
}

/**
 * Open a new WebSocket and wire up all event handlers.
 * Guards against opening a duplicate socket if one is already live.
 */
function _connectSocket() {
  // Prevent a second socket from being created while one is open/connecting.
  if (
    _socket &&
    (_socket.readyState === WebSocket.OPEN || _socket.readyState === WebSocket.CONNECTING)
  ) {
    console.log('[WS] Socket already open or connecting — skipping duplicate connect.');
    return;
  }

  const token = localStorage.getItem('access_token');
  if (!token) {
    console.warn('[WS] No access token — connection deferred until subscriber logs in.');
    return;
  }

  const wsBase = API_BASE_URL.replace(/^http/, 'ws');
  const wsUrl = `${wsBase}/api/v1/ws?token=${encodeURIComponent(token)}`;
  console.log(`[WS] Connecting to ${wsBase}/api/v1/ws...`);

  _socket = new WebSocket(wsUrl);

  // ── onopen ──────────────────────────────────────────────────────────────
  _socket.onopen = () => {
    console.log('[WS] ✅ Connected — live SOC feed online.');
    _resetBackoff();
    _clearReconnectTimer(); // cancel any timer that fired just before connect succeeded

    // Keepalive pings every 30 s. Always clear first to avoid duplicates.
    _clearPing();
    _pingInterval = setInterval(() => {
      if (_socket && _socket.readyState === WebSocket.OPEN) {
        _socket.send('ping');
      } else {
        _clearPing();
      }
    }, 30000);
  };

  // ── onmessage ───────────────────────────────────────────────────────────
  _socket.onmessage = (event) => {
    if (event.data === 'pong') return;
    try {
      const message = JSON.parse(event.data);
      listeners.forEach((cb) => {
        try {
          cb(message);
        } catch (listenerErr) {
          console.error('[WS] Listener callback error:', listenerErr);
        }
      });
    } catch (_parseErr) {
      // Suppress non-JSON frames (keepalive text etc.)
    }
  };

  // ── onerror ─────────────────────────────────────────────────────────────
  _socket.onerror = () => {
    // onerror always fires just before onclose — logging only.
    // Reconnect logic lives entirely in onclose to avoid double-scheduling.
    console.warn('[WS] ⚠️  Connection error — will attempt reconnect after close.');
  };

  // ── onclose ─────────────────────────────────────────────────────────────
  _socket.onclose = (event) => {
    _clearPing();
    _socket = null;

    // Intentional close (logout / all listeners removed) — do not reconnect.
    if (_intentionalClose) {
      console.log(`[WS] 🔴 Closed intentionally (code ${event.code}). Reconnect suppressed.`);
      _intentionalClose = false;
      return;
    }

    // Do not schedule a second timer if one is already pending.
    if (_reconnectTimer !== null) {
      console.log('[WS] Reconnect timer already pending — skipping duplicate schedule.');
      return;
    }

    const hasListeners = listeners.size > 0;
    const hasToken = !!localStorage.getItem('access_token');

    if (!hasListeners || !hasToken) {
      console.log(`[WS] Closed (code ${event.code}). No active listeners or token — not reconnecting.`);
      return;
    }

    const delayToUse = _retryDelay;
    console.log(`[WS] 🔌 Disconnected (code ${event.code}). Reconnecting in ${delayToUse / 1000}s...`);
    _nextBackoff(); // Advance delay NOW so the next failure waits longer

    _reconnectTimer = setTimeout(() => {
      _reconnectTimer = null;

      if (listeners.size > 0 && localStorage.getItem('access_token')) {
        console.log('[WS] 🔄 Reconnecting...');
        _connectSocket();
      } else {
        console.log('[WS] Reconnect aborted — session ended or no subscribers remain.');
        _resetBackoff();
      }
    }, delayToUse);
  };
}

/**
 * Subscribe a callback to real-time WebSocket events.
 *
 * - Safe to call multiple times with the same callback (idempotent via Set).
 * - Automatically opens or reuses a WebSocket connection.
 * - Reconnects with exponential backoff [1s → 2s → 4s → 8s → 15s] after any
 *   involuntary disconnect (backend restart, network interruption, etc.).
 * - Stops reconnecting when the last subscriber unsubscribes or the user
 *   logs out.
 *
 * @param   {function} callback  Called with each parsed JSON message object.
 * @returns {function}           Unsubscribe function — call it on component unmount.
 */
export const subscribeToEvents = (callback) => {
  listeners.add(callback);

  // Open a connection if none exists or if the existing one has already closed.
  if (!_socket || (_socket.readyState !== WebSocket.OPEN && _socket.readyState !== WebSocket.CONNECTING)) {
    _intentionalClose = false;
    _clearReconnectTimer(); // cancel any stale timer before a manual reconnect
    _connectSocket();
  }

  // Return the unsubscribe function for this specific callback.
  return () => {
    listeners.delete(callback);

    // Only close the socket when the LAST listener unsubscribes AND there is no
    // pending timer that would reopen it.  Pending timers fire into _connectSocket
    // which will no-op if listeners.size === 0 at that point.
    if (listeners.size === 0 && _reconnectTimer === null) {
      _intentionalClose = true;
      _clearPing();
      if (_socket) {
        _socket.close(1000, 'All listeners unsubscribed.');
        _socket = null;
      }
      _resetBackoff();
      console.log('[WS] 🔴 All listeners removed — connection closed cleanly.');
    }
  };
};

export default api;
