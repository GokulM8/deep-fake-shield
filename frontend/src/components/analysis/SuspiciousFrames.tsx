import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { SuspiciousFrame } from "@/lib/types";
import { SeverityBadge } from "@/components/common/primitives";
import { FrameImage } from "./FramePreview";

const COLLAPSED_FRAMES = 6;

export function SuspiciousFrames({
  frames,
  onSelect,
  note,
}: {
  frames: SuspiciousFrame[];
  onSelect: (frame: SuspiciousFrame) => void;
  /** Shown above the grid, e.g. how frame flags relate to the verdict. */
  note?: string | null;
}) {
  const [expanded, setExpanded] = useState(false);
  // Frames arrive sorted by score; always show every flagged frame, and at least two rows.
  const collapsedCount = Math.max(COLLAPSED_FRAMES, frames.filter((frame) => frame.flagged).length);
  const visible = expanded ? frames : frames.slice(0, collapsedCount);
  const hidden = frames.length - collapsedCount;

  return (
    <div>
      {note ? (
        <p className="mb-4 border-l-2 border-primary/40 pl-3 text-xs leading-relaxed text-muted-foreground">
          {note}
        </p>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {visible.map((frame) => (
          <button
            key={frame.id}
            type="button"
            onClick={() => onSelect(frame)}
            className="group panel overflow-hidden text-left transition-all duration-300 hover:border-border-strong hover:shadow-panel"
          >
            <FrameImage
              frame={frame}
              alt={`Frame ${frame.frame}`}
              showFaceBox
              imageClassName="opacity-80 transition-transform duration-500 group-hover:scale-[1.03]"
            >
              <div className="absolute left-2 top-2">
                <SeverityBadge severity={frame.severity} />
              </div>
              <div className="absolute bottom-2 right-2 rounded-sm border border-border-strong bg-background/80 px-1.5 py-0.5 font-mono text-[10px] tabular-nums backdrop-blur">
                {frame.timestamp}
              </div>
            </FrameImage>
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
      {hidden > 0 ? (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="mt-4 inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 font-mono text-xs text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground"
        >
          <ChevronDown
            className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`}
          />
          {expanded
            ? "Show fewer frames"
            : `Show all ${frames.length} sampled frames (${hidden} more)`}
        </button>
      ) : null}
    </div>
  );
}
