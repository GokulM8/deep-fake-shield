import type { Severity } from "./types";

/**
 * Severity band for a frame's fake probability (0–100). `flagged` is the backend's verdict for
 * the frame (at or above the served decision threshold), so a flagged frame is never shown as LOW
 * even when the threshold sits below the 45% band.
 */
export function frameSeverity(score: number, flagged = false): Severity {
  if (score >= 75) return "HIGH";
  if (score >= 45 || flagged) return "MEDIUM";
  return "LOW";
}

export const SEVERITY_COLOR: Record<Severity, string> = {
  HIGH: "var(--severity-high)",
  MEDIUM: "var(--severity-medium)",
  LOW: "var(--severity-low)",
  UNKNOWN: "var(--severity-unknown)",
};

/** Format seconds as mm:ss for timeline axes. */
export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}
