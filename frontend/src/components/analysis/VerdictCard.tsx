import type { Verdict, VideoDecision } from "@/lib/types";
import { Panel } from "@/components/common/primitives";
import { formatScore, UNCALIBRATED_NOTE } from "@/lib/format";
import { verdictTone } from "@/lib/verdict";
import { ConfidenceScore } from "./ConfidenceScore";

/** "Video-level score 0.516 · decision threshold 0.999 (EfficientNet-B0 + MLP head)". */
export function DecisionLine({ decision }: { decision: VideoDecision }) {
  return (
    <div className="space-y-1">
      <p className="font-mono text-xs text-foreground">
        Video-level score {formatScore(decision.score)}
        {decision.threshold != null
          ? ` · decision threshold ${formatScore(decision.threshold)}`
          : ""}{" "}
        <span className="text-muted-foreground">({decision.model})</span>
      </p>
      <p className="text-xs text-muted-foreground">{UNCALIBRATED_NOTE}</p>
    </div>
  );
}

export function VerdictCard({
  verdict,
  confidence,
  decision,
}: {
  verdict: Verdict;
  confidence: number;
  decision?: VideoDecision | undefined;
}) {
  const tone = verdictTone(verdict);
  const Icon = tone.icon;

  return (
    <Panel className="relative overflow-hidden p-6 sm:p-8">
      <div className="pointer-events-none absolute inset-0 grid-backdrop opacity-40" />
      <div className="relative grid gap-8 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
        <div className="min-w-0">
          <p className="label-caps">Authenticity Assessment</p>
          <div className="mt-3 flex items-center gap-3">
            <Icon className={`h-7 w-7 shrink-0 ${tone.color}`} />
            <h2 className={`text-2xl font-semibold tracking-tight sm:text-4xl ${tone.color}`}>
              {verdict}
            </h2>
          </div>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">
            {decision
              ? "Decided by the video-level head, which weighs all analysed frames together. Frame-level evidence remains reviewable below."
              : "Derived from fused visual, temporal and forensic evidence signals. Individual signals remain independently reviewable below."}
          </p>
          {decision ? (
            <div className="mt-4">
              <DecisionLine decision={decision} />
            </div>
          ) : null}
          <div className="mt-6 inline-flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-border px-3 py-2">
            <span className="label-caps">AI-assisted forensic assessment</span>
            <span className="text-xs text-muted-foreground">Not legal certainty</span>
          </div>
        </div>

        <div className="justify-self-start md:justify-self-end">
          <ConfidenceScore value={confidence} ringColor={tone.ring} />
        </div>
      </div>
    </Panel>
  );
}
