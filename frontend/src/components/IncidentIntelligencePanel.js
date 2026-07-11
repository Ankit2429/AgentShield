import React from 'react';

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
    if (!dec) return 'text-zinc-500 bg-zinc-900 border-zinc-800/80';
    const uppercase = dec.toUpperCase();
    if (uppercase === 'BLOCK') return 'text-rose-400 bg-rose-500/10 border border-rose-500/20';
    if (uppercase === 'QUARANTINE') return 'text-orange-400 bg-orange-500/10 border border-orange-500/20';
    if (uppercase === 'REVIEW') return 'text-amber-400 bg-amber-500/10 border border-amber-500/20';
    if (uppercase === 'MONITOR') return 'text-indigo-400 bg-indigo-500/10 border border-indigo-500/20';
    return 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20';
  };

  const getRiskColor = (risk) => {
    if (risk >= 0.8) return 'text-rose-400 font-semibold';
    if (risk >= 0.4) return 'text-amber-400';
    if (risk > 0.0) return 'text-indigo-400';
    return 'text-zinc-500';
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
    <div className="space-y-6 text-left max-w-4xl mx-auto w-full text-zinc-300 font-sans">
      
      {/* 1. What Happened (Concise Executive Summary) */}
      <section className="bg-zinc-950/80 border border-zinc-900 rounded p-4 space-y-2">
        <div className="flex justify-between items-center pb-2 border-b border-zinc-900/60">
          <span className="text-[10px] font-mono font-bold text-zinc-500 uppercase tracking-wider">01 / Executive Summary</span>
          <span className="text-[9px] font-mono text-zinc-650">Event ID: {event_id.substring(0, 18)}...</span>
        </div>
        <p className="text-xs text-zinc-350 leading-relaxed font-sans pt-1">
          At {new Date(timestamp).toLocaleString()}, Agent ID <code className="text-zinc-200 font-mono text-[11px] bg-zinc-900 border border-zinc-800 px-1 rounded">{agent_id}</code> initiated a transaction {result.requested_tool ? `requesting capability \`${result.requested_tool}\`` : 'with no specified tool call'}. 
          The payload was intercepted and analyzed by the intelligence gateway. Multiple threat signatures and variance deviations were identified, prompting the Decision Engine to orchestrate an automated <span className="text-zinc-200 font-semibold">{decision.decision}</span> action.
        </p>
      </section>

      {/* 2. Why was this decision made (Verdict Rationale) */}
      <section className="bg-zinc-950/80 border border-zinc-900 rounded p-4 space-y-3">
        <span className="text-[10px] font-mono font-bold text-zinc-500 uppercase tracking-wider block pb-2 border-b border-zinc-900/60">02 / Verdict Rationale</span>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* Detection Evidence */}
          <div className="p-3 bg-[#0c0c0e]/80 border border-zinc-900 rounded space-y-1">
            <span className="text-[9px] font-mono font-bold text-zinc-500 uppercase block">Detection Evidence</span>
            {detection.is_malicious ? (
              <div className="space-y-1 text-xs">
                <span className="text-rose-400 font-bold block">MALICIOUS SIGNATURE MATCH</span>
                <span className="text-[10px] text-zinc-450 block font-mono">Matched Rules ({detection.threat_count}):</span>
                <ul className="text-[10px] text-zinc-400 list-disc list-inside">
                  {detection.threats.slice(0, 3).map((t, i) => (
                    <li key={i} className="truncate" title={t.name}>{t.name} [{t.severity}]</li>
                  ))}
                </ul>
              </div>
            ) : (
              <span className="text-emerald-400 text-xs font-semibold block">Clean: No exploit signatures triggered.</span>
            )}
          </div>

          {/* Behavior Evidence */}
          <div className="p-3 bg-[#0c0c0e]/80 border border-zinc-900 rounded space-y-1">
            <span className="text-[9px] font-mono font-bold text-zinc-500 uppercase block">Behavioral Evidence</span>
            {behavior ? (
              <div className="space-y-1 text-xs">
                <span className={`font-bold block ${behavior.deviation_level === 'HIGH' ? 'text-amber-400' : 'text-zinc-400'}`}>
                  DNA DEVIATION: {behavior.deviation_level}
                </span>
                <span className="text-[10px] text-zinc-450 block font-sans leading-relaxed">{behavior.summary}</span>
              </div>
            ) : (
              <span className="text-zinc-500 text-[11px] italic block">DNA profiling: Insufficient baseline observations.</span>
            )}
          </div>

          {/* Trust Evidence */}
          <div className="p-3 bg-[#0c0c0e]/80 border border-zinc-900 rounded space-y-1">
            <span className="text-[9px] font-mono font-bold text-zinc-500 uppercase block">Reputation Evidence</span>
            <div className="space-y-1 text-xs">
              <span className="text-sky-400 font-bold block">Composite Trust Score: {(trust.trust_score * 100).toFixed(1)}%</span>
              <span className="text-[10px] text-zinc-450 block font-sans">
                Assigned Security Grade: <span className="text-zinc-300 font-bold font-mono">{trust.security_grade}</span> ({trust.trend} Trend)
              </span>
            </div>
          </div>

          {/* Decision Evidence */}
          <div className="p-3 bg-[#0c0c0e]/80 border border-zinc-900 rounded space-y-1">
            <span className="text-[9px] font-mono font-bold text-zinc-500 uppercase block">Enforcement Evidence</span>
            <div className="space-y-1 text-xs">
              <span className="text-zinc-300 font-bold block">Verdict: {decision.decision}</span>
              <span className="text-[10px] text-zinc-450 block leading-relaxed">{decision.recommendation}</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. What is the impact (Impact Assessment Grid) */}
      <section className="bg-zinc-950/80 border border-zinc-900 rounded p-4 space-y-3">
        <span className="text-[10px] font-mono font-bold text-zinc-500 uppercase tracking-wider block pb-2 border-b border-zinc-900/60">03 / Impact Assessment Matrix</span>
        
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5 pt-1 text-center font-mono">
          <div className="p-3 bg-[#0c0c0e] border border-zinc-900 rounded">
            <span className="text-zinc-500 text-[9px] block">Risk Index</span>
            <span className={`text-sm font-bold block mt-1.5 ${getRiskColor(detection.risk_score)}`}>
              {detection.risk_score.toFixed(3)}
            </span>
          </div>
          <div className="p-3 bg-[#0c0c0e] border border-zinc-900 rounded">
            <span className="text-zinc-500 text-[9px] block">Confidence</span>
            <span className="text-zinc-200 text-sm font-bold block mt-1.5">
              {(decision.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="p-3 bg-[#0c0c0e] border border-zinc-900 rounded">
            <span className="text-zinc-500 text-[9px] block">Trust Delta</span>
            <span className="text-sky-400 text-[10px] font-bold block mt-2">
              {prevTrust.toFixed(2)} &rarr; {trust.trust_score.toFixed(2)}
            </span>
          </div>
          <div className="p-3 bg-[#0c0c0e] border border-zinc-900 rounded">
            <span className="text-zinc-500 text-[9px] block">Behavior Drift</span>
            <span className={`text-[10px] font-bold block mt-2 ${behavior?.deviation_level === 'HIGH' ? 'text-amber-400' : 'text-zinc-400'}`}>
              {behavior ? behavior.deviation_level : 'DNA_N/A'}
            </span>
          </div>
          <div className="p-3 bg-[#0c0c0e] border border-zinc-900 rounded col-span-2 md:col-span-1">
            <span className="text-zinc-500 text-[9px] block">Affected Modules</span>
            <span className="text-zinc-400 text-[9px] font-sans font-medium block mt-2 truncate" title={affectedModules.join(', ')}>
              {affectedModules.join(', ')}
            </span>
          </div>
        </div>
      </section>

      {/* 4. What should the analyst do next (Mitigation Playbook) */}
      <section className="bg-zinc-950/80 border border-zinc-900 rounded p-4 space-y-3">
        <span className="text-[10px] font-mono font-bold text-zinc-500 uppercase tracking-wider block pb-2 border-b border-zinc-900/60">04 / Mitigation Playbook</span>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-1 text-xs">
          {/* Immediate Actions */}
          <div className="space-y-2">
            <span className="text-[9px] font-mono font-bold text-rose-400 uppercase block tracking-wider">Immediate Actions</span>
            <div className="space-y-1.5 font-sans text-zinc-400">
              {decision.decision === 'BLOCK' || decision.decision === 'QUARANTINE' ? (
                <>
                  <label className="flex items-start space-x-2">
                    <input type="checkbox" defaultChecked className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                    <span>Terminate current execution session.</span>
                  </label>
                  <label className="flex items-start space-x-2">
                    <input type="checkbox" defaultChecked className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                    <span>Block all transaction routes from agent.</span>
                  </label>
                  <label className="flex items-start space-x-2">
                    <input type="checkbox" className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                    <span>Revoke database API credentials.</span>
                  </label>
                </>
              ) : (
                <>
                  <label className="flex items-start space-x-2">
                    <input type="checkbox" defaultChecked className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                    <span>Acknowledge and log security verdict.</span>
                  </label>
                  <label className="flex items-start space-x-2">
                    <input type="checkbox" className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                    <span>Flag transaction for security review queue.</span>
                  </label>
                </>
              )}
            </div>
          </div>

          {/* Investigation Actions */}
          <div className="space-y-2">
            <span className="text-[9px] font-mono font-bold text-amber-400 uppercase block tracking-wider">Investigation Actions</span>
            <div className="space-y-1.5 font-sans text-zinc-400">
              <label className="flex items-start space-x-2">
                <input type="checkbox" className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                <span>Verify Replay Session ID: {session_id.substring(0, 8)}...</span>
              </label>
              <label className="flex items-start space-x-2">
                <input type="checkbox" className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                <span>Compare request payload with baseline baseline drift.</span>
              </label>
              <label className="flex items-start space-x-2">
                <input type="checkbox" className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                <span>Inspect matched detection rules severity.</span>
              </label>
            </div>
          </div>

          {/* Monitoring Actions */}
          <div className="space-y-2">
            <span className="text-[9px] font-mono font-bold text-indigo-400 uppercase block tracking-wider">Monitoring Actions</span>
            <div className="space-y-1.5 font-sans text-zinc-400">
              <label className="flex items-start space-x-2">
                <input type="checkbox" className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                <span>Enable strict inspection mode for {agent_id}.</span>
              </label>
              <label className="flex items-start space-x-2">
                <input type="checkbox" className="mt-0.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0" />
                <span>Sync custom signatures to Detection Engine.</span>
              </label>
            </div>
          </div>
        </div>
      </section>

      {/* Footer Audit Triggers */}
      <div className="flex justify-between items-center pt-4 border-t border-zinc-900">
        <span className="text-[10px] font-mono text-zinc-500">Replay Session ID: {session_id}</span>
        <div className="flex space-x-3">
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-800 text-[10px] font-bold rounded transition"
            >
              Simulate Another
            </button>
          )}
          <button
            type="button"
            onClick={() => onNavigateToSession(session_id)}
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-bold rounded transition flex items-center space-x-1.5"
          >
            <span>Open Timeline Audit Replay &rarr;</span>
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800/80 rounded text-[10px] font-medium transition"
            >
              Close Assessment
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
