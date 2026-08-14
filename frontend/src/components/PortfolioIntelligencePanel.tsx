import { useEffect, useState } from "react";
import { api } from "../api/client";
import { DECISION_PRIORITY_LABELS } from "../types";
import type { AnalysisExplanation, BuyingIntentLevel, DecisionPriority } from "../types";

// Caps how many companies we pull explanations for when building this
// portfolio rollup. There's no dedicated aggregate endpoint for Decision/
// Sales Intelligence (see project notes) so this composes the existing
// /companies and /company/{id}/explanation endpoints client-side - capped
// to keep that fan-out reasonable for a dev-facing dashboard.
const SAMPLE_SIZE = 50;

const PRIORITY_ORDER: DecisionPriority[] = ["high_priority", "medium_priority", "low_priority", "insufficient_data"];
const PRIORITY_COLOR: Record<DecisionPriority, string> = {
  high_priority: "bg-signal",
  medium_priority: "bg-amber",
  low_priority: "bg-ink-500",
  insufficient_data: "bg-paper-faint",
};

const INTENT_ORDER: BuyingIntentLevel[] = ["strong", "moderate", "weak", "none", "insufficient_data"];
const INTENT_LABEL: Record<BuyingIntentLevel, string> = {
  strong: "Strong",
  moderate: "Moderate",
  weak: "Weak",
  none: "None",
  insufficient_data: "Insufficient Data",
};
const INTENT_COLOR: Record<BuyingIntentLevel, string> = {
  strong: "bg-signal",
  moderate: "bg-amber",
  weak: "bg-ink-500",
  none: "bg-ink-600",
  insufficient_data: "bg-paper-faint",
};

interface Distribution {
  sampleSize: number;
  priority: Record<DecisionPriority, number>;
  buyingIntent: Record<BuyingIntentLevel, number>;
  strongWhyNow: number;
  hasContradictions: number;
  salesOpportunities: number;
}

function DistributionBar<K extends string>({
  counts,
  order,
  labels,
  colors,
  total,
}: {
  counts: Record<K, number>;
  order: K[];
  labels: Record<K, string>;
  colors: Record<K, string>;
  total: number;
}) {
  if (total === 0) return <p className="text-sm text-paper-faint italic">No data.</p>;
  return (
    <div>
      <div className="flex h-2 rounded-full overflow-hidden bg-ink-700 mb-2">
        {order.map((key) =>
          counts[key] > 0 ? (
            <div key={key} className={colors[key]} style={{ width: `${(counts[key] / total) * 100}%` }} />
          ) : null,
        )}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {order.map((key) => (
          <span key={key} className="font-mono text-[10px] text-paper-faint">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${colors[key]} mr-1.5`} />
            {labels[key]}: {counts[key]}
          </span>
        ))}
      </div>
    </div>
  );
}

function StatBlock({ label, value, color = "text-paper" }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-1">{label}</p>
      <p className={`font-display text-2xl ${color}`}>{value}</p>
    </div>
  );
}

function computeDistribution(explanations: AnalysisExplanation[]): Distribution {
  const priority: Record<DecisionPriority, number> = {
    high_priority: 0,
    medium_priority: 0,
    low_priority: 0,
    insufficient_data: 0,
  };
  const buyingIntent: Record<BuyingIntentLevel, number> = {
    strong: 0,
    moderate: 0,
    weak: 0,
    none: 0,
    insufficient_data: 0,
  };
  let strongWhyNow = 0;
  let hasContradictions = 0;
  let salesOpportunities = 0;

  for (const explanation of explanations) {
    const rec = explanation.decision_intelligence?.recommendation;
    if (!rec) continue;
    priority[rec.priority] += 1;
    buyingIntent[rec.buying_intent.level] += 1;
    if (rec.why_now.has_timing_trigger) strongWhyNow += 1;
    if (rec.contradictions.has_contradictions) hasContradictions += 1;
    if (explanation.sales_intelligence?.opportunity) salesOpportunities += 1;
  }

  return { sampleSize: explanations.length, priority, buyingIntent, strongWhyNow, hasContradictions, salesOpportunities };
}

export function PortfolioIntelligencePanel() {
  const [distribution, setDistribution] = useState<Distribution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .listCompanies({ limit: SAMPLE_SIZE })
      .then(async (res) => {
        const analyzed = res.items.filter((c) => c.final_decision !== null);
        const explanations = await Promise.all(
          analyzed.map((c) => api.getExplanation(c.id).catch(() => null)),
        );
        if (cancelled) return;
        const present = explanations.filter((e): e is AnalysisExplanation => e !== null);
        setDistribution(computeDistribution(present));
        setError(false);
      })
      .catch(() => !cancelled && setError(true))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return null;

  if (loading) {
    return (
      <div className="border border-ink-600 bg-ink-800 rounded-sm p-6">
        <p className="font-mono text-[10px] uppercase tracking-widest text-paper-faint animate-pulse-glow">
          Computing portfolio intelligence&hellip;
        </p>
      </div>
    );
  }

  if (!distribution || distribution.sampleSize === 0) return null;

  const priorityTotal = PRIORITY_ORDER.reduce((sum, k) => sum + distribution.priority[k], 0);
  const intentTotal = INTENT_ORDER.reduce((sum, k) => sum + distribution.buyingIntent[k], 0);

  return (
    <div className="border border-ink-600 bg-ink-800 rounded-sm p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint">
          Decision &amp; Sales Intelligence
        </h2>
        <span className="font-mono text-[10px] text-paper-faint">
          across {distribution.sampleSize} analyzed compan{distribution.sampleSize === 1 ? "y" : "ies"}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-6 mb-6">
        <StatBlock label="Strong Why-Now" value={String(distribution.strongWhyNow)} color="text-signal" />
        <StatBlock label="Sales Opportunities" value={String(distribution.salesOpportunities)} color="text-signal" />
        <StatBlock label="Contradictions" value={String(distribution.hasContradictions)} color="text-amber" />
      </div>

      <div className="grid sm:grid-cols-2 gap-6">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">
            Priority distribution
          </p>
          <DistributionBar
            counts={distribution.priority}
            order={PRIORITY_ORDER}
            labels={DECISION_PRIORITY_LABELS}
            colors={PRIORITY_COLOR}
            total={priorityTotal}
          />
        </div>
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">
            Buying intent distribution
          </p>
          <DistributionBar
            counts={distribution.buyingIntent}
            order={INTENT_ORDER}
            labels={INTENT_LABEL}
            colors={INTENT_COLOR}
            total={intentTotal}
          />
        </div>
      </div>
    </div>
  );
}
