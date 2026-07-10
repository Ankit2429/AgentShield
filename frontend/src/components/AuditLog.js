import React from 'react';

export default function AuditLog() {
  return (
    <div className="p-6 bg-slate-900/50 rounded-2xl border border-slate-800 backdrop-blur-md">
      <h2 className="text-xl font-semibold text-slate-300 mb-2">Audit Logs</h2>
      <div className="mt-4 space-y-2 text-xs font-mono">
        <div className="flex justify-between text-slate-500 border-b border-slate-800 pb-2">
          <span>Action</span>
          <span>Operator</span>
          <span>Time</span>
        </div>
        <div className="flex justify-between py-1 border-b border-slate-900">
          <span className="text-slate-300">AGENT_REGISTRATION</span>
          <span className="text-slate-400">SYSTEM</span>
          <span className="text-slate-500">19:50:35</span>
        </div>
      </div>
    </div>
  );
}
