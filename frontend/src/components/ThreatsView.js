import React, { useState, useEffect } from 'react';
import { getReplays } from '../services/api';
import {
  Search,
  Shield,
  ChevronDown,
  RefreshCw,
  AlertTriangle,
  AlertCircle,
  PlayCircle
} from 'lucide-react';

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
    if (risk === null || risk === undefined) return { label: 'LOW', color: 'text-zinc-450 bg-zinc-900 border border-white/[0.04]' };
    if (risk >= 0.8) return { label: 'CRITICAL', color: 'text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20' };
    if (risk >= 0.6) return { label: 'HIGH', color: 'text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20' };
    if (risk >= 0.4) return { label: 'MEDIUM', color: 'text-[#f59e0b] bg-[#f59e0b]/10 border border-[#f59e0b]/20' };
    return { label: 'LOW', color: 'text-[#22c55e] bg-[#22c55e]/10 border border-[#22c55e]/20' };
  };

  const getVerdictStyle = (decision) => {
    if (!decision) return 'text-zinc-550 border border-white/[0.04] bg-white/[0.01]';
    const uppercase = decision.toUpperCase();
    if (uppercase === 'BLOCK' || uppercase === 'QUARANTINE' || uppercase === 'CRITICAL') {
      return 'text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20';
    }
    if (uppercase === 'MONITOR' || uppercase === 'REVIEW' || uppercase.includes('WARNING')) {
      return 'text-[#f59e0b] bg-[#f59e0b]/10 border border-[#f59e0b]/20';
    }
    return 'text-[#22c55e] bg-[#22c55e]/10 border border-[#22c55e]/20';
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
    <div className="space-y-6 flex-grow flex flex-col">
      {/* View Header */}
      <div className="flex justify-between items-center border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight" style={{ color: '#FEFAE0', fontWeight: 600, letterSpacing: '-0.015em' }}>
            Threat Investigation Desk
          </h1>
          <p className="text-sm mt-1" style={{ color: 'rgba(254,250,224,0.6)' }}>
            Audit log of anomalous transactions and agent command bypasses requiring analysis.
          </p>
        </div>
        <button
          onClick={fetchThreats}
          className="px-3.5 py-2 text-xs font-medium rounded-lg transition-all duration-150 hover:bg-white/[0.03] flex items-center gap-1.5"
          style={{
            background: 'transparent',
            border: '1px solid rgba(254,250,224,0.08)',
            color: '#FEFAE0'
          }}
        >
          <RefreshCw className="w-[18px] h-[18px]" strokeWidth={1.5} />
          Re-evaluate Threats
        </button>
      </div>

      {error && (
        <div className="p-4 bg-[#E07A5F]/10 border border-[#E07A5F]/20 rounded-xl text-[#E07A5F] text-xs flex items-center space-x-2.5">
          <AlertCircle className="w-[18px] h-[18px] flex-shrink-0" strokeWidth={1.5} />
          <span>{error}</span>
        </div>
      )}

      {/* Threats Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Identified Threats', value: sessions.length, desc: 'Flagged transactions', color: '#4CC9F0' },
          { label: 'Critical Severity', value: criticalCount, desc: 'Risk score >= 0.80', color: '#E07A5F', highlight: criticalCount > 0 },
          { label: 'Active Blocks', value: blockedCount, desc: 'Enforced blockade rules', color: '#F4A261', highlight: blockedCount > 0 },
          { label: 'Peak Fleet Risk', value: highestRisk.toFixed(3), desc: 'Max interception threat', color: '#2A9D8F' }
        ].map((item, idx) => (
          <div key={idx} className="card-surface p-5 card-surface-hover flex flex-col justify-between">
            <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>{item.label}</span>
            <div className="mt-4 flex items-baseline justify-between">
              <span className={`text-2xl font-bold font-mono tracking-tight ${item.highlight ? 'text-[#E07A5F]' : ''}`} style={{ color: !item.highlight ? '#FEFAE0' : undefined }}>
                {loading ? '...' : item.value}
              </span>
              <span className="text-[9px]" style={{ color: 'rgba(254,250,224,0.35)' }}>{item.desc}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 p-4 rounded-xl border" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Search threats by Agent ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg outline-none border transition-all"
            style={{
              background: '#0c0c0e',
              border: '1px solid rgba(254,250,224,0.08)',
              color: '#FEFAE0',
              fontFamily: 'monospace'
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = '#4361EE'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(67,97,238,0.3)'; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(254,250,224,0.08)'; e.currentTarget.style.boxShadow = 'none'; }}
          />
          <Search className="w-[18px] h-[18px] absolute left-3 top-2.5" style={{ color: 'rgba(254,250,224,0.35)' }} strokeWidth={1.5} />
        </div>

        <div className="flex gap-3">
          <div className="relative">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="pl-3 pr-8 py-2 text-xs rounded-lg outline-none border appearance-none transition-all cursor-pointer font-sans"
              style={{
                background: '#0c0c0e',
                border: '1px solid rgba(254,250,224,0.08)',
                color: '#FEFAE0'
              }}
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical (&gt;= 0.8)</option>
              <option value="HIGH">High (0.6 - 0.8)</option>
              <option value="MEDIUM">Medium (0.4 - 0.6)</option>
              <option value="LOW">Low (&lt; 0.4)</option>
            </select>
            <ChevronDown className="w-[18px] h-[18px] absolute right-2.5 top-2.5 pointer-events-none" style={{ color: 'rgba(254,250,224,0.35)' }} strokeWidth={1.5} />
          </div>

          <div className="relative">
            <select
              value={verdictFilter}
              onChange={(e) => setVerdictFilter(e.target.value)}
              className="pl-3 pr-8 py-2 text-xs rounded-lg outline-none border appearance-none transition-all cursor-pointer font-sans"
              style={{
                background: '#0c0c0e',
                border: '1px solid rgba(254,250,224,0.08)',
                color: '#FEFAE0'
              }}
            >
              <option value="ALL">All Actions</option>
              <option value="BLOCKED">Blocked</option>
              <option value="QUARANTINED">Quarantined</option>
              <option value="REVIEW">Under Review</option>
            </select>
            <ChevronDown className="w-[18px] h-[18px] absolute right-2.5 top-2.5 pointer-events-none" style={{ color: 'rgba(254,250,224,0.35)' }} strokeWidth={1.5} />
          </div>
        </div>
      </div>

      {/* Threats Data Grid */}
      <div className="card-surface overflow-hidden flex-grow">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-border bg-white/[0.01]" style={{ color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>
                <th className="px-5 py-3 text-[10px] uppercase font-medium">Threat ID</th>
                <th className="px-5 py-3 text-[10px] uppercase font-medium">Agent ID</th>
                <th className="px-5 py-3 text-[10px] uppercase font-medium">Severity</th>
                <th className="px-5 py-3 text-[10px] uppercase font-medium">Peak Risk</th>
                <th className="px-5 py-3 text-[10px] uppercase font-medium">Enforcement</th>
                <th className="px-5 py-3 text-[10px] uppercase font-medium">Intercepted At</th>
                <th className="px-5 py-3 text-right font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-[11px]">
              {loading ? (
                <tr>
                  <td colSpan="7" className="px-5 py-12 text-center" style={{ color: 'rgba(254,250,224,0.35)' }}>
                    Querying security engines for threat events...
                  </td>
                </tr>
              ) : filteredSessions.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-5 py-12 text-center italic" style={{ color: 'rgba(254,250,224,0.35)' }}>
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
                      className="hover:bg-white/[0.02] transition cursor-pointer group"
                    >
                      <td className="px-5 py-3 font-mono" style={{ color: 'rgba(254,250,224,0.6)' }}>
                        {session.session_id.substring(0, 8)}
                      </td>
                      <td className="px-5 py-3 font-mono font-medium" style={{ color: '#FEFAE0' }}>
                        {session.agent_id}
                      </td>
                      <td className="px-5 py-3 font-sans">
                        <span className={`px-2.5 py-0.5 text-[9px] font-bold rounded-md uppercase ${severity.color}`} style={{ fontFamily: 'var(--font-display)' }}>
                          {severity.label}
                        </span>
                      </td>
                      <td className="px-5 py-3 font-mono" style={{ color: '#FEFAE0' }}>
                        {session.peak_risk_score !== null ? session.peak_risk_score.toFixed(3) : '0.000'}
                      </td>
                      <td className="px-5 py-3 font-sans">
                        <span className={`px-2 py-0.5 text-[9px] font-semibold rounded-md uppercase ${getVerdictStyle(session.final_decision)}`} style={{ fontFamily: 'var(--font-display)' }}>
                          {session.final_decision || 'PENDING'}
                        </span>
                      </td>
                      <td className="px-5 py-3 font-mono" style={{ color: 'rgba(254,250,224,0.35)' }}>
                        {new Date(session.started_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3 text-right font-sans">
                        <span className="text-[10px] group-hover:text-[#4361EE] border border-transparent group-hover:border-[#4361EE]/20 group-hover:bg-[#4361EE]/5 px-2 py-0.5 rounded transition" style={{ color: 'rgba(254,250,224,0.35)', fontFamily: 'var(--font-display)' }}>
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
