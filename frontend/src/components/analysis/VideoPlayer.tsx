import { Maximize2, Pause, Play, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { formatTimestamp } from "@/lib/mockData";

/**
 * Deterministic preview surface. The demo build has no decodable media file, so
 * playback is simulated against the analysis duration. Swapping in a real
 * <video src> element later keeps the same props and control layout.
 */
export function VideoPlayer({
  posterUrl,
  filename,
  duration,
  currentTime,
  onTimeChange,
}: {
  posterUrl: string;
  filename: string;
  duration: number;
  currentTime: number;
  onTimeChange: (t: number) => void;
}) {
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(true);
  const [volume, setVolume] = useState(60);
  const containerRef = useRef<HTMLDivElement>(null);
  const timeRef = useRef(currentTime);
  timeRef.current = currentTime;

  useEffect(() => {
    if (!playing) return;
    const interval = setInterval(() => {
      const next = timeRef.current + 0.1;
      onTimeChange(next >= duration ? 0 : Number(next.toFixed(2)));
    }, 100);
    return () => clearInterval(interval);
  }, [playing, duration, onTimeChange]);

  return (
    <div ref={containerRef} className="overflow-hidden rounded-md border border-border bg-black">
      <div className="relative aspect-video">
        <img
          src={posterUrl}
          alt={`Preview frame of ${filename}`}
          className="h-full w-full object-cover"
          style={{ filter: playing ? "contrast(1.05)" : "none" }}
        />
        {playing ? (
          <div className="pointer-events-none absolute inset-0 overflow-hidden">
            <div className="animate-scan h-10 w-full bg-gradient-to-b from-transparent via-primary/15 to-transparent" />
          </div>
        ) : null}
        <div className="pointer-events-none absolute left-3 top-3 flex items-center gap-2 rounded-sm border border-border-strong bg-background/75 px-2 py-1 backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          <span className="font-mono text-[10px] tracking-[0.14em]">FRAME PREVIEW</span>
        </div>
        <div className="pointer-events-none absolute right-3 top-3 rounded-sm border border-border-strong bg-background/75 px-2 py-1 font-mono text-[10px] tabular-nums backdrop-blur">
          {formatTimestamp(currentTime)} · F{Math.round(currentTime * 30)}
        </div>
      </div>

      <div className="border-t border-border bg-panel px-3 py-2.5">
        <input
          type="range"
          min={0}
          max={duration}
          step={0.1}
          value={currentTime}
          onChange={(e) => onTimeChange(Number(e.target.value))}
          aria-label="Seek"
          className="h-1 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
        />
        <div className="mt-2.5 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3">
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={() => setPlaying((p) => !p)}
              aria-label={playing ? "Pause" : "Play"}
              className="grid h-8 w-8 place-items-center rounded-md border border-border text-foreground transition-colors hover:border-primary/50 hover:text-primary"
            >
              {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            </button>
            <button
              type="button"
              onClick={() => setMuted((m) => !m)}
              aria-label={muted ? "Unmute" : "Mute"}
              className="grid h-8 w-8 place-items-center rounded-md border border-border text-muted-foreground transition-colors hover:text-foreground"
            >
              {muted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
            </button>
            <input
              type="range"
              min={0}
              max={100}
              value={muted ? 0 : volume}
              onChange={(e) => {
                setVolume(Number(e.target.value));
                setMuted(Number(e.target.value) === 0);
              }}
              aria-label="Volume"
              className="hidden h-1 w-20 cursor-pointer appearance-none rounded-full bg-muted accent-primary sm:block"
            />
          </div>
          <span className="min-w-0 truncate text-center font-mono text-xs tabular-nums text-muted-foreground">
            {formatTimestamp(currentTime)} / {formatTimestamp(duration)}
          </span>
          <button
            type="button"
            aria-label="Fullscreen"
            onClick={() => containerRef.current?.requestFullscreen?.()}
            className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-border text-muted-foreground transition-colors hover:text-foreground"
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
