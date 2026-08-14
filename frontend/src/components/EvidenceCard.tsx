import { formatPercent, formatRelativeDate } from "../lib/format";
import type { EvidenceRecord } from "../types";

const DIRECTION_CONFIG: Record<"positive" | "negative", { label: string; color: string; border: string }> = {
  positive: { label: "POSITIVE", color: "text-signal", border: "border-l-signal" },
  negative: { label: "NEGATIVE", color: "text-rose", border: "border-l-rose" },
};

export function EvidenceCard({
  evidence,
  direction,
}: {
  evidence: EvidenceRecord;
  /** When this item was matched by a pillar's scoring as a positive or
   * negative contribution (cross-referenced by evidence_id from
   * PillarExplanation), badge it accordingly. Undefined when the item
   * wasn't claimed by any pillar's contribution list. */
  direction?: "positive" | "negative";
}) {
  const directionConfig = direction ? DIRECTION_CONFIG[direction] : null;

  return (
    <div
      className={`border border-ink-600 rounded-sm p-3 bg-ink-900 ${
        directionConfig ? `border-l-2 ${directionConfig.border}` : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-mono text-[10px] uppercase tracking-wide text-signal truncate">
            {evidence.signal_label}
          </span>
          {directionConfig && (
            <span className={`font-mono text-[9px] uppercase tracking-wide shrink-0 ${directionConfig.color}`}>
              {directionConfig.label}
            </span>
          )}
        </div>
        <span className="font-mono text-[10px] text-paper-faint shrink-0">
          {formatPercent(evidence.confidence)} confidence
        </span>
      </div>

      <p className="text-sm text-paper-dim italic leading-relaxed mb-2">&ldquo;{evidence.excerpt}&rdquo;</p>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-paper-faint">
        {evidence.url ? (
          <a
            href={evidence.url}
            target="_blank"
            rel="noreferrer"
            className="text-paper-faint hover:text-signal underline underline-offset-2"
          >
            {evidence.source}
          </a>
        ) : (
          <span>{evidence.source}</span>
        )}
        {evidence.collector && <span>&middot; {evidence.collector}</span>}
        {evidence.category && <span>&middot; {evidence.category}</span>}
        {evidence.pillar && <span>&middot; {evidence.pillar.replace(/_/g, " ")}</span>}
        <span>&middot; {formatRelativeDate(evidence.published_at ?? evidence.created_at)}</span>
      </div>
    </div>
  );
}
