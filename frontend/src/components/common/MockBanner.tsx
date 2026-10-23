import { FlaskConical } from "lucide-react";

export function MockBanner() {
  return (
    <div className="print-hide flex items-start gap-2.5 rounded-md border border-primary/25 bg-primary/[0.06] px-3.5 py-2.5">
      <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
      <p className="text-xs leading-relaxed text-muted-foreground">
        <span className="font-medium text-foreground">Demonstration data.</span> All scores, frames
        and heatmaps on this screen are fixtures used to validate the interface. They are not real
        model predictions.
      </p>
    </div>
  );
}
