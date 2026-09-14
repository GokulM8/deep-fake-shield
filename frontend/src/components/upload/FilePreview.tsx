import { FileAudio, FileImage, FileVideo, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { MediaType } from "@/lib/types";
import { Panel } from "@/components/common/primitives";

export function detectMediaType(file: File): MediaType {
  if (file.type.startsWith("video")) return "video";
  if (file.type.startsWith("audio")) return "audio";
  return "image";
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FilePreview({
  file,
  onRemove,
  onAnalyze,
}: {
  file: File;
  onRemove: () => void;
  onAnalyze: () => void;
}) {
  const mediaType = detectMediaType(file);
  const [url, setUrl] = useState<string | null>(null);
  const [duration, setDuration] = useState<string | null>(null);

  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  const Icon = mediaType === "video" ? FileVideo : mediaType === "audio" ? FileAudio : FileImage;
  const supported = mediaType !== "audio";

  return (
    <Panel className="animate-rise p-5">
      <div className="grid gap-5 md:grid-cols-[minmax(0,260px)_minmax(0,1fr)]">
        <div className="overflow-hidden rounded-md border border-border bg-black">
          {url && mediaType === "video" ? (
            <video
              src={url}
              className="aspect-video w-full object-cover"
              muted
              playsInline
              preload="metadata"
              onLoadedMetadata={(e) => {
                const d = e.currentTarget.duration;
                if (Number.isFinite(d)) {
                  setDuration(
                    `${String(Math.floor(d / 60)).padStart(2, "0")}:${String(
                      Math.floor(d % 60),
                    ).padStart(2, "0")}`,
                  );
                }
              }}
            />
          ) : url && mediaType === "image" ? (
            <img src={url} alt={file.name} className="aspect-video w-full object-cover" />
          ) : (
            <div className="grid aspect-video place-items-center">
              <Icon className="h-8 w-8 text-muted-foreground" />
            </div>
          )}
        </div>

        <div className="min-w-0">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
            <div className="min-w-0">
              <p className="truncate font-mono text-sm">{file.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {formatBytes(file.size)} · {duration ?? "—"} ·{" "}
                <span className="text-primary">{mediaType.toUpperCase()}</span>
              </p>
            </div>
            <button
              type="button"
              onClick={onRemove}
              aria-label="Remove file"
              className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-border text-muted-foreground transition-colors hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          {!supported ? (
            <p className="mt-4 rounded-md border border-severity-medium/40 bg-severity-medium/10 px-3 py-2 text-xs text-severity-medium">
              AUDIO analysis is a planned modality. Video and image workflows are implemented in
              this build.
            </p>
          ) : null}

          <button
            type="button"
            disabled={!supported}
            onClick={onAnalyze}
            className="mt-5 w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto sm:px-6"
          >
            Start Analysis
          </button>

          <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
            Files are processed as forensic evidence. Uploaded media should never be executed.
          </p>
        </div>
      </div>
    </Panel>
  );
}
