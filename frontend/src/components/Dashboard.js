import React from 'react';

export default function Dashboard() {
  return (
    <div className="p-6 bg-slate-900/50 rounded-2xl border border-slate-800 backdrop-blur-md">
      <h2 className="text-xl font-semibold text-cyan-400 mb-2">System Metrics</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/50">
          <p className="text-sm text-slate-400">Active Agents</p>
          <p className="text-2xl font-bold text-white mt-1">2</p>
        </div>
        <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/50">
          <p className="text-sm text-slate-400">Total Intercepted Messages</p>
          <p className="text-2xl font-bold text-white mt-1">150</p>
        </div>
        <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/50">
          <p className="text-sm text-slate-400">Security Alerts</p>
          <p className="text-2xl font-bold text-rose-500 mt-1">1 Active</p>
        </div>
      </div>
    </div>
  );
}
