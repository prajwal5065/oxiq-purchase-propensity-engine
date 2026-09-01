import { formatDate, formatLabel } from "../lib/format";
import type { WhyNowExplanation } from "../types";

const FRESHNESS_COLOR: Record<string, string> = {
  very_fresh: "text-signal",
  recent: "text-signal",
  aging: "text-amber",
  stale: "text-paper-faint",
  historical: "text-paper-faint",
  unknown: "text-paper-faint",
};

export function WhyNowPanel({ whyNow }: { whyNow: WhyNowExplanation }) {
  const border = !whyNow.data_sufficient ? "border-amber" : whyNow.has_timing_trigger ? "border-signal" : "border-ink-600";

  return (
    <div className={`border ${border} bg-ink-800 rounded-sm p-6`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint">Why Now</h3>
        <span
          className={`font-mono text-xs uppercase tracking-widest font-semibold ${
            !whyNow.data_sufficient ? "text-amber" : whyNow.has_timing_trigger ? "text-signal" : "text-paper-faint"
          }`}
        >
          {!whyNow.data_sufficient
            ? "INSUFFICIENT DATA"
            : whyNow.has_timing_trigger
              ? "TIMING TRIGGER FOUND"
              : "NO TRIGGER"}
        </span>
      </div>

      <p className="text-sm text-paper-dim leading-relaxed mb-4">{whyNow.narrative}</p>

      {whyNow.triggers.length > 0 && (
        <ul className="space-y-2">
          {whyNow.triggers.map((trigger, i) => (
            <li key={trigger.evidence_id ?? i} className="border-l-2 border-ink-600 pl-3 py-0.5">
              <div className="flex flex-wrap items-center gap-2 mb-0.5">
                <span className="font-mono text-[10px] uppercase tracking-wide text-signal">
                  {formatLabel(trigger.trigger_type)}
                </span>
                <span className={`font-mono text-[10px] uppercase tracking-wide ${FRESHNESS_COLOR[trigger.freshness_label]}`}>
                  {formatLabel(trigger.freshness_label)}
                </span>
                {trigger.published_at && (
                  <span className="font-mono text-[10px] text-paper-faint">{formatDate(trigger.published_at)}</span>
                )}
              </div>
              <p className="text-sm text-paper-dim italic leading-relaxed">
                &ldquo;{trigger.excerpt}&rdquo; <span className="not-italic text-paper-faint">&mdash; {trigger.source}</span>
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
