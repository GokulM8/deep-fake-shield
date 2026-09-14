import { ChevronRight } from "lucide-react";
import type { SuspiciousFrame } from "@/lib/types";
import { SeverityBadge } from "@/components/common/primitives";

export function SuspiciousFrames({
  frames,
  onSelect,
}: {
  frames: SuspiciousFrame[];
  onSelect: (frame: SuspiciousFrame) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {frames.map((frame) => (
        <button
          key={frame.id}
          type="button"
          onClick={() => onSelect(frame)}
          className="group panel overflow-hidden text-left transition-all duration-300 hover:border-border-strong hover:shadow-panel"
        >
          <div className="relative aspect-video overflow-hidden bg-black">
            <img
              src={frame.thumbnailUrl}
              alt={`Frame ${frame.frame}`}
              loading="lazy"
              className="h-full w-full object-cover opacity-80 transition-transform duration-500 group-hover:scale-[1.03]"
            />
            <div className="absolute left-2 top-2">
              <SeverityBadge severity={frame.severity} />
            </div>
            <div className="absolute bottom-2 right-2 rounded-sm border border-border-strong bg-background/80 px-1.5 py-0.5 font-mono text-[10px] tabular-nums backdrop-blur">
              {frame.timestamp}
            </div>
          </div>
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 p-3.5">
            <div className="min-w-0">
              <p className="truncate font-mono text-sm">
                Frame {String(frame.frame).padStart(3, "0")}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Score {frame.score}% · {frame.suspiciousRegion}
              </p>
            </div>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
          </div>
        </button>
      ))}
    </div>
  );
}
