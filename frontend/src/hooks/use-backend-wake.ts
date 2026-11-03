import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { healthQuery, USING_MOCK_DATA, type HealthStatus } from "@/lib/api";

export type BackendWakeState = "checking" | "waking" | "ready" | "unreachable";

/** After this long without a /health answer, assume a cold start and tell the user. */
const SLOW_AFTER_MS = 1500;

/**
 * Pings GET /health and reports whether the backend is up. The hosted backend scales to zero, so the
 * first request after a quiet period can take a while: "waking" means the ping is still pending.
 */
export function useBackendWake(): { state: BackendWakeState; health: HealthStatus | undefined } {
  const health = useQuery({
    ...healthQuery(),
    enabled: !USING_MOCK_DATA,
    // A cold start can also surface as a failed request; keep trying for about a minute.
    retry: 8,
    retryDelay: 4000,
  });
  const pending = health.isPending && !USING_MOCK_DATA;
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (!pending) {
      setSlow(false);
      return;
    }
    const timer = window.setTimeout(() => setSlow(true), SLOW_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [pending]);

  if (USING_MOCK_DATA || health.data) return { state: "ready", health: health.data };
  if (health.isError) return { state: "unreachable", health: undefined };
  return { state: slow ? "waking" : "checking", health: undefined };
}
