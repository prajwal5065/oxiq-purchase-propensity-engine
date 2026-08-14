export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatScore(value: number): string {
  return Math.round(value).toString();
}

export function formatRelativeDate(iso: string | null): string {
  if (!iso) return "never";
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.round(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function priorityFromScore(score: number, disqualified: boolean): "high" | "medium" | "low" {
  if (disqualified) return "low";
  if (score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}

export function formatDate(iso: string | null): string {
  if (!iso) return "date unknown";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

/** "ai_ml_hiring" -> "AI/ML Hiring", "engineering_hiring" -> "Engineering Hiring" */
export function formatLabel(value: string): string {
  const SPECIAL: Record<string, string> = {
    ai_ml_hiring: "AI/ML Hiring",
    cloud_devops_hiring: "Cloud/DevOps Hiring",
  };
  if (SPECIAL[value]) return SPECIAL[value];
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
