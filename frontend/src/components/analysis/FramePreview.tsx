import { ImageOff } from "lucide-react";
import type { SuspiciousFrame } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Frame image at its native aspect ratio, so heatmaps and face boxes stay aligned. */
export function FrameImage({
  frame,
  alt,
  showFaceBox = false,
  className,
  imageClassName,
  children,
}: {
  frame: SuspiciousFrame;
  alt: string;
  showFaceBox?: boolean;
  className?: string;
  imageClassName?: string;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={cn("relative w-full overflow-hidden bg-black", className)}
      style={{ aspectRatio: frame.aspectRatio ?? 16 / 9 }}
    >
      {frame.thumbnailUrl ? (
        <img
          src={frame.thumbnailUrl}
          alt={alt}
          loading="lazy"
          className={cn("h-full w-full object-cover", imageClassName)}
        />
      ) : (
        <div className="grid h-full w-full place-items-center text-muted-foreground">
          <ImageOff className="h-6 w-6" aria-label="Frame image unavailable" />
        </div>
      )}
      {children}
      {showFaceBox && frame.faceBox ? (
        <div
          aria-hidden
          className={cn(
            "pointer-events-none absolute rounded-sm border",
            frame.flagged ? "border-severity-high/80" : "border-primary/70",
          )}
          style={{
            left: `${frame.faceBox.left}%`,
            top: `${frame.faceBox.top}%`,
            width: `${frame.faceBox.width}%`,
            height: `${frame.faceBox.height}%`,
          }}
        />
      ) : null}
    </div>
  );
}
