import React, { useState, useEffect } from 'react';
import { getReplays, getReplaySession } from '../services/api';

export default function ReplayView({ sessionId, onSelectSessionId }) {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [expandedFrameId, setExpandedFrameId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [error, setError] = useState(null);

  // Load session list on mount/filter/search
  useEffect(() => {
    const fetchList = async () => {
      try {
        setLoadingList(true);
        const params = {};
        if (searchQuery.trim()) params.agent_id = searchQuery.trim();
        if (statusFilter !== 'ALL') params.status = statusFilter;
        
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

  // Load detailed timeline when a session is selected
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
        // Expand the decision frame by default if present
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

  const handleSelectSession = (id) => {
    onSelectSessionId(id);
  };

  const toggleFrame = (frameId) => {
    setExpandedFrameId(expandedFrameId === frameId ? null : frameId);
  };

  const getVerdictStyle = (decision) => {
    if (!decision) return 'text-slate-500 bg-slate-900 border border-slate-800/80';
    const uppercase = decision.toUpperCase();
    if (uppercase === 'BLOCK') return 'text-rose-400 bg-rose-500/10 border border-rose-500/20';
    if (uppercase === 'QUARANTINE') return 'text-orange-400 bg-orange-500/10 border border-orange-500/20';
    if (uppercase === 'REVIEW') return 'text-amber-400 bg-amber-500/10 border border-amber-500/20';
    if (uppercase === 'MONITOR') return 'text-blue-400 bg-blue-500/10 border border-blue-500/20';
    return 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20';
  };

  const getStageDotColor = (stage) => {
    switch (stage) {
      case 'RECEIVED': return 'bg-slate-700 ring-slate-800';
      case 'DETECTED': return 'bg-rose-500 ring-rose-950/40';
      case 'BEHAVIOR_ANALYZED': return 'bg-indigo-500 ring-indigo-950/40';
      case 'TRUST_UPDATED': return 'bg-cyan-500 ring-cyan-950/40';
      case 'DECISION_MADE': return 'bg-violet-500 ring-violet-950/40';
      case 'AUDITED': return 'bg-emerald-500 ring-emerald-950/40';
      default: return 'bg-slate-500 ring-slate-800';
    }
  };

  return (
    <div className="flex-grow flex flex-col lg:flex-row gap-6">
      {/* Left Pane - Incident List */}
      <div className="w-full lg:w-96 flex flex-col bg-[#0b0e17] rounded-xl border border-slate-900 overflow-hidden shadow-sm max-h-[calc(100vh-12rem)]">
        {/* Header & Filters */}
        <div className="p-4 border-b border-slate-900 space-y-3">
          <span className="text-sm font-semibold text-white block">Interception Log</span>
          
          <div className="relative">
            <input
              type="text"
              placeholder="Search by Agent ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-900 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
            />
            <svg className="w-4 h-4 text-slate-500 absolute left-2.5 top-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <div className="flex rounded-md bg-slate-950/40 p-0.5 border border-slate-900 text-[10px]">
            {['ALL', 'COMPLETE', 'FAILED'].map(status => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`flex-1 py-1 rounded text-center font-medium ${
                  statusFilter === status 
                    ? 'bg-slate-900 text-cyan-400 shadow-sm' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        {/* List Content */}
        <div className="flex-grow overflow-y-auto divide-y divide-slate-900/60">
          {loadingList ? (
            <div className="p-8 text-center text-slate-500 font-mono text-xs">Loading incident feed...</div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center text-slate-500 font-mono text-xs">No replay sessions match filters.</div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.session_id}
                onClick={() => handleSelectSession(s.session_id)}
                className={`p-4 cursor-pointer transition text-xs border-l-2 ${
                  sessionId === s.session_id
                    ? 'bg-slate-900/40 border-cyan-500'
                    : 'border-transparent hover:bg-slate-900/10'
                }`}
              >
                <div className="flex justify-between items-center mb-1.5">
                  <span className="font-mono text-slate-400">{s.session_id.substring(0, 8)}...</span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {new Date(s.started_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-200 font-medium truncate max-w-[150px]">{s.agent_id}</span>
                  <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded ${getVerdictStyle(s.final_decision)}`}>
                    {s.final_decision || 'PENDING'}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Pane - Timeline Replay */}
      <div className="flex-1 flex flex-col bg-[#0b0e17] rounded-xl border border-slate-900 overflow-hidden shadow-sm min-h-[500px]">
        {loadingTimeline ? (
          <div className="flex-grow flex items-center justify-center text-slate-500 font-mono text-xs">
            Loading timeline frames...
          </div>
        ) : !activeSession ? (
          <div className="flex-grow flex flex-col items-center justify-center p-12 text-center text-slate-500 font-mono">
            <svg className="w-10 h-10 text-slate-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-xs">Select an incident from the log feed to replay how it traversed the security stack.</p>
          </div>
        ) : (
          <div className="flex-grow flex flex-col overflow-y-auto max-h-[calc(100vh-12rem)]">
            {/* Session Header */}
            <div className="p-5 border-b border-slate-900 bg-[#07090f]/30 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <div className="flex items-center space-x-3">
                  <h2 className="text-sm font-semibold text-white font-mono">INCIDENT-{activeSession.session_id.substring(0, 8).toUpperCase()}</h2>
                  <span className={`px-2 py-0.5 text-[9px] font-bold rounded-full uppercase ${
                    activeSession.status === 'COMPLETE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}>
                    {activeSession.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Agent: <span className="text-slate-200 font-semibold">{activeSession.agent_id}</span> • Original Event ID: <span className="font-mono text-slate-500">{activeSession.event_id}</span>
                </p>
              </div>
              <div className="text-right text-[10px] text-slate-500 font-mono">
                <p>Elapsed Time: <span className="text-slate-300 font-bold">{activeSession.duration_ms?.toFixed(2)} ms</span></p>
                <p className="mt-0.5">Processed: {new Date(activeSession.started_at).toLocaleString()}</p>
              </div>
            </div>

            {/* Overall Summary Alert */}
            {activeSession.overall_summary && (
              <div className="m-5 p-4 bg-slate-950 border border-slate-900 rounded-xl text-xs flex items-start space-x-3 shadow-inner">
                <div className="w-5 h-5 rounded-full bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 flex-shrink-0 text-cyan-400 mt-0.5">!</div>
                <div>
                  <span className="font-semibold text-slate-300 block mb-0.5">Analyst Overview Summary</span>
                  <span className="text-slate-400 leading-relaxed font-mono text-[11px]">{activeSession.overall_summary}</span>
                </div>
              </div>
            )}

            {/* Replay Timeline Component */}
            <div className="p-6 relative flex-grow">
              {/* Vertical connecting line */}
              <div className="absolute left-[33px] top-6 bottom-6 w-0.5 bg-slate-900 z-0"></div>

              <div className="space-y-6 relative z-10">
                {activeSession.frames?.map((frame) => {
                  const isExpanded = expandedFrameId === frame.frame_id;
                  return (
                    <div key={frame.frame_id} className="flex gap-4">
                      {/* Timeline Dot/Icon */}
                      <div className="flex-shrink-0 flex justify-center items-start mt-0.5">
                        <div className={`w-[20px] h-[20px] rounded-full ring-4 flex items-center justify-center ${getStageDotColor(frame.stage)}`}>
                          {/* Inner small dot */}
                          <div className="w-1.5 h-1.5 rounded-full bg-white"></div>
                        </div>
                      </div>

                      {/* Timeline Card */}
                      <div className="flex-1 bg-slate-950/40 border border-slate-900 hover:border-slate-800 rounded-xl transition overflow-hidden">
                        {/* Header */}
                        <div
                          onClick={() => toggleFrame(frame.frame_id)}
                          className="p-4 flex justify-between items-center cursor-pointer select-none"
                        >
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="text-xs font-bold text-white">{frame.title}</span>
                              <span className="text-[9px] text-slate-500 font-mono tracking-wider uppercase">({frame.stage})</span>
                            </div>
                            <p className="text-xs text-slate-400 mt-1 leading-normal">{frame.description}</p>
                          </div>
                          
                          <div className="flex items-center space-x-3">
                            {/* Short score chips */}
                            {frame.risk_score !== null && (
                              <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 bg-slate-900 rounded border border-slate-800/80 ${getRiskColor(frame.risk_score)}`}>
                                Risk: {frame.risk_score.toFixed(2)}
                              </span>
                            )}
                            {frame.trust_score !== null && (
                              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 bg-slate-900 rounded border border-slate-800/80 text-cyan-400">
                                Trust: {frame.trust_score.toFixed(2)}
                              </span>
                            )}
                            {frame.decision && (
                              <span className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded ${getVerdictStyle(frame.decision)}`}>
                                {frame.decision}
                              </span>
                            )}
                            <svg
                              className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </div>

                        {/* Collapsible Content Pane */}
                        {isExpanded && (
                          <div className="p-4 border-t border-slate-900 bg-slate-950/90 text-xs space-y-3 font-mono">
                            <div className="flex justify-between text-slate-500 text-[10px] pb-2 border-b border-slate-900">
                              <span>Source: {frame.engine}</span>
                              <span>Timestamp: {new Date(frame.timestamp).toLocaleTimeString()}</span>
                            </div>

                            {/* Formatted Key-Value Details */}
                            {Object.keys(frame.metadata || {}).length > 0 && (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                                {Object.entries(frame.metadata).map(([key, val]) => (
                                  <div key={key} className="flex justify-between py-1 border-b border-slate-900/40 last:border-0">
                                    <span className="text-slate-500">{key}:</span>
                                    <span className="text-slate-300 max-w-[200px] truncate">
                                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Full RAW JSON payload */}
                            <details className="mt-3">
                              <summary className="text-[10px] text-cyan-500 hover:text-cyan-400 cursor-pointer select-none">
                                View raw engine metadata payload
                              </summary>
                              <pre className="mt-2 p-3 bg-slate-950 border border-slate-900/60 rounded-lg text-[10px] text-slate-400 overflow-x-auto max-h-48">
                                {JSON.stringify(frame.metadata, null, 2)}
                              </pre>
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
