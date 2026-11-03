import { CloudOff, Loader2 } from "lucide-react";
import type { BackendWakeState } from "@/hooks/use-backend-wake";

/** Shown while the hosted backend is cold-starting, or when it cannot be reached at all. */
export function WakeBanner({ state }: { state: BackendWakeState }) {
  if (state === "waking") {
    return (
      <div
        role="status"
        className="print-hide flex items-start gap-2.5 rounded-md border border-primary/25 bg-primary/[0.06] px-3.5 py-2.5"
      >
        <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary" />
        <p className="text-xs leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground">Waking up the server…</span> The analysis
          server sleeps when nobody is using it and takes up to a minute to start. You can choose a
          file now; the upload starts once it is ready.
        </p>
      </div>
    );
  }
  if (state === "unreachable") {
    return (
      <div
        role="alert"
        className="print-hide flex items-start gap-2.5 rounded-md border border-severity-high/40 bg-severity-high/10 px-3.5 py-2.5"
      >
        <CloudOff className="mt-0.5 h-4 w-4 shrink-0 text-severity-high" />
        <p className="text-xs leading-relaxed text-severity-high">
          The analysis server is not responding. Refresh the page in a minute, or try again later.
        </p>
      </div>
    );
  }
  return null;
}
