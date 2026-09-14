import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { FileImage, FileVideo, ShieldAlert, Sparkles } from "lucide-react";
import { useState } from "react";
import { analyzeMedia, USING_MOCK_DATA } from "@/lib/api";
import { MOCK_ANALYSES } from "@/lib/mockData";
import type { MediaType } from "@/lib/types";
import { DropZone } from "@/components/upload/DropZone";
import { FilePreview, detectMediaType } from "@/components/upload/FilePreview";
import { MockBanner } from "@/components/common/MockBanner";

const DEMO_FILES = Object.values(MOCK_ANALYSES).map((a) => ({
  id: a.id,
  filename: a.filename,
  mediaType: a.mediaType,
  size: a.metadata.size,
  duration: a.metadata.duration,
  resolution: a.metadata.resolution,
  verdict: a.verdict,
  confidence: a.confidence,
}));

export const Route = createFileRoute("/analyze")({
  head: () => ({
    meta: [
      { title: "Analyze Media — DeepFake Shield" },
      {
        name: "description",
        content:
          "Upload a video, image or audio file for AI-assisted forensic authenticity analysis.",
      },
      { property: "og:title", content: "Analyze Media — DeepFake Shield" },
      {
        property: "og:description",
        content: "Submit digital media for AI-assisted forensic authenticity analysis.",
      },
    ],
  }),
  component: AnalyzePage,
});

function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  async function handleAnalyze() {
    if (!file) return;
    setSubmitting(true);
    try {
      const { analysisId } = await analyzeMedia({
        file,
        filename: file.name,
        mediaType: detectMediaType(file),
        sizeBytes: file.size,
      });
      navigate({ to: "/analysis/$id/processing", params: { id: analysisId } });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDemo(id: string, filename: string, mediaType: MediaType) {
    await analyzeMedia({ filename, mediaType, sizeBytes: 19_300_000 });
    navigate({ to: "/analysis/$id/processing", params: { id } });
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-14">
      <div className="animate-rise">
        <p className="label-caps">Intake</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          Analyze Digital Media
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          Upload an image, video, or audio file for AI-assisted forensic analysis. The video and
          image workflows are fully implemented; the audio pipeline is queued for release.
        </p>
      </div>

      <div className="mt-8 space-y-6">
        <MockBanner />

        {file ? (
          <FilePreview file={file} onRemove={() => setFile(null)} onAnalyze={handleAnalyze} />
        ) : (
          <DropZone onFile={setFile} />
        )}

        {!file && USING_MOCK_DATA ? (
          <div>
            <div className="flex items-center gap-3">
              <Sparkles className="h-4 w-4 text-primary" />
              <h2 className="label-caps">Or try a demo analysis</h2>
              <div className="h-px flex-1 bg-border" />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {DEMO_FILES.map((demo) => (
                <button
                  key={demo.id}
                  type="button"
                  onClick={() => handleDemo(demo.id, demo.filename, demo.mediaType)}
                  className="group rounded-lg border border-border bg-panel p-4 text-left transition-colors hover:border-primary/50"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border bg-muted/40">
                      {demo.mediaType === "image" ? (
                        <FileImage className="h-4 w-4 text-primary" />
                      ) : (
                        <FileVideo className="h-4 w-4 text-primary" />
                      )}
                    </span>
                    <span
                      className={
                        demo.verdict === "Likely Manipulated"
                          ? "rounded-sm border border-severity-high/40 bg-severity-high/10 px-2 py-0.5 font-mono text-[10px] tracking-[0.12em] text-severity-high"
                          : "rounded-sm border border-severity-low/40 bg-severity-low/10 px-2 py-0.5 font-mono text-[10px] tracking-[0.12em] text-severity-low"
                      }
                    >
                      {demo.verdict.toUpperCase()} · {demo.confidence.toFixed(1)}%
                    </span>
                  </div>
                  <p className="mt-3 truncate font-mono text-sm">{demo.filename}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {demo.size} · {demo.duration} · {demo.resolution}
                  </p>
                  <p className="mt-3 text-xs font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                    Run demo analysis →
                  </p>
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {submitting ? (
          <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
          </div>
        ) : null}

        <div className="flex items-start gap-2.5 rounded-md border border-border bg-panel px-4 py-3">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <p className="text-xs leading-relaxed text-muted-foreground">
            Files are processed as forensic evidence. Uploaded media should never be executed.
            Maintain chain-of-custody records outside this tool for any case work.
          </p>
        </div>
      </div>
    </div>
  );
}
