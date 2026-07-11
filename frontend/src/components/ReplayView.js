import React, { useState, useEffect } from 'react';
import { getReplays, getReplaySession, subscribeToEvents } from '../services/api';

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
          peak_risk_score: msg.data.detection.risk_score,
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
    if (!decision) return 'text-zinc-500 bg-zinc-900 border border-zinc-800/80';
    const uppercase = decision.toUpperCase();
    if (uppercase === 'BLOCK') return 'text-rose-400 bg-rose-500/10 border border-rose-500/20';
    if (uppercase === 'QUARANTINE') return 'text-orange-400 bg-orange-500/10 border border-orange-500/20';
    if (uppercase === 'REVIEW') return 'text-amber-400 bg-amber-500/10 border border-amber-500/20';
    if (uppercase === 'MONITOR') return 'text-indigo-400 bg-indigo-500/10 border border-indigo-500/20';
    return 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20';
  };

  const getRiskColor = (risk) => {
    if (risk === null || risk === undefined) return 'text-zinc-500';
    if (risk >= 0.8) return 'text-rose-400 font-semibold';
    if (risk >= 0.4) return 'text-amber-400';
    if (risk > 0.0) return 'text-indigo-400';
    return 'text-zinc-500';
  };

  const getStageBadge = (stage) => {
    switch (stage) {
      case 'RECEIVED': return 'bg-zinc-800 border-zinc-700 text-zinc-400';
      case 'DETECTED': return 'bg-rose-500/10 border-rose-500/25 text-rose-400';
      case 'BEHAVIOR_ANALYZED': return 'bg-indigo-500/10 border-indigo-500/25 text-indigo-400';
      case 'TRUST_UPDATED': return 'bg-sky-500/10 border-sky-500/25 text-sky-400';
      case 'DECISION_MADE': return 'bg-violet-500/10 border-violet-500/25 text-violet-400';
      case 'AUDITED': return 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400';
      default: return 'bg-zinc-800 border-zinc-700 text-zinc-400';
    }
  };

  return (
    <div className="flex-grow flex flex-col lg:flex-row gap-8 items-stretch min-h-[calc(100vh-10rem)]">
      {/* Left Pane - Incident Feed Log */}
      <div className="w-full lg:w-80 flex flex-col bg-[#0c0c0e] rounded border border-zinc-900 overflow-hidden flex-shrink-0">
        <div className="p-4 border-b border-zinc-900 space-y-3 bg-[#09090b]/40">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-400 block">Interception Log</span>
          
          <div className="relative">
            <input
              type="text"
              placeholder="Search by Agent ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-zinc-950 border border-zinc-900 rounded text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-zinc-800 transition font-mono"
            />
            <svg className="w-4 h-4 text-zinc-650 absolute left-2.5 top-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <div className="flex rounded p-0.5 bg-zinc-950 border border-zinc-900 text-[9px] font-mono">
            {['ALL', 'COMPLETE', 'FAILED'].map(status => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`flex-1 py-1 rounded text-center font-bold ${
                  statusFilter === status 
                    ? 'bg-zinc-900 text-zinc-200 border border-zinc-800/60' 
                    : 'text-zinc-500 hover:text-zinc-350'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        {/* List Content */}
        <div className="flex-grow overflow-y-auto divide-y divide-zinc-900/60 max-h-[calc(100vh-20rem)] lg:max-h-[none]">
          {loadingList ? (
            <div className="p-8 text-center text-zinc-500 font-mono text-[10px]">Loading session logs...</div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center text-zinc-500 font-mono text-[10px]">No logs matching filters.</div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.session_id}
                onClick={() => onSelectSessionId(s.session_id)}
                className={`p-4 cursor-pointer transition text-xs border-l-2 relative ${
                  sessionId === s.session_id
                    ? 'bg-zinc-900/30 border-indigo-500 text-zinc-100'
                    : 'border-transparent text-zinc-400 hover:bg-zinc-900/10'
                }`}
              >
                <div className="flex justify-between items-center mb-1.5 font-mono text-[10px]">
                  <span className={sessionId === s.session_id ? 'text-zinc-300 font-bold' : 'text-zinc-500'}>
                    {s.session_id.substring(0, 8)}
                  </span>
                  <span className="text-zinc-650">
                    {new Date(s.started_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex justify-between items-center gap-2">
                  <span className="text-zinc-200 font-sans font-medium truncate max-w-[130px]">{s.agent_id}</span>
                  <span className={`px-1.5 py-0.5 text-[8px] font-semibold rounded uppercase border ${getVerdictStyle(s.final_decision)}`}>
                    {s.final_decision || 'PENDING'}
                  </span>
                </div>
                {s.peak_risk_score !== null && s.peak_risk_score >= 0.4 && (
                  <span className="absolute top-4 right-4 w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Pane - Timeline Replay */}
      <div className="flex-1 flex flex-col bg-[#0c0c0e] rounded border border-zinc-900 overflow-hidden min-h-[500px]">
        {loadingTimeline ? (
          <div className="flex-grow flex items-center justify-center text-zinc-500 font-mono text-xs">
            Querying timeline frames...
          </div>
        ) : !activeSession ? (
          <div className="flex-grow flex flex-col items-center justify-center p-12 text-center text-zinc-500 font-mono">
            <svg className="w-8 h-8 text-zinc-700 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-[11px] text-zinc-400">Select an active incident from the interception log to analyze details.</p>
          </div>
        ) : (
          <div className="flex-grow flex flex-col overflow-y-auto max-h-[calc(100vh-10rem)]">
            {/* Session Audit Header */}
            <div className="p-5 border-b border-zinc-900 bg-[#09090b]/40 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider font-bold">Session Audit /</span>
                  <h2 className="text-sm font-bold text-zinc-200 font-mono">{activeSession.session_id.substring(0, 8)}</h2>
                  <span className={`px-2 py-0.5 text-[9px] font-semibold rounded uppercase ${
                    activeSession.status === 'COMPLETE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}>
                    {activeSession.status}
                  </span>
                </div>
                <p className="text-[11px] text-zinc-400 mt-1 font-sans">
                  Target Agent: <span className="text-zinc-200 font-semibold">{activeSession.agent_id}</span>
                  <span className="text-zinc-600 mx-2">•</span>
                  Event ID: <span className="font-mono text-zinc-450 text-[10px]">{activeSession.event_id}</span>
                </p>
              </div>
              <div className="text-right text-[10px] text-zinc-500 font-mono leading-relaxed">
                <p>Telemetry Latency: <span className="text-indigo-400 font-bold">{activeSession.duration_ms?.toFixed(3)} ms</span></p>
                <p className="mt-0.5">Captured: {new Date(activeSession.started_at).toLocaleString()}</p>
              </div>
            </div>

            {/* Analyst Executive Summary Callout */}
            {activeSession.overall_summary && (
              <div className="mx-6 mt-6 p-4 bg-zinc-950 border border-zinc-900/80 rounded text-xs flex items-start space-x-3.5 shadow-inner">
                <div className="w-5 h-5 rounded bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 font-mono font-bold flex-shrink-0 text-[11px] mt-0.5">
                  i
                </div>
                <div>
                  <span className="font-bold text-zinc-300 block mb-1">Analyst Executive Summary</span>
                  <p className="text-zinc-455 leading-relaxed font-sans text-[11px]">{activeSession.overall_summary}</p>
                </div>
              </div>
            )}

            {/* Event Timeline Trace */}
            <div className="p-6 relative flex-grow">
              {/* Timeline Connector Line */}
              <div className="absolute left-[33px] top-6 bottom-6 w-px bg-zinc-900 z-0"></div>

              <div className="space-y-6 relative z-10">
                {activeSession.frames?.map((frame) => {
                  const isExpanded = expandedFrameId === frame.frame_id;
                  return (
                    <div key={frame.frame_id} className="flex gap-4">
                      {/* Timeline Dot */}
                      <div className="flex-shrink-0 flex justify-center items-start mt-1">
                        <div className={`w-[20px] h-[20px] rounded-full border-4 border-[#0c0c0e] ring-1 flex items-center justify-center ${
                          frame.stage === 'DECISION_MADE' ? 'bg-indigo-500 ring-indigo-500/50' : 'bg-zinc-800 ring-zinc-800'
                        }`}>
                          <div className="w-1.5 h-1.5 rounded-full bg-zinc-950"></div>
                        </div>
                      </div>

                      {/* Timeline Frame Card */}
                      <div className="flex-1 bg-zinc-950/40 border border-zinc-900 hover:border-zinc-800/80 rounded transition overflow-hidden">
                        {/* Frame Header */}
                        <div
                          onClick={() => toggleFrame(frame.frame_id)}
                          className="p-4 flex justify-between items-center cursor-pointer select-none"
                        >
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="text-xs font-bold text-zinc-200">{frame.title}</span>
                              <span className={`px-1.5 py-0.5 text-[8px] font-mono font-bold border rounded uppercase ${getStageBadge(frame.stage)}`}>
                                {frame.stage}
                              </span>
                            </div>
                            <p className="text-xs text-zinc-450 mt-1 leading-normal font-sans">{frame.description}</p>
                          </div>
                          
                          <div className="flex items-center space-x-3.5 flex-shrink-0">
                            {/* Score Telemetry Badges */}
                            {frame.risk_score !== null && (
                              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 bg-zinc-900/60 rounded border border-zinc-800/80">
                                risk: <span className={getRiskColor(frame.risk_score)}>{frame.risk_score.toFixed(3)}</span>
                              </span>
                            )}
                            {frame.trust_score !== null && (
                              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 bg-zinc-900/60 rounded border border-zinc-800/80 text-zinc-400">
                                trust: <span className="text-sky-400">{frame.trust_score.toFixed(3)}</span>
                              </span>
                            )}
                            {frame.decision && (
                              <span className={`text-[8px] font-extrabold px-1.5 py-0.5 rounded uppercase border ${getVerdictStyle(frame.decision)}`}>
                                {frame.decision}
                              </span>
                            )}
                            <svg
                              className={`w-3.5 h-3.5 text-zinc-550 transition-transform duration-150 ${isExpanded ? 'rotate-180' : ''}`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </div>

                        {/* Collapsible Details Area */}
                        {isExpanded && (
                          <div className="p-4 border-t border-zinc-900 bg-zinc-950/80 text-xs font-mono space-y-4">
                            <div className="flex justify-between text-zinc-500 text-[10px] pb-2 border-b border-zinc-900/60">
                              <span>Source Module: {frame.engine}</span>
                              <span>Timestamp: {new Date(frame.timestamp).toLocaleTimeString()}</span>
                            </div>

                            {/* Beautiful structured layout for specific stages */}
                            {Object.keys(frame.metadata || {}).length > 0 ? (
                              <div className="space-y-3 font-sans">
                                <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500 block">Inspection Metadata</span>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 bg-[#0c0c0e]/60 border border-zinc-900 p-3 rounded">
                                  {Object.entries(frame.metadata).map(([key, val]) => {
                                    // Skip giant nested objects in table view, they are rendered in JSON details
                                    if (typeof val === 'object' && val !== null) return null;
                                    return (
                                      <div key={key} className="flex justify-between py-1 border-b border-zinc-900/40 last:border-0 text-[11px]">
                                        <span className="text-zinc-500 font-mono text-[10px]">{key}</span>
                                        <span className="text-zinc-300 font-medium truncate max-w-[200px]" title={String(val)}>
                                          {typeof val === 'boolean' ? (val ? 'TRUE' : 'FALSE') : String(val)}
                                        </span>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            ) : null}

                            {/* Threats list (Stage 1 specific formatting) */}
                            {frame.stage === 'DETECTED' && frame.metadata.threats?.length > 0 && (
                              <div className="space-y-2 font-sans pt-1">
                                <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-rose-400 block">Matched Vulnerability Rules</span>
                                <div className="border border-zinc-900 rounded overflow-hidden">
                                  <table className="w-full text-left text-[11px] border-collapse">
                                    <thead>
                                      <tr className="bg-zinc-900/40 text-zinc-500 border-b border-zinc-900">
                                        <th className="px-3 py-1.5 font-mono text-[9px] uppercase">Rule Name</th>
                                        <th className="px-3 py-1.5 font-mono text-[9px] uppercase">Category</th>
                                        <th className="px-3 py-1.5 font-mono text-[9px] uppercase">Severity</th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-zinc-900/60 font-mono">
                                      {frame.metadata.threats.map((threat, idx) => (
                                        <tr key={idx} className="hover:bg-zinc-900/20">
                                          <td className="px-3 py-1.5 text-zinc-300 font-sans">{threat.name}</td>
                                          <td className="px-3 py-1.5 text-zinc-455">{threat.category}</td>
                                          <td className="px-3 py-1.5">
                                            <span className="text-rose-400 font-semibold">{threat.severity}</span>
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
                              <summary className="text-[10px] text-zinc-500 hover:text-indigo-400 cursor-pointer select-none font-mono focus:outline-none">
                                View raw engine metadata payload
                              </summary>
                              <div className="mt-2.5">
                                <pre className="p-3 bg-zinc-950 border border-zinc-900 rounded text-[10px] text-zinc-400 overflow-x-auto max-h-56 font-mono font-medium leading-relaxed">
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
