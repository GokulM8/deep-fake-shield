import { AlertTriangle, ShieldCheck, ShieldQuestion } from "lucide-react";
import type { Verdict } from "@/lib/types";
import { Panel } from "@/components/common/primitives";
import { ConfidenceScore } from "./ConfidenceScore";

function verdictTone(verdict: Verdict) {
  if (verdict === "Likely Authentic")
    return { icon: ShieldCheck, color: "text-severity-low", ring: "var(--severity-low)" };
  if (verdict === "Inconclusive")
    return {
      icon: ShieldQuestion,
      color: "text-severity-unknown",
      ring: "var(--severity-unknown)",
    };
  return { icon: AlertTriangle, color: "text-severity-high", ring: "var(--severity-high)" };
}

export function VerdictCard({ verdict, confidence }: { verdict: Verdict; confidence: number }) {
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
            Derived from fused visual, temporal and forensic evidence signals. Individual signals
            remain independently reviewable below.
          </p>
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
