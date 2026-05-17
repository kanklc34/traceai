import { useEffect, useRef } from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

export interface TraceRow {
  id: number;
  service: string;
  operation: string;
  status: string;
  duration_ms: number;
  timestamp: string;
}

export function LiveTraceFeed({ traces, highlightIds }: { traces: TraceRow[]; highlightIds: Set<number> }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (highlightIds.size > 0) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [traces.length, highlightIds.size]);

  return (
    <div className="relative h-[220px] overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-slate-900/90 to-transparent z-10 pointer-events-none" />
      <div className="h-full overflow-y-auto pr-1 space-y-1">
        {traces.length === 0 ? (
          <p className="text-xs text-slate-500 italic text-center py-12">Waiting for telemetry...</p>
        ) : (
          traces.slice(0, 30).map((t) => (
            <div
              key={t.id}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg border border-slate-800/50 bg-slate-900/40 text-xs transition-all ${
                highlightIds.has(t.id) ? 'trace-new border-red-500/30' : ''
              }`}
            >
              {t.status === 'error' ? (
                <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              )}
              <span className="font-mono text-slate-400 w-16 shrink-0">
                {new Date(t.timestamp).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </span>
              <span className="font-semibold text-slate-300 w-28 truncate">{t.service}</span>
              <span className="text-slate-500 font-mono flex-1 truncate">{t.operation}</span>
              <span
                className={`font-mono font-bold tabular-nums ${
                  t.duration_ms > 800 ? 'text-red-400' : t.duration_ms > 400 ? 'text-amber-400' : 'text-emerald-400'
                }`}
              >
                {t.duration_ms}ms
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
      <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-slate-900/90 to-transparent pointer-events-none" />
    </div>
  );
}
