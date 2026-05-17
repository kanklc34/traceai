import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import type { TraceRow } from './LiveTraceFeed';

export function LatencyChart({ traces, service }: { traces: TraceRow[]; service?: string }) {
  const filtered = traces
    .filter((t) => !service || t.service === service)
    .slice(0, 20)
    .reverse()
    .map((t, i) => ({
      i,
      ms: t.duration_ms,
      status: t.status,
      time: new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    }));

  if (filtered.length < 2) {
    return (
      <div className="h-[140px] flex items-center justify-center text-xs text-slate-500 border border-dashed border-slate-700 rounded-lg">
        Latency chart appears after traces arrive
      </div>
    );
  }

  return (
    <div className="h-[140px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={filtered} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="latGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 9 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#64748b', fontSize: 9 }} axisLine={false} tickLine={false} width={36} />
          <Tooltip
            contentStyle={{
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: 8,
              fontSize: 11,
            }}
            formatter={(v: number) => [`${v} ms`, 'Latency']}
          />
          <Area
            type="monotone"
            dataKey="ms"
            stroke="#818cf8"
            strokeWidth={2}
            fill="url(#latGrad)"
            isAnimationActive
            animationDuration={400}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
