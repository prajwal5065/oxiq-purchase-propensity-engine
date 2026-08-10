import type { CollectorStatusType } from "../types";

const STATUS_CONFIG: Record<CollectorStatusType, { icon: string; label: string; color: string }> = {
  success: { icon: "\u2713", label: "LIVE", color: "text-signal" },
  no_results: { icon: "\u25CB", label: "NO RESULTS", color: "text-paper-dim" },
  not_configured: { icon: "\u2013", label: "NOT CONFIGURED", color: "text-paper-faint" },
  blocked: { icon: "\u26A0", label: "BLOCKED", color: "text-amber" },
  timeout: { icon: "\u26A0", label: "TIMEOUT", color: "text-amber" },
  error: { icon: "\u2715", label: "ERROR", color: "text-rose" },
};

export function CollectorStatusBadge({ status }: { status: CollectorStatusType }) {
  const config = STATUS_CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide ${config.color}`}>
      <span aria-hidden="true">{config.icon}</span>
      {config.label}
    </span>
  );
}
