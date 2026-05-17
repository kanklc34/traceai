import { Activity, AlertTriangle, Database, Play, Shield, Zap, Wifi, WifiOff } from 'lucide-react';
import { useIncident } from './hooks/useIncident';
import { AgentStepFeed } from './components/AgentStepFeed';
import { RCAPanel } from './components/RCAPanel';
import { LiveMetrics } from './components/LiveMetrics';
import { LiveTraceFeed } from './components/LiveTraceFeed';
import { LatencyChart } from './components/LatencyChart';
import { IncidentTimeline } from './components/IncidentTimeline';

const TraceLogo = () => (
  <svg width="32" height="32" viewBox="0 0 32 32" fill="none" className="drop-shadow-[0_0_12px_rgba(99,102,241,0.6)]">
    <circle cx="16" cy="16" r="14" stroke="#6366f1" strokeWidth="2" strokeDasharray="4 4" className="animate-spin" style={{ animationDuration: '8s' }} />
    <circle cx="16" cy="16" r="8" stroke="#818cf8" strokeWidth="2" />
    <circle cx="16" cy="16" r="3" fill="#6366f1" />
  </svg>
);

function App() {
  const {
    incident,
    status,
    traces,
    triggerSpike,
    triggering,
    connected,
    highlightIds,
    analyzing,
    errorRate,
  } = useIncident();

  const report = incident?.report ?? null;
  const steps = incident?.steps ?? [];
  const focusService = report?.service ?? (analyzing ? 'payment-service' : undefined);

  return (
    <div className="min-h-screen bg-[#060a12] text-slate-200 bg-grid">
      {/* Ambient glow */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-indigo-600/10 blur-[120px] pointer-events-none" />
      {analyzing && (
        <div className="fixed top-20 right-10 w-[200px] h-[200px] bg-red-600/10 blur-[80px] pointer-events-none animate-pulse" />
      )}

      <header className="relative border-b border-slate-800/60 bg-[#060a12]/80 backdrop-blur-xl sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <TraceLogo />
            <div>
              <h1 className="text-lg font-black tracking-tight">
                Trace<span className="text-indigo-400">AI</span>
                <span className="text-slate-600 font-normal text-sm ml-2">Live</span>
              </h1>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest">
                Gemma 4 · Rural Health Network
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <div
              className={`hidden sm:flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-bold uppercase ${
                connected ? 'text-emerald-500' : 'text-red-400'
              }`}
            >
              {connected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {connected ? 'API Live' : 'Offline'}
            </div>

            <button
              onClick={triggerSpike}
              disabled={triggering || analyzing || !connected}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-bold shadow-lg shadow-red-900/30 transition-all active:scale-95"
            >
              <Play className="w-4 h-4 fill-current" />
              {triggering ? 'Injecting...' : analyzing ? 'Investigating...' : 'Trigger Incident'}
            </button>

            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-[10px] font-bold uppercase ${
                analyzing
                  ? 'border-indigo-500/50 bg-indigo-500/10 text-indigo-300'
                  : 'border-emerald-500/30 bg-emerald-500/5 text-emerald-400'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${analyzing ? 'bg-indigo-400 animate-pulse' : 'bg-emerald-500'}`}
              />
              {analyzing ? 'Agent Active' : 'Monitoring'}
            </div>
          </div>
        </div>
      </header>

      <main className="relative max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        <LiveMetrics
          availability={status?.availability ?? '---'}
          confidence={status?.confidence ?? '---'}
          traceCount={traces.length}
          stepCount={steps.length}
          analyzing={analyzing}
          errorRate={errorRate}
        />

        {(analyzing || report) && (
          <div
            className={`rounded-xl border p-4 animate-fade-slide ${
              analyzing
                ? 'bg-indigo-500/10 border-indigo-500/40'
                : 'bg-red-500/5 border-red-500/30'
            }`}
          >
            <div className="flex items-start gap-3">
              <AlertTriangle
                className={`w-5 h-5 shrink-0 mt-0.5 ${analyzing ? 'text-indigo-400 animate-pulse' : 'text-red-400'}`}
              />
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-bold text-white">
                    {analyzing ? 'SEV-1 · Incident in progress' : 'Incident resolved'}
                  </span>
                  {focusService && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {focusService}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-1 truncate">
                  {incident?.analysis_status ?? (report ? report.root_cause : 'Monitoring...')}
                </p>
              </div>
            </div>
            <div className="mt-4 border-t border-slate-700/30 pt-3">
              <IncidentTimeline steps={steps} analyzing={analyzing} hasReport={!!report} />
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          {/* Agent — 2 cols */}
          <section className="xl:col-span-2 bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-indigo-400" />
                <h2 className="text-sm font-bold uppercase tracking-widest text-white">
                  Gemma 4 Agent
                </h2>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">
                {status?.gemma_model ?? 'gemma-4-26b-a4b-it'}
              </span>
            </div>
            <AgentStepFeed steps={steps} analyzing={analyzing} />
          </section>

          {/* RCA */}
          <section className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-red-400" />
              <h2 className="text-sm font-bold uppercase tracking-widest text-white">Root Cause</h2>
            </div>
            <RCAPanel report={report} analyzing={analyzing} />
          </section>
        </div>

        {/* Live telemetry row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <section className="bg-slate-900/40 border border-slate-800/80 rounded-2xl overflow-hidden backdrop-blur-sm">
            <div className="px-5 py-3 border-b border-slate-800/80 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold uppercase tracking-widest text-slate-400">
                  Latency · {focusService ?? 'all services'}
                </span>
              </div>
              {analyzing && (
                <span className="text-[10px] text-red-400 font-bold animate-pulse">SPIKE</span>
              )}
            </div>
            <div className="p-4">
              <LatencyChart traces={traces} service={focusService} />
            </div>
          </section>

          <section className="bg-slate-900/40 border border-slate-800/80 rounded-2xl overflow-hidden backdrop-blur-sm">
            <div className="px-5 py-3 border-b border-slate-800/80 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-slate-400" />
                <span className="text-xs font-bold uppercase tracking-widest text-slate-400">
                  Live Trace Feed
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              </div>
              <span className="text-[10px] text-slate-500 font-mono">{traces.length} events</span>
            </div>
            <div className="p-3">
              <LiveTraceFeed traces={traces} highlightIds={highlightIds} />
            </div>
          </section>
        </div>

        <footer className="text-center text-[10px] text-slate-600 pb-6 flex items-center justify-center gap-2">
          <Activity className="w-3 h-3 text-indigo-500" />
          TraceAI · Real telemetry · Gemma 4 investigation · Hackathon demo
        </footer>
      </main>
    </div>
  );
}

export default App;
