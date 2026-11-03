import { Lock } from "lucide-react";
import { DEFAULT_MAX_UPLOAD_BYTES, DEFAULT_RETENTION_SECONDS } from "@/lib/api";

function retentionText(seconds: number): string {
  if (seconds % 3600 === 0) return seconds === 3600 ? "1 hour" : `${seconds / 3600} hours`;
  return `${Math.round(seconds / 60)} minutes`;
}

/** What happens to an upload. Values come from GET /health when the backend has answered. */
export function PrivacyNotice({
  retentionSeconds = DEFAULT_RETENTION_SECONDS,
  maxUploadBytes = DEFAULT_MAX_UPLOAD_BYTES,
}: {
  retentionSeconds?: number | undefined;
  maxUploadBytes?: number | undefined;
}) {
  return (
    <div className="flex items-start gap-2.5 rounded-md border border-border bg-panel px-4 py-3">
      <Lock className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="space-y-1.5 text-xs leading-relaxed text-muted-foreground">
        <p className="font-medium text-foreground">Privacy</p>
        <p>
          Your video is sent to the analysis server, analyzed, and deleted as soon as the analysis
          ends. The result and the extracted face frames and heatmaps are kept in server memory for
          up to {retentionText(retentionSeconds)}, then deleted. Nothing is stored in a database.
          Anyone with an analysis link can open that result until then.
        </p>
        <p>
          Only upload videos you have the right to share. Do not upload footage of people without
          their consent. Files up to {(maxUploadBytes / 1_000_000).toFixed(0)} MB.
        </p>
      </div>
    </div>
  );
}
