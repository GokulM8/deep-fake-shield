import { Maximize2, Pause, Play, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { formatTimestamp } from "@/lib/mockData";

export function VideoPlayer({
  src,
  posterUrl,
  filename,
  duration,
  currentTime,
  onTimeChange,
  onDurationChange,
}: {
  src?: string;
  posterUrl: string;
  filename: string;
  duration: number;
  currentTime: number;
  onTimeChange: (t: number) => void;
  onDurationChange?: (duration: number) => void;
}) {
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(true);
  const [volume, setVolume] = useState(60);
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (playing) void video.play();
    else video.pause();
  }, [playing]);

  useEffect(() => {
    if (videoRef.current) videoRef.current.currentTime = currentTime;
  }, [currentTime]);

  return (
    <div ref={containerRef} className="overflow-hidden rounded-md border border-border bg-black">
      <div className="relative aspect-video">
        {src ? (
          <video
            ref={videoRef}
            src={src}
            poster={posterUrl}
            muted={muted}
            playsInline
            className="h-full w-full object-cover"
            onLoadedMetadata={(event) => onDurationChange?.(event.currentTarget.duration)}
            onTimeUpdate={(event) => onTimeChange(event.currentTarget.currentTime)}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
          />
        ) : (
          <img
            src={posterUrl}
            alt={`Preview frame of ${filename}`}
            className="h-full w-full object-cover"
          />
        )}
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
          onChange={(e) => {
            const nextTime = Number(e.target.value);
            onTimeChange(nextTime);
            if (videoRef.current) videoRef.current.currentTime = nextTime;
          }}
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
