import React, { useState, useEffect } from 'react';
import { getDashboard } from '../services/api';

export default function DashboardView({ onNavigateToSession }) {
  const [stats, setStats] = useState({
    active_agents: 0,
    total_sessions: 0,
    threat_sessions: 0,
    blocked_sessions: 0,
    average_trust_score: 0.0,
    recent_decisions: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const data = await getDashboard();
      setStats(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching dashboard stats:', err);
      setError('Unable to load real-time metrics from the security engines.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  const formatDecision = (decision) => {
    const uppercase = decision.toUpperCase();
    if (uppercase === 'BLOCK') return 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
    if (uppercase === 'QUARANTINE') return 'bg-orange-500/10 text-orange-400 border border-orange-500/20';
    if (uppercase === 'REVIEW') return 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
    if (uppercase === 'MONITOR') return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
    return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
  };

  const getRiskColor = (risk) => {
    if (risk === null || risk === undefined) return 'text-slate-500';
    if (risk >= 0.7) return 'text-rose-400 font-bold';
    if (risk >= 0.4) return 'text-amber-400';
    if (risk > 0.0) return 'text-blue-400';
    return 'text-slate-400';
  };

  return (
    <div className="space-y-8 flex-grow flex flex-col">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Security Command Center</h1>
          <p className="text-sm text-slate-400 mt-1">Real-time AI agent monitoring, anomaly detection, and trust scoring.</p>
        </div>
        <button
          onClick={fetchDashboardData}
          className="px-3.5 py-1.5 text-xs font-semibold bg-slate-900 border border-slate-800 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/80 transition"
        >
          Force Refresh
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/20 border border-rose-900/40 rounded-xl text-rose-400 text-sm flex items-center space-x-3">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Active Agents', value: loading ? '...' : stats.active_agents, desc: 'Known profiles' },
          { label: 'Total Interceptions', value: loading ? '...' : stats.total_sessions, desc: 'Requests monitored' },
          { label: 'Threats Flagged', value: loading ? '...' : stats.threat_sessions, desc: 'Malicious payloads', alert: stats.threat_sessions > 0 },
          { label: 'Active Blocks', value: loading ? '...' : stats.blocked_sessions, desc: 'Access denied', alert: stats.blocked_sessions > 0 },
          { label: 'Average Trust Score', value: loading ? '...' : `${(stats.average_trust_score * 100).toFixed(1)}%`, desc: 'Fleet health' }
        ].map((metric, i) => (
          <div
            key={i}
            className="p-5 bg-[#0b0e17] rounded-xl border border-slate-900 flex flex-col justify-between hover:border-slate-800 transition duration-300 shadow-sm"
          >
            <span className="text-xs text-slate-400 font-medium tracking-normal">{metric.label}</span>
            <div className="my-3">
              <span className={`text-2xl font-extrabold tracking-tight ${
                metric.alert && metric.value !== '...' ? 'text-rose-400' : 'text-white'
              }`}>
                {metric.value}
              </span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">{metric.desc}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Decisions Table */}
        <div className="lg:col-span-2 bg-[#0b0e17] rounded-xl border border-slate-900 overflow-hidden flex flex-col shadow-sm">
          <div className="p-5 border-b border-slate-900 flex justify-between items-center">
            <span className="text-sm font-semibold text-white">Recent Security Verdicts</span>
            <span className="text-xs text-slate-500 font-mono">{stats.recent_decisions.length} captured</span>
          </div>
          <div className="flex-grow overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-900/60 bg-[#07090f]/50 text-slate-400 font-semibold">
                  <th className="p-4">Session ID</th>
                  <th className="p-4">Agent ID</th>
                  <th className="p-4">Verdict</th>
                  <th className="p-4">Peak Risk</th>
                  <th className="p-4">Timestamp</th>
                  <th className="p-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900/60">
                {stats.recent_decisions.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="p-8 text-center text-slate-500 font-mono">
                      No security decisions logged. Run an analysis in the Simulator Sandbox.
                    </td>
                  </tr>
                ) : (
                  stats.recent_decisions.map((decision) => (
                    <tr key={decision.session_id} className="hover:bg-slate-900/20 transition group">
                      <td className="p-4 font-mono text-slate-300">
                        {decision.session_id.substring(0, 8)}...
                      </td>
                      <td className="p-4 text-slate-200 font-medium">
                        {decision.agent_id}
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 text-[10px] font-semibold rounded-full ${formatDecision(decision.decision)}`}>
                          {decision.decision}
                        </span>
                      </td>
                      <td className="p-4 font-mono">
                        <span className={getRiskColor(decision.risk_score)}>
                          {decision.risk_score !== null ? decision.risk_score.toFixed(2) : '0.00'}
                        </span>
                      </td>
                      <td className="p-4 text-slate-400 font-mono">
                        {new Date(decision.started_at).toLocaleTimeString()}
                      </td>
                      <td className="p-4 text-right">
                        <button
                          onClick={() => onNavigateToSession(decision.session_id)}
                          className="px-2.5 py-1 text-[10px] font-semibold text-cyan-400 border border-cyan-500/20 bg-cyan-500/5 hover:bg-cyan-500/15 rounded transition opacity-80 group-hover:opacity-100"
                        >
                          Replay
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Engine Stack Status */}
        <div className="bg-[#0b0e17] rounded-xl border border-slate-900 p-5 flex flex-col justify-between shadow-sm">
          <div>
            <h2 className="text-sm font-semibold text-white mb-4">Security Engine Stack</h2>
            <div className="space-y-4">
              {[
                { name: 'Detection Engine', role: 'Malicious pattern matching', status: 'Active', color: 'text-emerald-400' },
                { name: 'Behavioral DNA', role: 'Statistical deviation profiler', status: 'Calibrated', color: 'text-emerald-400' },
                { name: 'Trust Intelligence', role: 'Lifecycle reputation scoring', status: 'Active', color: 'text-emerald-400' },
                { name: 'Decision Engine', role: 'Explainable verdict orchestrator', status: 'Active', color: 'text-emerald-400' },
                { name: 'Attack Replay', role: 'Durable event timeline builder', status: 'Active', color: 'text-emerald-400' }
              ].map((engine, i) => (
                <div key={i} className="flex justify-between items-start py-2 border-b border-slate-900 last:border-0">
                  <div>
                    <p className="text-xs font-semibold text-slate-200">{engine.name}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">{engine.role}</p>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span className={`text-[10px] font-bold ${engine.color} font-mono uppercase`}>{engine.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-900 text-[10px] text-slate-500 leading-normal">
            <p>Platform status is nominal. Security engine latency averages &lt;1.5ms. Fleet configuration is synchronized.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
