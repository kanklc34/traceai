import { useEffect, useRef } from 'react';
import { CheckCircle2, Loader2, Wrench } from 'lucide-react';
import type { AgentStep } from '../hooks/useIncident';

function summarizeStep(step: AgentStep): string {
  const out = step.tool_output;
  switch (step.tool_name) {
    case 'get_error_breakdown':
      return `Error rate ${((out.error_rate as number) * 100).toFixed(1)}% · ${out.error_count}/${out.total_traces} failed`;
    case 'get_recent_traces':
      return `Loaded ${out.count} recent traces`;
    case 'get_deployment':
      return out.found ? `Deploy ${out.version} (${out.deployed_at})` : 'No recent deployment';
    case 'compare_to_baseline':
      return out.found
        ? `Latency ${out.latency_multiplier}x · errors ${out.error_rate_multiplier}x baseline`
        : 'No baseline data';
    case 'search_similar_incidents':
      return out.best_match
        ? `Match: ${(out.best_match as { title: string }).title}`
        : 'No playbook match';
    case 'gemma_synthesize':
      return out.status === 'calling_gemma_4'
        ? 'Synthesizing with Gemma 4...'
        : `Done: ${out.root_cause || 'RCA ready'}`;
    default:
      return step.status === 'running' ? 'Running...' : 'Complete';
  }
}

const TOOL_PROGRESS = [
  'get_error_breakdown',
  'get_recent_traces',
  'get_deployment',
  'compare_to_baseline',
  'search_similar_incidents',
  'gemma_synthesize',
];

export function AgentStepFeed({ steps, analyzing }: { steps: AgentStep[]; analyzing: boolean }) {
  const endRef = useRef<HTMLDivElement>(null);
  const completedTools = steps.filter((s) => s.status === 'complete' && s.tool_name !== 'gemma_synthesize').length;
  const progress = Math.min(100, Math.round((completedTools / TOOL_PROGRESS.length) * 100));

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [steps.length]);

  if (steps.length === 0 && !analyzing) {
    return (
      <div className="text-slate-500 text-sm py-10 text-center border border-dashed border-slate-700/80 rounded-xl bg-slate-900/30">
        <Wrench className="w-8 h-8 mx-auto mb-2 opacity-30" />
        <p>Trigger an incident to watch Gemma 4 investigate live</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {(analyzing || steps.length > 0) && (
        <div className="space-y-1">
          <div className="flex justify-between text-[10px] text-slate-500 uppercase font-bold">
            <span>Investigation progress</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-600 to-violet-500 transition-all duration-500 ease-out rounded-full"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1 relative">
        <div className="absolute left-[19px] top-4 bottom-4 w-px bg-slate-800" />
        {steps.map((step, idx) => (
          <div
            key={step.id}
            className="flex gap-3 p-3 rounded-lg bg-slate-900/70 border border-slate-700/40 animate-slide-left relative"
            style={{ animationDelay: `${idx * 60}ms` }}
          >
            <div className="mt-0.5 shrink-0 z-10 bg-slate-900 rounded-full p-0.5">
              {step.status === 'running' ? (
                <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-indigo-300">{step.tool_name}</span>
                <span className="text-[9px] text-slate-600">#{step.step_order}</span>
              </div>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{summarizeStep(step)}</p>
            </div>
          </div>
        ))}
        {analyzing && steps.length > 0 && steps[steps.length - 1]?.status !== 'running' && (
          <div className="flex gap-3 p-3 rounded-lg border border-indigo-500/30 bg-indigo-500/5 animate-pulse">
            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin mt-0.5" />
            <span className="text-xs text-indigo-300">Next tool executing...</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
