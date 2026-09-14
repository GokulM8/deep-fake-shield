import { X } from "lucide-react";
import { useEffect } from "react";
import type { SuspiciousFrame } from "@/lib/types";
import { SeverityBadge } from "@/components/common/primitives";
import { HeatmapViewer } from "./HeatmapViewer";

export function FrameInspector({
  frame,
  onClose,
}: {
  frame: SuspiciousFrame | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!frame) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [frame, onClose]);

  if (!frame) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto bg-background/80 p-4 backdrop-blur-sm sm:p-8">
      <div className="absolute inset-0" onClick={onClose} aria-hidden role="presentation" />
      <div className="animate-rise relative w-full max-w-5xl rounded-lg border border-border-strong bg-card shadow-panel">
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4 border-b border-border p-5">
          <div className="min-w-0">
            <p className="label-caps">Frame Analysis</p>
            <h3 className="mt-1 truncate text-xl font-semibold">
              Frame {String(frame.frame).padStart(3, "0")} · {frame.timestamp}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close frame inspector"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border text-muted-foreground transition-colors hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid gap-5 p-5 lg:grid-cols-2">
          <div className="space-y-3">
            <p className="label-caps">Original Frame</p>
            <div className="aspect-video overflow-hidden rounded-md border border-border bg-black">
              <img
                src={frame.thumbnailUrl}
                alt={`Original frame ${frame.frame}`}
                loading="lazy"
                className="h-full w-full object-cover"
              />
            </div>
          </div>
          <div className="space-y-3">
            <p className="label-caps">Model Attention Heatmap</p>
            <HeatmapViewer frameUrl={frame.thumbnailUrl} heatmapUrl={frame.heatmapUrl} />
          </div>
        </div>

        <div className="grid gap-3 border-t border-border p-5 sm:grid-cols-3">
          <div className="rounded-md border border-border bg-muted/30 p-4">
            <p className="label-caps">Frame Score</p>
            <p className="mt-1.5 font-mono text-2xl tabular-nums text-severity-high">
              {frame.score.toFixed(1)}%
            </p>
          </div>
          <div className="rounded-md border border-border bg-muted/30 p-4">
            <p className="label-caps">Suspicious Region</p>
            <p className="mt-1.5 text-sm">{frame.suspiciousRegion}</p>
          </div>
          <div className="rounded-md border border-border bg-muted/30 p-4">
            <p className="label-caps">Model Attention</p>
            <p className="mt-1.5 text-sm">{frame.modelAttention}</p>
          </div>
        </div>

        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4 border-t border-border p-5">
          <p className="min-w-0 text-sm leading-relaxed text-muted-foreground">
            {frame.explanation}{" "}
            <span className="text-foreground">
              Demonstration visualisation — not a real model output.
            </span>
          </p>
          <SeverityBadge severity={frame.severity} />
        </div>
      </div>
    </div>
  );
}
