import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Check, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import sampleFrame from "@/assets/sample-frame.jpg";
import { IMAGE_PROCESSING_STAGES, PROCESSING_STAGES } from "@/lib/mockData";
import { getAnalysis, USING_MOCK_DATA } from "@/lib/api";
import { Panel } from "@/components/common/primitives";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/analysis/$id/processing")({
  head: () => ({
    meta: [
      { title: "Analysis In Progress — DeepFake Shield" },
      { name: "description", content: "Forensic analysis pipeline progress for submitted media." },
      { property: "og:title", content: "Analysis In Progress — DeepFake Shield" },
      { property: "og:description", content: "Forensic analysis pipeline progress." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ProcessingPage,
});

const TOTAL_FRAMES = 360;
const STEP_MS = 700;

function ProcessingPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const [step, setStep] = useState(4);
  const [frame, setFrame] = useState(112);
  const [submitted, setSubmitted] = useState<{
    filename: string;
    mediaType: string;
  } | null>(null);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(`dfs:submitted:${id}`);
      if (raw) setSubmitted(JSON.parse(raw));
    } catch {
      /* no submission context */
    }
  }, [id]);

  const isImage = submitted?.mediaType === "image";
  const stages = isImage ? IMAGE_PROCESSING_STAGES : PROCESSING_STAGES;

  useEffect(() => {
    if (USING_MOCK_DATA) return;
    let active = true;
    const poll = async () => {
      try {
        const analysis = await getAnalysis(id);
        if (!active) return;
        if (analysis.status === "failed") {
          setStep(stages.length);
          return;
        }
        if (analysis.status === "completed") {
          navigate({ to: "/analysis/$id", params: { id } });
        }
      } catch {
        // Keep the processing view visible while the backend is unavailable.
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 800);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [id, navigate, stages.length]);

  useEffect(() => {
    if (!USING_MOCK_DATA) return;
    const stageTimer = setInterval(() => {
      setStep((s) => {
        if (s >= stages.length) {
          clearInterval(stageTimer);
          return s;
        }
        return s + 1;
      });
    }, STEP_MS);
    return () => clearInterval(stageTimer);
  }, [stages.length]);

  useEffect(() => {
    const frameTimer = setInterval(() => {
      setFrame((f) => Math.min(TOTAL_FRAMES, f + 7));
    }, 90);
    return () => clearInterval(frameTimer);
  }, []);

  useEffect(() => {
    if (step < stages.length) return;
    const t = setTimeout(() => navigate({ to: "/analysis/$id", params: { id } }), 900);
    return () => clearTimeout(t);
  }, [step, id, navigate, stages.length]);

  const progress = Math.min(100, Math.round((step / stages.length) * 100));

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="relative grid h-2 w-2 place-items-center">
              <span className="absolute h-2 w-2 animate-pulse-ring rounded-full bg-primary" />
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            </span>
            <p className="label-caps text-primary">Analysis in progress</p>
          </div>
          <h1 className="mt-2 truncate font-mono text-2xl font-semibold sm:text-3xl">{id}</h1>
          <p className="mt-1.5 truncate text-sm text-muted-foreground">
            {submitted?.filename ?? (isImage ? "portrait_photo.jpg" : "deepfake_sample.mp4")}
          </p>
        </div>
        <span className="shrink-0 font-mono text-3xl tabular-nums text-primary">{progress}%</span>
      </div>

      <div className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,380px)]">
        <Panel className="p-5 sm:p-6">
          <ol className="space-y-1">
            {stages.map((stage, i) => {
              const done = i < step;
              const active = i === step;
              return (
                <li
                  key={stage.id}
                  className={cn(
                    "grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-3 py-2.5 transition-colors duration-500",
                    active && "bg-primary/[0.07]",
                  )}
                >
                  <span
                    className={cn(
                      "grid h-5 w-5 shrink-0 place-items-center rounded-full border",
                      done && "border-primary/50 bg-primary/15 text-primary",
                      active && "border-primary text-primary",
                      !done && !active && "border-border text-muted-foreground",
                    )}
                  >
                    {done ? (
                      <Check className="h-3 w-3" />
                    ) : active ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-50" />
                    )}
                  </span>
                  <span
                    className={cn(
                      "min-w-0 truncate text-sm transition-colors",
                      done || active ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {stage.label}
                  </span>
                  <span className="label-caps shrink-0">
                    {done ? "Done" : active ? "Running" : "Queued"}
                  </span>
                </li>
              );
            })}
          </ol>

          <div className="mt-6 border-t border-border pt-5">
            <div className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-4">
              <span className="min-w-0 truncate text-sm">
                {isImage ? "Analyzing image" : "Analyzing video"}
              </span>
              <span className="shrink-0 font-mono text-sm tabular-nums text-muted-foreground">
                {isImage ? `Tile ${frame} / ${TOTAL_FRAMES}` : `Frame ${frame} / ${TOTAL_FRAMES}`}
              </span>
            </div>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </Panel>

        <Panel className="overflow-hidden p-0">
          <div className="relative aspect-video overflow-hidden bg-black">
            <img
              src={sampleFrame}
              alt="Media under analysis"
              loading="lazy"
              className="h-full w-full object-cover opacity-70"
            />
            <div className="pointer-events-none absolute inset-0 overflow-hidden">
              <div className="animate-scan h-12 w-full bg-gradient-to-b from-transparent via-primary/25 to-transparent" />
            </div>
            <div className="pointer-events-none absolute inset-0 grid-backdrop opacity-40" />
          </div>
          <div className="space-y-2.5 p-4">
            <p className="label-caps">Live extraction preview</p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              {isImage
                ? "The image is decoded, face regions are cropped and normalised, then scored by the spatial and frequency models before evidence fusion."
                : "Frames are decoded, face regions are cropped and normalised, then scored by the frame and temporal models before evidence fusion."}
            </p>
          </div>
        </Panel>
      </div>
    </div>
  );
}
