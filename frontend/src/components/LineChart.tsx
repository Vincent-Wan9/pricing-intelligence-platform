import { money } from "../lib/format";

export interface ChartSeries {
  name: string;
  color: string;
  points: { date: string; value: number }[];
}
export function LineChart({
  series,
  height = 250,
  valueLabel = "currency",
  ariaLabel = "Price history line chart",
}: {
  series: ChartSeries[];
  height?: number;
  valueLabel?: "currency" | "units";
  ariaLabel?: string;
}) {
  const points = series.flatMap((s) => s.points);
  if (!points.length)
    return <div className="chart-empty">No history available yet.</div>;
  const values = points.map((p) => p.value),
    min = Math.min(...values),
    max = Math.max(...values),
    spread = max - min || 1;
  const width = 800,
    padX = 50,
    padY = 24,
    innerW = width - padX * 2,
    innerH = height - padY * 2;
  const allDates = [...new Set(points.map((p) => p.date))].sort();
  const x = (date: string) =>
    padX + (allDates.indexOf(date) / Math.max(allDates.length - 1, 1)) * innerW;
  const y = (value: number) => padY + (1 - (value - min) / spread) * innerH;
  return (
    <div className="chart-wrap">
      <div className="legend">
        {series.map((s) => (
          <span key={s.name}>
            <i style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        {[0, 0.5, 1].map((n) => {
          const yy = padY + n * innerH,
            value = max - n * spread;
          return (
            <g key={n}>
              <line
                x1={padX}
                x2={width - padX}
                y1={yy}
                y2={yy}
                className="grid-line"
              />
              <text x={4} y={yy + 4}>
                {valueLabel === "currency" ? money(value) : Math.round(value)}
              </text>
            </g>
          );
        })}
        {series.map((s) => (
          <g key={s.name}>
            <polyline
              points={s.points
                .map((p) => `${x(p.date)},${y(p.value)}`)
                .join(" ")}
              fill="none"
              stroke={s.color}
              strokeWidth="3"
              strokeLinejoin="round"
            />
            {s.points.map((p, i) => (
              <circle
                key={i}
                cx={x(p.date)}
                cy={y(p.value)}
                r="4"
                fill={s.color}
              >
                <title>{`${s.name}: ${valueLabel === "currency" ? money(p.value) : `${p.value} units`} · ${new Date(p.date).toLocaleDateString()}`}</title>
              </circle>
            ))}
          </g>
        ))}
      </svg>
      <div className="chart-axis">
        <span>{new Date(allDates[0]).toLocaleDateString()}</span>
        <span>{new Date(allDates.at(-1)!).toLocaleDateString()}</span>
      </div>
    </div>
  );
}
