import React from 'react';
import Dashboard from './components/Dashboard';
import TrustGraph from './components/TrustGraph';
import AlertPanel from './components/AlertPanel';
import AgentList from './components/AgentList';
import MessageFlow from './components/MessageFlow';
import AuditLog from './components/AuditLog';

export default function App() {
  return (
    <div className="relative min-h-screen bg-[#070b13] bg-radial-gradient text-slate-100 flex flex-col selection:bg-cyan-500/30">
      
      {/* Background Glows */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-10 right-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl pointer-events-none"></div>

      {/* Header */}
      <header className="border-b border-slate-800/80 bg-slate-950/40 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-violet-500 flex items-center justify-center font-bold text-white shadow-lg shadow-cyan-500/20">
              AS
            </div>
            <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              AgentShield
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-xs text-slate-400 font-mono">CORE STATUS: BOOTED</span>
          </div>
        </div>
      </header>

      {/* Main Layout (Blurred while coming soon) */}
      <main className="max-w-7xl mx-auto px-6 py-8 w-full flex-grow relative">
        
        {/* Banner Overlay */}
        <div className="absolute inset-0 z-40 flex items-center justify-center bg-slate-950/40 backdrop-blur-[6px] rounded-3xl p-4">
          <div className="p-8 md:p-12 max-w-lg w-full bg-gradient-to-b from-slate-900/90 to-slate-950/95 border border-slate-700/60 rounded-2xl shadow-2xl text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 via-violet-500 to-fuchsia-500"></div>
            
            <div className="w-16 h-16 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-cyan-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>

            <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2">
              AgentShield Dashboard
            </h1>
            <p className="text-slate-400 font-medium mb-6 text-cyan-400/90">
              Coming Soon
            </p>
            <p className="text-sm text-slate-400 leading-relaxed mb-8">
              A comprehensive interceptor, analyzer, and trust dashboard mapping multi-agent safety metrics in real-time.
            </p>
            <div className="inline-flex items-center space-x-2 text-xs font-mono text-slate-500 border border-slate-800 rounded-full px-3 py-1 bg-slate-950/40">
              <span>FastAPI Backend online</span>
            </div>
          </div>
        </div>

        {/* Dashboard Grid Background preview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 select-none opacity-40">
          <div className="lg:col-span-2 space-y-6">
            <Dashboard />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TrustGraph />
              <MessageFlow />
            </div>
          </div>
          <div className="space-y-6">
            <AlertPanel />
            <AgentList />
            <AuditLog />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900/60 bg-slate-950/20 py-6 text-center text-xs text-slate-500 font-mono">
        &copy; {new Date().getFullYear()} AgentShield. All rights reserved.
      </footer>
    </div>
  );
}
