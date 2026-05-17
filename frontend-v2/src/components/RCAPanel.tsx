import { Shield, Terminal, Copy, Check, Sparkles } from 'lucide-react';
import { useState, useEffect } from 'react';
import type { Report } from '../hooks/useIncident';

export function RCAPanel({ report, analyzing }: { report: Report | null; analyzing: boolean }) {
  const [copied, setCopied] = useState(false);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    if (report) {
      setRevealed(false);
      const t = requestAnimationFrame(() => setRevealed(true));
      return () => cancelAnimationFrame(t);
    }
    setRevealed(false);
  }, [report?.id]);

  if (!report) {
    return (
      <div className="h-full min-h-[320px] flex flex-col items-center justify-center border border-dashed border-slate-700/80 rounded-xl bg-slate-900/30 text-slate-500 gap-3 p-8">
        {analyzing ? (
          <>
            <div className="w-12 h-12 rounded-full border-2 border-indigo-500/30 border-t-indigo-400 animate-spin" />
            <p className="text-sm text-indigo-300">Gemma 4 synthesizing RCA...</p>
            <p className="text-[10px] text-slate-600">Usually 30–60 seconds</p>
          </>
        ) : (
          <>
            <Shield className="w-10 h-10 opacity-20" />
            <p className="text-sm">RCA will appear after investigation</p>
          </>
        )}
      </div>
    );
  }

  const isHigh = report.impact_level === 'High';
  const isGemma = report.gemma_model?.includes('gemma');

  const copyAction = () => {
    navigator.clipboard.writeText(report.recommended_action);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`border-l-4 transition-all duration-700 ${
        revealed ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      } ${isHigh ? 'border-red-500' : 'border-amber-500'} bg-slate-800/40 border border-slate-700/50 rounded-xl p-6 shadow-lg shadow-black/20`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Shield className={`w-5 h-5 ${isHigh ? 'text-red-400' : 'text-amber-400'}`} />
          <span
            className={`text-xs font-bold uppercase tracking-widest ${isHigh ? 'text-red-400' : 'text-amber-400'}`}
          >
            {report.impact_level} · {report.service}
          </span>
        </div>
        <span
          className={`text-[10px] font-mono px-2 py-1 rounded-full border flex items-center gap-1 ${
            isGemma
              ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30'
              : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
          }`}
        >
          {isGemma && <Sparkles className="w-3 h-3" />}
          {report.gemma_model}
        </span>
      </div>

      <h2 className="text-xl font-bold text-white mb-2 leading-snug">{report.root_cause}</h2>
      <p className="text-slate-400 text-sm leading-relaxed mb-4">{report.explanation}</p>

      {report.evidence?.length > 0 && (
        <div className="mb-4 p-3 rounded-lg bg-slate-900/60 border border-slate-700/50">
          <div className="text-[10px] font-bold text-slate-500 uppercase mb-2">Evidence chain</div>
          <ul className="space-y-1.5">
            {report.evidence.map((e, i) => (
              <li key={i} className="text-xs text-slate-300 flex gap-2 animate-fade-slide" style={{ animationDelay: `${i * 80}ms` }}>
                <span className="text-indigo-400 font-bold">{i + 1}.</span>
                <span>{e}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="bg-slate-900 border border-sky-500/20 rounded-lg p-3 flex items-start gap-3">
        <Terminal className="w-4 h-4 text-sky-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">Remediation</div>
          <code className="text-sky-300 text-xs font-mono break-all">{report.recommended_action}</code>
        </div>
        <button
          onClick={copyAction}
          className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
          title="Copy command"
        >
          {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>

      <div className="mt-3 flex justify-between text-[10px] text-slate-500">
        <span>Confidence: {(report.confidence_score * 100).toFixed(0)}%</span>
        <span className="truncate max-w-[60%]">Tools: {report.tools_used?.slice(0, 3).join(', ')}</span>
      </div>
    </div>
  );
}
