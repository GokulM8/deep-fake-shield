import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { Download, FileText, RotateCcw } from "lucide-react";
import { useState } from "react";
import sampleFrame from "@/assets/sample-frame.jpg";
import { analysisQuery, USING_MOCK_DATA } from "@/lib/api";
import type { SuspiciousFrame } from "@/lib/types";
import { MockBanner } from "@/components/common/MockBanner";
import { Panel, SectionTitle } from "@/components/common/primitives";
import { VerdictCard } from "@/components/analysis/VerdictCard";
import { EvidencePanel } from "@/components/analysis/EvidencePanel";
import { ModelScores } from "@/components/analysis/ModelScores";
import { VideoPlayer } from "@/components/analysis/VideoPlayer";
import { VideoTimeline } from "@/components/analysis/VideoTimeline";
import { SuspiciousFrames } from "@/components/analysis/SuspiciousFrames";
import { FrameInspector } from "@/components/analysis/FrameInspector";
import {
  CompressionPanel,
  FileInformation,
  MetadataPanel,
  ProvenancePanel,
} from "@/components/analysis/ForensicPanels";
import { FinalAssessment } from "@/components/analysis/FinalAssessment";

export const Route = createFileRoute("/analysis/$id/")({
  head: () => ({
    meta: [
      { title: "Forensic Analysis — DeepFake Shield" },
      {
        name: "description",
        content:
          "Frame-level evidence, model scores, timeline and forensic signals for the analyzed media.",
      },
      { property: "og:title", content: "Forensic Analysis — DeepFake Shield" },
      {
        property: "og:description",
        content: "Evidence-first forensic dashboard for analyzed digital media.",
      },
    ],
  }),
  loader: async ({ context, params }) => {
    await context.queryClient.ensureQueryData(analysisQuery(params.id));
  },
  component: AnalysisDashboard,
});

function AnalysisDashboard() {
  const { id } = Route.useParams();
  const { data: analysis } = useSuspenseQuery(analysisQuery(id));
  const [currentTime, setCurrentTime] = useState(0);
  const [inspected, setInspected] = useState<SuspiciousFrame | null>(null);

  const isVideo = analysis.mediaType === "video";
  const duration = analysis.timeline[analysis.timeline.length - 1]?.time ?? 12;

  function seekAndInspect(time: number) {
    setCurrentTime(time);
    const nearest = analysis.suspiciousFrames.reduce<SuspiciousFrame | null>((best, f) => {
      if (Math.abs(f.time - time) > 0.75) return best;
      if (!best || Math.abs(f.time - time) < Math.abs(best.time - time)) return f;
      return best;
    }, null);
    if (nearest) setInspected(nearest);
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12">
      {/* Header */}
      <div className="animate-rise grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
        <div className="min-w-0">
          <p className="label-caps">Forensic Analysis</p>
          <h1 className="mt-2 truncate text-2xl font-semibold tracking-tight sm:text-3xl">
            {analysis.filename}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 font-mono text-xs text-muted-foreground">
            <span>
              Analysis ID <span className="text-primary">{analysis.id}</span>
            </span>
            <span>{analysis.mediaType.toUpperCase()}</span>
          </div>
        </div>
        <span className="inline-flex shrink-0 items-center gap-2 rounded-md border border-primary/30 bg-primary/10 px-3 py-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          <span className="label-caps text-primary">Completed</span>
        </span>
      </div>

      {USING_MOCK_DATA ? (
        <div className="mt-6">
          <MockBanner />
        </div>
      ) : null}

      {/* Verdict */}
      <section className="mt-6">
        <VerdictCard verdict={analysis.verdict} confidence={analysis.confidence} />
      </section>

      {/* Evidence */}
      <section className="mt-12">
        <SectionTitle
          index="01"
          title="Evidence Summary"
          description="Independent signals. Model confidence is reported separately from the forensic assessment."
        />
        <EvidencePanel evidence={analysis.evidence} />
      </section>

      {/* Models */}
      <section className="mt-12">
        <SectionTitle
          index="02"
          title="Model Analysis"
          description="Per-model response and sampling coverage."
        />
        <ModelScores model={analysis.modelAnalysis} />
      </section>

      {/* Media viewer */}
      <section className="mt-12">
        <SectionTitle
          index="03"
          title={isVideo ? "Video Viewer" : "Image Viewer"}
          description={
            isVideo
              ? "Scrub the media and inspect the frame-level authenticity signal."
              : "Inspect the image and its region-level authenticity signal."
          }
        />
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
          {isVideo ? (
            <VideoPlayer
              posterUrl={sampleFrame}
              filename={analysis.filename}
              duration={duration}
              currentTime={currentTime}
              onTimeChange={setCurrentTime}
            />
          ) : (
            <Panel className="overflow-hidden p-0">
              <div className="relative aspect-video overflow-hidden bg-black">
                <img
                  src={sampleFrame}
                  alt={analysis.filename}
                  className="h-full w-full object-cover"
                />
                <div className="pointer-events-none absolute inset-0 grid-backdrop opacity-30" />
                <div className="pointer-events-none absolute left-[22%] top-[18%] h-[46%] w-[34%] rounded-sm border border-severity-high/70">
                  <span className="absolute -top-6 left-0 label-caps text-[10px] text-severity-high">
                    Face boundary · HIGH
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between gap-3 border-t border-border px-4 py-2.5">
                <span className="min-w-0 truncate font-mono text-xs text-muted-foreground">
                  {analysis.filename}
                </span>
                <span className="label-caps shrink-0">Region overlay · mock</span>
              </div>
            </Panel>
          )}
          <Panel className="p-5">
            <p className="label-caps">
              {isVideo ? "Frame analysis summary" : "Image analysis summary"}
            </p>
            <div className="mt-4 space-y-3">
              {[
                ["Duration", analysis.metadata.duration],
                ["Resolution", analysis.metadata.resolution],
                ["Frame rate", analysis.metadata.frameRate],
                ["Frames analyzed", String(analysis.modelAnalysis.framesAnalyzed)],
                ["Faces analyzed", String(analysis.modelAnalysis.facesAnalyzed)],
                ["Suspicious regions", String(analysis.suspiciousFrames.length)],
              ].map(([k, v]) => (
                <div
                  key={k}
                  className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-4 border-b border-border/60 pb-2.5 last:border-0"
                >
                  <span className="min-w-0 truncate text-sm text-muted-foreground">{k}</span>
                  <span className="shrink-0 font-mono text-sm">{v}</span>
                </div>
              ))}
            </div>
            <p className="mt-5 text-xs leading-relaxed text-muted-foreground">
              {isVideo
                ? "Highest sustained anomaly response occurs between 00:03 and 00:06, with a secondary cluster near 00:09."
                : "Strongest anomaly response is concentrated on the facial boundary and mouth region."}
            </p>
          </Panel>
        </div>

        {isVideo ? (
          <Panel className="mt-5 p-5">
            <VideoTimeline
              timeline={analysis.timeline}
              currentTime={currentTime}
              onSeek={seekAndInspect}
            />
          </Panel>
        ) : null}
      </section>

      {/* Suspicious frames */}
      <section className="mt-12">
        <SectionTitle
          index="04"
          title={isVideo ? "Suspicious Frames" : "Suspicious Regions"}
          description="Select an entry to open the explainability inspector."
        />
        <SuspiciousFrames frames={analysis.suspiciousFrames} onSelect={setInspected} />
      </section>

      {/* Forensics */}
      <section className="mt-12">
        <SectionTitle
          index="05"
          title="Digital Forensics"
          description="Container, compression and artifact-level signals."
        />
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="space-y-3">
            <FileInformation metadata={analysis.metadata} />
            <ProvenancePanel provenance={analysis.provenance} />
          </div>
          <CompressionPanel compression={analysis.compression} />
        </div>
      </section>

      {/* Metadata */}
      <section className="mt-12">
        <SectionTitle index="06" title="Metadata" />
        <MetadataPanel metadata={analysis.metadata} />
      </section>

      {/* Final */}
      <section className="mt-12">
        <SectionTitle index="07" title="Final Assessment" />
        <FinalAssessment analysis={analysis} />
      </section>

      {/* Actions */}
      <div className="mt-10 flex flex-col gap-3 sm:flex-row">
        <Link
          to="/analysis/$id/report"
          params={{ id: analysis.id }}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <FileText className="h-4 w-4" /> View Full Report
        </Link>
        <Link
          to="/analysis/$id/report"
          params={{ id: analysis.id }}
          search={{ print: true }}
          className="inline-flex items-center justify-center gap-2 rounded-md border border-border-strong px-5 py-3 text-sm font-medium transition-colors hover:border-primary/50 hover:text-primary"
        >
          <Download className="h-4 w-4" /> Export Report
        </Link>
        <Link
          to="/analyze"
          className="inline-flex items-center justify-center gap-2 rounded-md border border-border px-5 py-3 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <RotateCcw className="h-4 w-4" /> Analyze Another File
        </Link>
      </div>

      <FrameInspector frame={inspected} onClose={() => setInspected(null)} />
    </div>
  );
}
