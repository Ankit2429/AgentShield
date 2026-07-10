import React from 'react';

export default function AgentList() {
  const agents = [
    { id: 1, name: "Agent Alpha", role: "Router", status: "Active", trust: 0.95 },
    { id: 2, name: "Agent Beta", role: "Reader", status: "Active", trust: 0.85 }
  ];

  return (
    <div className="p-6 bg-slate-900/50 rounded-2xl border border-slate-800 backdrop-blur-md">
      <h2 className="text-xl font-semibold text-emerald-400 mb-2">Monitored Agents</h2>
      <div className="mt-4 space-y-3">
        {agents.map(agent => (
          <div key={agent.id} className="p-3 bg-slate-850/30 border border-slate-800 rounded-xl flex justify-between items-center">
            <div>
              <p className="text-sm font-medium text-white">{agent.name}</p>
              <p className="text-xs text-slate-400">{agent.role}</p>
            </div>
            <div className="text-right">
              <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                {Math.round(agent.trust * 100)}% Trust
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
