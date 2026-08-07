import type { ContactPriority } from "../types";

const STAMP_CONFIG: Record<
  ContactPriority | "disqualified",
  { label: string; color: string; border: string }
> = {
  high: { label: "HIGH PRIORITY", color: "text-signal", border: "border-signal" },
  medium: { label: "MEDIUM PRIORITY", color: "text-amber", border: "border-amber" },
  low: { label: "LOW PRIORITY", color: "text-paper-dim", border: "border-paper-dim" },
  disqualified: { label: "DISQUALIFIED", color: "text-rose", border: "border-rose" },
};

export function PriorityStamp({
  priority,
  disqualified = false,
  size = "md",
}: {
  priority: ContactPriority;
  disqualified?: boolean;
  size?: "sm" | "md";
}) {
  const config = STAMP_CONFIG[disqualified ? "disqualified" : priority];
  const sizeClasses = size === "sm" ? "text-[10px] px-2 py-1" : "text-xs px-3 py-1.5";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm border-2 ${config.border} ${config.color} ${sizeClasses} font-mono font-semibold uppercase tracking-widest -rotate-2 select-none`}
      style={{ boxShadow: "0 0 0 1px rgba(0,0,0,0.2) inset" }}
    >
      {config.label}
    </span>
  );
}
