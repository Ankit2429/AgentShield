import React, { useState, useEffect } from 'react';
import { getReplays, getReplaySession, subscribeToEvents } from '../services/api';
import {
  Search,
  Shield,
  PlayCircle,
  Clock,
  ChevronDown,
  CheckCircle,
  AlertTriangle,
  Info,
  Terminal,
  AlertCircle
} from 'lucide-react';

export default function ReplayView({ sessionId, onSelectSessionId }) {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [expandedFrameId, setExpandedFrameId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [error, setError] = useState(null);

  // Load session list
  useEffect(() => {
    const fetchList = async () => {
      try {
        setLoadingList(true);
        const params = {};
        if (searchQuery.trim()) {
          params.agent_id = searchQuery.trim();
        }
        if (statusFilter !== 'ALL') {
          params.status = statusFilter;
        }
        
        const data = await getReplays(params);
        setSessions(data.sessions || []);
      } catch (err) {
        console.error('Error fetching replays list:', err);
        setError('Failed to load incident sessions.');
      } finally {
        setLoadingList(false);
      }
    };
    fetchList();
  }, [searchQuery, statusFilter]);

  // Subscribe to real-time session creations
  useEffect(() => {
    const unsubscribe = subscribeToEvents((msg) => {
      if (msg.type === 'NEW_ANALYSIS') {
        const newSession = {
          session_id: msg.data.session_id,
          agent_id: msg.data.agent_id,
          started_at: msg.data.timestamp,
          final_decision: msg.data.decision.decision,
          peak_risk_score: msg.data.decision.risk_score ?? msg.data.detection.risk_score,
          status: 'COMPLETE'
        };

        const matchSearch = !searchQuery.trim() || newSession.agent_id.toLowerCase().includes(searchQuery.trim().toLowerCase());
        const matchStatus = statusFilter === 'ALL' || (statusFilter === 'COMPLETE' && newSession.final_decision !== 'FAILED') || (statusFilter === 'FAILED' && newSession.final_decision === 'FAILED');
        
        if (matchSearch && matchStatus) {
          setSessions(prev => {
            if (prev.some(s => s.session_id === newSession.session_id)) return prev;
            return [newSession, ...prev];
          });
        }
      }
    });

    return () => unsubscribe();
  }, [searchQuery, statusFilter]);

  // Load detailed timeline when session is selected
  useEffect(() => {
    if (!sessionId) {
      setActiveSession(null);
      return;
    }
    const fetchTimeline = async () => {
      try {
        setLoadingTimeline(true);
        const data = await getReplaySession(sessionId);
        setActiveSession(data);
        
        // Expand the decision frame by default
        const decisionFrame = data.frames?.find(f => f.stage === 'DECISION_MADE');
        if (decisionFrame) {
          setExpandedFrameId(decisionFrame.frame_id);
        } else if (data.frames?.length > 0) {
          setExpandedFrameId(data.frames[0].frame_id);
        }
      } catch (err) {
        console.error('Error fetching session details:', err);
        setError('Failed to load replay timeline.');
      } finally {
        setLoadingTimeline(false);
      }
    };
    fetchTimeline();
  }, [sessionId]);

  const toggleFrame = (frameId) => {
    setExpandedFrameId(expandedFrameId === frameId ? null : frameId);
  };

  const getVerdictStyle = (decision) => {
    if (!decision) return 'text-zinc-550 bg-white/[0.01] border border-white/[0.04]';
    const uppercase = decision.toUpperCase();
    if (uppercase === 'BLOCK' || uppercase === 'QUARANTINE' || uppercase === 'CRITICAL') {
      return 'text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20';
    }
    if (uppercase === 'MONITOR' || uppercase === 'REVIEW' || uppercase.includes('WARNING')) {
      return 'text-[#f59e0b] bg-[#f59e0b]/10 border border-[#f59e0b]/20';
    }
    return 'text-[#22c55e] bg-[#22c55e]/10 border border-[#22c55e]/20';
  };

  const getRiskColor = (risk) => {
    if (risk === null || risk === undefined) return 'text-zinc-550';
    if (risk >= 0.8) return 'text-[#ef4444] font-semibold';
    if (risk >= 0.4) return 'text-[#f59e0b]';
    if (risk > 0.0) return 'text-[#22c55e]';
    return 'text-zinc-550';
  };

  const getStageBadge = (stage) => {
    switch (stage) {
      case 'RECEIVED': return 'bg-white/[0.03] border-white/[0.08] text-zinc-400';
      case 'DETECTED': return 'bg-[#ef4444]/10 border-[#ef4444]/25 text-[#ef4444]';
      case 'BEHAVIOR_ANALYZED': return 'bg-[#f59e0b]/10 border-[#f59e0b]/25 text-[#f59e0b]';
      case 'TRUST_UPDATED': return 'bg-[#4CC9F0]/10 border-[#4CC9F0]/25 text-[#4CC9F0]';
      case 'DECISION_MADE': return 'bg-violet-500/10 border-violet-500/25 text-violet-400';
      case 'AUDITED': return 'bg-[#22c55e]/10 border-[#22c55e]/25 text-[#22c55e]';
      default: return 'bg-white/[0.03] border-white/[0.08] text-zinc-400';
    }
  };

  return (
    <div className="flex-grow flex flex-col lg:flex-row gap-6 items-stretch min-h-[calc(100vh-10rem)]">
      {/* Left Pane - Incident Feed Log */}
      <div className="w-full lg:w-80 flex flex-col rounded-2xl border overflow-hidden flex-shrink-0" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
        <div className="p-4 border-b border-white/[0.04] space-y-3 bg-white/[0.01]">
          <span className="text-xs font-bold uppercase tracking-wider block" style={{ color: '#FEFAE0', fontFamily: 'var(--font-display)' }}>Interception Log</span>
          
          <div className="relative">
            <input
              type="text"
              placeholder="Search by Agent ID..."
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

          <div className="flex rounded-lg p-0.5 border text-[9px]" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)', fontFamily: 'var(--font-display)' }}>
            {['ALL', 'COMPLETE', 'FAILED'].map(status => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className="flex-1 py-1 rounded-md text-center font-bold transition-all"
                style={{
                  background: statusFilter === status ? 'rgba(254,250,224,0.08)' : 'transparent',
                  color: statusFilter === status ? '#FEFAE0' : 'rgba(254,250,224,0.35)',
                  border: statusFilter === status ? '1px solid rgba(254,250,224,0.08)' : '1px solid transparent'
                }}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        {/* List Content */}
        <div className="flex-grow overflow-y-auto divide-y divide-white/[0.04] max-h-[calc(100vh-20rem)] lg:max-h-[none] scrollbar-thin">
          {loadingList ? (
            <div className="p-8 text-center text-[10px]" style={{ color: 'rgba(254,250,224,0.35)' }}>Loading session logs...</div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center text-[10px]" style={{ color: 'rgba(254,250,224,0.35)' }}>No logs matching filters.</div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.session_id}
                onClick={() => onSelectSessionId(s.session_id)}
                className={`p-4 cursor-pointer transition text-xs border-l-2 relative ${
                  sessionId === s.session_id
                    ? 'bg-white/[0.03] border-[#4361EE] text-[#FEFAE0]'
                    : 'border-transparent hover:bg-white/[0.01]'
                }`}
                style={{
                  color: sessionId === s.session_id ? '#FEFAE0' : 'rgba(254,250,224,0.6)'
                }}
              >
                <div className="flex justify-between items-center mb-1.5 text-[10px]">
                  <span className={`font-mono ${sessionId === s.session_id ? 'text-[#FEFAE0] font-bold' : 'text-zinc-550'}`}>
                    {s.session_id.substring(0, 8)}
                  </span>
                  <span className="font-mono" style={{ color: 'rgba(254,250,224,0.35)' }}>
                    {new Date(s.started_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex justify-between items-center gap-2">
                  <span className="font-mono font-medium truncate max-w-[130px]" style={{ color: '#FEFAE0' }}>{s.agent_id}</span>
                  <span className={`px-1.5 py-0.5 text-[8px] font-semibold rounded uppercase border ${getVerdictStyle(s.final_decision)}`} style={{ fontFamily: 'var(--font-display)' }}>
                    {s.final_decision || 'PENDING'}
                  </span>
                </div>
                {s.peak_risk_score !== null && s.peak_risk_score >= 0.4 && (
                  <span className="absolute top-4 right-4 w-1.5 h-1.5 rounded-full bg-[#E07A5F]"></span>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Pane - Timeline Replay */}
      <div className="flex-1 flex flex-col rounded-2xl border overflow-hidden min-h-[500px]" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
        {loadingTimeline ? (
          <div className="flex-grow flex items-center justify-center text-xs" style={{ color: 'rgba(254,250,224,0.35)' }}>
            Querying timeline frames...
          </div>
        ) : !activeSession ? (
          <div className="flex-grow flex flex-col items-center justify-center p-12 text-center" style={{ color: 'rgba(254,250,224,0.35)' }}>
            <PlayCircle className="w-6 h-6 mb-3" style={{ color: 'rgba(254,250,224,0.15)' }} strokeWidth={1.5} />
            <p className="text-[11px]" style={{ color: 'rgba(254,250,224,0.6)' }}>Select an active incident from the interception log to analyze details.</p>
          </div>
        ) : (
          <div className="flex-grow flex flex-col overflow-y-auto max-h-[calc(100vh-10rem)] scrollbar-thin">
            {/* Session Audit Header */}
            <div className="p-5 border-b border-white/[0.04] bg-white/[0.01] flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] uppercase tracking-wider font-bold" style={{ color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>Session Audit /</span>
                  <h2 className="text-sm font-bold font-mono" style={{ color: '#FEFAE0' }}>{activeSession.session_id.substring(0, 8)}</h2>
                  <span className={`px-2 py-0.5 text-[9px] font-semibold rounded uppercase ${
                    activeSession.status === 'COMPLETE' ? 'bg-[#22c55e]/15 text-[#22c55e] border border-[#22c55e]/20' : 'bg-[#ef4444]/15 text-[#ef4444] border border-[#ef4444]/20'
                  }`} style={{ fontFamily: 'var(--font-display)' }}>
                    {activeSession.status}
                  </span>
                </div>
                <p className="text-[11px] mt-1 font-sans" style={{ color: 'rgba(254,250,224,0.6)' }}>
                  Target Agent: <span className="font-semibold font-mono" style={{ color: '#FEFAE0' }}>{activeSession.agent_id}</span>
                  <span className="mx-2" style={{ color: 'rgba(254,250,224,0.15)' }}>•</span>
                  Event ID: <span className="font-mono text-[10px]" style={{ color: 'rgba(254,250,224,0.35)' }}>{activeSession.event_id}</span>
                </p>
              </div>
              <div className="text-right text-[10px] leading-relaxed" style={{ color: 'rgba(254,250,224,0.35)' }}>
                <p>Telemetry Latency: <span className="font-bold font-mono" style={{ color: '#4361EE' }}>{activeSession.duration_ms?.toFixed(3)} ms</span></p>
                <p className="mt-0.5 font-mono">Captured: {new Date(activeSession.started_at).toLocaleString()}</p>
              </div>
            </div>

            {/* Analyst Executive Summary Callout */}
            {activeSession.overall_summary && (
              <div className="mx-6 mt-6 p-4 rounded-xl border flex items-start space-x-3.5" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                <div className="w-5 h-5 rounded flex items-center justify-center font-bold flex-shrink-0 text-[11px] mt-0.5 border" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)', color: 'rgba(254,250,224,0.6)', fontFamily: 'var(--font-display)' }}>
                  i
                </div>
                <div>
                  <span className="font-bold block mb-1 text-xs" style={{ color: '#FEFAE0' }}>Analyst Executive Summary</span>
                  <p className="leading-relaxed font-sans text-[11px]" style={{ color: 'rgba(254,250,224,0.8)' }}>{activeSession.overall_summary}</p>
                </div>
              </div>
            )}

            {/* Event Timeline Trace */}
            <div className="p-6 relative flex-grow">
              {/* Timeline Connector Line */}
              <div className="absolute left-[33px] top-6 bottom-6 w-px z-0" style={{ background: 'rgba(254,250,224,0.08)' }}></div>

              <div className="space-y-6 relative z-10">
                {activeSession.frames?.map((frame) => {
                  const isExpanded = expandedFrameId === frame.frame_id;
                  return (
                    <div key={frame.frame_id} className="flex gap-4">
                      {/* Timeline Dot */}
                      <div className="flex-shrink-0 flex justify-center items-start mt-1">
                        <div className="w-[20px] h-[20px] rounded-full border-4 flex items-center justify-center ring-1" style={{
                          background: frame.stage === 'DECISION_MADE' ? '#4361EE' : '#181D4A',
                          borderColor: '#181D4A',
                          ringColor: frame.stage === 'DECISION_MADE' ? 'rgba(67, 97, 238, 0.3)' : 'rgba(254,250,224,0.04)'
                        }}>
                          <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#0c0c0e' }}></div>
                        </div>
                      </div>

                      {/* Timeline Frame Card */}
                      <div className="flex-1 rounded-xl border overflow-hidden transition-all duration-150" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                        {/* Frame Header */}
                        <div
                          onClick={() => toggleFrame(frame.frame_id)}
                          className="p-4 flex justify-between items-center cursor-pointer select-none"
                        >
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="text-xs font-bold" style={{ color: '#FEFAE0' }}>{frame.title}</span>
                              <span className={`px-1.5 py-0.5 text-[8px] font-mono font-bold border rounded-md uppercase ${getStageBadge(frame.stage)}`}>
                                {frame.stage}
                              </span>
                            </div>
                            <p className="text-xs mt-1 leading-normal font-sans" style={{ color: 'rgba(254,250,224,0.6)' }}>{frame.description}</p>
                          </div>
                          
                          <div className="flex items-center space-x-3.5 flex-shrink-0">
                            {/* Score Telemetry Badges */}
                            {frame.risk_score !== null && (
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md border" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)', color: 'rgba(254,250,224,0.6)' }}>
                                risk: <span className={`font-mono ${getRiskColor(frame.risk_score)}`}>{frame.risk_score.toFixed(3)}</span>
                              </span>
                            )}
                            {frame.trust_score !== null && (
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md border" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)', color: 'rgba(254,250,224,0.6)' }}>
                                trust: <span className="font-mono text-[#4CC9F0]">{frame.trust_score.toFixed(3)}</span>
                              </span>
                            )}
                            {frame.decision && (
                              <span className={`text-[8px] font-extrabold px-1.5 py-0.5 rounded-md uppercase border ${getVerdictStyle(frame.decision)}`} style={{ fontFamily: 'var(--font-display)' }}>
                                {frame.decision}
                              </span>
                            )}
                            <ChevronDown
                              className="w-[18px] h-[18px] transition-transform duration-150"
                              style={{ color: 'rgba(254,250,224,0.35)', transform: isExpanded ? 'rotate(180deg)' : 'none' }}
                              strokeWidth={1.5}
                            />
                          </div>
                        </div>

                        {/* Collapsible Details Area */}
                        {isExpanded && (
                          <div className="p-4 border-t border-white/[0.04] text-xs space-y-4" style={{ background: '#181D4A' }}>
                            <div className="flex justify-between text-[10px] pb-2 border-b border-white/[0.04] font-mono" style={{ color: 'rgba(254,250,224,0.35)' }}>
                              <span>Source Module: {frame.engine}</span>
                              <span>Timestamp: {new Date(frame.timestamp).toLocaleTimeString()}</span>
                            </div>

                            {/* Structured metadata layout */}
                            {Object.keys(frame.metadata || {}).length > 0 ? (
                              <div className="space-y-3 font-sans">
                                <span className="text-[9px] font-bold uppercase tracking-wider block" style={{ color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>Inspection Metadata</span>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 border p-3 rounded-lg" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                                  {Object.entries(frame.metadata).map(([key, val]) => {
                                    if (typeof val === 'object' && val !== null) return null;
                                    return (
                                      <div key={key} className="flex justify-between py-1 border-b border-white/[0.04] last:border-0 text-[11px]">
                                        <span className="font-mono text-[10px]" style={{ color: 'rgba(254,250,224,0.35)' }}>{key}</span>
                                        <span className="font-medium truncate max-w-[200px]" style={{ color: '#FEFAE0' }} title={String(val)}>
                                          {typeof val === 'boolean' ? (val ? 'TRUE' : 'FALSE') : String(val)}
                                        </span>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            ) : null}

                            {/* Threats list */}
                            {frame.stage === 'DETECTED' && frame.metadata.threats?.length > 0 && (
                              <div className="space-y-2 font-sans pt-1">
                                <span className="text-[9px] font-bold uppercase tracking-wider block" style={{ color: '#E07A5F', fontFamily: 'var(--font-display)' }}>Matched Vulnerability Rules</span>
                                <div className="border rounded-lg overflow-hidden" style={{ borderColor: 'rgba(254,250,224,0.08)' }}>
                                  <table className="w-full text-left text-[11px] border-collapse">
                                    <thead>
                                      <tr className="border-b bg-white/[0.01]" style={{ borderColor: 'rgba(254,250,224,0.08)', color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>
                                        <th className="px-3 py-1.5 text-[9px] uppercase font-medium">Rule Name</th>
                                        <th className="px-3 py-1.5 text-[9px] uppercase font-medium">Category</th>
                                        <th className="px-3 py-1.5 text-[9px] uppercase font-medium">Severity</th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/[0.04]">
                                      {frame.metadata.threats.map((threat, idx) => (
                                        <tr key={idx} className="hover:bg-white/[0.01]">
                                          <td className="px-3 py-1.5 font-sans" style={{ color: '#FEFAE0' }}>{threat.name}</td>
                                          <td className="px-3 py-1.5 text-zinc-450">{threat.category}</td>
                                          <td className="px-3 py-1.5">
                                            <span className="font-semibold font-mono" style={{ color: '#E07A5F' }}>{threat.severity}</span>
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}

                            {/* Full RAW JSON payload */}
                            <details className="mt-3 group">
                              <summary className="text-[10px] hover:text-[#4361EE] cursor-pointer select-none font-mono focus:outline-none" style={{ color: 'rgba(254,250,224,0.35)' }}>
                                View raw engine metadata payload
                              </summary>
                              <div className="mt-2.5">
                                <pre className="p-3 border rounded-lg text-[10px] overflow-x-auto max-h-56 font-mono font-medium leading-relaxed" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)', color: 'rgba(254,250,224,0.6)' }}>
                                  {JSON.stringify(frame.metadata, null, 2)}
                                </pre>
                              </div>
                            </details>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
