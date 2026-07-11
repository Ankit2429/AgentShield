import React, { useState, useEffect } from 'react';
import { getHealth } from './services/api';
import DashboardView from './components/DashboardView';
import ReplayView from './components/ReplayView';
import AgentsView from './components/AgentsView';
import SandboxView from './components/SandboxView';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [healthStatus, setHealthStatus] = useState({ status: 'connecting', version: 'unknown', uptime_seconds: 0 });
  const [selectedSessionId, setSelectedSessionId] = useState(null);

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

  const navigateToSession = (sessionId) => {
    setSelectedSessionId(sessionId);
    setActiveTab('replay');
  };

  return (
    <div className="relative min-h-screen bg-[#080b11] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-white">
      {/* Background glow effects - soft and subtle */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-cyan-500/[0.02] rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-10 right-1/4 w-[500px] h-[500px] bg-violet-500/[0.02] rounded-full blur-3xl pointer-events-none"></div>

      {/* Main Header */}
      <header className="border-b border-slate-900 bg-[#0c101b]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-8">
            {/* Logo */}
            <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md shadow-cyan-500/10">
                AS
              </div>
              <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                AgentShield X
              </span>
            </div>

            {/* Navigation Tabs */}
            <nav className="flex items-center space-x-1">
              {[
                { id: 'dashboard', label: 'Overview' },
                { id: 'replay', label: 'Incidents & Replay' },
                { id: 'agents', label: 'Agent Profiles' },
                { id: 'sandbox', label: 'Simulator Sandbox' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id);
                    if (tab.id !== 'replay') setSelectedSessionId(null);
                  }}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                    activeTab === tab.id
                      ? 'bg-slate-900 text-cyan-400 border border-slate-800'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* System Status Indicators */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-slate-950/60 border border-slate-900 rounded-full px-3.5 py-1">
              <span className={`inline-block w-2 h-2 rounded-full ${
                healthStatus.status === 'ok' 
                  ? 'bg-emerald-500 animate-pulse' 
                  : healthStatus.status === 'connecting' 
                    ? 'bg-amber-500 animate-pulse' 
                    : 'bg-rose-500'
              }`}></span>
              <span className="text-xs text-slate-400 font-mono tracking-tight uppercase">
                {healthStatus.status === 'ok' ? 'SOC CONNECTED' : `SOC ${healthStatus.status.toUpperCase()}`}
              </span>
            </div>
            {healthStatus.version !== 'unknown' && (
              <span className="text-xs text-slate-500 font-mono hidden sm:inline">
                v{healthStatus.version}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-6 py-8 w-full flex-grow flex flex-col relative z-10">
        {activeTab === 'dashboard' && (
          <DashboardView onNavigateToSession={navigateToSession} />
        )}
        {activeTab === 'replay' && (
          <ReplayView sessionId={selectedSessionId} onSelectSessionId={setSelectedSessionId} />
        )}
        {activeTab === 'agents' && (
          <AgentsView />
        )}
        {activeTab === 'sandbox' && (
          <SandboxView onNavigateToSession={navigateToSession} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900/60 bg-[#0a0d15]/50 py-6">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center text-xs text-slate-500 font-mono">
          <span>&copy; {new Date().getFullYear()} AgentShield X. All rights reserved.</span>
          <div className="flex space-x-4 mt-2 md:mt-0">
            <span>Detections: ACTIVE</span>
            <span>DNA Engine: CALIBRATED</span>
            <span>Uptime: {healthStatus.uptime_seconds ? `${Math.round(healthStatus.uptime_seconds)}s` : '0s'}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
