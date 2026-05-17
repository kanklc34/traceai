import { Activity, Shield, Zap, Radio } from 'lucide-react';

interface Props {
  availability: string;
  confidence: string;
  traceCount: number;
  stepCount: number;
  analyzing: boolean;
  errorRate?: number;
}

function MetricCard({
  label,
  value,
  icon: Icon,
  accent,
  pulse,
}: {
  label: string;
  value: string;
  icon: typeof Activity;
  accent: string;
  pulse?: boolean;
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-slate-800/80 bg-slate-900/50 p-4 backdrop-blur-sm transition-all duration-300 ${
        pulse ? 'animate-pulse-glow border-indigo-500/40' : ''
      }`}
    >
      {pulse && <div className="absolute inset-0 animate-shimmer pointer-events-none" />}
      <div className="flex items-start justify-between relative">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{label}</p>
          <p className={`text-2xl font-black font-mono mt-1 ${accent}`}>{value}</p>
        </div>
        <div className="p-2 rounded-lg bg-slate-800/80">
          <Icon className={`w-4 h-4 ${accent}`} />
        </div>
      </div>
    </div>
  );
}

export function LiveMetrics({
  availability,
  confidence,
  traceCount,
  stepCount,
  analyzing,
  errorRate,
}: Props) {
  const errorDisplay = errorRate !== undefined ? `${(errorRate * 100).toFixed(0)}%` : '—';

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <MetricCard label="Live traces" value={String(traceCount)} icon={Activity} accent="text-emerald-400" />
      <MetricCard
        label="Error rate (5m)"
        value={errorDisplay}
        icon={Radio}
        accent={errorRate && errorRate > 0.3 ? 'text-red-400' : 'text-slate-300'}
        pulse={!!(errorRate && errorRate > 0.3)}
      />
      <MetricCard
        label="Agent steps"
        value={String(stepCount)}
        icon={Zap}
        accent="text-indigo-400"
        pulse={analyzing}
      />
      <MetricCard label="RCA confidence" value={confidence} icon={Shield} accent="text-sky-400" />
    </div>
  );
}
