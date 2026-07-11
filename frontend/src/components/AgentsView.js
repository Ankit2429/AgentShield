import React, { useState, useEffect } from 'react';
import { getAgents } from '../services/api';

export default function AgentsView() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [error, setError] = useState(null);

  const fetchAgentsData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (searchQuery.trim()) params.agent_id = searchQuery.trim();
      if (statusFilter) params.agent_status = statusFilter;
      
      const data = await getAgents(params);
      setAgents(data.agents || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching agents:', err);
      setError('Unable to load agent profiles registry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgentsData();
  }, [searchQuery, statusFilter]);

  const getStatusBadge = (status) => {
    const uppercase = status.toUpperCase();
    if (uppercase === 'BLOCKED') return 'text-rose-400 bg-rose-500/10 border border-rose-500/20';
    if (uppercase === 'QUARANTINED') return 'text-orange-400 bg-orange-500/10 border border-orange-500/20';
    if (uppercase === 'SUSPICIOUS') return 'text-amber-400 bg-amber-500/10 border border-amber-500/20';
    if (uppercase === 'MONITOR') return 'text-blue-400 bg-blue-500/10 border border-blue-500/20';
    if (uppercase === 'VERIFIED') return 'text-teal-400 bg-teal-500/10 border border-teal-500/20';
    if (uppercase === 'TRUSTED') return 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20';
    return 'text-slate-400 bg-slate-900 border border-slate-800';
  };

  const getTrendBadge = (trend) => {
    const uppercase = trend.toUpperCase();
    if (uppercase === 'IMPROVING') {
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-emerald-400 bg-emerald-500/5 px-1.5 py-0.5 rounded border border-emerald-500/10">
          ▲ Improving
        </span>
      );
    }
    if (uppercase === 'DECLINING') {
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-rose-400 bg-rose-500/5 px-1.5 py-0.5 rounded border border-rose-500/10">
          ▼ Declining
        </span>
      );
    }
    return (
      <span className="inline-flex items-center text-[10px] font-semibold text-slate-400 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-900">
        ▶ Stable
      </span>
    );
  };

  const getGradeStyle = (grade) => {
    if (grade.startsWith('A')) return 'text-emerald-400 font-extrabold';
    if (grade.startsWith('B')) return 'text-teal-400 font-extrabold';
    if (grade.startsWith('C')) return 'text-blue-400 font-bold';
    if (grade.startsWith('D')) return 'text-amber-400 font-bold';
    return 'text-rose-400 font-black';
  };

  return (
    <div className="space-y-6 flex-grow flex flex-col">
      {/* Header section */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Agent Trust Registry</h1>
        <p className="text-sm text-slate-400 mt-1">Operational profiles and long-term reputation metrics of all observed AI agents.</p>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 p-4 bg-[#0b0e17] rounded-xl border border-slate-900 shadow-sm">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Filter by Agent ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-900 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
          />
          <svg className="w-4 h-4 text-slate-500 absolute left-2.5 top-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 text-xs bg-slate-950 border border-slate-900 rounded-lg text-slate-300 focus:outline-none focus:border-cyan-500 transition"
        >
          <option value="">All Lifecycle Statuses</option>
          <option value="TRUSTED">TRUSTED</option>
          <option value="VERIFIED">VERIFIED</option>
          <option value="MONITOR">MONITOR</option>
          <option value="SUSPICIOUS">SUSPICIOUS</option>
          <option value="QUARANTINED">QUARANTINED</option>
          <option value="BLOCKED">BLOCKED</option>
        </select>

        <button
          onClick={fetchAgentsData}
          className="px-3.5 py-1.5 text-xs font-semibold bg-slate-900 border border-slate-800 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/80 transition"
        >
          Reload
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/20 border border-rose-900/40 rounded-xl text-rose-400 text-sm">
          {error}
        </div>
      )}

      {/* Main Table */}
      <div className="bg-[#0b0e17] rounded-xl border border-slate-900 overflow-hidden shadow-sm flex-grow">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-900 bg-[#07090f]/50 text-slate-400 font-semibold">
                <th className="p-4">Agent ID</th>
                <th className="p-4">Trust Score</th>
                <th className="p-4">Grade</th>
                <th className="p-4">Behavior Score</th>
                <th className="p-4">Policy Score</th>
                <th className="p-4">Status</th>
                <th className="p-4">Trend</th>
                <th className="p-4">Successful / Blocked / Suspicious</th>
                <th className="p-4 text-right">Last Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900/60">
              {loading ? (
                <tr>
                  <td colSpan="9" className="p-12 text-center text-slate-500 font-mono">
                    Querying agent trust records...
                  </td>
                </tr>
              ) : agents.length === 0 ? (
                <tr>
                  <td colSpan="9" className="p-12 text-center text-slate-500 font-mono">
                    No agent trust profiles found. Intercept a message in the Sandbox to register profiles.
                  </td>
                </tr>
              ) : (
                agents.map((agent) => (
                  <tr key={agent.agent_id} className="hover:bg-slate-900/10 transition">
                    <td className="p-4 text-slate-200 font-semibold font-mono">
                      {agent.agent_id}
                    </td>
                    <td className="p-4 font-mono font-bold text-slate-300">
                      {(agent.trust_score * 100).toFixed(1)}%
                    </td>
                    <td className="p-4 font-mono">
                      <span className={getGradeStyle(agent.security_grade)}>
                        {agent.security_grade}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-slate-400">
                      {agent.behavior_score.toFixed(2)}
                    </td>
                    <td className="p-4 font-mono text-slate-400">
                      {agent.policy_score.toFixed(2)}
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 text-[9px] font-bold rounded-full uppercase ${getStatusBadge(agent.status)}`}>
                        {agent.status}
                      </span>
                    </td>
                    <td className="p-4">
                      {getTrendBadge(agent.trend)}
                    </td>
                    <td className="p-4 font-mono text-slate-400">
                      <span className="text-emerald-400 font-semibold">{agent.successful_requests}</span>
                      <span className="text-slate-600 mx-1">/</span>
                      <span className="text-rose-400 font-semibold">{agent.blocked_requests}</span>
                      <span className="text-slate-600 mx-1">/</span>
                      <span className="text-amber-400 font-semibold">{agent.suspicious_requests}</span>
                    </td>
                    <td className="p-4 text-slate-500 font-mono text-right">
                      {new Date(agent.last_updated).toLocaleTimeString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
