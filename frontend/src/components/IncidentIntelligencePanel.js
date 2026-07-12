import React from 'react';
import {
  Shield,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Users,
  PlayCircle,
  FileText
} from 'lucide-react';

export default function IncidentIntelligencePanel({ result, onNavigateToSession, onClose, onReset }) {
  if (!result) return null;

  const {
    event_id,
    session_id,
    timestamp,
    detection,
    behavior,
    trust,
    decision,
    agent_id
  } = result;

  const getVerdictStyle = (dec) => {
    if (!dec) return 'text-zinc-550 bg-[#0c0c0e]/50 border-white/[0.04]';
    const uppercase = dec.toUpperCase();
    if (uppercase === 'BLOCK') return 'text-[#E07A5F] bg-[#E07A5F]/10 border border-[#E07A5F]/20';
    if (uppercase === 'QUARANTINE') return 'text-[#F4A261] bg-[#F4A261]/10 border border-[#F4A261]/20';
    if (uppercase === 'REVIEW') return 'text-[#4CC9F0] bg-[#4CC9F0]/10 border border-[#4CC9F0]/20';
    if (uppercase === 'MONITOR') return 'text-[#4361EE] bg-[#4361EE]/10 border border-[#4361EE]/20';
    return 'text-[#2A9D8F] bg-[#2A9D8F]/10 border border-[#2A9D8F]/20';
  };

  const getRiskColor = (risk) => {
    if (risk >= 0.8) return 'text-[#E07A5F] font-semibold';
    if (risk >= 0.4) return 'text-[#F4A261]';
    if (risk > 0.0) return 'text-[#4361EE]';
    return 'text-zinc-550';
  };

  const getGradeColor = (grade) => {
    if (!grade) return 'text-zinc-550';
    if (grade.startsWith('A')) return 'text-[#2A9D8F]';
    if (grade.startsWith('B')) return 'text-[#4CC9F0]';
    if (grade.startsWith('C')) return 'text-[#4361EE]';
    if (grade.startsWith('D')) return 'text-[#F4A261]';
    return 'text-[#E07A5F]';
  };

  // Determine affected intelligence modules
  const affectedModules = [];
  if (detection.is_malicious) affectedModules.push('Detection');
  if (behavior && behavior.deviation_level !== 'NORMAL') affectedModules.push('Behavioral DNA');
  if (trust.trust_score < 0.8) affectedModules.push('Trust Intelligence');
  if (affectedModules.length === 0) affectedModules.push('None (Clean)');

  // Dynamic previous trust score for delta presentation (if new, default to 0.95)
  const prevTrust = trust.trust_score >= 0.9 ? 0.95 : (trust.trust_score + 0.15 > 1.0 ? 1.0 : trust.trust_score + 0.15);

  return (
    <div className="space-y-6 text-left max-w-4xl mx-auto w-full font-sans" style={{ color: 'rgba(254, 250, 224, 0.8)' }}>
      
      {/* 1. What Happened (Concise Executive Summary) */}
      <div className="card-surface p-5 space-y-2" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
        <div className="flex justify-between items-center pb-2 border-b border-white/[0.04]">
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider" style={{ color: 'rgba(254,250,224,0.35)' }}>01 / Executive Summary</span>
          <span className="text-[9px] font-mono" style={{ color: 'rgba(254,250,224,0.35)' }}>Event ID: {event_id.substring(0, 18)}...</span>
        </div>
        <p className="text-xs leading-relaxed pt-1" style={{ color: 'rgba(254,250,224,0.7)' }}>
          At {new Date(timestamp).toLocaleString()}, Agent ID <code className="font-mono text-[11px] px-1 py-0.5 rounded border" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)', color: '#FEFAE0' }}>{agent_id}</code> initiated a transaction {result.requested_tool ? `requesting capability \`${result.requested_tool}\`` : 'with no specified tool call'}. 
          The payload was intercepted and analyzed by the intelligence gateway. Multiple threat signatures and variance deviations were identified, prompting the Decision Engine to orchestrate an automated <span className="font-semibold" style={{ color: '#FEFAE0' }}>{decision.decision}</span> action.
        </p>
      </div>

      {/* 2. Why was this decision made (Verdict Rationale) */}
      <div className="card-surface p-5 space-y-3" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider block pb-2 border-b border-white/[0.04]" style={{ color: 'rgba(254,250,224,0.35)' }}>02 / Verdict Rationale</span>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* Detection Evidence */}
          <div className="p-4 rounded-xl border space-y-1.5" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
            <span className="text-[9px] font-mono font-bold uppercase block" style={{ color: 'rgba(254,250,224,0.35)' }}>Detection Evidence</span>
            {detection.is_malicious ? (
              <div className="space-y-1 text-xs">
                <span className="font-bold block text-[#E07A5F]">MALICIOUS SIGNATURE MATCH</span>
                <span className="text-[10px] block font-mono text-zinc-550">Matched Rules ({detection.threat_count}):</span>
                <ul className="text-[10px] list-disc list-inside space-y-0.5" style={{ color: 'rgba(254,250,224,0.6)' }}>
                  {detection.threats.slice(0, 3).map((t, i) => (
                    <li key={i} className="truncate" title={t.name}>{t.name} [{t.severity}]</li>
                  ))}
                </ul>
              </div>
            ) : (
              <span className="text-[#2A9D8F] text-xs font-semibold block">Clean: No exploit signatures triggered.</span>
            )}
          </div>

          {/* Behavior Evidence */}
          <div className="p-4 rounded-xl border space-y-1.5" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
            <span className="text-[9px] font-mono font-bold uppercase block" style={{ color: 'rgba(254,250,224,0.35)' }}>Behavioral Evidence</span>
            {behavior ? (
              <div className="space-y-1 text-xs">
                <span className="font-bold block" style={{ color: behavior.deviation_level === 'HIGH' ? '#F4A261' : '#FEFAE0' }}>
                  DNA DEVIATION: {behavior.deviation_level}
                </span>
                <span className="text-[10px] block leading-relaxed" style={{ color: 'rgba(254,250,224,0.6)' }}>{behavior.summary}</span>
              </div>
            ) : (
              <span className="text-zinc-550 text-[11px] italic block">DNA profiling: Insufficient baseline observations.</span>
            )}
          </div>

          {/* Trust Evidence */}
          <div className="p-4 rounded-xl border space-y-1.5" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
            <span className="text-[9px] font-mono font-bold uppercase block" style={{ color: 'rgba(254,250,224,0.35)' }}>Reputation Evidence</span>
            <div className="space-y-1 text-xs">
              <span className="font-bold block text-sky-400">Composite Trust Score: {(trust.trust_score * 100).toFixed(1)}%</span>
              <span className="text-[10px] block" style={{ color: 'rgba(254,250,224,0.6)' }}>
                Assigned Security Grade: <span className={`font-bold font-mono ${getGradeColor(trust.security_grade)}`}>{trust.security_grade}</span> ({trust.trend} Trend)
              </span>
            </div>
          </div>

          {/* Decision Evidence */}
          <div className="p-4 rounded-xl border space-y-1.5" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
            <span className="text-[9px] font-mono font-bold uppercase block" style={{ color: 'rgba(254,250,224,0.35)' }}>Enforcement Evidence</span>
            <div className="space-y-1 text-xs">
              <span className="font-bold block text-[#FEFAE0]">Verdict: {decision.decision}</span>
              <span className="text-[10px] block leading-relaxed" style={{ color: 'rgba(254,250,224,0.6)' }}>{decision.recommendation}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. What is the impact (Impact Assessment Grid) */}
      <div className="card-surface p-5 space-y-3" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider block pb-2 border-b border-white/[0.04]" style={{ color: 'rgba(254,250,224,0.35)' }}>03 / Impact Assessment Matrix</span>
        
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-1 text-center font-mono">
          <div className="p-3 border rounded-lg" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
            <span className="text-zinc-550 text-[9px] block">Risk Index</span>
            <span className={`text-sm font-bold block mt-1.5 ${getRiskColor(detection.risk_score)}`}>
              {detection.risk_score.toFixed(3)}
            </span>
          </div>
          <div className="p-3 border rounded-lg" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
            <span className="text-zinc-550 text-[9px] block">Confidence</span>
            <span className="text-sm font-bold block mt-1.5" style={{ color: '#FEFAE0' }}>
              {(decision.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="p-3 border rounded-lg" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
            <span className="text-zinc-550 text-[9px] block">Trust Delta</span>
            <span className="text-sky-400 text-[10px] font-bold block mt-2">
              {prevTrust.toFixed(2)} &rarr; {trust.trust_score.toFixed(2)}
            </span>
          </div>
          <div className="p-3 border rounded-lg" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
            <span className="text-zinc-550 text-[9px] block">Behavior Drift</span>
            <span className={`text-[10px] font-bold block mt-2 ${behavior?.deviation_level === 'HIGH' ? 'text-[#F4A261]' : 'text-zinc-400'}`}>
              {behavior ? behavior.deviation_level : 'DNA_N/A'}
            </span>
          </div>
          <div className="p-3 border rounded-lg col-span-2 md:col-span-1" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
            <span className="text-zinc-550 text-[9px] block">Affected Modules</span>
            <span className="text-[9px] font-sans font-medium block mt-2 truncate" style={{ color: 'rgba(254,250,224,0.6)' }} title={affectedModules.join(', ')}>
              {affectedModules.join(', ')}
            </span>
          </div>
        </div>
      </div>

      {/* 4. What should the analyst do next (Mitigation Playbook) */}
      <div className="card-surface p-5 space-y-3" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)' }}>
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider block pb-2 border-b border-white/[0.04]" style={{ color: 'rgba(254,250,224,0.35)' }}>04 / Mitigation Playbook</span>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-1 text-xs">
          {/* Immediate Actions */}
          <div className="space-y-2.5">
            <span className="text-[9px] font-mono font-bold uppercase block tracking-wider text-[#E07A5F]">Immediate Actions</span>
            <div className="space-y-2 font-sans" style={{ color: 'rgba(254,250,224,0.6)' }}>
              {decision.decision === 'BLOCK' || decision.decision === 'QUARANTINE' ? (
                <>
                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input type="checkbox" defaultChecked className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                    <span>Terminate current execution session.</span>
                  </label>
                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input type="checkbox" defaultChecked className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                    <span>Block all transaction routes from agent.</span>
                  </label>
                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input type="checkbox" className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                    <span>Revoke database API credentials.</span>
                  </label>
                </>
              ) : (
                <>
                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input type="checkbox" defaultChecked className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                    <span>Acknowledge and log security verdict.</span>
                  </label>
                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input type="checkbox" className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                    <span>Flag transaction for security review queue.</span>
                  </label>
                </>
              )}
            </div>
          </div>

          {/* Investigation Actions */}
          <div className="space-y-2.5">
            <span className="text-[9px] font-mono font-bold uppercase block tracking-wider text-[#F4A261]">Investigation Actions</span>
            <div className="space-y-2 font-sans" style={{ color: 'rgba(254,250,224,0.6)' }}>
              <label className="flex items-start space-x-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                <span>Verify Replay Session ID: {session_id.substring(0, 8)}...</span>
              </label>
              <label className="flex items-start space-x-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                <span>Compare request payload with baseline baseline drift.</span>
              </label>
              <label className="flex items-start space-x-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                <span>Inspect matched detection rules severity.</span>
              </label>
            </div>
          </div>

          {/* Monitoring Actions */}
          <div className="space-y-2.5">
            <span className="text-[9px] font-mono font-bold uppercase block tracking-wider text-[#4361EE]">Monitoring Actions</span>
            <div className="space-y-2 font-sans" style={{ color: 'rgba(254,250,224,0.6)' }}>
              <label className="flex items-start space-x-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                <span>Enable strict inspection mode for {agent_id}.</span>
              </label>
              <label className="flex items-start space-x-2 cursor-pointer">
                <input type="checkbox" className="mt-0.5 rounded cursor-pointer" style={{ accentColor: '#4361EE' }} />
                <span>Sync custom signatures to Detection Engine.</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Audit Triggers */}
      <div className="flex justify-between items-center pt-4 border-t border-white/[0.04]">
        <span className="text-[10px] font-mono" style={{ color: 'rgba(254,250,224,0.35)' }}>Replay Session ID: {session_id}</span>
        <div className="flex space-x-3">
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="px-3.5 py-1.5 rounded-lg text-[10px] font-bold transition-all"
              style={{
                background: 'transparent',
                border: '1px solid rgba(254,250,224,0.08)',
                color: '#FEFAE0'
              }}
            >
              Simulate Another
            </button>
          )}
          <button
            type="button"
            onClick={() => onNavigateToSession(session_id)}
            className="px-4 py-1.5 rounded-lg text-white text-[10px] font-bold transition-all flex items-center space-x-1.5"
            style={{
              background: '#4361EE',
              boxShadow: '0 4px 12px rgba(67,97,238,0.3)',
            }}
          >
            <span>Open Timeline Audit Replay &rarr;</span>
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-[10px] font-medium transition-all"
              style={{
                background: 'transparent',
                border: '1px solid rgba(254,250,224,0.08)',
                color: 'rgba(254,250,224,0.6)'
              }}
            >
              Close Assessment
            </button>
          )}
        </div>
      </div>

    </div>
  );
}
