import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/types";

export const severityStyles: Record<Severity, string> = {
  HIGH: "text-severity-high border-severity-high/40 bg-severity-high/10",
  MEDIUM: "text-severity-medium border-severity-medium/40 bg-severity-medium/10",
  LOW: "text-severity-low border-severity-low/40 bg-severity-low/10",
  UNKNOWN: "text-severity-unknown border-border-strong bg-muted/40",
};

export const severityBar: Record<Severity, string> = {
  HIGH: "bg-severity-high",
  MEDIUM: "bg-severity-medium",
  LOW: "bg-severity-low",
  UNKNOWN: "bg-severity-unknown",
};

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-1.5 py-0.5 font-mono text-[10px] tracking-[0.14em]",
        severityStyles[severity],
        className,
      )}
    >
      {severity}
    </span>
  );
}

export function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("panel shadow-panel", className)}>{children}</div>;
}

export function SectionTitle({
  index,
  title,
  description,
  action,
}: {
  index?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-5 grid grid-cols-[minmax(0,1fr)_auto] items-end gap-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {index ? <span className="label-caps text-primary">{index}</span> : null}
          <h2 className="truncate text-lg font-semibold tracking-tight sm:text-xl">{title}</h2>
        </div>
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function MetricBar({ value, severity = "LOW" }: { value: number; severity?: Severity }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
      <div
        className={cn("h-full rounded-full transition-[width] duration-700", severityBar[severity])}
        style={{ width: `${Math.max(2, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-4 border-b border-border/60 py-2.5 last:border-0">
      <span className="min-w-0 truncate text-sm text-muted-foreground">{label}</span>
      <span className="shrink-0 font-mono text-sm text-foreground">{value}</span>
    </div>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return (
    <p className="mt-4 border-l-2 border-primary/40 pl-3 text-xs leading-relaxed text-muted-foreground">
      {children}
    </p>
  );
}
