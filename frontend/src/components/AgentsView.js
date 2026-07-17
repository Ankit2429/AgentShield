import React, { useState, useEffect } from 'react';
import { getAgents, getReplays } from '../services/api';
import {
  Search,
  Shield,
  ChevronDown,
  RefreshCw,
  AlertTriangle,
  AlertCircle,
  PlayCircle,
  Users,
  Activity,
  TrendingUp,
  TrendingDown
} from 'lucide-react';

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
    if (uppercase === 'BLOCKED' || uppercase === 'QUARANTINED') {
      return 'text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20';
    }
    if (uppercase === 'SUSPICIOUS' || uppercase === 'MONITOR') {
      return 'text-[#f59e0b] bg-[#f59e0b]/10 border border-[#f59e0b]/20';
    }
    return 'text-[#22c55e] bg-[#22c55e]/10 border border-[#22c55e]/20';
  };

  const getTrendBadge = (trend) => {
    const uppercase = trend.toUpperCase();
    if (uppercase === 'IMPROVING') {
      return (
        <span className="text-[#22c55e] font-medium text-[9px] flex items-center gap-0.5">
          <TrendingUp className="w-[18px] h-[18px]" strokeWidth={1.5} /> Improving
        </span>
      );
    }
    if (uppercase === 'DECLINING') {
      return (
        <span className="text-[#ef4444] font-medium text-[9px] flex items-center gap-0.5">
          <TrendingDown className="w-[18px] h-[18px]" strokeWidth={1.5} /> Declining
        </span>
      );
    }
    return <span className="text-zinc-550 font-medium text-[9px] flex items-center gap-0.5">Stable</span>;
  };

  const getGradeColor = (grade) => {
    if (grade.startsWith('A')) return 'text-[#2A9D8F]';
    if (grade.startsWith('B')) return 'text-[#4CC9F0]';
    if (grade.startsWith('C')) return 'text-[#4361EE]';
    if (grade.startsWith('D')) return 'text-[#F4A261]';
    return 'text-[#E07A5F]';
  };

  return (
    <div className="flex-grow flex flex-col lg:flex-row gap-6 items-stretch min-h-[calc(100vh-10rem)]">
      {/* Left Column - Agent Registry List */}
      <div className="w-full lg:w-80 flex flex-col rounded-2xl border overflow-hidden flex-shrink-0" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
        {/* Filters */}
        <div className="p-4 border-b border-white/[0.04] space-y-3 bg-white/[0.01]">
          <span className="text-xs font-bold uppercase tracking-wider block" style={{ color: '#FEFAE0', fontFamily: 'var(--font-display)' }}>Agent Registry</span>
          
          <div className="relative">
            <input
              type="text"
              placeholder="Filter by Agent ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-xs rounded-lg outline-none border transition-all"
              style={{
                background: '#0c0c0e',
                border: '1px solid rgba(254,250,224,0.08)',
                color: '#FEFAE0',
                fontFamily: 'var(--font-mono)'
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = '#4361EE'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(67,97,238,0.3)'; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(254,250,224,0.08)'; e.currentTarget.style.boxShadow = 'none'; }}
            />
            <Search className="w-[18px] h-[18px] absolute left-3 top-2.5" style={{ color: 'rgba(254,250,224,0.35)' }} strokeWidth={1.5} />
          </div>

          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full pl-3 pr-8 py-2 text-xs rounded-lg outline-none border appearance-none transition-all cursor-pointer font-sans"
              style={{
                background: '#0c0c0e',
                border: '1px solid rgba(254,250,224,0.08)',
                color: '#FEFAE0'
              }}
            >
              <option value="">All Lifecycle Statuses</option>
              <option value="TRUSTED">TRUSTED</option>
              <option value="VERIFIED">VERIFIED</option>
              <option value="MONITOR">MONITOR</option>
              <option value="SUSPICIOUS">SUSPICIOUS</option>
              <option value="QUARANTINED">QUARANTINED</option>
              <option value="BLOCKED">BLOCKED</option>
            </select>
            <ChevronDown className="w-[18px] h-[18px] absolute right-2.5 top-2.5 pointer-events-none" style={{ color: 'rgba(254,250,224,0.35)' }} strokeWidth={1.5} />
          </div>
        </div>

        {/* List Content */}
        <div className="flex-grow overflow-y-auto divide-y divide-white/[0.04] max-h-[calc(100vh-20rem)] lg:max-h-[none] scrollbar-thin">
          {loadingList ? (
            <div className="p-8 text-center text-[10px]" style={{ color: 'rgba(254,250,224,0.35)' }}>Querying monitored fleet...</div>
          ) : agents.length === 0 ? (
            <div className="p-8 text-center text-[10px]" style={{ color: 'rgba(254,250,224,0.35)' }}>No agent profiles registered.</div>
          ) : (
            agents.map((agent) => (
              <div
                key={agent.agent_id}
                onClick={() => setSelectedAgentId(agent.agent_id)}
                className={`p-4 cursor-pointer transition flex items-center justify-between border-l-2 ${
                  selectedAgentId === agent.agent_id
                    ? 'bg-white/[0.03] border-[#4361EE] text-[#FEFAE0]'
                    : 'border-transparent hover:bg-white/[0.01]'
                }`}
                style={{
                  color: selectedAgentId === agent.agent_id ? '#FEFAE0' : 'rgba(254,250,224,0.6)'
                }}
              >
                <div className="space-y-1">
                  <span className="font-mono font-bold text-xs block" style={{ color: '#FEFAE0' }}>{agent.agent_id}</span>
                  <div className="flex items-center space-x-2 text-[10px]">
                    <span style={{ color: 'rgba(254,250,224,0.35)' }}>trust: <span className="font-mono">{(agent.trust_score * 100).toFixed(1)}%</span></span>
                    <span style={{ color: 'rgba(254,250,224,0.15)' }}>•</span>
                    {getTrendBadge(agent.trend)}
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <span className={`text-[10px] font-bold font-mono ${getGradeColor(agent.security_grade)}`}>
                    {agent.security_grade}
                  </span>
                  <span className={`px-1.5 py-0.5 text-[8px] font-bold rounded-md uppercase border ${
                    agent.status === 'BLOCKED' || agent.status === 'QUARANTINED'
                      ? 'text-[#ef4444] border-[#ef4444]/20 bg-[#ef4444]/5'
                      : agent.status === 'MONITOR' || agent.status === 'SUSPICIOUS'
                        ? 'text-[#f59e0b] border-[#f59e0b]/20 bg-[#f59e0b]/5'
                        : 'text-[#22c55e] border-[#22c55e]/20 bg-[#22c55e]/5'
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
      <div className="flex-1 flex flex-col rounded-2xl border overflow-hidden min-h-[500px]" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
        {!selectedAgent ? (
          <div className="flex-grow flex flex-col items-center justify-center p-12 text-center" style={{ color: 'rgba(254,250,224,0.35)' }}>
            <Shield className="w-6 h-6 mb-3" style={{ color: 'rgba(254,250,224,0.15)' }} strokeWidth={1.5} />
            <p className="text-[11px]" style={{ color: 'rgba(254,250,224,0.6)' }}>Select an agent profile from the registry to view reputation analysis.</p>
          </div>
        ) : (
          <div className="flex-grow flex flex-col overflow-y-auto max-h-[calc(100vh-10rem)] p-6 space-y-6 scrollbar-thin">
            {/* Profile Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-white/[0.04] pb-5 gap-4">
              <div>
                <div className="flex items-center space-x-3">
                  <span className="text-[10px] uppercase tracking-wider font-bold" style={{ color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>Profile Registry /</span>
                  <h2 className="text-sm font-bold font-mono" style={{ color: '#FEFAE0' }}>{selectedAgent.agent_id}</h2>
                </div>
                <p className="text-[10px] mt-1" style={{ color: 'rgba(254,250,224,0.35)' }}>
                  Last monitored activity logged at: <span className="font-mono">{new Date(selectedAgent.last_updated).toLocaleString()}</span>
                </p>
              </div>
              <div className="flex items-center space-x-3">
                <span className={`px-2 py-0.5 text-[9px] font-bold rounded-md uppercase border ${getStatusBadge(selectedAgent.status)}`} style={{ fontFamily: 'var(--font-display)' }}>
                  {selectedAgent.status}
                </span>
                <div className="px-2.5 py-1 rounded-md border flex items-center space-x-1.5 text-xs" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                  <span style={{ color: 'rgba(254,250,224,0.35)' }}>Security Grade:</span>
                  <span className={`font-bold font-mono ${getGradeColor(selectedAgent.security_grade)}`}>{selectedAgent.security_grade}</span>
                </div>
              </div>
            </div>

            {/* Score Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: 'Composite Trust Score', value: `${(selectedAgent.trust_score * 100).toFixed(1)}%`, desc: 'Reputation baseline', color: '#4CC9F0' },
                { label: 'Behavioral DNA Score', value: selectedAgent.behavior_score.toFixed(3), desc: 'Statistical variance index', color: '#4361EE' },
                { label: 'Policy Adherence Index', value: selectedAgent.policy_score.toFixed(3), desc: 'Rule match coefficient', color: '#2A9D8F' }
              ].map((metric, idx) => (
                <div key={idx} className="card-surface p-4 flex flex-col justify-between" style={{ background: '#0c0c0e' }}>
                  <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>{metric.label}</span>
                  <div className="mt-3 flex items-baseline justify-between">
                    <span className="text-base font-bold font-mono" style={{ color: '#FEFAE0' }}>{metric.value}</span>
                    <span className="text-[9px]" style={{ color: 'rgba(254,250,224,0.35)' }}>{metric.desc}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Request Telemetry Proportion Meter */}
            <div className="space-y-3">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: '#FEFAE0', fontFamily: 'var(--font-display)' }}>Request Telemetry Analysis</h3>
                <p className="text-[10px] mt-0.5" style={{ color: 'rgba(254,250,224,0.35)' }}>Ratio of successful, blocked, and suspicious transactions</p>
              </div>

              {/* Meter bar */}
              {(() => {
                const total = selectedAgent.successful_requests + selectedAgent.blocked_requests + selectedAgent.suspicious_requests;
                const successPct = total > 0 ? (selectedAgent.successful_requests / total) * 100 : 100;
                const blockPct = total > 0 ? (selectedAgent.blocked_requests / total) * 100 : 0;
                const suspPct = total > 0 ? (selectedAgent.suspicious_requests / total) * 100 : 0;

                return (
                  <div className="space-y-4 rounded-xl border p-5" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                    {/* Visual bar */}
                    <div className="w-full h-2.5 rounded-full bg-white/[0.03] flex overflow-hidden border border-white/[0.04] shadow-inner">
                      {total === 0 ? (
                        <div className="w-full h-full bg-white/[0.05]" title="No request telemetry"></div>
                      ) : (
                        <>
                          <div style={{ width: `${successPct}%` }} className="h-full bg-[#22c55e]/80" title="Successful Requests"></div>
                          <div style={{ width: `${suspPct}%` }} className="h-full bg-[#f59e0b]/80" title="Suspicious Requests"></div>
                          <div style={{ width: `${blockPct}%` }} className="h-full bg-[#ef4444]/80" title="Blocked Requests"></div>
                        </>
                      )}
                    </div>
 
                    {/* Telemetry indices */}
                    <div className="grid grid-cols-3 gap-4 text-center text-[10px]">
                      <div className="p-2 border rounded-lg" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
                        <span className="block mb-0.5" style={{ color: 'rgba(254,250,224,0.35)' }}>Successful</span>
                        <span className="font-bold text-xs font-mono" style={{ color: '#22c55e' }}>{selectedAgent.successful_requests}</span>
                        <span className="block mt-0.5 font-mono" style={{ color: 'rgba(254,250,224,0.2)' }}>({successPct.toFixed(1)}%)</span>
                      </div>
                      <div className="p-2 border rounded-lg" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
                        <span className="block mb-0.5" style={{ color: 'rgba(254,250,224,0.35)' }}>Suspicious</span>
                        <span className="font-bold text-xs font-mono" style={{ color: '#f59e0b' }}>{selectedAgent.suspicious_requests}</span>
                        <span className="block mt-0.5 font-mono" style={{ color: 'rgba(254,250,224,0.2)' }}>({suspPct.toFixed(1)}%)</span>
                      </div>
                      <div className="p-2 border rounded-lg" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
                        <span className="block mb-0.5" style={{ color: 'rgba(254,250,224,0.35)' }}>Blocked</span>
                        <span className="font-bold text-xs font-mono" style={{ color: '#ef4444' }}>{selectedAgent.blocked_requests}</span>
                        <span className="block mt-0.5 font-mono" style={{ color: 'rgba(254,250,224,0.2)' }}>({blockPct.toFixed(1)}%)</span>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Related Incidents Feed */}
            <div className="space-y-3">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: '#FEFAE0', fontFamily: 'var(--font-display)' }}>Recent Operational Events</h3>
                <p className="text-[10px] mt-0.5" style={{ color: 'rgba(254,250,224,0.35)' }}>Timeline sessions mapped to this profile</p>
              </div>

              <div className="card-surface overflow-hidden" style={{ background: '#0c0c0e' }}>
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b bg-white/[0.01]" style={{ borderColor: 'rgba(254,250,224,0.08)', color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>
                      <th className="px-4 py-2.5 text-[9px] uppercase font-medium">Session ID</th>
                      <th className="px-4 py-2.5 text-[9px] uppercase font-medium">Enforcement</th>
                      <th className="px-4 py-2.5 text-[9px] uppercase font-medium">Peak Risk</th>
                      <th className="px-4 py-2.5 text-[9px] uppercase font-medium">Timestamp</th>
                      <th className="px-4 py-2.5 text-right font-medium">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04] text-[11px]">
                    {loadingDetails ? (
                      <tr>
                        <td colSpan="5" className="px-4 py-8 text-center" style={{ color: 'rgba(254,250,224,0.35)' }}>
                          Fetching agent session timeline...
                        </td>
                      </tr>
                    ) : agentSessions.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="px-4 py-8 text-center italic" style={{ color: 'rgba(254,250,224,0.35)' }}>
                          No interaction history recorded for this agent profile.
                        </td>
                      </tr>
                    ) : (
                      agentSessions.map((session) => (
                        <tr 
                          key={session.session_id}
                          onClick={() => onNavigateToSession(session.session_id)}
                          className="hover:bg-white/[0.01] transition cursor-pointer group"
                        >
                          <td className="px-4 py-2.5 font-mono" style={{ color: 'rgba(254,250,224,0.6)' }}>
                            {session.session_id.substring(0, 8)}
                          </td>
                          <td className="px-4 py-2.5 font-sans">
                            <span className={`px-1.5 py-0.5 text-[8px] font-semibold rounded-md uppercase border ${
                              session.final_decision === 'BLOCK' || session.final_decision === 'QUARANTINE' 
                                ? 'text-[#ef4444] border-[#ef4444]/20 bg-[#ef4444]/5' 
                                : session.final_decision === 'MONITOR' || session.final_decision === 'REVIEW'
                                  ? 'text-[#f59e0b] border-[#f59e0b]/20 bg-[#f59e0b]/5'
                                  : 'text-[#22c55e] border-[#22c55e]/20 bg-[#22c55e]/5'
                            }`} style={{ fontFamily: 'var(--font-display)' }}>
                              {session.final_decision || 'PENDING'}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 font-mono" style={{ color: '#FEFAE0' }}>
                            {session.peak_risk_score !== null ? session.peak_risk_score.toFixed(3) : '0.000'}
                          </td>
                          <td className="px-4 py-2.5 font-mono" style={{ color: 'rgba(254,250,224,0.35)' }}>
                            {new Date(session.started_at).toLocaleString()}
                          </td>
                          <td className="px-4 py-2.5 text-right font-sans">
                            <span className="text-[10px] group-hover:text-[#4361EE] border border-transparent group-hover:border-[#4361EE]/20 group-hover:bg-[#4361EE]/5 px-2 py-0.5 rounded transition" style={{ color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>
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
