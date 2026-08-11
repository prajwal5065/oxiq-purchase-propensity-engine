import { CollectorStatusBadge } from "./CollectorStatusBadge";
import { formatPercent } from "../lib/format";
import type { EvidenceCoverage } from "../types";

const SOURCE_LABELS: Record<string, string> = {
  search: "Search",
  website: "Website",
  tech: "Technology",
  news: "News",
  github: "GitHub",
  company_profile: "Company Profile",
};

export function EvidenceCoverageSection({ coverage }: { coverage: EvidenceCoverage }) {
  return (
    <div className="border border-ink-600 bg-ink-800 rounded-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint">Evidence Coverage</h3>
        <span className="font-mono text-sm text-signal">{formatPercent(coverage.coverage_percentage)} covered</span>
      </div>

      <div className="space-y-2 mb-5">
        {coverage.collector_statuses.map((report) => (
          <div key={report.source} className="flex items-center justify-between border-b border-ink-700 pb-2">
            <span className="text-sm text-paper-dim">{SOURCE_LABELS[report.source] ?? report.source}</span>
            <div className="flex items-center gap-3">
              {report.signal_count > 0 && (
                <span className="font-mono text-[10px] text-paper-faint">{report.signal_count} signals</span>
              )}
              <CollectorStatusBadge status={report.status} />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-2 font-mono text-[10px] text-paper-faint">
        <div className="flex justify-between">
          <span>Sources discovered</span>
          <span className="text-paper-dim">{coverage.sources_discovered}</span>
        </div>
        <div className="flex justify-between">
          <span>Successful</span>
          <span className="text-signal">{coverage.sources_successful}</span>
        </div>
        <div className="flex justify-between">
          <span>Zero results</span>
          <span className="text-paper-dim">{coverage.sources_zero_results}</span>
        </div>
        <div className="flex justify-between">
          <span>Not configured</span>
          <span className="text-paper-faint">{coverage.sources_not_configured}</span>
        </div>
        <div className="flex justify-between">
          <span>Failed</span>
          <span className="text-rose">{coverage.sources_failed}</span>
        </div>
        <div className="flex justify-between">
          <span>Evidence accepted</span>
          <span className="text-paper-dim">
            {coverage.evidence_items_accepted} / {coverage.evidence_items_extracted} extracted
          </span>
        </div>
      </div>

      {coverage.sources_not_implemented.length > 0 && (
        <div className="mt-5 pt-4 border-t border-ink-700">
          <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">
            Not yet available
          </p>
          <div className="space-y-1">
            {coverage.sources_not_implemented.map((label) => (
              <div key={label} className="flex items-center gap-2 text-[13px] text-paper-faint">
                <span aria-hidden="true">&#10007;</span>
                {label}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
