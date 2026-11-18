"use client";

type Props = {
  values: number[];
  width?: number;
  height?: number;
  className?: string;
};

export default function Sparkline({ values, width = 120, height = 32, className }: Props) {
  if (values.length === 0) {
    return <div className={`h-8 w-full rounded bg-surface-muted ${className ?? ""}`} />;
  }
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const step = values.length > 1 ? width / (values.length - 1) : width;
  const points = values
    .map((value, index) => {
      const x = index * step;
      const y = height - ((value - min) / span) * (height - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const area = `0,${height} ${points} ${width},${height}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Tren hotspot tujuh hari"
      className={`h-8 w-full ${className ?? ""}`}
      preserveAspectRatio="none"
    >
      <polygon points={area} fill="#FFF1E6" />
      <polyline
        points={points}
        fill="none"
        stroke="#D9480F"
        strokeWidth={1.8}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
