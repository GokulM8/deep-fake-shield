import { AlertTriangle, ShieldCheck, ShieldQuestion } from "lucide-react";
import type { Verdict } from "./types";

/** Icon and colours for a verdict: authentic reads as safe, manipulated as risk. */
export function verdictTone(verdict: Verdict) {
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
