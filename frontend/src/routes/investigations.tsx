import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { ChevronRight, Video } from "lucide-react";
import { investigationsQuery } from "@/lib/api";
import type { Verdict } from "@/lib/types";
import { Panel } from "@/components/common/primitives";

export const Route = createFileRoute("/investigations")({
  head: () => ({
    meta: [
      { title: "Investigations — DeepFake Shield" },
      { name: "description", content: "History of previously analyzed digital media files." },
      { property: "og:title", content: "Investigations — DeepFake Shield" },
      { property: "og:description", content: "Review previously analyzed media and verdicts." },
    ],
  }),
  loader: async ({ context }) => {
    await context.queryClient.ensureQueryData(investigationsQuery());
  },
  component: InvestigationsPage,
});

function verdictClass(verdict: Verdict) {
  if (verdict === "Likely Authentic") return "text-severity-low";
  if (verdict === "Inconclusive") return "text-severity-unknown";
  return "text-severity-high";
}

function InvestigationsPage() {
  const { data } = useSuspenseQuery(investigationsQuery());

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <p className="label-caps">Case history</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Investigations</h1>
      <p className="mt-3 text-sm text-muted-foreground">Previously analyzed media.</p>

      <Panel className="mt-8 overflow-hidden">
        <div className="hidden grid-cols-[160px_minmax(0,1fr)_90px_170px_110px_150px] gap-4 border-b border-border px-5 py-3 lg:grid">
          {["Analysis ID", "Filename", "Type", "Verdict", "Confidence", "Date"].map((h) => (
            <span key={h} className="label-caps">
              {h}
            </span>
          ))}
        </div>

        <div className="divide-y divide-border/70">
          {data.map((item) => (
            <Link
              key={item.id}
              to="/analysis/$id"
              params={{ id: item.id }}
              className="group block px-5 py-4 transition-colors hover:bg-secondary/40"
            >
              <div className="grid gap-2 lg:grid-cols-[160px_minmax(0,1fr)_90px_170px_110px_150px] lg:items-center lg:gap-4">
                <span className="font-mono text-sm text-primary">{item.id}</span>
                <span className="min-w-0 truncate text-sm">{item.filename}</span>
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Video className="h-3.5 w-3.5 shrink-0" />
                  {item.mediaType.toUpperCase()}
                </span>
                <span className={`text-sm font-medium ${verdictClass(item.verdict)}`}>
                  {item.verdict}
                </span>
                <span className="font-mono text-sm tabular-nums">
                  {item.confidence.toFixed(1)}%
                </span>
                <span className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 text-xs text-muted-foreground">
                  <span className="min-w-0 truncate">{item.createdAt}</span>
                  <ChevronRight className="hidden h-4 w-4 shrink-0 transition-transform group-hover:translate-x-0.5 group-hover:text-primary lg:block" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </Panel>
    </div>
  );
}
