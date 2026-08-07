const SIZE = 168;
const STROKE = 10;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function ScoreDial({
  score,
  confidence,
  disqualified = false,
}: {
  score: number;
  confidence: number;
  disqualified?: boolean;
}) {
  const clamped = Math.max(0, Math.min(100, score));
  const offset = CIRCUMFERENCE * (1 - clamped / 100);
  const color = disqualified ? "#E4636F" : "#3ED6C4";

  return (
    <div className="relative" style={{ width: SIZE, height: SIZE }}>
      <svg width={SIZE} height={SIZE} className="-rotate-90">
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="#2A323C"
          strokeWidth={STROKE}
        />
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-4xl font-semibold text-paper tabular-nums">
          {Math.round(clamped)}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-widest text-paper-faint">
          / 100
        </span>
        <span className="mt-1 font-mono text-[10px] uppercase tracking-wider text-paper-dim">
          conf. {Math.round(confidence * 100)}%
        </span>
      </div>
    </div>
  );
}
