import { MOCK_ANALYSES, MOCK_INVESTIGATIONS } from "./mockData";
import type {
  Analysis,
  AnalysisSummary,
  EvidenceSignal,
  MediaType,
  Severity,
  SuspiciousFrame,
  Verdict,
} from "./types";
import { frameSeverity } from "./severity";

export const USING_MOCK_DATA = import.meta.env["VITE_USE_MOCK_DATA"] === "true";
const uploadedMediaUrls = new Map<string, string>();
const API_BASE_URL = (import.meta.env["VITE_API_BASE_URL"] ?? "http://127.0.0.1:8000").replace(
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

/** Browser-local object URL for media uploaded in this tab; the backend does not keep the file. */
export function getUploadedMediaUrl(analysisId: string): string | undefined {
  return uploadedMediaUrls.get(analysisId);
}

interface BackendSignal {
  name: string;
  score: number;
  level: string;
  explanation: string;
}

interface BackendFrameScore {
  frame_id: number;
  timestamp?: number | null;
  fake_probability: number;
  face_box?: [number, number, number, number] | null;
  thumbnail_url?: string | null;
  heatmap_url?: string | null;
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
    fake_probability?: number | null;
    real_probability?: number | null;
    frames_analyzed?: number | null;
    frame_scores?: BackendFrameScore[];
    duration_seconds?: number | null;
    frame_rate?: number | null;
    width?: number | null;
    height?: number | null;
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

/** Same bands as the timeline colours. */
function backendUrl(path: string | null | undefined): string {
  return path ? `${API_BASE_URL}${path}` : "";
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
  const flaggedTimes = new Set(result?.suspicious_frames ?? []);
  const suspiciousFrames = (result?.frame_scores ?? [])
    .filter((frame) => frame.timestamp !== null && frame.timestamp !== undefined)
    .map((frame): SuspiciousFrame => {
      const time = frame.timestamp as number;
      const score = Math.round(frame.fake_probability * 1000) / 10;
      const flagged = flaggedTimes.has(time);
      const [left, top, right, bottom] = frame.face_box ?? [];
      const width = result?.width;
      const height = result?.height;
      const hasHeatmap = Boolean(frame.heatmap_url);
      return {
        id: `${record.analysis_id}-frame-${frame.frame_id}`,
        frame: frame.frame_id,
        timestamp: `${time.toFixed(2)}s`,
        time,
        score,
        severity: frameSeverity(score, flagged),
        thumbnailUrl: backendUrl(frame.thumbnail_url),
        heatmapUrl: backendUrl(frame.heatmap_url) || null,
        ...(width && height ? { aspectRatio: width / height } : {}),
        ...(left !== undefined &&
        top !== undefined &&
        right !== undefined &&
        bottom !== undefined &&
        width &&
        height
          ? {
              faceBox: {
                left: (left / width) * 100,
                top: (top / height) * 100,
                width: ((right - left) / width) * 100,
                height: ((bottom - top) / height) * 100,
              },
            }
          : {}),
        flagged,
        suspiciousRegion: flagged
          ? (result?.suspicious_regions[0] ?? "Face region")
          : "None flagged",
        modelAttention: hasHeatmap ? "Grad-CAM, EfficientNet-B0 final conv block" : "Not provided",
        explanation: `The detector gave the face in this frame a ${score.toFixed(1)}% fake probability${
          flagged ? ", above the decision threshold" : ", below the decision threshold"
        }.${hasHeatmap ? " Warmer heatmap areas pushed the score towards fake the most." : ""}`,
      };
    })
    .sort((a, b) => b.score - a.score);
  const timeline = (result?.frame_scores ?? [])
    .filter((frame) => frame.timestamp !== null && frame.timestamp !== undefined)
    .map((frame) => ({
      time: frame.timestamp as number,
      frame: frame.frame_id,
      score: Math.round(frame.fake_probability * 100),
      flagged: flaggedTimes.has(frame.timestamp as number),
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
      models: result?.frames_analyzed
        ? [
            {
              id: "efficientnet-b0",
              label: "Video detector",
              architecture: "EfficientNet-B0",
              confidence: Math.round((result.confidence ?? 0) * 100),
            },
          ]
        : [],
      overallConfidence: Math.round((result?.confidence ?? 0) * 100),
      inputFrames: result?.frames_analyzed ?? 0,
      framesAnalyzed: result?.frames_analyzed ?? 0,
      facesDetected: result?.frames_analyzed ?? 0,
      facesAnalyzed: result?.frames_analyzed ?? 0,
    },
    evidence,
    suspiciousFrames,
    timeline,
    metadata: {
      filename: record.filename,
      format: record.content_type,
      size: `${(record.size_bytes / 1_000_000).toFixed(2)} MB`,
      resolution:
        result?.width && result?.height ? `${result.width} x ${result.height}` : "Not available",
      frameRate: result?.frame_rate ? `${result.frame_rate.toFixed(2)} fps` : "Not available",
      videoCodec: "Not available",
      audioCodec: "Not available",
      duration: result?.duration_seconds
        ? `${result.duration_seconds.toFixed(2)} s`
        : "Not available",
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
    const analysisId = Object.keys(MOCK_ANALYSES)[0] ?? "unknown";
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
  if (input.file.type.startsWith("video/") || input.file.type.startsWith("image/")) {
    uploadedMediaUrls.set(record.analysis_id, URL.createObjectURL(input.file));
  }
  return { analysisId: record.analysis_id, status: record.status };
}

/** GET /api/v1/analyze/{analysis_id} */
export async function getAnalysis(id: string): Promise<Analysis> {
  if (USING_MOCK_DATA) {
    const fallbackId = Object.keys(MOCK_ANALYSES)[0] ?? id;
    return MOCK_ANALYSES[id] ?? MOCK_ANALYSES[fallbackId]!;
  }
  return toAnalysis(await request<BackendRecord>(`/api/v1/analyze/${encodeURIComponent(id)}`));
}

/** GET /api/v1/analyze/{analysis_id}/evidence */
export async function getEvidence(id: string): Promise<EvidenceSignal[]> {
  if (USING_MOCK_DATA) return (await getAnalysis(id)).evidence;
  const signals = await request<BackendSignal[]>(
    `/api/v1/analyze/${encodeURIComponent(id)}/evidence`,
  );
  return signals.map((signal, index) => ({
    id: index === 0 ? "visual" : index === 1 ? "compression" : "temporal",
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
  if (USING_MOCK_DATA) return MOCK_INVESTIGATIONS;
  const records = await request<BackendRecord[]>("/api/v1/analyze");
  return records.map((record) => {
    const analysis = toAnalysis(record);
    return {
      id: analysis.id,
      filename: analysis.filename,
      mediaType: analysis.mediaType,
      verdict: analysis.verdict,
      confidence: analysis.confidence,
      createdAt: analysis.createdAt,
      status: analysis.status,
    };
  });
}

export const analysisQuery = (id: string) => ({
  queryKey: ["analysis", id] as const,
  queryFn: () => getAnalysis(id),
});

export const investigationsQuery = () => ({
  queryKey: ["investigations"] as const,
  queryFn: () => listInvestigations(),
});
