import React from 'react';

export default function AlertPanel() {
  return (
    <div className="p-6 bg-slate-900/50 rounded-2xl border border-slate-800 backdrop-blur-md">
      <h2 className="text-xl font-semibold text-rose-400 mb-2">Live Security Alerts</h2>
      <div className="mt-4 space-y-3">
        <div className="p-4 bg-rose-950/20 border border-rose-800/40 rounded-xl">
          <div className="flex justify-between items-center">
            <span className="px-2 py-0.5 bg-rose-500/20 text-rose-400 text-xs font-semibold rounded-full uppercase border border-rose-500/30">
              High
            </span>
            <span className="text-xs text-slate-500">Just now</span>
          </div>
          <h3 className="text-sm font-semibold text-rose-300 mt-2">Unauthorized Command Attempt</h3>
          <p className="text-xs text-slate-400 mt-1">Agent Beta tried to write directly to system audit logs.</p>
        </div>
      </div>
    </div>
  );
}
