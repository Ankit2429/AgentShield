import React, { useState, useEffect } from 'react';
import { getReplays } from '../services/api';

export default function ThreatsView({ onNavigateToSession }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [verdictFilter, setVerdictFilter] = useState('ALL');
  const [error, setError] = useState(null);

  const fetchThreats = async () => {
    try {
      setLoading(true);
      const params = {};
      if (searchQuery.trim()) {
        params.agent_id = searchQuery.trim();
      }
      const data = await getReplays(params);
      
      // Filter sessions that have a significant risk (>= 0.40) or a restrictive final verdict
      const threatList = (data.sessions || []).filter(s => {
        const hasRisk = s.peak_risk_score !== null && s.peak_risk_score >= 0.4;
        const hasVerdict = s.final_decision && ['BLOCK', 'QUARANTINE', 'REVIEW'].includes(s.final_decision.toUpperCase());
        return hasRisk || hasVerdict;
      });

      setSessions(threatList);
      setError(null);
    } catch (err) {
      console.error('Error fetching threats list:', err);
      setError('Failed to load active security threats registry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchThreats();
  }, [searchQuery]);

  const getSeverity = (risk) => {
    if (risk === null || risk === undefined) return { label: 'LOW', color: 'text-zinc-500 bg-zinc-900 border border-zinc-800/80' };
    if (risk >= 0.8) return { label: 'CRITICAL', color: 'text-rose-400 bg-rose-500/10 border border-rose-500/20' };
    if (risk >= 0.6) return { label: 'HIGH', color: 'text-orange-400 bg-orange-500/10 border border-orange-500/20' };
    if (risk >= 0.4) return { label: 'MEDIUM', color: 'text-amber-400 bg-amber-500/10 border border-amber-500/20' };
    return { label: 'LOW', color: 'text-indigo-400 bg-indigo-500/10 border border-indigo-500/20' };
  };

  const getVerdictStyle = (decision) => {
    if (!decision) return 'text-zinc-500 border border-zinc-900 bg-zinc-950';
    const uppercase = decision.toUpperCase();
    if (uppercase === 'BLOCK') return 'text-rose-400 bg-rose-500/10 border border-rose-500/20';
    if (uppercase === 'QUARANTINE') return 'text-orange-400 bg-orange-500/10 border border-orange-500/20';
    if (uppercase === 'REVIEW') return 'text-amber-400 bg-amber-500/10 border border-amber-500/20';
    return 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20';
  };

  // Filter based on selected UI dropdowns
  const filteredSessions = sessions.filter(s => {
    // Severity filtering
    const risk = s.peak_risk_score || 0;
    if (severityFilter === 'CRITICAL' && risk < 0.8) return false;
    if (severityFilter === 'HIGH' && (risk < 0.6 || risk >= 0.8)) return false;
    if (severityFilter === 'MEDIUM' && (risk < 0.4 || risk >= 0.6)) return false;
    if (severityFilter === 'LOW' && risk >= 0.4) return false;

    // Verdict filtering
    if (verdictFilter !== 'ALL') {
      const decision = s.final_decision ? s.final_decision.toUpperCase() : 'PENDING';
      if (verdictFilter === 'BLOCKED' && decision !== 'BLOCK') return false;
      if (verdictFilter === 'QUARANTINED' && decision !== 'QUARANTINE') return false;
      if (verdictFilter === 'REVIEW' && decision !== 'REVIEW') return false;
    }

    return true;
  });

  // Calculate summary metrics
  const criticalCount = sessions.filter(s => (s.peak_risk_score || 0) >= 0.8).length;
  const blockedCount = sessions.filter(s => s.final_decision?.toUpperCase() === 'BLOCK').length;
  const reviewCount = sessions.filter(s => ['REVIEW', 'QUARANTINE'].includes(s.final_decision?.toUpperCase())).length;
  const highestRisk = sessions.length > 0 ? Math.max(...sessions.map(s => s.peak_risk_score || 0)) : 0;

  return (
    <div className="space-y-8 flex-grow flex flex-col">
      {/* View Header */}
      <div className="flex justify-between items-center border-b border-zinc-900/60 pb-5">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100">Threat Investigation Desk</h1>
          <p className="text-xs text-zinc-400 mt-1">Audit log of anomalous transactions and agent command bypasses requiring analysis.</p>
        </div>
        <button
          onClick={fetchThreats}
          className="px-3 py-1.5 text-xs font-medium bg-zinc-900 border border-zinc-800/80 rounded hover:text-zinc-100 hover:bg-zinc-800/60 transition"
        >
          Re-evaluate Threats
        </button>
      </div>

      {error && (
        <div className="p-3 bg-rose-950/20 border border-rose-900/40 rounded text-rose-400 text-xs flex items-center space-x-2.5">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Threats Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Identified Threats', value: sessions.length, desc: 'Flagged transactions' },
          { label: 'Critical Severity', value: criticalCount, desc: 'Risk score >= 0.80', highlight: criticalCount > 0 },
          { label: 'Active Blocks', value: blockedCount, desc: 'Enforced blockade rules', highlight: blockedCount > 0 },
          { label: 'Peak Fleet Risk', value: highestRisk.toFixed(3), desc: 'Max interception threat' }
        ].map((item, idx) => (
          <div key={idx} className="bg-[#0c0c0e] border border-zinc-900/80 rounded p-4 flex flex-col justify-between hover:border-zinc-850 transition duration-150">
            <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-zinc-500">{item.label}</span>
            <div className="mt-2.5 flex items-baseline justify-between">
              <span className={`text-lg font-bold tracking-tight ${item.highlight ? 'text-rose-400' : 'text-zinc-100'}`}>
                {loading ? '...' : item.value}
              </span>
              <span className="text-[9px] font-mono text-zinc-650">{item.desc}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 p-4 bg-[#0c0c0e] rounded border border-zinc-900/80">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Search threats by Agent ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-zinc-950 border border-zinc-900 rounded text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-800 transition font-mono"
          />
          <svg className="w-4 h-4 text-zinc-650 absolute left-2.5 top-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        <div className="flex gap-3">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 text-xs bg-zinc-950 border border-zinc-900 rounded text-zinc-300 focus:outline-none focus:border-zinc-800 transition font-mono"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical (&gt;= 0.8)</option>
            <option value="HIGH">High (0.6 - 0.8)</option>
            <option value="MEDIUM">Medium (0.4 - 0.6)</option>
            <option value="LOW">Low (&lt; 0.4)</option>
          </select>

          <select
            value={verdictFilter}
            onChange={(e) => setVerdictFilter(e.target.value)}
            className="px-3 py-1.5 text-xs bg-zinc-950 border border-zinc-900 rounded text-zinc-300 focus:outline-none focus:border-zinc-800 transition font-mono"
          >
            <option value="ALL">All Actions</option>
            <option value="BLOCKED">Blocked</option>
            <option value="QUARANTINED">Quarantined</option>
            <option value="REVIEW">Under Review</option>
          </select>
        </div>
      </div>

      {/* Threats Data Grid */}
      <div className="bg-[#0c0c0e] rounded border border-zinc-900/80 overflow-hidden shadow-sm flex-grow">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-zinc-900/80 bg-[#09090b]/40 text-zinc-500 font-medium">
                <th className="px-5 py-3 font-mono text-[10px] uppercase">Threat ID</th>
                <th className="px-5 py-3 font-mono text-[10px] uppercase">Agent ID</th>
                <th className="px-5 py-3 font-mono text-[10px] uppercase">Severity</th>
                <th className="px-5 py-3 font-mono text-[10px] uppercase">Peak Risk</th>
                <th className="px-5 py-3 font-mono text-[10px] uppercase">Enforcement</th>
                <th className="px-5 py-3 font-mono text-[10px] uppercase">Intercepted At</th>
                <th className="px-5 py-3 text-right font-mono text-[10px] uppercase">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900/60 font-mono text-[11px]">
              {loading ? (
                <tr>
                  <td colSpan="7" className="px-5 py-12 text-center text-zinc-500">
                    Querying security engines for threat events...
                  </td>
                </tr>
              ) : filteredSessions.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-5 py-12 text-center text-zinc-500 italic">
                    No matching threat vectors logged. Run simulations to generate threats.
                  </td>
                </tr>
              ) : (
                filteredSessions.map((session) => {
                  const severity = getSeverity(session.peak_risk_score);
                  return (
                    <tr 
                      key={session.session_id}
                      onClick={() => onNavigateToSession(session.session_id)}
                      className="hover:bg-zinc-900/30 transition cursor-pointer group"
                    >
                      <td className="px-5 py-3 text-zinc-400">
                        {session.session_id.substring(0, 8)}
                      </td>
                      <td className="px-5 py-3 text-zinc-200 font-sans font-medium">
                        {session.agent_id}
                      </td>
                      <td className="px-5 py-3">
                        <span className={`px-2 py-0.5 text-[9px] font-mono font-bold rounded uppercase ${severity.color}`}>
                          {severity.label}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-zinc-300">
                        {session.peak_risk_score !== null ? session.peak_risk_score.toFixed(3) : '0.000'}
                      </td>
                      <td className="px-5 py-3 font-sans">
                        <span className={`px-2 py-0.5 text-[9px] font-semibold rounded uppercase ${getVerdictStyle(session.final_decision)}`}>
                          {session.final_decision || 'PENDING'}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-zinc-500">
                        {new Date(session.started_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <span className="text-[10px] text-zinc-400 group-hover:text-indigo-400 border border-transparent group-hover:border-indigo-500/20 group-hover:bg-indigo-500/5 px-2 py-0.5 rounded transition">
                          Triage Incident &rarr;
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
