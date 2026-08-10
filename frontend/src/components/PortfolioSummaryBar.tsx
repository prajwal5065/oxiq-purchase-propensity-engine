import { useEffect, useState } from "react";
import { api } from "../api/client";
import { formatPercent, formatScore } from "../lib/format";
import type { DashboardSummary } from "../types";

function StatBlock({ label, value, color = "text-paper" }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-1">{label}</p>
      <p className={`font-display text-2xl ${color}`}>{value}</p>
    </div>
  );
}

function DecisionBar({ summary }: { summary: DashboardSummary }) {
  const total = summary.analyzed_companies;
  if (total === 0) return null;

  const segments = [
    { count: summary.by_decision.qualified, color: "bg-signal", label: "Qualified" },
    { count: summary.by_decision.insufficient_data, color: "bg-amber", label: "Insufficient data" },
    { count: summary.by_decision.disqualified, color: "bg-rose", label: "Disqualified" },
  ];

  return (
    <div>
      <div className="flex h-2 rounded-full overflow-hidden bg-ink-700 mb-2">
        {segments.map((s) =>
          s.count > 0 ? (
            <div key={s.label} className={s.color} style={{ width: `${(s.count / total) * 100}%` }} />
          ) : null
        )}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {segments.map((s) => (
          <span key={s.label} className="font-mono text-[10px] text-paper-faint">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${s.color} mr-1.5`} />
            {s.label}: {s.count}
          </span>
        ))}
      </div>
    </div>
  );
}

export function PortfolioSummaryBar() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .getDashboardSummary()
      .then((res) => !cancelled && setSummary(res))
      .catch(() => !cancelled && setError(true));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error || !summary || summary.total_companies === 0) return null;

  return (
    <div className="border border-ink-600 bg-ink-800 rounded-sm p-6">
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-5">Portfolio</h2>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 mb-6">
        <StatBlock label="Analyzed" value={`${summary.analyzed_companies} / ${summary.total_companies}`} />
        <StatBlock label="High priority" value={String(summary.high_priority_count)} color="text-signal" />
        <StatBlock label="Avg confidence" value={formatPercent(summary.avg_confidence)} />
        <StatBlock label="Avg score" value={formatScore(summary.avg_purchase_score)} />
      </div>

      <DecisionBar summary={summary} />
    </div>
  );
}
