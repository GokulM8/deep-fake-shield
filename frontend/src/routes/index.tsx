import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Activity,
  AudioLines,
  Boxes,
  Eye,
  FileDigit,
  Fingerprint,
  Image as ImageIcon,
  ScanFace,
  Sparkles,
  Video,
  type LucideIcon,
} from "lucide-react";
import heroGrid from "@/assets/hero-grid.jpg";
import { Panel } from "@/components/common/primitives";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "DeepFake Shield — Detect. Localize. Explain. Investigate." },
      {
        name: "description",
        content:
          "AI-assisted digital media authenticity and forensic analysis. Frame-level detection, timeline localization and explainable evidence for video.",
      },
      {
        property: "og:title",
        content: "DeepFake Shield — Detect. Localize. Explain. Investigate.",
      },
      {
        property: "og:description",
        content: "AI-assisted digital media authenticity and forensic analysis.",
      },
    ],
  }),
  component: Landing,
});

const MODALITIES = [
  {
    icon: Video,
    name: "VIDEO",
    status: "ACTIVE",
    points: ["Temporal analysis", "Frame-level detection", "Suspicious timestamp localization"],
  },
  {
    icon: ImageIcon,
    name: "IMAGE",
    status: "COMING NEXT",
    points: ["Visual manipulation detection", "Face-region analysis", "Explainable heatmaps"],
  },
  {
    icon: AudioLines,
    name: "AUDIO",
    status: "COMING NEXT",
    points: ["Synthetic speech detection", "Spectral analysis", "Audio segment analysis"],
  },
];

const SIGNALS: { icon: LucideIcon; label: string; body: string; weight: number }[] = [
  {
    icon: Eye,
    label: "Visual anomalies",
    body: "Spatial artifacts across sampled frames.",
    weight: 91,
  },
  {
    icon: Activity,
    label: "Temporal inconsistencies",
    body: "Identity drift between frame windows.",
    weight: 88,
  },
  {
    icon: ScanFace,
    label: "Face-region anomalies",
    body: "Boundary and blending irregularities.",
    weight: 86,
  },
  {
    icon: Boxes,
    label: "Compression signals",
    body: "Recompression and block consistency.",
    weight: 74,
  },
  {
    icon: FileDigit,
    label: "Metadata",
    body: "Container traces and editing history.",
    weight: 34,
  },
  {
    icon: Fingerprint,
    label: "Provenance",
    body: "Content Credentials and C2PA checks.",
    weight: 18,
  },
];

function Landing() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <img
          src={heroGrid}
          alt=""
          aria-hidden
          width={1920}
          height={1088}
          className="absolute inset-0 h-full w-full object-cover opacity-50"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-background/70 via-background/85 to-background" />
        <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28">
          <div className="animate-rise max-w-3xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5">
              <Sparkles className="h-3.5 w-3.5 shrink-0 text-primary" />
              <span className="label-caps">Video forensics · Evidence-first</span>
            </span>
            <h1 className="mt-6 font-display text-4xl font-semibold tracking-tight sm:text-6xl">
              DEEPFAKE SHIELD
            </h1>
            <p className="mt-4 font-mono text-sm tracking-[0.2em] text-primary sm:text-base">
              Detect. Localize. Explain. Investigate.
            </p>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground">
              AI-assisted digital media authenticity and forensic analysis.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/analyze"
                className="inline-flex items-center justify-center rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
              >
                Analyze Media
              </Link>
              <Link
                to="/investigations"
                className="inline-flex items-center justify-center rounded-md border border-border-strong px-6 py-3 text-sm font-medium transition-colors hover:border-primary/50 hover:text-primary"
              >
                Explore Investigation
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Modalities */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20">
        <div className="grid gap-3 md:grid-cols-3">
          {MODALITIES.map((m) => {
            const active = m.status === "ACTIVE";
            const Icon = m.icon;
            return (
              <Panel
                key={m.name}
                className={`p-6 transition-colors duration-300 hover:border-border-strong ${
                  active ? "border-primary/30" : ""
                }`}
              >
                <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border bg-muted/40">
                    <Icon
                      className={`h-4 w-4 ${active ? "text-primary" : "text-muted-foreground"}`}
                    />
                  </span>
                  <h2 className="min-w-0 truncate font-display text-sm font-semibold tracking-[0.14em]">
                    {m.name}
                  </h2>
                  <span
                    className={`shrink-0 rounded-sm border px-1.5 py-0.5 font-mono text-[10px] tracking-[0.14em] ${
                      active
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "border-border text-muted-foreground"
                    }`}
                  >
                    {m.status}
                  </span>
                </div>
                <ul className="mt-5 space-y-2.5">
                  {m.points.map((p) => (
                    <li key={p} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary/70" />
                      {p}
                    </li>
                  ))}
                </ul>
              </Panel>
            );
          })}
        </div>
      </section>

      {/* Why */}
      <section className="border-y border-border bg-panel/40">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="min-w-0">
              <p className="label-caps">Why DeepFake Shield?</p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">
                A single verdict hides the reasoning
              </h2>
              <p className="mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">
                Instead of returning only real or fake, DeepFake Shield surfaces every evidence
                signal separately, so an investigator can see what the assessment rests on — and
                where it is weak.
              </p>
            </div>

            <div className="grid gap-2.5 sm:grid-cols-2">
              {SIGNALS.map((s) => {
                const Icon = s.icon;
                return (
                  <div
                    key={s.label}
                    className="group rounded-md border border-border bg-card p-4 transition-colors hover:border-border-strong"
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className="h-4 w-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
                      <span className="min-w-0 truncate text-sm font-medium">{s.label}</span>
                    </div>
                    <p className="mt-1.5 text-xs text-muted-foreground">{s.body}</p>
                    <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary/70 transition-[width] duration-700"
                        style={{ width: `${s.weight}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <Panel className="relative overflow-hidden p-8 text-center sm:p-14">
          <div className="pointer-events-none absolute inset-0 grid-backdrop opacity-40" />
          <div className="relative">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Start a forensic analysis
            </h2>
            <p className="mx-auto mt-3 max-w-md text-sm text-muted-foreground">
              Submit a video file and review frame-level evidence, timeline localization and
              explainable attention output.
            </p>
            <Link
              to="/analyze"
              className="mt-7 inline-flex items-center justify-center rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Analyze Media
            </Link>
          </div>
        </Panel>
      </section>
    </div>
  );
}
