import React, { useState, useEffect } from 'react';
import { getHealth, loginUser, logoutUser, getCurrentUser } from './services/api';
import DashboardView from './components/DashboardView';
import ReplayView from './components/ReplayView';
import AgentsView from './components/AgentsView';
import ThreatsView from './components/ThreatsView';
import SettingsView from './components/SettingsView';
import SandboxView from './components/SandboxView';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [healthStatus, setHealthStatus] = useState({ status: 'connecting', version: 'unknown', uptime_seconds: 0 });
  const [selectedSessionId, setSelectedSessionId] = useState(null);

  // Login form state
  const [emailInput, setEmailInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [loginError, setLoginError] = useState(null);
  const [loginLoading, setLoginLoading] = useState(false);

  // Poll system health
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await getHealth();
        setHealthStatus(data);
      } catch (err) {
        setHealthStatus({ status: 'offline', version: 'unknown', uptime_seconds: 0 });
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // Bootstrap user session and monitor credentials revocation events
  useEffect(() => {
    const handleAuthRequired = () => {
      setCurrentUser(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    };

    window.addEventListener('auth_required', handleAuthRequired);

    const bootstrapSession = async () => {
      const accessToken = localStorage.getItem('access_token');
      if (accessToken) {
        try {
          const user = await getCurrentUser();
          setCurrentUser(user);
        } catch (err) {
          console.warn('[AUTH] Session validation failed on startup. Clearing stale tokens.');
          handleAuthRequired();
        }
      }
      setAuthLoading(false);
    };

    bootstrapSession();

    return () => {
      window.removeEventListener('auth_required', handleAuthRequired);
    };
  }, []);

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError(null);
    setLoginLoading(true);
    try {
      await loginUser(emailInput, passwordInput);
      const user = await getCurrentUser();
      setCurrentUser(user);
      setEmailInput('');
      setPasswordInput('');
    } catch (err) {
      console.error('[AUTH] Login failed:', err);
      let errorMessage = 'Authentication failed. Please verify credentials.';
      const detail = err.response?.data?.detail;
      if (detail) {
        if (Array.isArray(detail)) {
          errorMessage = detail.map(d => d.msg || JSON.stringify(d)).join(', ');
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        } else {
          errorMessage = JSON.stringify(detail);
        }
      }
      setLoginError(errorMessage);
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setActiveTab('dashboard');
  };

  const navigateToSession = (sessionId) => {
    setSelectedSessionId(sessionId);
    setActiveTab('replay');
  };

  const getTabLabel = (id) => {
    switch (id) {
      case 'dashboard': return 'Command Overview';
      case 'threats': return 'Threat Investigation';
      case 'replay': return 'Incident Replay';
      case 'agents': return 'Fleet Status';
      case 'sandbox': return 'Sandbox Simulator';
      case 'settings': return 'System Configuration';
      default: return '';
    }
  };

  // Role-Based Navigation Configuration
  const allTabs = [
    { id: 'dashboard', label: 'Command Overview', minRole: 'Viewer', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z" />
      </svg>
    )},
    { id: 'threats', label: 'Threat Investigation', minRole: 'Viewer', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    )},
    { id: 'replay', label: 'Incident Replay', minRole: 'Security Analyst', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )},
    { id: 'agents', label: 'Fleet Status', minRole: 'Viewer', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    )},
    { id: 'sandbox', label: 'Sandbox Simulator', minRole: 'Security Analyst', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
      </svg>
    )},
    { id: 'settings', label: 'Settings', minRole: 'Admin', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    )}
  ];

  const visibleTabs = allTabs.filter(tab => {
    if (!currentUser) return false;
    const roles = ['Viewer', 'Security Analyst', 'Admin'];
    const userRoleIdx = roles.indexOf(currentUser.role);
    const minRoleIdx = roles.indexOf(tab.minRole);
    return userRoleIdx >= minRoleIdx;
  });

  // Render a clean bootstrap spinner during active validation checks
  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col items-center justify-center font-sans antialiased">
        <div className="w-6 h-6 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin mb-4"></div>
        <p className="text-[10px] font-mono tracking-widest text-zinc-500 uppercase">Validating Security Session...</p>
      </div>
    );
  }

  // Render Auth Login overlay if session context is missing
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100 flex items-center justify-center font-sans antialiased selection:bg-indigo-500/30 selection:text-white p-4">
        <div className="w-full max-w-md bg-[#0c0c0e] rounded border border-zinc-900 p-8 shadow-2xl space-y-6">
          <div className="text-center space-y-2">
            <div className="inline-block w-10 h-10 rounded bg-zinc-800 flex items-center justify-center font-bold text-base text-zinc-100 border border-zinc-700 shadow-inner mb-2">
              S
            </div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">AgentShield X</h1>
            <p className="text-[10px] font-mono tracking-widest text-zinc-500 uppercase">Enterprise Security Operations Hub</p>
          </div>

          <form onSubmit={handleLoginSubmit} className="space-y-4">
            {loginError && (
              <div className="p-3 rounded text-[11px] font-mono border border-rose-500/20 bg-rose-500/10 text-rose-400">
                {loginError}
              </div>
            )}

            <div className="space-y-1">
              <label className="text-[10px] font-mono tracking-wider text-zinc-500 uppercase block">Email Address</label>
              <input
                type="email"
                required
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                placeholder="analyst@agentshield.com"
                className="w-full px-3 py-2 bg-zinc-900/60 border border-zinc-800/80 rounded text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-zinc-700 font-mono transition duration-150"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-mono tracking-wider text-zinc-500 uppercase block">Security Password</label>
              <input
                type="password"
                required
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3 py-2 bg-zinc-900/60 border border-zinc-800/80 rounded text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-zinc-700 font-mono transition duration-150"
              />
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full py-2.5 bg-zinc-100 hover:bg-zinc-200 disabled:opacity-50 text-zinc-950 text-xs font-bold rounded shadow transition duration-150 flex justify-center items-center mt-6"
            >
              <span>{loginLoading ? 'Authenticating credentials...' : 'Access Command Deck'}</span>
            </button>
          </form>

          <div className="border-t border-zinc-900/60 pt-4 space-y-2">
            <h3 className="text-[10px] font-mono tracking-wider text-zinc-500 uppercase">Preconfigured SOC Accounts:</h3>
            <div className="grid grid-cols-1 gap-1.5 text-[10px] font-mono text-zinc-400">
              <div className="flex justify-between items-center bg-zinc-900/30 rounded p-1.5 border border-zinc-900/60">
                <span>Admin: <strong className="text-zinc-300 font-bold">admin@agentshield.com</strong></span>
                <span className="text-[9px] bg-zinc-800 px-1 py-0.5 rounded text-zinc-500 uppercase">Full privileges</span>
              </div>
              <div className="flex justify-between items-center bg-zinc-900/30 rounded p-1.5 border border-zinc-900/60">
                <span>Security Analyst: <strong className="text-zinc-300 font-bold">analyst@agentshield.com</strong></span>
                <span className="text-[9px] bg-zinc-800 px-1 py-0.5 rounded text-zinc-500 uppercase">Read / Write</span>
              </div>
              <div className="flex justify-between items-center bg-zinc-900/30 rounded p-1.5 border border-zinc-900/60">
                <span>Viewer: <strong className="text-zinc-300 font-bold">viewer@agentshield.com</strong></span>
                <span className="text-[9px] bg-zinc-800 px-1 py-0.5 rounded text-zinc-500 uppercase">Read-only</span>
              </div>
            </div>
            <p className="text-[9px] text-zinc-600 text-center italic mt-2">Passwords are standard format: [role]-password (e.g. analyst-password)</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 flex font-sans antialiased selection:bg-indigo-500/30 selection:text-white">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-[#0c0c0e] border-r border-zinc-900 flex flex-col justify-between fixed h-screen z-40">
        <div>
          {/* Logo & Product Identity */}
          <div className="px-6 py-6 border-b border-zinc-900/60 flex items-center justify-between">
            <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
              <div className="w-7 h-7 rounded bg-zinc-800 flex items-center justify-center font-bold text-xs text-zinc-100 border border-zinc-700">
                S
              </div>
              <span className="text-sm font-bold tracking-tight text-zinc-200">
                AgentShield X
              </span>
            </div>
            <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-500 uppercase tracking-widest">
              SOC
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5 mt-2">
            {visibleTabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  if (tab.id !== 'replay') setSelectedSessionId(null);
                }}
                className={`w-full flex items-center space-x-3 px-3 py-2 text-xs font-medium rounded transition-all duration-150 ${
                  activeTab === tab.id
                    ? 'bg-zinc-900 text-zinc-100 border border-zinc-800/80 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/30'
                }`}
              >
                <span className={`${activeTab === tab.id ? 'text-indigo-400' : 'text-zinc-500'}`}>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Footer info & Telemetry */}
        <div className="p-4 border-t border-zinc-900/60 bg-[#0a0a0c]/80 text-[10px] text-zinc-500 font-mono space-y-2">
          <div className="flex justify-between items-center">
            <span>Uptime:</span>
            <span className="text-zinc-400">{healthStatus.uptime_seconds ? `${Math.round(healthStatus.uptime_seconds)}s` : '0s'}</span>
          </div>
          <div className="flex justify-between items-center">
            <span>Engine API:</span>
            <span className={`flex items-center space-x-1 ${healthStatus.status === 'ok' ? 'text-emerald-500' : 'text-rose-500'}`}>
              <span className={`w-1 h-1 rounded-full ${healthStatus.status === 'ok' ? 'bg-emerald-500' : 'bg-rose-500'} inline-block`}></span>
              <span>{healthStatus.status === 'ok' ? 'CONNECTED' : 'DISCONNECTED'}</span>
            </span>
          </div>
          {healthStatus.version !== 'unknown' && (
            <div className="text-[9px] text-zinc-600 border-t border-zinc-900/40 pt-1.5 flex justify-between">
              <span>Platform Version:</span>
              <span>v{healthStatus.version}</span>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 pl-64 flex flex-col min-h-screen relative bg-[#09090b]">
        {/* Top Header */}
        <header className="h-16 border-b border-zinc-900 bg-[#09090b]/80 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-8">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-mono font-bold tracking-widest text-zinc-500 uppercase">SYS_TAB /</span>
            <h2 className="text-sm font-bold text-zinc-100 tracking-tight">{getTabLabel(activeTab)}</h2>
          </div>

          <div className="flex items-center space-x-4">
            {/* API Status Indicator */}
            <div className="flex items-center space-x-2 bg-zinc-900/40 border border-zinc-800/80 rounded px-2.5 py-1">
              <span className={`inline-block w-1.5 h-1.5 rounded-full ${
                healthStatus.status === 'ok' 
                  ? 'bg-emerald-500' 
                  : healthStatus.status === 'connecting' 
                    ? 'bg-amber-500 animate-pulse' 
                    : 'bg-rose-500'
              }`}></span>
              <span className="text-[10px] text-zinc-400 font-mono tracking-tight uppercase">
                {healthStatus.status === 'ok' ? 'nominal' : healthStatus.status}
              </span>
            </div>

            {/* User Profile Info & Logout */}
            {currentUser && (
              <div className="flex items-center space-x-3 text-xs border-l border-zinc-800 pl-4">
                <span className="text-zinc-400 font-mono">{currentUser.email}</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 uppercase">
                  {currentUser.role}
                </span>
                <button
                  onClick={handleLogout}
                  className="text-zinc-550 hover:text-zinc-350 hover:bg-zinc-900/60 p-1.5 rounded transition duration-150 flex items-center justify-center"
                  title="Sign out"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Viewport wrapper */}
        <main className="flex-grow p-8 flex flex-col relative">
          {activeTab === 'dashboard' && (
            <DashboardView onNavigateToSession={navigateToSession} />
          )}
          {activeTab === 'threats' && (
            <ThreatsView onNavigateToSession={navigateToSession} />
          )}
          {activeTab === 'replay' && (
            <ReplayView sessionId={selectedSessionId} onSelectSessionId={setSelectedSessionId} />
          )}
          {activeTab === 'agents' && (
            <AgentsView onNavigateToSession={navigateToSession} />
          )}
          {activeTab === 'sandbox' && (
            <SandboxView onNavigateToSession={navigateToSession} />
          )}
          {activeTab === 'settings' && (
            <SettingsView />
          )}
        </main>
      </div>
    </div>
  );
}
