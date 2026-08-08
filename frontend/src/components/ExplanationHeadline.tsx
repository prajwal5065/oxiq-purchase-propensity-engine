export function ExplanationHeadline({ headline }: { headline: string }) {
  const isInsufficientData = headline.includes("CANNOT RECOMMEND");
  const isLow = headline.includes("SCORED LOW");
  const color = isInsufficientData ? "text-amber" : isLow ? "text-rose" : "text-signal";
  const border = isInsufficientData ? "border-amber" : isLow ? "border-rose" : "border-signal";

  return (
    <div className={`border-l-2 ${border} pl-4 py-1 mb-6`}>
      <h2 className={`font-mono text-xs uppercase tracking-widest font-semibold ${color}`}>{headline}</h2>
    </div>
  );
}
