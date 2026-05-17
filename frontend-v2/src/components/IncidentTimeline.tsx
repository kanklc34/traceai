import { AlertTriangle, Wrench, Brain, FileCheck } from 'lucide-react';
import type { AgentStep } from '../hooks/useIncident';

const PHASES = [
  { id: 'detect', label: 'Detected', icon: AlertTriangle },
  { id: 'tools', label: 'Tools', icon: Wrench },
  { id: 'gemma', label: 'Gemma 4', icon: Brain },
  { id: 'rca', label: 'RCA', icon: FileCheck },
];

function phaseIndex(steps: AgentStep[], analyzing: boolean, hasReport: boolean): number {
  if (hasReport) return 3;
  if (steps.some((s) => s.tool_name === 'gemma_synthesize' && s.status === 'running')) return 2;
  if (steps.length > 0 || analyzing) return 1;
  if (analyzing) return 0;
  return -1;
}

export function IncidentTimeline({
  steps,
  analyzing,
  hasReport,
}: {
  steps: AgentStep[];
  analyzing: boolean;
  hasReport: boolean;
}) {
  const active = analyzing || steps.length > 0 || hasReport;
  const current = active ? Math.max(0, phaseIndex(steps, analyzing, hasReport)) : -1;

  return (
    <div className="flex items-center justify-between gap-1 px-2 py-3">
      {PHASES.map((phase, i) => {
        const Icon = phase.icon;
        const done = i < current;
        const activePhase = i === current;
        return (
          <div key={phase.id} className="flex items-center flex-1 min-w-0">
            <div className="flex flex-col items-center gap-1 flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-500 ${
                  done
                    ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                    : activePhase
                      ? 'bg-indigo-500/20 border-indigo-400 text-indigo-300 animate-pulse-glow'
                      : 'bg-slate-800/50 border-slate-700 text-slate-600'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
              </div>
              <span
                className={`text-[9px] font-bold uppercase tracking-wider truncate ${
                  activePhase ? 'text-indigo-300' : done ? 'text-emerald-500' : 'text-slate-600'
                }`}
              >
                {phase.label}
              </span>
            </div>
            {i < PHASES.length - 1 && (
              <div
                className={`h-0.5 flex-1 mx-1 rounded transition-all duration-700 ${
                  done ? 'bg-emerald-500/60' : 'bg-slate-800'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
