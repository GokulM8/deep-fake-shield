import type { ModelAnalysis } from "@/lib/types";
import { Panel } from "@/components/common/primitives";

function Bar({ label, sub, value }: { label: string; sub: string; value: number }) {
  return (
    <div>
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{label}</p>
          <p className="truncate font-mono text-xs text-muted-foreground">{sub}</p>
        </div>
        <span className="shrink-0 font-mono text-sm tabular-nums">{value.toFixed(1)}%</span>
      </div>
      <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-1000"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export function ModelScores({ model }: { model: ModelAnalysis }) {
  const stats = [
    { label: "Input frames", value: model.inputFrames },
    { label: "Frames analyzed", value: model.framesAnalyzed },
    { label: "Faces detected", value: model.facesDetected },
    { label: "Faces analyzed", value: model.facesAnalyzed },
  ];

  return (
    <Panel className="p-5 sm:p-6">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          {model.models.map((m) => (
            <Bar key={m.id} label={m.label} sub={m.architecture} value={m.confidence} />
          ))}
          <div className="border-t border-border pt-6">
            <Bar
              label="Overall Model Confidence"
              sub="Weighted fusion"
              value={model.overallConfidence}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 self-start">
          {stats.map((s) => (
            <div key={s.label} className="rounded-md border border-border bg-muted/30 p-4">
              <p className="font-mono text-2xl tabular-nums">{s.value}</p>
              <p className="label-caps mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}
