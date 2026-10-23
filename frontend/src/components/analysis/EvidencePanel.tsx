import {
  Activity,
  AudioWaveform,
  Boxes,
  Eye,
  FileDigit,
  Fingerprint,
  ScanFace,
  type LucideIcon,
} from "lucide-react";
import type { EvidenceKind, EvidenceSignal } from "@/lib/types";
import { MetricBar, Panel, SeverityBadge } from "@/components/common/primitives";

const ICONS: Record<EvidenceKind, LucideIcon> = {
  visual: Eye,
  temporal: Activity,
  face: ScanFace,
  frequency: AudioWaveform,
  compression: Boxes,
  metadata: FileDigit,
  provenance: Fingerprint,
};

export function EvidenceCard({ signal }: { signal: EvidenceSignal }) {
  const Icon = ICONS[signal.id];
  return (
    <Panel className="group p-4 transition-colors duration-300 hover:border-border-strong">
      <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-border bg-muted/50">
          <Icon className="h-4 w-4 text-muted-foreground transition-colors group-hover:text-primary" />
        </span>
        <h3 className="min-w-0 truncate text-sm font-medium">{signal.label}</h3>
        <SeverityBadge severity={signal.severity} />
      </div>

      <div className="mt-4 flex items-baseline justify-between">
        <span className="label-caps">Signal strength</span>
        <span className="font-mono text-lg tabular-nums">
          {signal.score !== undefined ? `${signal.score}%` : "—"}
        </span>
      </div>
      <div className="mt-2">
        <MetricBar value={signal.score ?? 0} severity={signal.severity} />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{signal.description}</p>
    </Panel>
  );
}

export function EvidencePanel({ evidence }: { evidence: EvidenceSignal[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {evidence.map((signal) => (
        <EvidenceCard key={signal.id} signal={signal} />
      ))}
    </div>
  );
}
