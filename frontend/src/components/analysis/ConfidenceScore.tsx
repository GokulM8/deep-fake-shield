import { useEffect, useState } from "react";

export function ConfidenceScore({
  value,
  ringColor = "var(--primary)",
  size = 190,
  label = "Model Confidence",
}: {
  value: number;
  ringColor?: string;
  size?: number;
  label?: string;
}) {
  const [progress, setProgress] = useState(0);
  const stroke = 8;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    const t = setTimeout(() => setProgress(value), 120);
    return () => clearTimeout(t);
  }, [value]);

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--muted)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={ringColor}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - (progress / 100) * circumference}
          style={{ transition: "stroke-dashoffset 1.1s cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="font-display text-3xl font-semibold tabular-nums">{value.toFixed(1)}%</div>
        <div className="label-caps mt-1">{label}</div>
      </div>
    </div>
  );
}
