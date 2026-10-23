import { useState } from "react";
import type { TimelinePoint } from "@/lib/types";
import { cn } from "@/lib/utils";

function toneFor(score: number) {
  if (score >= 75) return "var(--severity-high)";
  if (score >= 45) return "var(--severity-medium)";
  return "var(--severity-low)";
}

export function VideoTimeline({
  timeline,
  currentTime,
  onSeek,
}: {
  timeline: TimelinePoint[];
  currentTime: number;
  onSeek: (time: number) => void;
}) {
  const [hovered, setHovered] = useState<TimelinePoint | null>(null);
  const duration = timeline[timeline.length - 1]?.time ?? 1;

  return (
    <div>
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-4">
        <div className="min-w-0">
          <p className="label-caps">Frame Authenticity Timeline</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Per-frame manipulation probability. Select a point to inspect that frame.
          </p>
        </div>
        <div className="shrink-0 text-right font-mono text-xs tabular-nums text-muted-foreground">
          {hovered ? (
            <>
              <span className="text-foreground">{hovered.score}%</span> · frame {hovered.frame}
            </>
          ) : (
            <>00:00 → 00:{String(Math.round(duration)).padStart(2, "0")}</>
          )}
        </div>
      </div>

      <div className="relative mt-4 flex h-32 items-end gap-[2px] overflow-hidden rounded-md border border-border bg-muted/20 p-2 sm:gap-1">
        <div className="pointer-events-none absolute inset-x-0 top-[25%] border-t border-dashed border-border/70" />
        {timeline.map((point) => {
          const active = Math.abs(point.time - currentTime) < 0.26;
          return (
            <button
              key={point.frame}
              type="button"
              onMouseEnter={() => setHovered(point)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onSeek(point.time)}
              aria-label={`Frame ${point.frame} at ${point.time}s, score ${point.score}%`}
              className={cn(
                "group relative flex-1 rounded-sm transition-all duration-300 hover:opacity-100",
                active ? "opacity-100" : "opacity-75",
              )}
              style={{
                height: `${Math.max(6, point.score)}%`,
                background: toneFor(point.score),
                boxShadow: active ? "0 0 0 1px var(--foreground)" : undefined,
              }}
            />
          );
        })}
        <div
          className="pointer-events-none absolute bottom-0 top-0 w-px bg-foreground/70 transition-[left] duration-150"
          style={{ left: `${(currentTime / duration) * 100}%` }}
        />
      </div>

      <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-muted-foreground">
        <span>00:00</span>
        <span>00:06</span>
        <span>00:12</span>
      </div>

      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
        {[
          { label: "Low risk", color: "var(--severity-low)" },
          { label: "Elevated", color: "var(--severity-medium)" },
          { label: "High risk", color: "var(--severity-high)" },
        ].map((l) => (
          <span key={l.label} className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-sm" style={{ background: l.color }} />
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}
