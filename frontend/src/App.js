import React, { useState, useEffect, useRef } from 'react';
import { getHealth, loginUser, logoutUser, getCurrentUser } from './services/api';
import DashboardView from './components/DashboardView';
import ReplayView from './components/ReplayView';
import AgentsView from './components/AgentsView';
import ThreatsView from './components/ThreatsView';
import SettingsView from './components/SettingsView';
import SandboxView from './components/SandboxView';
import {
  LayoutDashboard,
  ShieldAlert,
  PlayCircle,
  Bot,
  Settings,
  Shield,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  ChevronDown,
  LogOut
} from 'lucide-react';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [healthStatus, setHealthStatus] = useState({ status: 'connecting', version: 'unknown', uptime_seconds: 0 });
  const [selectedSessionId, setSelectedSessionId] = useState(null);

  // Login form state
  const [emailInput, setEmailInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState(null);
  const [loginLoading, setLoginLoading] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // Poll system health
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await getHealth();
        setHealthStatus(data);
      } catch (err) {
        setHealthStatus({ status: 'offline', version: 'unknown', uptime_seconds: 0 });
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // Click outside to close user profile dropdown
  useEffect(() => {
    function handleClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Bootstrap user session and monitor credentials revocation events
  useEffect(() => {
    const handleAuthRequired = () => {
      setCurrentUser(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    };

    window.addEventListener('auth_required', handleAuthRequired);

    const bootstrapSession = async () => {
      const accessToken = localStorage.getItem('access_token');
      if (accessToken) {
        try {
          const user = await getCurrentUser();
          setCurrentUser(user);
        } catch (err) {
          console.warn('[AUTH] Session validation failed on startup. Clearing stale tokens.');
          handleAuthRequired();
        }
      }
      setAuthLoading(false);
    };

    bootstrapSession();

    return () => {
      window.removeEventListener('auth_required', handleAuthRequired);
    };
  }, []);

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError(null);
    setLoginLoading(true);
    try {
      await loginUser(emailInput, passwordInput);
      const user = await getCurrentUser();
      setCurrentUser(user);
      setEmailInput('');
      setPasswordInput('');
    } catch (err) {
      console.error('[AUTH] Login failed:', err);
      let errorMessage = 'Authentication failed. Please verify credentials.';
      const detail = err.response?.data?.detail;
      if (detail) {
        if (Array.isArray(detail)) {
          errorMessage = detail.map(d => d.msg || JSON.stringify(d)).join(', ');
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        } else {
          errorMessage = JSON.stringify(detail);
        }
      }
      setLoginError(errorMessage);
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setActiveTab('dashboard');
  };

  const navigateToSession = (sessionId) => {
    setSelectedSessionId(sessionId);
    setActiveTab('replay');
  };

  const getTabLabel = (id) => {
    switch (id) {
      case 'dashboard': return 'Command Overview';
      case 'threats': return 'Threat Investigation';
      case 'replay': return 'Incident Replay';
      case 'agents': return 'Fleet Status';
      case 'sandbox': return 'Sandbox Simulator';
      case 'settings': return 'System Configuration';
      default: return '';
    }
  };

  // Role-Based Navigation Configuration
  const allTabs = [
    { id: 'dashboard', label: 'Command Overview', minRole: 'Viewer', icon: LayoutDashboard },
    { id: 'threats', label: 'Threat Investigation', minRole: 'Viewer', icon: ShieldAlert },
    { id: 'replay', label: 'Incident Replay', minRole: 'Security Analyst', icon: PlayCircle },
    { id: 'agents', label: 'Fleet Status', minRole: 'Viewer', icon: Bot },
    { id: 'sandbox', label: 'Sandbox Simulator', minRole: 'Security Analyst', icon: ShieldAlert },
    { id: 'settings', label: 'Settings', minRole: 'Admin', icon: Settings }
  ];

  const visibleTabs = allTabs.filter(tab => {
    if (!currentUser) return false;
    const roles = ['Viewer', 'Security Analyst', 'Admin'];
    const userRoleIdx = roles.indexOf(currentUser.role);
    const minRoleIdx = roles.indexOf(tab.minRole);
    return userRoleIdx >= minRoleIdx;
  });

  // Render a clean bootstrap spinner during active validation checks
  if (authLoading) {
    return (
      <div className="min-h-screen text-foreground flex flex-col items-center justify-center font-sans antialiased" style={{ background: '#03045E' }}>
        <div className="w-8 h-8 rounded-full border-2 animate-spin mb-4" style={{ borderColor: 'rgba(254,250,224,0.08)', borderTopColor: '#4361EE' }}></div>
        <p className="text-[10px] font-mono tracking-widest uppercase" style={{ color: 'rgba(254,250,224,0.35)' }}>Validating Security Session...</p>
      </div>
    );
  }

  // Render Auth Login overlay if session context is missing
  if (!currentUser) {
    return (
      <div className="min-h-screen flex" style={{ background: '#03045E' }}>
        {/* Left Panel - Login Form */}
        <div className="w-full lg:w-[45%] flex flex-col justify-center items-center px-8 relative" style={{ background: '#03045E' }}>
          <div className="absolute inset-0 opacity-30" style={{
            background: 'radial-gradient(ellipse at 20% 50%, rgba(67,97,238,0.15) 0%, transparent 70%)'
          }} />

          <div className="relative w-full max-w-[400px]">
            {/* Wordmark (Shield logo removed per requirements) */}
            <div className="flex items-center gap-2.5 mb-1">
              <span className="text-2xl font-bold tracking-tight" style={{ color: '#FEFAE0', fontWeight: 700, letterSpacing: '-0.015em' }}>
                AgentShield
              </span>
            </div>
            <p className="text-sm mb-10" style={{ color: 'rgba(254,250,224,0.6)' }}>
              AI Security Intelligence Platform
            </p>

            {/* Form */}
            <h1 className="text-4xl font-bold tracking-tight" style={{ color: '#FEFAE0', fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1.1 }}>
              Welcome back
            </h1>
            <p className="text-sm mt-2 mb-8" style={{ color: 'rgba(254,250,224,0.6)' }}>
              Sign in to your security operations center
            </p>

            <form onSubmit={handleLoginSubmit} className="space-y-4">
              {loginError && (
                <p className="text-xs" style={{ color: '#E07A5F' }}>{loginError}</p>
              )}

              <div>
                <label className="block text-[11px] font-medium tracking-wide mb-1.5" style={{ color: 'rgba(254,250,224,0.6)', letterSpacing: '0.04em' }}>
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'rgba(254,250,224,0.35)' }} />
                  <input
                    type="email"
                    required
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    placeholder="Enter your email"
                    className="w-full h-11 rounded-lg pl-10 pr-4 text-sm outline-none transition-all duration-150 focus:ring-2"
                    style={{
                      background: '#181D4A',
                      border: '1px solid rgba(254,250,224,0.08)',
                      color: '#FEFAE0',
                      fontSize: '14px',
                    }}
                    onFocus={(e) => { e.currentTarget.style.borderColor = '#4361EE'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(67,97,238,0.3)'; }}
                    onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(254,250,224,0.08)'; e.currentTarget.style.boxShadow = 'none'; }}
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-medium tracking-wide mb-1.5" style={{ color: 'rgba(254,250,224,0.6)', letterSpacing: '0.04em' }}>
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'rgba(254,250,224,0.35)' }} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={passwordInput}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full h-11 rounded-lg pl-10 pr-10 text-sm outline-none transition-all duration-150"
                    style={{
                      background: '#181D4A',
                      border: '1px solid rgba(254,250,224,0.08)',
                      color: '#FEFAE0',
                      fontSize: '14px',
                    }}
                    onFocus={(e) => { e.currentTarget.style.borderColor = '#4361EE'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(67,97,238,0.3)'; }}
                    onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(254,250,224,0.08)'; e.currentTarget.style.boxShadow = 'none'; }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                    style={{ color: 'rgba(254,250,224,0.35)' }}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4 rounded border cursor-pointer"
                    style={{ accentColor: '#4361EE', borderColor: 'rgba(254,250,224,0.08)' }}
                  />
                  <span className="text-[13px]" style={{ color: 'rgba(254,250,224,0.6)' }}>Remember me</span>
                </label>
                <button type="button" className="text-[13px] transition-colors hover:underline" style={{ color: '#4361EE' }}>
                  Forgot password?
                </button>
              </div>

              <button
                type="submit"
                disabled={loginLoading}
                className="w-full h-12 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-all duration-150 hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed mt-4"
                style={{
                  background: '#4361EE',
                  color: '#FFFFFF',
                  boxShadow: '0 4px 12px rgba(67,97,238,0.3)',
                }}
                onMouseEnter={(e) => { if (!loginLoading) e.currentTarget.style.background = '#5A75F0'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = '#4361EE'; }}
              >
                {loginLoading ? (
                  <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          <p className="absolute bottom-6 left-8 text-[11px]" style={{ color: 'rgba(254,250,224,0.35)', letterSpacing: '0.04em' }}>
            &copy; 2026 AgentShield. All rights reserved.
          </p>
        </div>

        {/* Right Panel - Visual */}
        <div className="hidden lg:flex lg:w-[55%] relative items-center justify-center overflow-hidden" style={{ background: '#03045E' }}>
          {/* Animated gradient orbs */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full opacity-20" style={{
              background: 'radial-gradient(circle, #4361EE 0%, transparent 70%)',
              animation: 'pulse-glow 4s ease-in-out infinite',
              filter: 'blur(60px)',
            }} />
            <div className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full opacity-15" style={{
              background: 'radial-gradient(circle, #4CC9F0 0%, transparent 70%)',
              animation: 'pulse-glow 5s ease-in-out infinite 1s',
              filter: 'blur(50px)',
            }} />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-10" style={{
              background: 'radial-gradient(circle, #D4AF37 0%, transparent 70%)',
              animation: 'pulse-glow 6s ease-in-out infinite 2s',
              filter: 'blur(80px)',
            }} />
          </div>

          {/* Central sphere representation */}
          <div className="relative">
            <div className="w-48 h-48 rounded-full relative" style={{
              background: 'radial-gradient(circle at 35% 35%, #C0C0C8, #4a4a5a, #1a1a2e)',
              boxShadow: '0 0 60px rgba(67,97,238,0.2), inset 0 0 40px rgba(255,255,255,0.1)',
              animation: 'pulse-glow 3s ease-in-out infinite',
            }}>
              <div className="absolute inset-4 rounded-full" style={{
                background: 'radial-gradient(circle at 40% 30%, rgba(192,192,200,0.6), transparent 60%)',
              }} />
            </div>
            {/* Orbiting ring */}
            <div className="absolute inset-0 -m-8" style={{
              border: '1px solid rgba(67,97,238,0.15)',
              borderRadius: '50%',
              animation: 'spin-slow 20s linear infinite',
            }}>
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full" style={{ background: '#4361EE', boxShadow: '0 0 8px rgba(67,97,238,0.5)' }} />
            </div>
            <div className="absolute inset-0 -m-16" style={{
              border: '1px solid rgba(76,201,240,0.1)',
              borderRadius: '50%',
              animation: 'spin-slow 30s linear infinite reverse',
            }} />
          </div>

          <p className="absolute bottom-[15%] left-1/2 -translate-x-1/2 text-center text-[11px] font-medium tracking-[0.1em] uppercase whitespace-nowrap" style={{ color: 'rgba(254,250,224,0.25)' }}>
            Protecting AI interactions across enterprise infrastructure
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex font-sans antialiased text-foreground bg-background">
      {/* Sidebar Navigation */}
      <aside className="fixed left-0 top-0 h-screen w-[240px] flex flex-col z-40" style={{ background: '#03045E', borderRight: '1px solid rgba(254,250,224,0.08)' }}>
        {/* Logo */}
        <div className="px-5 pt-6 pb-4">
          <div className="flex items-center gap-2.5">
            <Shield className="w-5 h-5" style={{ color: '#4361EE' }} />
            <span className="text-lg font-bold tracking-tight" style={{ color: '#FEFAE0', fontSize: '18px', fontWeight: 700, letterSpacing: '-0.01em' }}>
              AgentShield
            </span>
          </div>
          <p style={{ color: 'rgba(254,250,224,0.35)', fontSize: '11px', fontWeight: 500, letterSpacing: '0.04em', marginTop: '2px' }}>
            AI Security Intelligence
          </p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto scrollbar-thin">
          {visibleTabs.map((tab) => {
            const isActive = activeTab === tab.id;
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  if (tab.id !== 'replay') setSelectedSessionId(null);
                }}
                className={`flex items-center gap-3 px-3 w-full h-10 rounded-lg transition-all duration-150 text-[13px] font-medium tracking-wide text-left ${
                  isActive ? 'text-[#4361EE]' : 'hover:text-[#FEFAE0]'
                }`}
                style={{
                  background: isActive ? 'rgba(67, 97, 238, 0.12)' : 'transparent',
                  color: isActive ? '#4361EE' : 'rgba(254, 250, 224, 0.6)',
                }}
              >
                <Icon className="w-[18px] h-[18px] flex-shrink-0" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* User Section */}
        <div className="px-3 pb-4 relative" ref={menuRef}>
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg transition-all duration-150 hover:bg-white/[0.03]"
          >
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold" style={{ background: 'rgba(67, 97, 238, 0.2)', color: '#4361EE' }}>
              {currentUser.email ? currentUser.email[0].toUpperCase() : 'U'}
            </div>
            <div className="flex-1 text-left overflow-hidden">
              <p className="text-xs font-medium truncate" style={{ color: '#FEFAE0' }}>{currentUser.email}</p>
            </div>
            <ChevronDown className="w-4 h-4 flex-shrink-0" style={{ color: 'rgba(254,250,224,0.35)' }} />
          </button>

          {userMenuOpen && (
            <div className="absolute bottom-full left-3 right-3 mb-1 rounded-lg overflow-hidden z-50" style={{ background: '#111640', border: '1px solid rgba(254,250,224,0.08)', boxShadow: '0 12px 40px rgba(0,0,0,0.5)' }}>
              <button
                onClick={() => { setActiveTab('settings'); setUserMenuOpen(false); }}
                className="flex items-center gap-2.5 px-3 py-2 text-xs w-full text-left transition-colors hover:bg-white/[0.03]"
                style={{ color: 'rgba(254,250,224,0.6)' }}
              >
                <Settings className="w-4 h-4" /> Settings
              </button>
              <button
                onClick={() => { handleLogout(); setUserMenuOpen(false); }}
                className="flex items-center gap-2.5 px-3 py-2 text-xs w-full text-left transition-colors hover:bg-white/[0.03]"
                style={{ color: '#E07A5F' }}
              >
                <LogOut className="w-4 h-4" /> Sign Out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-grow pl-[240px] flex flex-col min-h-screen relative">
        {/* Top Header */}
        <header className="sticky top-0 h-14 flex items-center justify-between px-6 z-30 border-b border-border" style={{ background: 'rgba(3,4,94,0.8)', backdropFilter: 'blur(12px)' }}>
          <div className="flex items-center space-x-3">
            <span className="text-xs font-mono font-bold tracking-widest uppercase" style={{ color: 'rgba(254, 250, 224, 0.35)' }}>SYS_TAB /</span>
            <h2 className="text-sm font-bold tracking-tight" style={{ color: '#FEFAE0' }}>{getTabLabel(activeTab)}</h2>
          </div>

          <div className="flex items-center space-x-4">
            {/* API Status Indicator */}
            <div className="flex items-center space-x-2 rounded px-2.5 py-1" style={{ background: 'rgba(254,250,224,0.03)', border: '1px solid rgba(254,250,224,0.08)' }}>
              <span className={`inline-block w-1.5 h-1.5 rounded-full ${
                healthStatus.status === 'ok' 
                  ? 'bg-[#2A9D8F]' 
                  : healthStatus.status === 'connecting' 
                    ? 'bg-[#F4A261] animate-pulse' 
                    : 'bg-[#E07A5F]'
              }`}></span>
              <span className="text-[10px] font-mono tracking-tight uppercase" style={{ color: 'rgba(254, 250, 224, 0.6)' }}>
                {healthStatus.status === 'ok' ? 'nominal' : healthStatus.status}
              </span>
            </div>

            {/* User Profile Info Badge */}
            {currentUser && (
              <div className="flex items-center space-x-3 text-xs border-l border-white/10 pl-4">
                <span className="font-mono" style={{ color: 'rgba(254,250,224,0.6)' }}>{currentUser.email}</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide uppercase" style={{ background: 'rgba(67, 97, 238, 0.15)', border: '1px solid rgba(67, 97, 238, 0.25)', color: '#4361EE' }}>
                  {currentUser.role}
                </span>
              </div>
            )}
          </div>
        </header>

        {/* Viewport wrapper */}
        <main className="flex-grow p-6 flex flex-col relative bg-background">
          {activeTab === 'dashboard' && (
            <DashboardView onNavigateToSession={navigateToSession} />
          )}
          {activeTab === 'threats' && (
            <ThreatsView onNavigateToSession={navigateToSession} />
          )}
          {activeTab === 'replay' && (
            <ReplayView sessionId={selectedSessionId} onSelectSessionId={setSelectedSessionId} />
          )}
          {activeTab === 'agents' && (
            <AgentsView onNavigateToSession={navigateToSession} />
          )}
          {activeTab === 'sandbox' && (
            <SandboxView onNavigateToSession={navigateToSession} />
          )}
          {activeTab === 'settings' && (
            <SettingsView />
          )}
        </main>
      </div>
    </div>
  );
}
