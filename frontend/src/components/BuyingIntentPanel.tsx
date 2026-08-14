import type { BuyingIntentAssessment } from "../types";

const LEVEL_CONFIG: Record<BuyingIntentAssessment["level"], { label: string; color: string; border: string }> = {
  strong: { label: "STRONG", color: "text-signal", border: "border-signal" },
  moderate: { label: "MODERATE", color: "text-amber", border: "border-amber" },
  weak: { label: "WEAK", color: "text-paper-dim", border: "border-ink-500" },
  none: { label: "NONE DETECTED", color: "text-paper-faint", border: "border-ink-600" },
  insufficient_data: { label: "INSUFFICIENT DATA", color: "text-amber", border: "border-amber" },
};

const STRENGTH_COLOR: Record<string, string> = {
  strong: "text-signal",
  moderate: "text-amber",
  weak: "text-paper-faint",
};

export function BuyingIntentPanel({ intent }: { intent: BuyingIntentAssessment }) {
  const config = LEVEL_CONFIG[intent.level];
  const isInsufficient = intent.level === "insufficient_data";

  return (
    <div className={`border ${config.border} bg-ink-800 rounded-sm p-6`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint">Buying Intent</h3>
        <span className={`font-mono text-xs uppercase tracking-widest font-semibold ${config.color}`}>
          {config.label}
        </span>
      </div>

      {!isInsufficient && (
        <div className="h-1 bg-ink-700 rounded-full overflow-hidden mb-3">
          <div className="h-full bg-signal-dim" style={{ width: `${Math.round(intent.score * 100)}%` }} />
        </div>
      )}

      <p className="text-sm text-paper-dim leading-relaxed mb-4">{intent.rationale}</p>

      {intent.matched_signals.length > 0 && (
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">Matched signals</p>
          <ul className="space-y-2">
            {intent.matched_signals.map((signal, i) => (
              <li key={signal.evidence_id ?? i} className="border-l-2 border-ink-600 pl-3 py-0.5">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`font-mono text-[10px] uppercase tracking-wide ${STRENGTH_COLOR[signal.strength]}`}>
                    {signal.strength}
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-wide text-paper-faint">
                    {signal.label}
                  </span>
                </div>
                <p className="text-sm text-paper-dim italic leading-relaxed">
                  &ldquo;{signal.excerpt}&rdquo; <span className="not-italic text-paper-faint">&mdash; {signal.source}</span>
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {intent.matched_signals.length === 0 && !isInsufficient && (
        <p className="text-sm text-paper-faint italic">No buying-intent signals matched in the available evidence.</p>
      )}

      {isInsufficient && (
        <p className="text-sm text-amber/90 italic">
          Not enough evidence was collected to assess buying intent &mdash; this is distinct from a
          negative assessment.
        </p>
      )}
    </div>
  );
}
