import { Fingerprint, HardDrive, Layers } from "lucide-react";
import type { Analysis } from "@/lib/types";
import { KeyValue, MetricBar, Note, Panel, SeverityBadge } from "@/components/common/primitives";

export function FileInformation({ metadata }: { metadata: Analysis["metadata"] }) {
  const rows = [
    ["File Type", metadata.format],
    ["File Size", metadata.size],
    ["Resolution", metadata.resolution],
    ["Frame Rate", metadata.frameRate],
    ["Video Codec", metadata.videoCodec],
    ["Audio Codec", metadata.audioCodec],
  ] as const;

  return (
    <Panel className="p-5">
      <div className="mb-3 flex items-center gap-2">
        <HardDrive className="h-4 w-4 shrink-0 text-primary" />
        <h3 className="text-sm font-medium">File Information</h3>
      </div>
      {rows.map(([k, v]) => (
        <KeyValue key={k} label={k} value={v} />
      ))}
    </Panel>
  );
}

export function CompressionPanel({ compression }: { compression: Analysis["compression"] }) {
  return (
    <Panel className="p-5">
      <div className="mb-3 flex items-center gap-2">
        <Layers className="h-4 w-4 shrink-0 text-primary" />
        <h3 className="text-sm font-medium">Compression Analysis</h3>
      </div>
      <KeyValue label="Recompression" value={compression.recompression} />
      <KeyValue
        label="Blocking artifacts"
        value={<SeverityBadge severity={compression.blockingArtifacts} />}
      />
      <KeyValue
        label="Compression consistency"
        value={<SeverityBadge severity={compression.compressionConsistency} />}
      />

      <p className="label-caps mt-6">Artifact Analysis</p>
      <div className="mt-3 space-y-3.5">
        {compression.artifacts.map((a) => (
          <div key={a.label}>
            <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
              <span className="min-w-0 truncate text-sm">{a.label}</span>
              <SeverityBadge severity={a.severity} />
            </div>
            <div className="mt-2">
              <MetricBar
                value={a.severity === "HIGH" ? 88 : a.severity === "MEDIUM" ? 58 : 24}
                severity={a.severity}
              />
            </div>
          </div>
        ))}
      </div>
      <Note>These signals are forensic evidence, not definitive proof.</Note>
    </Panel>
  );
}

export function MetadataPanel({ metadata }: { metadata: Analysis["metadata"] }) {
  const rows = [
    ["Filename", metadata.filename],
    ["Format", metadata.format],
    ["Size", metadata.size],
    ["Resolution", metadata.resolution],
    ["Frame rate", metadata.frameRate],
    ["Codec", metadata.videoCodec],
    ["Duration", metadata.duration],
    ["Creation time", metadata.creationTime],
    ["Software tag", metadata.softwareTag],
  ] as const;

  return (
    <Panel className="p-5">
      <h3 className="text-sm font-medium">Metadata</h3>
      <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 border-b border-border pb-2">
        <span className="label-caps">Property</span>
        <span className="label-caps text-right">Value</span>
      </div>
      {rows.map(([k, v]) => (
        <KeyValue key={k} label={k} value={v} />
      ))}
      <Note>Missing metadata does not automatically indicate manipulation.</Note>
    </Panel>
  );
}

export function ProvenancePanel({ provenance }: { provenance: Analysis["provenance"] }) {
  return (
    <Panel className="p-5">
      <div className="mb-3 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Fingerprint className="h-4 w-4 shrink-0 text-primary" />
          <h3 className="truncate text-sm font-medium">Provenance</h3>
        </div>
        <SeverityBadge severity={provenance.status} />
      </div>
      <KeyValue label="Content Credentials" value={provenance.contentCredentials} />
      <KeyValue label="C2PA" value={provenance.c2pa} />
      <KeyValue label="Cryptographic provenance" value={provenance.cryptographicProvenance} />
      <Note>Missing provenance does not prove that media is manipulated.</Note>
    </Panel>
  );
}
