import { MOCK_ANALYSES, MOCK_INVESTIGATIONS } from "./mockData";
import type {
  Analysis,
  AnalysisSummary,
  EvidenceSignal,
  MediaType,
  Severity,
  Verdict,
} from "./types";

export const USING_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === "true";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export interface AnalyzeMediaInput {
  file?: File;
  filename: string;
  mediaType: MediaType;
  sizeBytes: number;
}

export interface AnalyzeMediaResponse {
  analysisId: string;
  status: Analysis["status"];
}

interface BackendSignal {
  name: string;
  score: number;
  level: string;
  explanation: string;
}

interface BackendRecord {
  analysis_id: string;
  filename: string;
  media_type: MediaType;
  content_type: string;
  size_bytes: number;
  sha256: string;
  status: "processing" | "completed" | "failed";
  created_at: string;
  completed_at?: string | null;
  error?: string | null;
  result?: {
    verdict: "likely_authentic" | "likely_manipulated" | "likely_synthetic" | "inconclusive";
    confidence: number;
    signals: BackendSignal[];
    suspicious_regions: string[];
    suspicious_frames: number[];
    provenance: string;
  } | null;
}

function severity(level: string): Severity {
  const normalized = level.toUpperCase();
  return normalized === "HIGH" || normalized === "MEDIUM" || normalized === "LOW"
    ? normalized
    : "UNKNOWN";
}

function verdict(value: string): Verdict {
  return (
    (
      {
        likely_authentic: "Likely Authentic",
        likely_manipulated: "Likely Manipulated",
        likely_synthetic: "Likely Synthetic",
        inconclusive: "Inconclusive",
      } as Record<string, Verdict>
    )[value] ?? "Inconclusive"
  );
}

function toAnalysis(record: BackendRecord): Analysis {
  const result = record.result;
  const evidence = (result?.signals ?? []).map((signal, index): EvidenceSignal => ({
    id: index === 0 ? "visual" : index === 1 ? "compression" : "temporal",
    label: signal.name,
    severity: severity(signal.level),
    score: Math.round(signal.score * 100),
    description: signal.explanation,
  }));
  const suspiciousFrames = (result?.suspicious_frames ?? []).map((time, index) => ({
    id: `${record.analysis_id}-frame-${index}`,
    frame: index,
    timestamp: `${time.toFixed(2)}s`,
    time,
    score: 0,
    severity: "UNKNOWN" as Severity,
    thumbnailUrl: "",
    heatmapUrl: null,
    suspiciousRegion: result?.suspicious_regions[index] ?? "Not provided",
    modelAttention: "Not provided",
    explanation:
      "The backend reported a suspicious timestamp; frame-level evidence is not available yet.",
  }));
  return {
    id: record.analysis_id,
    filename: record.filename,
    mediaType: record.media_type,
    status: record.status,
    verdict: verdict(result?.verdict ?? "inconclusive"),
    confidence: Math.round((result?.confidence ?? 0) * 100),
    createdAt: record.created_at,
    modelAnalysis: {
      models: [],
      overallConfidence: Math.round((result?.confidence ?? 0) * 100),
      inputFrames: 0,
      framesAnalyzed: 0,
      facesDetected: 0,
      facesAnalyzed: 0,
    },
    evidence,
    suspiciousFrames,
    timeline: [],
    metadata: {
      filename: record.filename,
      format: record.content_type,
      size: `${(record.size_bytes / 1_000_000).toFixed(2)} MB`,
      resolution: "Not available",
      frameRate: "Not available",
      videoCodec: "Not available",
      audioCodec: "Not available",
      duration: "Not available",
      creationTime: record.created_at,
      softwareTag: "Not available",
    },
    compression: {
      recompression: "Not analyzed",
      blockingArtifacts: "UNKNOWN",
      compressionConsistency: "UNKNOWN",
      artifacts: [],
    },
    provenance: {
      status: "UNKNOWN",
      contentCredentials: result?.provenance ?? "Not available",
      c2pa: "Not analyzed",
      cryptographicProvenance: "Not analyzed",
    },
    report: {
      generatedAt: record.completed_at ?? record.created_at,
      executiveAssessment:
        "This result is produced by the configured backend analysis service. Missing signals are not evidence of manipulation.",
      finalAssessment: "Model confidence is not legal certainty.",
    },
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) throw new Error(`Backend request failed (${response.status})`);
  return response.json() as Promise<T>;
}

/** POST /api/v1/analyze */
export async function analyzeMedia(input: AnalyzeMediaInput): Promise<AnalyzeMediaResponse> {
  if (USING_MOCK_DATA) {
    const analysisId = Object.keys(MOCK_ANALYSES)[0];
    return { analysisId, status: "processing" };
  }
  if (!input.file) throw new Error("A media file is required for backend analysis");
  const form = new FormData();
  form.append("file", input.file, input.filename);
  const record = await request<{ analysis_id: string; status: "processing" }>("/api/v1/analyze", {
    method: "POST",
    body: form,
  });
  if (typeof window !== "undefined")
    window.sessionStorage.setItem(`dfs:submitted:${record.analysis_id}`, JSON.stringify(input));
  return { analysisId: record.analysis_id, status: record.status };
}

/** GET /api/v1/analyze/{analysis_id} */
export async function getAnalysis(id: string): Promise<Analysis> {
  if (USING_MOCK_DATA) return MOCK_ANALYSES[id] ?? MOCK_ANALYSES[Object.keys(MOCK_ANALYSES)[0]];
  return toAnalysis(await request<BackendRecord>(`/api/v1/analyze/${encodeURIComponent(id)}`));
}

/** GET /api/v1/analyze/{analysis_id}/evidence */
export async function getEvidence(id: string): Promise<EvidenceSignal[]> {
  if (USING_MOCK_DATA) return (await getAnalysis(id)).evidence;
  const signals = await request<BackendSignal[]>(
    `/api/v1/analyze/${encodeURIComponent(id)}/evidence`,
  );
  return signals.map((signal, index) => ({
    id: index === 0 ? "visual" : "temporal",
    label: signal.name,
    severity: severity(signal.level),
    score: Math.round(signal.score * 100),
    description: signal.explanation,
  }));
}

/** GET /api/v1/analyze/{analysis_id}/report */
export async function getReport(id: string): Promise<Analysis> {
  return getAnalysis(id);
}

/** GET /api/v1/analyze (history) */
export async function listInvestigations(): Promise<AnalysisSummary[]> {
  return MOCK_INVESTIGATIONS;
}

export const analysisQuery = (id: string) => ({
  queryKey: ["analysis", id] as const,
  queryFn: () => getAnalysis(id),
});

export const investigationsQuery = () => ({
  queryKey: ["investigations"] as const,
  queryFn: () => listInvestigations(),
});
