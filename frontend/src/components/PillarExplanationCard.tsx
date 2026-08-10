import { useState } from "react";
import { formatPercent, formatScore } from "../lib/format";
import { PILLAR_LABELS } from "../types";
import type { PillarExplanation, ScoreContribution } from "../types";

function ContributionRow({ contribution }: { contribution: ScoreContribution }) {
  const sign = contribution.direction === "positive" ? "+" : "\u2212";
  const color = contribution.direction === "positive" ? "text-signal" : "text-rose";
  return (
    <li className="flex items-start gap-3 border-l-2 border-ink-600 pl-3 py-0.5">
      <span className={`font-mono text-xs shrink-0 ${color}`}>
        {sign}
        {Math.abs(contribution.points).toFixed(1)}
      </span>
      <div className="min-w-0">
        <span className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mr-2">
          {contribution.label}
        </span>
        <span className="text-sm text-paper-dim italic">&ldquo;{contribution.excerpt}&rdquo;</span>
      </div>
    </li>
  );
}

export function PillarExplanationCard({ pillar }: { pillar: PillarExplanation }) {
  const [expanded, setExpanded] = useState(false);
  const hasEvidence = pillar.positive_evidence.length > 0 || pillar.negative_evidence.length > 0;

  return (
    <div className="border border-ink-600 bg-ink-800 rounded-sm">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between gap-4 p-4 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs uppercase tracking-widest text-paper">
            {PILLAR_LABELS[pillar.score_type] ?? pillar.score_type}
          </span>
          <span className="font-mono text-[10px] text-paper-faint">
            {formatPercent(pillar.confidence)} confidence
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-lg text-signal">{formatScore(pillar.score)}</span>
          <span className={`font-mono text-xs text-paper-faint transition-transform ${expanded ? "rotate-180" : ""}`}>
            &#9660;
          </span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-ink-700 pt-4">
          {pillar.positive_evidence.length > 0 && (
            <div className="mb-4">
              <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">
                Positive evidence
              </p>
              <ul className="space-y-2">
                {pillar.positive_evidence.map((c, i) => (
                  <ContributionRow key={i} contribution={c} />
                ))}
              </ul>
            </div>
          )}

          {pillar.negative_evidence.length > 0 && (
            <div className="mb-4">
              <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">
                Negative evidence
              </p>
              <ul className="space-y-2">
                {pillar.negative_evidence.map((c, i) => (
                  <ContributionRow key={i} contribution={c} />
                ))}
              </ul>
            </div>
          )}

          {!hasEvidence && (
            <p className="text-sm text-paper-faint italic mb-4">No matched evidence for this pillar.</p>
          )}

          {pillar.missing_expected_signals.length > 0 && (
            <div className="mb-4">
              <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">
                Missing expected signals
              </p>
              <div className="flex flex-wrap gap-1.5">
                {pillar.missing_expected_signals.map((signal, i) => (
                  <span
                    key={i}
                    className="font-mono text-[10px] text-paper-faint border border-dashed border-ink-600 rounded-sm px-1.5 py-0.5"
                  >
                    {signal}
                  </span>
                ))}
              </div>
            </div>
          )}

          {Object.keys(pillar.source_coverage).length > 0 && (
            <div>
              <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">Source coverage</p>
              <div className="flex flex-wrap gap-3">
                {Object.entries(pillar.source_coverage).map(([source, count]) => (
                  <span key={source} className="font-mono text-[10px] text-paper-dim">
                    {source}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
