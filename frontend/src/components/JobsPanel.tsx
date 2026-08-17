import { formatDate, formatLabel, formatRelativeDate } from "../lib/format";
import type { EvidenceRecord } from "../types";

const HIRING_CATEGORIES = new Set([
  "hiring",
  "ai_ml_hiring",
  "engineering_hiring",
  "data_hiring",
  "cloud_devops_hiring",
  "security_hiring",
  "general_hiring",
]);

const ATS_LABEL: Record<string, string> = {
  greenhouse: "Greenhouse",
  lever: "Lever",
};

export function JobsPanel({ evidence }: { evidence: EvidenceRecord[] }) {
  const jobsEvidence = evidence.filter(
    (e) =>
      e.collector === "jobs" ||
      e.category === "hiring" ||
      (e.category && e.category.endsWith("_hiring")) ||
      (e.job_title && e.job_title.trim() !== "")
  );

  if (jobsEvidence.length === 0) {
    return (
      <div className="border border-dashed border-ink-500 rounded-sm p-8 text-center">
        <p className="font-mono text-xs uppercase tracking-wider text-paper-faint mb-1">No job postings on file</p>
        <p className="text-sm text-paper-dim max-w-md mx-auto">
          No open requisitions were found on this company&rsquo;s Greenhouse or Lever board &mdash; or no
          board was found under a guessed name. That is not evidence the company isn&rsquo;t hiring.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {jobsEvidence.map((item) => {
        let atsLabel = item.job_ats_provider
          ? (ATS_LABEL[item.job_ats_provider] ?? item.job_ats_provider)
          : null;
        if (!atsLabel && item.url) {
          const urlStr = item.url.toLowerCase();
          if (urlStr.includes("greenhouse")) {
            atsLabel = "Greenhouse";
          } else if (urlStr.includes("lever")) {
            atsLabel = "Lever";
          }
        }
        if (!atsLabel) {
          atsLabel = item.source ? (item.source.charAt(0).toUpperCase() + item.source.slice(1)) : "Job Board";
        }

        const postingDate = item.job_posting_date ?? item.published_at;

        return (
          <div key={item.id} className="border border-ink-600 rounded-sm p-4 bg-ink-900">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-1.5">
              <div>
                <p className="text-sm text-paper">{item.job_title ?? item.signal_label}</p>
                {(item.job_department || item.job_location) && (
                  <p className="font-mono text-[10px] text-paper-faint mt-0.5">
                    {[item.job_department, item.job_location].filter(Boolean).join(" \u00b7 ")}
                  </p>
                )}
              </div>
              {item.category && (HIRING_CATEGORIES.has(item.category) || item.category.includes("hiring")) && (
                <span className="font-mono text-[10px] uppercase tracking-wide text-signal shrink-0 border border-signal/40 rounded-sm px-1.5 py-0.5">
                  {formatLabel(item.category)}
                </span>
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
                  {atsLabel}
                </a>
              ) : (
                <span>{atsLabel}</span>
              )}
              <span>
                &middot; posted {postingDate ? formatDate(postingDate) : formatRelativeDate(item.created_at)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
