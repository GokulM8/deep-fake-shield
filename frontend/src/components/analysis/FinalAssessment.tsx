import type { Analysis } from "@/lib/types";
import { Panel, SeverityBadge } from "@/components/common/primitives";
import { formatPercent } from "@/lib/format";
import { verdictTone } from "@/lib/verdict";
import { DecisionLine } from "./VerdictCard";

export function FinalAssessment({ analysis }: { analysis: Analysis }) {
  return (
    <Panel className="p-5 sm:p-6">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div className="min-w-0">
          <p className="label-caps">Final Assessment</p>
          <h3 className={`mt-2 text-2xl font-semibold ${verdictTone(analysis.verdict).color}`}>
            {analysis.verdict}
          </h3>
          <div className="mt-4 flex items-baseline gap-3">
            <span className="font-mono text-3xl tabular-nums">
              {formatPercent(analysis.confidence)}
            </span>
            <span className="label-caps">Fake score</span>
          </div>
          {analysis.decision ? (
            <div className="mt-3">
              <DecisionLine decision={analysis.decision} />
            </div>
          ) : null}
          <p className="mt-5 max-w-md text-sm leading-relaxed text-muted-foreground">
            {analysis.report.finalAssessment}
          </p>
          <p className="mt-4 border-l-2 border-primary/40 pl-3 text-xs text-muted-foreground">
            AI-assisted forensic assessment — not legal certainty.
          </p>
        </div>

        <div className="min-w-0">
          <p className="label-caps mb-3">Evidence</p>
          <div className="divide-y divide-border/70 rounded-md border border-border">
            {analysis.evidence.map((signal) => (
              <div
                key={signal.id}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-3"
              >
                <span className="min-w-0 truncate text-sm">{signal.label}</span>
                <SeverityBadge severity={signal.severity} label={signal.badgeLabel} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}
