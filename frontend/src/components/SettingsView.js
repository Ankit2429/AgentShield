import React, { useState, useEffect } from 'react';

export default function SettingsView() {
  const [activeConfigTab, setActiveConfigTab] = useState('detections');
  const [config, setConfig] = useState({
    promptInjectionRule: true,
    dataDisclosureRule: true,
    commandExecRule: true,
    sqlInjectionRule: true,
    detectionSensitivity: 'MEDIUM',
    baselineSessionsLimit: 3,
    driftSensitivity: 0.75,
    criticalDefaultAction: 'BLOCK',
    warningDefaultAction: 'REVIEW',
    webhookUrl: 'https://api.internal.agentshield.net/v1/webhooks/alerts',
    syslogEnabled: false,
    datadogEnabled: false
  });
  const [showApiKey, setShowApiKey] = useState(false);
  const [savedMessage, setSavedMessage] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const local = localStorage.getItem('agentshield_config');
    if (local) {
      try {
        setConfig(JSON.parse(local));
      } catch (e) {
        console.error('Failed to parse config');
      }
    }
  }, []);

  const handleSave = (e) => {
    e.preventDefault();
    localStorage.setItem('agentshield_config', JSON.stringify(config));
    setSavedMessage(true);
    setTimeout(() => setSavedMessage(false), 3000);
  };

  const resetConfig = () => {
    const defaults = {
      promptInjectionRule: true,
      dataDisclosureRule: true,
      commandExecRule: true,
      sqlInjectionRule: true,
      detectionSensitivity: 'MEDIUM',
      baselineSessionsLimit: 3,
      driftSensitivity: 0.75,
      criticalDefaultAction: 'BLOCK',
      warningDefaultAction: 'REVIEW',
      webhookUrl: 'https://api.internal.agentshield.net/v1/webhooks/alerts',
      syslogEnabled: false,
      datadogEnabled: false
    };
    setConfig(defaults);
    localStorage.setItem('agentshield_config', JSON.stringify(defaults));
    setSavedMessage(true);
    setTimeout(() => setSavedMessage(false), 3000);
  };

  return (
    <div className="space-y-8 flex-grow flex flex-col max-w-4xl mx-auto w-full">
      {/* Title Header */}
      <div className="flex justify-between items-center border-b border-zinc-900/60 pb-5">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100">System Configuration</h1>
          <p className="text-xs text-zinc-400 mt-1">Calibrate threat detection thresholds, engine baselines, and webhook responders.</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={resetConfig}
            className="px-3 py-1.5 text-xs font-medium bg-zinc-900 border border-zinc-800/80 rounded hover:text-zinc-100 transition"
          >
            Reset Defaults
          </button>
          <button
            onClick={handleSave}
            className="px-3 py-1.5 text-xs font-medium bg-zinc-100 hover:bg-zinc-200 text-zinc-950 rounded transition shadow-sm"
          >
            Save Changes
          </button>
        </div>
      </div>

      {savedMessage && (
        <div className="p-3 bg-emerald-950/20 border border-emerald-900/40 rounded text-emerald-400 text-xs flex items-center space-x-2.5">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Configuration saved successfully and replicated to the security engine cluster.</span>
        </div>
      )}

      {/* Settings Grid Panel */}
      <div className="bg-[#0c0c0e] rounded border border-zinc-900 overflow-hidden flex flex-col md:flex-row items-stretch min-h-[450px]">
        {/* Navigation Sidebar */}
        <aside className="w-full md:w-56 bg-[#09090b]/40 border-r border-zinc-900 p-4 space-y-1">
          {[
            { id: 'detections', label: 'Detections & Rules' },
            { id: 'dna', label: 'Behavioral DNA' },
            { id: 'actions', label: 'Action Responders' },
            { id: 'integrations', label: 'Integrations & API' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveConfigTab(tab.id)}
              className={`w-full text-left px-3 py-2 text-xs font-medium rounded transition ${
                activeConfigTab === tab.id
                  ? 'bg-zinc-900 text-zinc-100 border border-zinc-800/80 font-semibold'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/30'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </aside>

        {/* Configuration content panel */}
        <form onSubmit={handleSave} className="flex-1 p-6 space-y-6">
          {/* DETECTIONS TAB */}
          {activeConfigTab === 'detections' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-300">Vulnerability Signature Matching</h3>
                <p className="text-[10px] text-zinc-500 mt-0.5">Toggle active protection rules analyzed during Stage 1: Threat Detection</p>
              </div>

              <div className="space-y-4">
                {[
                  { key: 'promptInjectionRule', label: 'Prompt Injection Signatures', desc: 'Detect system override attempts and jailbreak heuristics.' },
                  { key: 'dataDisclosureRule', label: 'Sensitive Data Disclosures', desc: 'Scan agent outputs for private keys, database connections, and credentials.' },
                  { key: 'commandExecRule', label: 'OS Command Exec Inspections', desc: 'Identify shell command substrings (e.g. rm -rf, cat /etc/passwd).' },
                  { key: 'sqlInjectionRule', label: 'Database SQL Injection Checks', desc: 'Match SQL syntax fragments indicating authentication bypass patterns.' }
                ].map(item => (
                  <div key={item.key} className="flex items-start justify-between p-3.5 bg-zinc-950 rounded border border-zinc-900">
                    <div className="space-y-0.5 pr-4">
                      <span className="text-xs font-bold text-zinc-200 block">{item.label}</span>
                      <span className="text-[10px] text-zinc-500 block leading-relaxed">{item.desc}</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer mt-1">
                      <input
                        type="checkbox"
                        checked={config[item.key]}
                        onChange={(e) => setConfig({ ...config, [item.key]: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-7 h-4 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 after:border-zinc-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-indigo-600 peer-checked:after:bg-zinc-100"></div>
                    </label>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-zinc-900 space-y-2">
                <label className="text-[10px] uppercase font-mono font-bold tracking-wider text-zinc-500 block">Detection Sensitivity</label>
                <select
                  value={config.detectionSensitivity}
                  onChange={(e) => setConfig({ ...config, detectionSensitivity: e.target.value })}
                  className="px-3 py-1.5 text-xs bg-zinc-950 border border-zinc-900 rounded text-zinc-300 focus:outline-none focus:border-zinc-800 transition font-mono max-w-xs w-full"
                >
                  <option value="LOW">LOW (Minimize false positives)</option>
                  <option value="MEDIUM">MEDIUM (Balanced heuristics)</option>
                  <option value="HIGH">HIGH (Paranoid strict signature check)</option>
                </select>
              </div>
            </div>
          )}

          {/* DNA TAB */}
          {activeConfigTab === 'dna' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-300">Behavioral DNA Engine Configuration</h3>
                <p className="text-[10px] text-zinc-500 mt-0.5">Adjust Stage 2 baselines for identifying statistical anomalies in fleet communication</p>
              </div>

              <div className="space-y-4">
                <div className="p-4 bg-zinc-950 rounded border border-zinc-900 space-y-2">
                  <label className="text-xs font-bold text-zinc-200 block">Baseline Observation Limit</label>
                  <p className="text-[10px] text-zinc-500 leading-normal mb-3">
                    Minimum number of clean interaction sessions required per agent to establish a baseline profile. 
                    DNA anomalies are skipped until this limit is reached.
                  </p>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={config.baselineSessionsLimit}
                    onChange={(e) => setConfig({ ...config, baselineSessionsLimit: parseInt(e.target.value) || 3 })}
                    className="px-3 py-1.5 text-xs bg-zinc-900 border border-zinc-850 rounded text-zinc-200 focus:outline-none focus:border-zinc-800 transition font-mono w-24"
                  />
                </div>

                <div className="p-4 bg-zinc-950 rounded border border-zinc-900 space-y-2">
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs font-bold text-zinc-200">Behavioral Deviation Drift Sensitivity</label>
                    <span className="text-xs font-mono text-zinc-400 font-bold">{(config.driftSensitivity * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-[10px] text-zinc-500 leading-normal mb-3">
                    Threshold for signaling drift. Lower values detect finer behavioral changes (e.g. stylistic variations) at the risk of higher false alarm rates.
                  </p>
                  <input
                    type="range"
                    min="0.10"
                    max="0.95"
                    step="0.05"
                    value={config.driftSensitivity}
                    onChange={(e) => setConfig({ ...config, driftSensitivity: parseFloat(e.target.value) })}
                    className="w-full accent-indigo-500 bg-zinc-900 h-1 rounded-full cursor-pointer appearance-none"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ACTIONS TAB */}
          {activeConfigTab === 'actions' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-300">Security Action Matrix</h3>
                <p className="text-[10px] text-zinc-500 mt-0.5">Define automated Stage 4 verdict orchestrations based on risk levels</p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-zinc-950 rounded border border-zinc-900">
                  <div className="space-y-0.5 pr-4">
                    <span className="text-xs font-bold text-zinc-200 block">Critical Risk Action</span>
                    <span className="text-[10px] text-zinc-500 block">Verdict applied when cumulative threat score is &gt;= 0.80</span>
                  </div>
                  <select
                    value={config.criticalDefaultAction}
                    onChange={(e) => setConfig({ ...config, criticalDefaultAction: e.target.value })}
                    className="px-3 py-1.5 text-xs bg-zinc-900 border border-zinc-800 rounded text-zinc-350 focus:outline-none focus:border-zinc-700 transition font-mono w-32"
                  >
                    <option value="BLOCK">BLOCK</option>
                    <option value="QUARANTINE">QUARANTINE</option>
                    <option value="REVIEW">REVIEW</option>
                  </select>
                </div>

                <div className="flex items-center justify-between p-4 bg-zinc-950 rounded border border-zinc-900">
                  <div className="space-y-0.5 pr-4">
                    <span className="text-xs font-bold text-zinc-200 block">Warning Risk Action</span>
                    <span className="text-[10px] text-zinc-500 block">Verdict applied when cumulative threat score is 0.40 - 0.80</span>
                  </div>
                  <select
                    value={config.warningDefaultAction}
                    onChange={(e) => setConfig({ ...config, warningDefaultAction: e.target.value })}
                    className="px-3 py-1.5 text-xs bg-zinc-900 border border-zinc-800 rounded text-zinc-350 focus:outline-none focus:border-zinc-700 transition font-mono w-32"
                  >
                    <option value="QUARANTINE">QUARANTINE</option>
                    <option value="REVIEW">REVIEW</option>
                    <option value="MONITOR">MONITOR</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* INTEGRATIONS TAB */}
          {activeConfigTab === 'integrations' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-300">Integrations & API</h3>
                <p className="text-[10px] text-zinc-500 mt-0.5">Export security verdicts to webhook endpoints and syslog receivers</p>
              </div>

              <div className="space-y-4">
                <div className="p-4 bg-zinc-950 rounded border border-zinc-900 space-y-2">
                  <label className="text-xs font-bold text-zinc-200 block">Webhook alert endpoint URL</label>
                  <input
                    type="url"
                    value={config.webhookUrl}
                    onChange={(e) => setConfig({ ...config, webhookUrl: e.target.value })}
                    className="w-full px-3 py-1.5 text-xs bg-zinc-900 border border-zinc-850 rounded text-zinc-200 focus:outline-none focus:border-zinc-800 transition font-mono"
                  />
                </div>

                <div className="flex items-center justify-between p-3.5 bg-zinc-950 rounded border border-zinc-900">
                  <div className="space-y-0.5 pr-4">
                    <span className="text-xs font-bold text-zinc-200 block">Syslog Target Receiver</span>
                    <span className="text-[10px] text-zinc-500 block">Forward security timelines to standard UDP/514 syslog.</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer mt-1">
                    <input
                      type="checkbox"
                      checked={config.syslogEnabled}
                      onChange={(e) => setConfig({ ...config, syslogEnabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-7 h-4 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 after:border-zinc-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-indigo-600 peer-checked:after:bg-zinc-100"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-3.5 bg-zinc-950 rounded border border-zinc-900">
                  <div className="space-y-0.5 pr-4">
                    <span className="text-xs font-bold text-zinc-200 block">Datadog Event Streaming</span>
                    <span className="text-[10px] text-zinc-500 block">Stream intercept logs to Datadog security dashboard.</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer mt-1">
                    <input
                      type="checkbox"
                      checked={config.datadogEnabled}
                      onChange={(e) => setConfig({ ...config, datadogEnabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-7 h-4 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 after:border-zinc-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-indigo-600 peer-checked:after:bg-zinc-100"></div>
                  </label>
                </div>

                {/* API Key Mock Generator */}
                <div className="p-4 bg-zinc-950 rounded border border-zinc-900 space-y-3">
                  <span className="text-xs font-bold text-zinc-200 block">AgentShield API Credentials</span>
                  <p className="text-[10px] text-zinc-500 leading-normal">
                    Generate read-only tokens for backend CLI tools and SDK scripts.
                  </p>
                  
                  <div className="flex items-center space-x-3">
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="px-3 py-1.5 bg-zinc-900 border border-zinc-800 text-[10px] font-bold text-zinc-300 rounded hover:text-zinc-100 transition"
                    >
                      {showApiKey ? 'Hide Token' : 'Reveal API Token'}
                    </button>
                    {showApiKey && (
                      <code className="px-3 py-1.5 bg-[#0c0c0e] border border-zinc-900 rounded text-[10px] text-indigo-400 font-mono flex-1 select-all truncate">
                        as_live_58f98a2e411ba7fc190d64aef810a4e3
                      </code>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
