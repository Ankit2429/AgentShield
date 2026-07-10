import React from 'react';

export default function MessageFlow() {
  return (
    <div className="p-6 bg-slate-900/50 rounded-2xl border border-slate-800 backdrop-blur-md">
      <h2 className="text-xl font-semibold text-blue-400 mb-2">Message Flow logs</h2>
      <div className="mt-4 space-y-2 max-h-48 overflow-y-auto">
        <div className="p-3 bg-slate-950/30 rounded-lg text-xs font-mono border border-slate-850">
          <span className="text-emerald-400">Agent Alpha</span>
          <span className="text-slate-500 mx-2">➔</span>
          <span className="text-sky-400">Agent Beta</span>
          <p className="text-slate-300 mt-1">"Fetch system stats"</p>
        </div>
      </div>
    </div>
  );
}
