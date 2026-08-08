import { formatPercent } from "../lib/format";
import type { ConfidenceExplanation } from "../types";

const LEVEL_COLOR: Record<string, string> = {
  high: "text-signal",
  medium: "text-amber",
  low: "text-rose",
};

export function ConfidenceExplanationPanel({ confidence }: { confidence: ConfidenceExplanation }) {
  const weighted = confidence.factors.filter((f) => f.weight > 0);

  return (
    <div className="border border-ink-600 bg-ink-800 rounded-sm p-6">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint">Confidence</h3>
        <span className={`font-mono text-sm uppercase tracking-wide ${LEVEL_COLOR[confidence.level]}`}>
          {confidence.level} &middot; {formatPercent(confidence.overall_confidence)}
        </span>
      </div>
      <p className="text-sm text-paper-dim mb-5">{confidence.summary}</p>

      <div className="space-y-3">
        {weighted.map((factor) => (
          <div key={factor.name}>
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-[10px] uppercase tracking-wide text-paper-faint">
                {factor.name.replace(/_/g, " ")}
              </span>
              <span className="font-mono text-[10px] text-paper-dim">{formatPercent(factor.value)}</span>
            </div>
            <div className="h-1 bg-ink-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-signal-dim"
                style={{ width: `${Math.round(factor.value * 100)}%` }}
              />
            </div>
            <p className="text-[11px] text-paper-faint mt-1">{factor.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
