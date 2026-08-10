import { formatPercent, formatRelativeDate } from "../lib/format";
import type { EvidenceRecord } from "../types";

export function EvidenceCard({ evidence }: { evidence: EvidenceRecord }) {
  return (
    <div className="border border-ink-600 rounded-sm p-3 bg-ink-900">
      <div className="flex items-start justify-between gap-3 mb-1.5">
        <span className="font-mono text-[10px] uppercase tracking-wide text-signal">{evidence.signal_label}</span>
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
