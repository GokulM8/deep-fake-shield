import { useState } from "react";

/**
 * Grad-CAM style visualisation.
 *
 * When the backend returns a real Grad-CAM PNG, pass it as `heatmapUrl` and the
 * generated overlay below is replaced automatically — no layout change needed.
 */
export function HeatmapViewer({
  frameUrl,
  heatmapUrl,
  intensity: initialIntensity = 70,
}: {
  frameUrl: string;
  heatmapUrl: string | null;
  intensity?: number;
}) {
  const [intensity, setIntensity] = useState(initialIntensity);

  return (
    <div className="space-y-3">
      <div className="relative aspect-video overflow-hidden rounded-md border border-border bg-black">
        <img
          src={frameUrl}
          alt="Analyzed frame"
          loading="lazy"
          className="h-full w-full object-cover opacity-70 grayscale"
        />
        {heatmapUrl ? (
          <img
            src={heatmapUrl}
            alt="Model attention heatmap"
            loading="lazy"
            className="absolute inset-0 h-full w-full object-cover mix-blend-screen transition-opacity duration-500"
            style={{ opacity: intensity / 100 }}
          />
        ) : (
          <div
            aria-hidden
            className="absolute inset-0 transition-opacity duration-500 mix-blend-screen"
            style={{
              opacity: intensity / 100,
              backgroundImage: [
                "radial-gradient(circle at 47% 41%, oklch(0.7 0.2 30 / 0.95), transparent 16%)",
                "radial-gradient(circle at 41% 38%, oklch(0.8 0.19 75 / 0.85), transparent 12%)",
                "radial-gradient(circle at 53% 39%, oklch(0.8 0.19 75 / 0.85), transparent 12%)",
                "radial-gradient(circle at 47% 62%, oklch(0.68 0.21 28 / 0.9), transparent 15%)",
                "radial-gradient(ellipse at 47% 55%, oklch(0.62 0.16 200 / 0.5), transparent 38%)",
                "radial-gradient(ellipse at 47% 50%, oklch(0.5 0.14 250 / 0.4), transparent 55%)",
              ].join(","),
            }}
          />
        )}
        <div className="pointer-events-none absolute inset-0 grid-backdrop opacity-30" />
        <span className="absolute left-3 top-3 rounded-sm border border-border-strong bg-background/80 px-2 py-1 font-mono text-[10px] tracking-[0.14em] backdrop-blur">
          GRAD-CAM · DEMO RENDER
        </span>
      </div>

      <label className="flex items-center gap-3">
        <span className="label-caps shrink-0">Overlay</span>
        <input
          type="range"
          min={0}
          max={100}
          value={intensity}
          onChange={(e) => setIntensity(Number(e.target.value))}
          className="h-1 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
        />
        <span className="w-10 shrink-0 text-right font-mono text-xs tabular-nums">
          {intensity}%
        </span>
      </label>
    </div>
  );
}
