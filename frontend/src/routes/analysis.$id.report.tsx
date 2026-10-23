import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { ArrowLeft, Printer, ShieldHalf } from "lucide-react";
import { useEffect, type ReactNode } from "react";
import { analysisQuery, USING_MOCK_DATA } from "@/lib/api";
import { MockBanner } from "@/components/common/MockBanner";
import { KeyValue, MetricBar, SeverityBadge } from "@/components/common/primitives";

export const Route = createFileRoute("/analysis/$id/report")({
  validateSearch: (search: Record<string, unknown>): { print?: boolean } => {
    const raw = search["print"];
    return raw === true || raw === "true" ? { print: true } : {};
  },
  head: () => ({
    meta: [
      { title: "Forensic Analysis Report — DeepFake Shield" },
      {
        name: "description",
        content: "Full AI-assisted forensic analysis report for the submitted media file.",
      },
      { property: "og:title", content: "Forensic Analysis Report — DeepFake Shield" },
      {
        property: "og:description",
        content: "Complete evidence, model results and assessment in a printable report.",
      },
    ],
  }),
  loader: async ({ context, params }) => {
    await context.queryClient.ensureQueryData(analysisQuery(params.id));
  },
  component: ReportPage,
});

function ReportSection({
  index,
  title,
  children,
}: {
  index: number;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="border-t border-border py-8">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-xs text-primary">{String(index).padStart(2, "0")}</span>
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function ReportPage() {
  const { id } = Route.useParams();
  const { print } = Route.useSearch();
  const { data: analysis } = useSuspenseQuery(analysisQuery(id));

  useEffect(() => {
    if (!print) return;
    const t = setTimeout(() => window.print(), 600);
    return () => clearTimeout(t);
  }, [print]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
      <div className="print-hide mb-8 flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/analysis/$id"
          params={{ id }}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Back to dashboard
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Printer className="h-4 w-4" /> Print / Export
        </button>
      </div>

      {USING_MOCK_DATA ? (
        <div className="print-hide mb-8">
          <MockBanner />
        </div>
      ) : null}

      {/* Report header */}
      <header className="border-b border-border pb-8">
        <div className="flex items-center gap-2.5">
          <ShieldHalf className="h-5 w-5 shrink-0 text-primary" />
          <span className="font-display text-sm font-semibold tracking-[0.14em]">
            DEEPFAKE SHIELD
          </span>
        </div>
        <h1 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">
          Forensic Analysis Report
        </h1>
        <dl className="mt-6 grid gap-x-8 gap-y-3 sm:grid-cols-2">
          {[
            ["Analysis ID", analysis.id],
            ["Media", analysis.filename],
            ["Type", analysis.mediaType.toUpperCase()],
            ["Status", "COMPLETED"],
            ["Generated", analysis.report.generatedAt],
          ].map(([k, v]) => (
            <div key={k} className="grid grid-cols-[minmax(0,1fr)_auto] gap-4">
              <dt className="label-caps">{k}</dt>
              <dd className="truncate font-mono text-sm">{v}</dd>
            </div>
          ))}
        </dl>
      </header>

      <div className="mt-8 rounded-lg border border-border bg-panel p-6">
        <p className="label-caps">Authenticity Assessment</p>
        <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-end gap-4">
          <h2 className="min-w-0 text-2xl font-semibold text-severity-high sm:text-3xl">
            {analysis.verdict}
          </h2>
          <div className="shrink-0 text-right">
            <p className="font-mono text-2xl tabular-nums">{analysis.confidence.toFixed(1)}%</p>
            <p className="label-caps">Model Confidence</p>
          </div>
        </div>
      </div>

      <ReportSection index={1} title="Executive Assessment">
        <p className="text-sm leading-relaxed text-muted-foreground">
          {analysis.report.executiveAssessment}
        </p>
      </ReportSection>

      <ReportSection index={2} title="Evidence Summary">
        <div className="space-y-4">
          {analysis.evidence.map((signal) => (
            <div key={signal.id}>
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
                <span className="min-w-0 truncate text-sm">{signal.label}</span>
                <span className="flex shrink-0 items-center gap-3">
                  <span className="font-mono text-xs tabular-nums">
                    {signal.score !== undefined ? `${signal.score}%` : "—"}
                  </span>
                  <SeverityBadge severity={signal.severity} />
                </span>
              </div>
              <div className="mt-2">
                <MetricBar value={signal.score ?? 0} severity={signal.severity} />
              </div>
            </div>
          ))}
        </div>
      </ReportSection>

      <ReportSection index={3} title="Model Results">
        {analysis.modelAnalysis.models.map((m) => (
          <KeyValue
            key={m.id}
            label={`${m.label} — ${m.architecture}`}
            value={`${m.confidence.toFixed(1)}%`}
          />
        ))}
        <KeyValue
          label="Overall model confidence"
          value={`${analysis.modelAnalysis.overallConfidence.toFixed(1)}%`}
        />
        <KeyValue label="Frames analyzed" value={analysis.modelAnalysis.framesAnalyzed} />
        <KeyValue label="Faces detected" value={analysis.modelAnalysis.facesDetected} />
        <KeyValue label="Faces analyzed" value={analysis.modelAnalysis.facesAnalyzed} />
      </ReportSection>

      <ReportSection index={4} title="Suspicious Frames">
        <div className="grid gap-3 sm:grid-cols-2">
          {analysis.suspiciousFrames.map((f) => (
            <div key={f.id} className="rounded-md border border-border p-4">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
                <span className="min-w-0 truncate font-mono text-sm">
                  Frame {String(f.frame).padStart(3, "0")} · {f.timestamp}
                </span>
                <SeverityBadge severity={f.severity} />
              </div>
              <p className="mt-2 font-mono text-xs text-muted-foreground">
                Score {f.score}% · {f.suspiciousRegion}
              </p>
            </div>
          ))}
        </div>
      </ReportSection>

      <ReportSection index={5} title="Explainability">
        <p className="text-sm leading-relaxed text-muted-foreground">
          Attention visualisations concentrate on the facial boundary and on facial feature regions
          (eyes and mouth) across the highest-scoring frames. This is consistent with
          face-replacement or resynthesis pipelines, which typically leave blending residue at
          region boundaries. Visualisations in this build are demonstration renders and are not
          produced by a trained model.
        </p>
      </ReportSection>

      {analysis.timeline.length > 0 ? (
        <ReportSection index={6} title="Video Timeline">
          <div className="flex h-24 items-end gap-[2px] rounded-md border border-border bg-muted/20 p-2">
            {analysis.timeline.map((p) => (
              <div
                key={p.frame}
                className="flex-1 rounded-sm"
                style={{
                  height: `${Math.max(6, p.score)}%`,
                  background:
                    p.score >= 75
                      ? "var(--severity-high)"
                      : p.score >= 45
                        ? "var(--severity-medium)"
                        : "var(--severity-low)",
                }}
              />
            ))}
          </div>
          <p className="mt-2 font-mono text-[10px] text-muted-foreground">
            00:00 → {analysis.metadata.duration}
          </p>
        </ReportSection>
      ) : null}

      <ReportSection index={7} title="Metadata">
        <KeyValue label="Filename" value={analysis.metadata.filename} />
        <KeyValue label="Format" value={analysis.metadata.format} />
        <KeyValue label="Size" value={analysis.metadata.size} />
        <KeyValue label="Resolution" value={analysis.metadata.resolution} />
        <KeyValue label="Frame rate" value={analysis.metadata.frameRate} />
        <KeyValue label="Codec" value={analysis.metadata.videoCodec} />
        <KeyValue label="Creation time" value={analysis.metadata.creationTime} />
        <KeyValue label="Software tag" value={analysis.metadata.softwareTag} />
        <p className="mt-4 text-xs text-muted-foreground">
          Missing metadata does not automatically indicate manipulation.
        </p>
      </ReportSection>

      <ReportSection index={8} title="Compression Analysis">
        <KeyValue label="Recompression" value={analysis.compression.recompression} />
        <KeyValue
          label="Blocking artifacts"
          value={<SeverityBadge severity={analysis.compression.blockingArtifacts} />}
        />
        <KeyValue
          label="Compression consistency"
          value={<SeverityBadge severity={analysis.compression.compressionConsistency} />}
        />
        {analysis.compression.artifacts.map((a) => (
          <KeyValue key={a.label} label={a.label} value={<SeverityBadge severity={a.severity} />} />
        ))}
      </ReportSection>

      <ReportSection index={9} title="Provenance">
        <KeyValue label="Status" value={<SeverityBadge severity={analysis.provenance.status} />} />
        <KeyValue label="Content Credentials" value={analysis.provenance.contentCredentials} />
        <KeyValue label="C2PA" value={analysis.provenance.c2pa} />
        <KeyValue
          label="Cryptographic provenance"
          value={analysis.provenance.cryptographicProvenance}
        />
        <p className="mt-4 text-xs text-muted-foreground">
          Missing provenance does not prove that media is manipulated.
        </p>
      </ReportSection>

      <ReportSection index={10} title="Final Assessment">
        <p className="text-sm leading-relaxed text-muted-foreground">
          {analysis.report.finalAssessment}
        </p>
        <p className="mt-5 border-l-2 border-primary/40 pl-3 text-xs leading-relaxed text-muted-foreground">
          This report represents an AI-assisted forensic assessment. Model confidence does not
          constitute legal certainty. Values in this build are demonstration fixtures.
        </p>
      </ReportSection>
    </div>
  );
}
