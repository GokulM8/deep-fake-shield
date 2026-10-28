import type { EvidenceSignal, VideoDecision } from "./types";

/**
 * Score formatting. The hybrid heads saturate near 1, so anything that would round to 100.0%
 * is shown as ">99.9%" rather than implying certainty.
 */

/** A 0–100 model score as a percentage with one decimal. */
export function formatPercent(score: number): string {
  return score >= 99.95 ? ">99.9%" : `${score.toFixed(1)}%`;
}

/** A 0–1 model score or threshold with three decimals. */
export function formatScore(score: number): string {
  return score >= 0.9995 ? ">0.999" : score.toFixed(3);
}

export const UNCALIBRATED_NOTE = "Scores are not calibrated probabilities.";

/** Explains why frame flags and the verdict can disagree; null without backend thresholds. */
export function frameFlagNote(decision: VideoDecision | undefined): string | null {
  if (!decision || decision.frameThreshold == null) return null;
  const frame = decision.frameThreshold.toFixed(2);
  // In baseline mode the verdict is the mean of the same frame scores, at the same threshold.
  if (decision.threshold === decision.frameThreshold)
    return `Frame flags and the verdict come from the same frame-level model (threshold ${frame}); the verdict averages all frame scores, so it can differ from individual frames.`;
  return `Frame flags come from the frame-level model (threshold ${frame}). The final verdict comes from the video-level head, which weighs all frames together, so an authentic verdict can still contain flagged frames.`;
}

/** Evidence values: model scores use `formatPercent`; coverage is an exact share of frames. */
export function formatSignalScore(signal: EvidenceSignal): string {
  if (signal.score === undefined) return "—";
  return signal.badgeLabel ? `${Math.round(signal.score)}%` : formatPercent(signal.score);
}
