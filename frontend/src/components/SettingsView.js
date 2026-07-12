import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  CheckCircle2,
  ChevronDown,
  Eye,
  EyeOff,
  Sliders,
  ShieldCheck,
  ToggleLeft,
  Radio,
  Link as LinkIcon
} from 'lucide-react';

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
    if (e) e.preventDefault();
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
    <div className="space-y-6 flex-grow flex flex-col max-w-4xl mx-auto w-full">
      {/* Title Header */}
      <div className="flex justify-between items-center border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight" style={{ color: '#FEFAE0', fontWeight: 600, letterSpacing: '-0.015em' }}>
            System Configuration
          </h1>
          <p className="text-sm mt-1" style={{ color: 'rgba(254,250,224,0.6)' }}>
            Calibrate threat detection thresholds, engine baselines, and webhook responders.
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={resetConfig}
            className="px-3.5 py-2 text-xs font-medium rounded-lg transition-all duration-150 hover:bg-white/[0.03] flex items-center gap-1.5"
            style={{
              background: 'transparent',
              border: '1px solid rgba(254,250,224,0.08)',
              color: '#FEFAE0'
            }}
          >
            Reset Defaults
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-xs font-semibold rounded-lg transition-all duration-150 hover:-translate-y-0.5"
            style={{
              background: '#4361EE',
              color: '#FFFFFF',
              boxShadow: '0 4px 12px rgba(67,97,238,0.3)',
            }}
          >
            Save Changes
          </button>
        </div>
      </div>

      {savedMessage && (
        <div className="p-4 bg-[#2A9D8F]/10 border border-[#2A9D8F]/20 rounded-xl text-[#2A9D8F] text-xs flex items-center space-x-2.5">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>Configuration saved successfully and replicated to the security engine cluster.</span>
        </div>
      )}

      {/* Settings Grid Panel */}
      <div className="card-surface overflow-hidden flex flex-col md:flex-row items-stretch min-h-[450px]">
        {/* Navigation Sidebar */}
        <aside className="w-full md:w-56 bg-white/[0.01] border-r border-border p-4 space-y-1">
          {[
            { id: 'detections', label: 'Detections & Rules', icon: ShieldCheck },
            { id: 'dna', label: 'Behavioral DNA', icon: Sliders },
            { id: 'actions', label: 'Action Responders', icon: Radio },
            { id: 'integrations', label: 'Integrations & API', icon: LinkIcon }
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveConfigTab(tab.id)}
                className={`w-full text-left px-3 py-2 text-xs font-medium rounded-lg transition-all duration-150 flex items-center gap-2 ${
                  activeConfigTab === tab.id
                    ? 'text-[#4361EE]'
                    : 'text-rgba(254,250,224,0.6) hover:text-[#FEFAE0]'
                }`}
                style={{
                  background: activeConfigTab === tab.id ? 'rgba(67, 97, 238, 0.12)' : 'transparent',
                  color: activeConfigTab === tab.id ? '#4361EE' : 'rgba(254, 250, 224, 0.6)',
                }}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </aside>

        {/* Configuration content panel */}
        <form onSubmit={handleSave} className="flex-1 p-6 space-y-6">
          {/* DETECTIONS TAB */}
          {activeConfigTab === 'detections' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider" style={{ color: '#FEFAE0' }}>Vulnerability Signature Matching</h3>
                <p className="text-[10px] mt-0.5" style={{ color: 'rgba(254,250,224,0.35)' }}>Toggle active protection rules analyzed during Stage 1: Threat Detection</p>
              </div>

              <div className="space-y-4">
                {[
                  { key: 'promptInjectionRule', label: 'Prompt Injection Signatures', desc: 'Detect system override attempts and jailbreak heuristics.' },
                  { key: 'dataDisclosureRule', label: 'Sensitive Data Disclosures', desc: 'Scan agent outputs for private keys, database connections, and credentials.' },
                  { key: 'commandExecRule', label: 'OS Command Exec Inspections', desc: 'Identify shell command substrings (e.g. rm -rf, cat /etc/passwd).' },
                  { key: 'sqlInjectionRule', label: 'Database SQL Injection Checks', desc: 'Match SQL syntax fragments indicating authentication bypass patterns.' }
                ].map(item => (
                  <div key={item.key} className="flex items-start justify-between p-4 rounded-xl border" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                    <div className="space-y-0.5 pr-4">
                      <span className="text-xs font-bold block" style={{ color: '#FEFAE0' }}>{item.label}</span>
                      <span className="text-[10px] block leading-relaxed" style={{ color: 'rgba(254,250,224,0.6)' }}>{item.desc}</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer mt-1">
                      <input
                        type="checkbox"
                        checked={config[item.key]}
                        onChange={(e) => setConfig({ ...config, [item.key]: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-7 h-4 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 after:border-zinc-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-[#4361EE] peer-checked:after:bg-[#FEFAE0]"></div>
                    </label>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-white/[0.04] space-y-2">
                <label className="text-[10px] uppercase font-mono font-bold tracking-wider block" style={{ color: 'rgba(254,250,224,0.35)' }}>Detection Sensitivity</label>
                <div className="relative max-w-xs w-full">
                  <select
                    value={config.detectionSensitivity}
                    onChange={(e) => setConfig({ ...config, detectionSensitivity: e.target.value })}
                    className="w-full pl-3 pr-8 py-2 text-xs rounded-lg outline-none border appearance-none transition-all cursor-pointer font-mono"
                    style={{
                      background: '#0c0c0e',
                      border: '1px solid rgba(254,250,224,0.08)',
                      color: '#FEFAE0'
                    }}
                  >
                    <option value="LOW">LOW (Minimize false positives)</option>
                    <option value="MEDIUM">MEDIUM (Balanced heuristics)</option>
                    <option value="HIGH">HIGH (Paranoid strict signature check)</option>
                  </select>
                  <ChevronDown className="w-4 h-4 absolute right-2.5 top-2.5 pointer-events-none" style={{ color: 'rgba(254,250,224,0.35)' }} />
                </div>
              </div>
            </div>
          )}

          {/* DNA TAB */}
          {activeConfigTab === 'dna' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider" style={{ color: '#FEFAE0' }}>Behavioral DNA Engine Configuration</h3>
                <p className="text-[10px] mt-0.5" style={{ color: 'rgba(254,250,224,0.35)' }}>Adjust Stage 2 baselines for identifying statistical anomalies in fleet communication</p>
              </div>

              <div className="space-y-4">
                <div className="p-4 rounded-xl border space-y-2" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                  <label className="text-xs font-bold block" style={{ color: '#FEFAE0' }}>Baseline Observation Limit</label>
                  <p className="text-[10px] leading-normal mb-3" style={{ color: 'rgba(254,250,224,0.6)' }}>
                    Minimum number of clean interaction sessions required per agent to establish a baseline profile. 
                    DNA anomalies are skipped until this limit is reached.
                  </p>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={config.baselineSessionsLimit}
                    onChange={(e) => setConfig({ ...config, baselineSessionsLimit: parseInt(e.target.value) || 3 })}
                    className="px-3 py-2 text-xs rounded-lg outline-none border transition-all font-mono w-24"
                    style={{
                      background: '#181D4A',
                      border: '1px solid rgba(254,250,224,0.08)',
                      color: '#FEFAE0'
                    }}
                    onFocus={(e) => { e.currentTarget.style.borderColor = '#4361EE'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(67,97,238,0.3)'; }}
                    onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(254,250,224,0.08)'; e.currentTarget.style.boxShadow = 'none'; }}
                  />
                </div>

                <div className="p-4 rounded-xl border space-y-2" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs font-bold block" style={{ color: '#FEFAE0' }}>Behavioral Deviation Drift Sensitivity</label>
                    <span className="text-xs font-mono font-bold" style={{ color: '#4CC9F0' }}>{(config.driftSensitivity * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-[10px] leading-normal mb-3" style={{ color: 'rgba(254,250,224,0.6)' }}>
                    Threshold for signaling drift. Lower values detect finer behavioral changes (e.g. stylistic variations) at the risk of higher false alarm rates.
                  </p>
                  <input
                    type="range"
                    min="0.10"
                    max="0.95"
                    step="0.05"
                    value={config.driftSensitivity}
                    onChange={(e) => setConfig({ ...config, driftSensitivity: parseFloat(e.target.value) })}
                    className="w-full accent-[#4361EE] h-1 rounded-full cursor-pointer appearance-none bg-white/[0.08]"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ACTIONS TAB */}
          {activeConfigTab === 'actions' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider" style={{ color: '#FEFAE0' }}>Security Action Matrix</h3>
                <p className="text-[10px] mt-0.5" style={{ color: 'rgba(254,250,224,0.35)' }}>Define automated Stage 4 verdict orchestrations based on risk levels</p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-xl border" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                  <div className="space-y-0.5 pr-4">
                    <span className="text-xs font-bold block" style={{ color: '#FEFAE0' }}>Critical Risk Action</span>
                    <span className="text-[10px]" style={{ color: 'rgba(254,250,224,0.6)' }}>Verdict applied when cumulative threat score is &gt;= 0.80</span>
                  </div>
                  <div className="relative">
                    <select
                      value={config.criticalDefaultAction}
                      onChange={(e) => setConfig({ ...config, criticalDefaultAction: e.target.value })}
                      className="pl-3 pr-8 py-2 text-xs rounded-lg outline-none border appearance-none transition-all cursor-pointer font-mono w-32"
                      style={{
                        background: '#181D4A',
                        border: '1px solid rgba(254,250,224,0.08)',
                        color: '#FEFAE0'
                      }}
                    >
                      <option value="BLOCK">BLOCK</option>
                      <option value="QUARANTINE">QUARANTINE</option>
                      <option value="REVIEW">REVIEW</option>
                    </select>
                    <ChevronDown className="w-4 h-4 absolute right-2.5 top-2.5 pointer-events-none" style={{ color: 'rgba(254,250,224,0.35)' }} />
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 rounded-xl border" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                  <div className="space-y-0.5 pr-4">
                    <span className="text-xs font-bold block" style={{ color: '#FEFAE0' }}>Warning Risk Action</span>
                    <span className="text-[10px]" style={{ color: 'rgba(254,250,224,0.6)' }}>Verdict applied when cumulative threat score is 0.40 - 0.80</span>
                  </div>
                  <div className="relative">
                    <select
                      value={config.warningDefaultAction}
                      onChange={(e) => setConfig({ ...config, warningDefaultAction: e.target.value })}
                      className="pl-3 pr-8 py-2 text-xs rounded-lg outline-none border appearance-none transition-all cursor-pointer font-mono w-36"
                      style={{
                        background: '#181D4A',
                        border: '1px solid rgba(254,250,224,0.08)',
                        color: '#FEFAE0'
                      }}
                    >
                      <option value="QUARANTINE">QUARANTINE</option>
                      <option value="REVIEW">REVIEW</option>
                      <option value="MONITOR">MONITOR</option>
                    </select>
                    <ChevronDown className="w-4 h-4 absolute right-2.5 top-2.5 pointer-events-none" style={{ color: 'rgba(254,250,224,0.35)' }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* INTEGRATIONS TAB */}
          {activeConfigTab === 'integrations' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider" style={{ color: '#FEFAE0' }}>Integrations & API</h3>
                <p className="text-[10px] mt-0.5" style={{ color: 'rgba(254,250,224,0.35)' }}>Export security verdicts to webhook endpoints and syslog receivers</p>
              </div>

              <div className="space-y-4">
                <div className="p-4 rounded-xl border space-y-2" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                  <label className="text-xs font-bold block" style={{ color: '#FEFAE0' }}>Webhook alert endpoint URL</label>
                  <input
                    type="url"
                    value={config.webhookUrl}
                    onChange={(e) => setConfig({ ...config, webhookUrl: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-lg outline-none border transition-all font-mono"
                    style={{
                      background: '#181D4A',
                      border: '1px solid rgba(254,250,224,0.08)',
                      color: '#FEFAE0'
                    }}
                    onFocus={(e) => { e.currentTarget.style.borderColor = '#4361EE'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(67,97,238,0.3)'; }}
                    onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(254,250,224,0.08)'; e.currentTarget.style.boxShadow = 'none'; }}
                  />
                </div>

                <div className="flex items-center justify-between p-4 rounded-xl border" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                  <div className="space-y-0.5 pr-4">
                    <span className="text-xs font-bold block" style={{ color: '#FEFAE0' }}>Syslog Target Receiver</span>
                    <span className="text-[10px]" style={{ color: 'rgba(254,250,224,0.6)' }}>Forward security timelines to standard UDP/514 syslog.</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer mt-1">
                    <input
                      type="checkbox"
                      checked={config.syslogEnabled}
                      onChange={(e) => setConfig({ ...config, syslogEnabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-7 h-4 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 after:border-zinc-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-[#4361EE] peer-checked:after:bg-[#FEFAE0]"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 rounded-xl border" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                  <div className="space-y-0.5 pr-4">
                    <span className="text-xs font-bold block" style={{ color: '#FEFAE0' }}>Datadog Event Streaming</span>
                    <span className="text-[10px]" style={{ color: 'rgba(254,250,224,0.6)' }}>Stream intercept logs to Datadog security dashboard.</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer mt-1">
                    <input
                      type="checkbox"
                      checked={config.datadogEnabled}
                      onChange={(e) => setConfig({ ...config, datadogEnabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-7 h-4 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 after:border-zinc-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-[#4361EE] peer-checked:after:bg-[#FEFAE0]"></div>
                  </label>
                </div>

                {/* API Key Mock Generator */}
                <div className="p-4 rounded-xl border space-y-3" style={{ background: '#0c0c0e', borderColor: 'rgba(254,250,224,0.08)' }}>
                  <span className="text-xs font-bold block" style={{ color: '#FEFAE0' }}>AgentShield API Credentials</span>
                  <p className="text-[10px] leading-normal" style={{ color: 'rgba(254,250,224,0.6)' }}>
                    Generate read-only tokens for backend CLI tools and SDK scripts.
                  </p>
                  
                  <div className="flex items-center space-x-3">
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="px-3.5 py-2 rounded-lg transition-all duration-150 hover:bg-white/[0.03] text-xs font-medium"
                      style={{
                        background: 'transparent',
                        border: '1px solid rgba(254,250,224,0.08)',
                        color: '#FEFAE0'
                      }}
                    >
                      {showApiKey ? 'Hide Token' : 'Reveal API Token'}
                    </button>
                    {showApiKey && (
                      <code className="px-3 py-2 border rounded-lg text-[10px] font-mono flex-1 select-all truncate" style={{ background: '#181D4A', borderColor: 'rgba(254,250,224,0.08)', color: '#4CC9F0' }}>
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
