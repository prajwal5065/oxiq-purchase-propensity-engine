import { PILLAR_LABELS, PILLAR_TYPES, type PillarScore } from "../types";

const SIZE = 340;
const CENTER = SIZE / 2;
const MAX_RADIUS = SIZE / 2 - 56;
const RINGS = [0.25, 0.5, 0.75, 1];

function pointForAxis(index: number, fraction: number): [number, number] {
  // Start at the top (12 o'clock) and go clockwise, six evenly spaced axes.
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / 6;
  const r = MAX_RADIUS * fraction;
  return [CENTER + r * Math.cos(angle), CENTER + r * Math.sin(angle)];
}

function polygonPoints(fraction: number): string {
  return PILLAR_TYPES.map((_, i) => pointForAxis(i, fraction).join(",")).join(" ");
}

export function PillarRadar({ pillars }: { pillars: PillarScore[] }) {
  const byType = new Map(pillars.map((p) => [p.score_type, p]));
  const scorePoints = PILLAR_TYPES.map((type, i) => {
    const pillar = byType.get(type);
    return pointForAxis(i, (pillar?.score ?? 0) / 100).join(",");
  }).join(" ");

  return (
    <div className="relative mx-auto" style={{ width: SIZE, height: SIZE }}>
      {/* Radar sweep - a slow rotating wedge of light behind the grid, the one
          bold/animated gesture on the page. Respects prefers-reduced-motion
          globally via index.css. */}
      <div
        className="absolute rounded-full animate-sweep opacity-30"
        style={{
          width: MAX_RADIUS * 2,
          height: MAX_RADIUS * 2,
          top: CENTER - MAX_RADIUS,
          left: CENTER - MAX_RADIUS,
          background:
            "conic-gradient(from 0deg, rgba(62,214,196,0.55) 0deg, rgba(62,214,196,0) 55deg, rgba(62,214,196,0) 360deg)",
        }}
      />

      <svg width={SIZE} height={SIZE} className="relative">
        {RINGS.map((fraction) => (
          <polygon
            key={fraction}
            points={polygonPoints(fraction)}
            fill="none"
            stroke="#2A323C"
            strokeWidth={1}
          />
        ))}

        {PILLAR_TYPES.map((_, i) => {
          const [x, y] = pointForAxis(i, 1);
          return (
            <line key={i} x1={CENTER} y1={CENTER} x2={x} y2={y} stroke="#1D242C" strokeWidth={1} />
          );
        })}

        <polygon
          points={scorePoints}
          fill="rgba(62, 214, 196, 0.18)"
          stroke="#3ED6C4"
          strokeWidth={2}
          strokeLinejoin="round"
        />

        {PILLAR_TYPES.map((type, i) => {
          const pillar = byType.get(type);
          const [x, y] = pointForAxis(i, (pillar?.score ?? 0) / 100);
          return <circle key={type} cx={x} cy={y} r={3.5} fill="#3ED6C4" />;
        })}
      </svg>

      {PILLAR_TYPES.map((type, i) => {
        const [x, y] = pointForAxis(i, 1.32);
        const pillar = byType.get(type);
        return (
          <div
            key={type}
            className="absolute -translate-x-1/2 -translate-y-1/2 text-center"
            style={{ left: x, top: y, width: 96 }}
          >
            <div className="font-mono text-[10px] uppercase tracking-wider text-paper-dim">
              {PILLAR_LABELS[type]}
            </div>
            <div className="font-mono text-sm font-semibold text-paper tabular-nums">
              {Math.round(pillar?.score ?? 0)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
