import React, { useState, useEffect } from 'react';
import { getAgents, getReplays } from '../services/api';

export default function AgentsView({ onNavigateToSession }) {
  const [agents, setAgents] = useState([]);
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agentSessions, setAgentSessions] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [error, setError] = useState(null);

  // Fetch agents list
  const fetchAgentsData = async () => {
    try {
      setLoadingList(true);
      const params = {};
      if (searchQuery.trim()) {
        params.agent_id = searchQuery.trim();
      }
      if (statusFilter) {
        params.agent_status = statusFilter;
      }
      
      const data = await getAgents(params);
      const list = data.agents || [];
      setAgents(list);

      // Auto-select the first agent if none is selected
      if (list.length > 0 && !selectedAgentId) {
        setSelectedAgentId(list[0].agent_id);
      }
      setError(null);
    } catch (err) {
      console.error('Error fetching agents:', err);
      setError('Unable to load agent profiles registry.');
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchAgentsData();
  }, [searchQuery, statusFilter]);

  // Load details and session log when selected agent changes
  useEffect(() => {
    if (!selectedAgentId) {
      setSelectedAgent(null);
      setAgentSessions([]);
      return;
    }

    const current = agents.find(a => a.agent_id === selectedAgentId);
    if (current) {
      setSelectedAgent(current);
    }

    const fetchAgentSessions = async () => {
      try {
        setLoadingDetails(true);
        const data = await getReplays({ agent_id: selectedAgentId });
        setAgentSessions(data.sessions || []);
      } catch (err) {
        console.error('Error fetching agent sessions:', err);
      } finally {
        setLoadingDetails(false);
      }
    };

    fetchAgentSessions();
  }, [selectedAgentId, agents]);

  const getStatusBadge = (status) => {
    const uppercase = status.toUpperCase();
    if (uppercase === 'BLOCKED') return 'text-rose-400 bg-rose-500/10 border border-rose-500/20';
    if (uppercase === 'QUARANTINED') return 'text-orange-400 bg-orange-500/10 border border-orange-500/20';
    if (uppercase === 'SUSPICIOUS') return 'text-amber-400 bg-amber-500/10 border border-amber-500/20';
    if (uppercase === 'MONITOR') return 'text-indigo-400 bg-indigo-500/10 border border-indigo-500/20';
    if (uppercase === 'VERIFIED') return 'text-sky-400 bg-sky-500/10 border border-sky-500/20';
    return 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20';
  };

  const getTrendBadge = (trend) => {
    const uppercase = trend.toUpperCase();
    if (uppercase === 'IMPROVING') {
      return <span className="text-emerald-400 font-medium font-mono text-[9px]">&#9650; Improving</span>;
    }
    if (uppercase === 'DECLINING') {
      return <span className="text-rose-400 font-medium font-mono text-[9px]">&#9660; Declining</span>;
    }
    return <span className="text-zinc-550 font-medium font-mono text-[9px]">&#9654; Stable</span>;
  };

  const getGradeColor = (grade) => {
    if (grade.startsWith('A')) return 'text-emerald-400';
    if (grade.startsWith('B')) return 'text-sky-400';
    if (grade.startsWith('C')) return 'text-indigo-400';
    if (grade.startsWith('D')) return 'text-amber-400';
    return 'text-rose-400';
  };

  return (
    <div className="flex-grow flex flex-col lg:flex-row gap-8 items-stretch min-h-[calc(100vh-10rem)]">
      {/* Left Column - Agent Registry List */}
      <div className="w-full lg:w-96 flex flex-col bg-[#0c0c0e] rounded border border-zinc-900 overflow-hidden flex-shrink-0">
        {/* Filters */}
        <div className="p-4 border-b border-zinc-900 space-y-3 bg-[#09090b]/40">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-400 block">Agent Registry</span>
          
          <div className="relative">
            <input
              type="text"
              placeholder="Filter by Agent ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-zinc-950 border border-zinc-900 rounded text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-800 transition font-mono"
            />
            <svg className="w-4 h-4 text-zinc-650 absolute left-2.5 top-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full px-3 py-1.5 text-xs bg-zinc-950 border border-zinc-900 rounded text-zinc-300 focus:outline-none focus:border-zinc-800 transition font-mono"
          >
            <option value="">All Lifecycle Statuses</option>
            <option value="TRUSTED">TRUSTED</option>
            <option value="VERIFIED">VERIFIED</option>
            <option value="MONITOR">MONITOR</option>
            <option value="SUSPICIOUS">SUSPICIOUS</option>
            <option value="QUARANTINED">QUARANTINED</option>
            <option value="BLOCKED">BLOCKED</option>
          </select>
        </div>

        {/* List Content */}
        <div className="flex-grow overflow-y-auto divide-y divide-zinc-900/60 max-h-[calc(100vh-20rem)] lg:max-h-[none]">
          {loadingList ? (
            <div className="p-8 text-center text-zinc-500 font-mono text-[10px]">Querying monitored fleet...</div>
          ) : agents.length === 0 ? (
            <div className="p-8 text-center text-zinc-500 font-mono text-[10px]">No agent profiles registered.</div>
          ) : (
            agents.map((agent) => (
              <div
                key={agent.agent_id}
                onClick={() => setSelectedAgentId(agent.agent_id)}
                className={`p-4 cursor-pointer transition flex items-center justify-between border-l-2 ${
                  selectedAgentId === agent.agent_id
                    ? 'bg-zinc-900/30 border-indigo-500 text-zinc-100'
                    : 'border-transparent text-zinc-400 hover:bg-zinc-900/10'
                }`}
              >
                <div className="space-y-1">
                  <span className="text-zinc-200 font-mono font-bold text-xs block">{agent.agent_id}</span>
                  <div className="flex items-center space-x-2 text-[10px]">
                    <span className="text-zinc-500 font-mono">trust: {(agent.trust_score * 100).toFixed(1)}%</span>
                    <span className="text-zinc-650">•</span>
                    {getTrendBadge(agent.trend)}
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <span className={`text-[10px] font-bold font-mono ${getGradeColor(agent.security_grade)}`}>
                    {agent.security_grade}
                  </span>
                  <span className={`px-1.5 py-0.5 text-[8px] font-bold rounded uppercase border ${
                    agent.status === 'BLOCKED' ? 'text-rose-400 border-rose-500/20 bg-rose-500/5' : 'text-zinc-500 border-zinc-800 bg-zinc-900/30'
                  }`}>
                    {agent.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Column - Agent Details & Timeline Log */}
      <div className="flex-1 flex flex-col bg-[#0c0c0e] rounded border border-zinc-900 overflow-hidden min-h-[500px]">
        {!selectedAgent ? (
          <div className="flex-grow flex flex-col items-center justify-center p-12 text-center text-zinc-500 font-mono">
            <svg className="w-8 h-8 text-zinc-700 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <p className="text-[11px] text-zinc-400">Select an agent profile from the registry to view reputation analysis.</p>
          </div>
        ) : (
          <div className="flex-grow flex flex-col overflow-y-auto max-h-[calc(100vh-10rem)] p-6 space-y-8">
            {/* Profile Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-zinc-900/80 pb-5 gap-4">
              <div>
                <div className="flex items-center space-x-3">
                  <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider font-bold">Profile Registry /</span>
                  <h2 className="text-sm font-bold text-zinc-200 font-mono">{selectedAgent.agent_id}</h2>
                </div>
                <p className="text-[10px] text-zinc-500 font-mono mt-1">
                  Last monitored activity logged at: {new Date(selectedAgent.last_updated).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center space-x-3">
                <span className={`px-2 py-0.5 text-[9px] font-bold rounded uppercase border ${getStatusBadge(selectedAgent.status)}`}>
                  {selectedAgent.status}
                </span>
                <div className="px-2.5 py-1 bg-zinc-950 border border-zinc-900 rounded flex items-center space-x-1.5 font-mono text-xs">
                  <span className="text-zinc-500">Security Grade:</span>
                  <span className={`font-bold ${getGradeColor(selectedAgent.security_grade)}`}>{selectedAgent.security_grade}</span>
                </div>
              </div>
            </div>

            {/* Score Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: 'Composite Trust Score', value: `${(selectedAgent.trust_score * 100).toFixed(1)}%`, desc: 'Reputation baseline' },
                { label: 'Behavioral DNA Score', value: selectedAgent.behavior_score.toFixed(3), desc: 'Statistical variance index' },
                { label: 'Policy Adherence Index', value: selectedAgent.policy_score.toFixed(3), desc: 'Rule match coefficient' }
              ].map((metric, idx) => (
                <div key={idx} className="bg-zinc-950 border border-zinc-900 rounded p-4 flex flex-col justify-between">
                  <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-zinc-500">{metric.label}</span>
                  <div className="mt-3 flex items-baseline justify-between">
                    <span className="text-base font-bold text-zinc-200 font-mono">{metric.value}</span>
                    <span className="text-[9px] text-zinc-600 font-mono">{metric.desc}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Request Telemetry Proportion Meter */}
            <div className="space-y-3">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-400">Request Telemetry Analysis</h3>
                <p className="text-[10px] text-zinc-500 mt-0.5">Ratio of successful, blocked, and suspicious transactions</p>
              </div>

              {/* Meter bar */}
              {(() => {
                const total = selectedAgent.successful_requests + selectedAgent.blocked_requests + selectedAgent.suspicious_requests;
                const successPct = total > 0 ? (selectedAgent.successful_requests / total) * 100 : 100;
                const blockPct = total > 0 ? (selectedAgent.blocked_requests / total) * 100 : 0;
                const suspPct = total > 0 ? (selectedAgent.suspicious_requests / total) * 100 : 0;

                return (
                  <div className="space-y-4 bg-zinc-950 border border-zinc-900 rounded p-5">
                    {/* Visual bar */}
                    <div className="w-full h-2.5 rounded-full bg-zinc-900 flex overflow-hidden border border-zinc-900 shadow-inner">
                      {total === 0 ? (
                        <div className="w-full h-full bg-zinc-800" title="No request telemetry"></div>
                      ) : (
                        <>
                          <div style={{ width: `${successPct}%` }} className="h-full bg-emerald-500/80" title="Successful Requests"></div>
                          <div style={{ width: `${suspPct}%` }} className="h-full bg-amber-500/80" title="Suspicious Requests"></div>
                          <div style={{ width: `${blockPct}%` }} className="h-full bg-rose-500/80" title="Blocked Requests"></div>
                        </>
                      )}
                    </div>

                    {/* Telemetry indices */}
                    <div className="grid grid-cols-3 gap-4 text-center font-mono text-[10px]">
                      <div className="p-2 border border-zinc-900 bg-[#0c0c0e] rounded">
                        <span className="text-zinc-500 block mb-0.5">Successful</span>
                        <span className="text-emerald-400 font-bold text-xs">{selectedAgent.successful_requests}</span>
                        <span className="text-zinc-600 block mt-0.5">({successPct.toFixed(1)}%)</span>
                      </div>
                      <div className="p-2 border border-zinc-900 bg-[#0c0c0e] rounded">
                        <span className="text-zinc-500 block mb-0.5">Suspicious</span>
                        <span className="text-amber-400 font-bold text-xs">{selectedAgent.suspicious_requests}</span>
                        <span className="text-zinc-600 block mt-0.5">({suspPct.toFixed(1)}%)</span>
                      </div>
                      <div className="p-2 border border-zinc-900 bg-[#0c0c0e] rounded">
                        <span className="text-zinc-500 block mb-0.5">Blocked</span>
                        <span className="text-rose-400 font-bold text-xs">{selectedAgent.blocked_requests}</span>
                        <span className="text-zinc-600 block mt-0.5">({blockPct.toFixed(1)}%)</span>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Related Incidents Feed */}
            <div className="space-y-3">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-400">Recent Operational Events</h3>
                <p className="text-[10px] text-zinc-500 mt-0.5">Timeline sessions mapped to this profile</p>
              </div>

              <div className="bg-zinc-950 border border-zinc-900 rounded overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-900 bg-zinc-900/40 text-zinc-500 font-medium">
                      <th className="px-4 py-2.5 font-mono text-[9px] uppercase">Session ID</th>
                      <th className="px-4 py-2.5 font-mono text-[9px] uppercase">Enforcement</th>
                      <th className="px-4 py-2.5 font-mono text-[9px] uppercase">Peak Risk</th>
                      <th className="px-4 py-2.5 font-mono text-[9px] uppercase">Timestamp</th>
                      <th className="px-4 py-2.5 text-right font-mono text-[9px] uppercase">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900/60 font-mono text-[11px]">
                    {loadingDetails ? (
                      <tr>
                        <td colSpan="5" className="px-4 py-8 text-center text-zinc-500">
                          Fetching agent session timeline...
                        </td>
                      </tr>
                    ) : agentSessions.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="px-4 py-8 text-center text-zinc-500 italic">
                          No interaction history recorded for this agent profile.
                        </td>
                      </tr>
                    ) : (
                      agentSessions.map((session) => (
                        <tr 
                          key={session.session_id}
                          onClick={() => onNavigateToSession(session.session_id)}
                          className="hover:bg-zinc-900/30 transition cursor-pointer group"
                        >
                          <td className="px-4 py-2.5 text-zinc-400">
                            {session.session_id.substring(0, 8)}
                          </td>
                          <td className="px-4 py-2.5 font-sans">
                            <span className={`px-1.5 py-0.5 text-[8px] font-semibold rounded uppercase border ${
                              session.final_decision === 'BLOCK' ? 'text-rose-400 border-rose-500/20 bg-rose-500/5' : 'text-zinc-500 border-zinc-800 bg-zinc-900/20'
                            }`}>
                              {session.final_decision || 'PENDING'}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-zinc-300">
                            {session.peak_risk_score !== null ? session.peak_risk_score.toFixed(3) : '0.000'}
                          </td>
                          <td className="px-4 py-2.5 text-zinc-500">
                            {new Date(session.started_at).toLocaleString()}
                          </td>
                          <td className="px-4 py-2.5 text-right">
                            <span className="text-[10px] text-zinc-400 group-hover:text-indigo-400 border border-transparent group-hover:border-indigo-500/20 group-hover:bg-indigo-500/5 px-2 py-0.5 rounded transition">
                              Audit &rarr;
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
