import { createFileRoute, Link } from "@tanstack/react-router";
import { Panel } from "@/components/common/primitives";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About — DeepFake Shield" },
      {
        name: "description",
        content:
          "How DeepFake Shield presents evidence signals, model confidence and forensic limitations.",
      },
      { property: "og:title", content: "About — DeepFake Shield" },
      {
        property: "og:description",
        content: "Methodology and limitations of AI-assisted media forensics.",
      },
    ],
  }),
  component: AboutPage,
});

const PRINCIPLES = [
  {
    title: "Evidence over verdicts",
    body: "Every signal — visual, temporal, face-region, compression, metadata and provenance — stays individually visible so an investigator can weigh it independently.",
  },
  {
    title: "Confidence is not certainty",
    body: "Model confidence describes how strongly a model responded. It is never presented as legal proof, and language stays within likely authentic, likely manipulated, likely synthetic or inconclusive.",
  },
  {
    title: "Absence is not evidence",
    body: "Missing metadata or missing provenance is reported as unknown. Neither is treated as an indicator of manipulation.",
  },
  {
    title: "Explainability by default",
    body: "Suspicious frames expose attention visualisations so a reviewer can see which regions drove a score, rather than accepting a number.",
  },
];

function AboutPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
      <p className="label-caps">About</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
        A forensic workstation, not a verdict machine
      </h1>
      <p className="mt-4 text-sm leading-relaxed text-muted-foreground sm:text-base">
        DeepFake Shield is an AI-assisted digital media authenticity platform. It combines
        frame-level and temporal model outputs with classical forensic signals, then presents them
        as reviewable evidence for a human investigator.
      </p>

      <div className="mt-10 grid gap-3 sm:grid-cols-2">
        {PRINCIPLES.map((p) => (
          <Panel key={p.title} className="p-5">
            <h2 className="text-sm font-medium">{p.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
          </Panel>
        ))}
      </div>

      <Panel className="mt-6 p-5">
        <h2 className="text-sm font-medium">Current build status</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          This is a frontend demonstration. All analysis results are fixtures served through a mock
          API layer that mirrors the planned FastAPI contract. No inference is performed and no
          result on this site should be cited as a real detection outcome.
        </p>
        <Link
          to="/analyze"
          className="mt-5 inline-flex rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Analyze Media
        </Link>
      </Panel>
    </div>
  );
}
