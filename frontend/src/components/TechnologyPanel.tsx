import { formatRelativeDate } from "../lib/format";
import type { EvidenceRecord } from "../types";

const PROVIDER_LABEL: Record<string, string> = {
  builtwith: "BuiltWith",
  wappalyzer: "Wappalyzer",
};

/** Best-effort provider label for evidence that predates the structured
 * technology_provider field (see project notes) - derived from the
 * free-text `source` field. Falls back to the raw source string when
 * neither known provider name appears in it, so nothing is invented. */
function inferProviderFromSource(source: string): string {
  const lowered = source.toLowerCase();
  if (lowered.includes("builtwith")) return "BuiltWith";
  if (lowered.includes("wappalyzer")) return "Wappalyzer";
  return source;
}

export function TechnologyPanel({ evidence }: { evidence: EvidenceRecord[] }) {
  const techEvidence = evidence.filter((e) => e.collector === "tech");

  if (techEvidence.length === 0) {
    return (
      <div className="border border-dashed border-ink-500 rounded-sm p-8 text-center">
        <p className="font-mono text-xs uppercase tracking-wider text-paper-faint mb-1">
          No technology evidence
        </p>
        <p className="text-sm text-paper-dim max-w-md mx-auto">
          Either the tech detection collector found nothing on this domain, or it hasn&rsquo;t run yet
          (BuiltWith primary / Wappalyzer fallback) &mdash; check Evidence Coverage above for collector status.
        </p>
      </div>
    );
  }

  return (
    <div className="grid sm:grid-cols-2 gap-3">
      {techEvidence.map((item) => {
        const providerLabel = item.technology_provider
          ? (PROVIDER_LABEL[item.technology_provider] ?? item.technology_provider)
          : inferProviderFromSource(item.source);
        return (
          <div key={item.id} className="border border-ink-600 rounded-sm p-3 bg-ink-900">
            <div className="flex items-start justify-between gap-3 mb-1.5">
              <span className="font-mono text-[10px] uppercase tracking-wide text-signal">
                {item.technology_name ?? item.signal_label}
              </span>
              {item.category && (
                <span className="font-mono text-[10px] text-paper-faint shrink-0">{item.category}</span>
              )}
            </div>
            <p className="text-sm text-paper-dim leading-relaxed mb-2">{item.excerpt}</p>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-paper-faint">
              {item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-signal underline underline-offset-2"
                >
                  {providerLabel}
                </a>
              ) : (
                <span>{providerLabel}</span>
              )}
              <span>&middot; {formatRelativeDate(item.published_at ?? item.created_at)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
