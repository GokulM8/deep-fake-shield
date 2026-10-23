import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

const ACCEPTED = [
  { label: "Image", exts: "JPG PNG WEBP" },
  { label: "Video", exts: "MP4 MOV AVI WEBM" },
  { label: "Audio", exts: "WAV MP3 FLAC M4A" },
];

export function DropZone({ onFile }: { onFile: (file: File) => void }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) onFile(file);
      }}
      className={cn(
        "relative overflow-hidden rounded-lg border border-dashed p-8 text-center transition-colors duration-300 sm:p-14",
        dragging ? "border-primary bg-primary/[0.06]" : "border-border-strong bg-panel",
      )}
    >
      <div className="pointer-events-none absolute inset-0 grid-backdrop opacity-40" />
      <div className="relative">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-lg border border-border bg-muted/40">
          <UploadCloud className="h-6 w-6 text-primary" />
        </span>
        <h2 className="mt-5 font-display text-lg font-semibold tracking-[0.08em]">
          DROP MEDIA HERE
        </h2>
        <p className="mt-1.5 text-sm text-muted-foreground">Drag &amp; drop your file, or</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-4 rounded-md border border-border-strong bg-secondary px-4 py-2.5 text-sm font-medium transition-colors hover:border-primary/50 hover:text-primary"
        >
          Select File
        </button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept="image/*,video/*,audio/*"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
            e.target.value = "";
          }}
        />

        <div className="mx-auto mt-8 grid max-w-lg gap-2 sm:grid-cols-3">
          {ACCEPTED.map((a) => (
            <div key={a.label} className="rounded-md border border-border px-3 py-2.5">
              <p className="label-caps">{a.label}</p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">{a.exts}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
