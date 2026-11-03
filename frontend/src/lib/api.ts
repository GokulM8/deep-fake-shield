import { MOCK_ANALYSES, MOCK_INVESTIGATIONS } from "./mockData";
import type {
  Analysis,
  AnalysisSummary,
  EvidenceSignal,
  MediaType,
  Severity,
  SuspiciousFrame,
  Verdict,
  VideoDecision,
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
  /** The server's upload limit from GET /health, when known. */
  maxUploadBytes?: number;
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
    model_name?: string | null;
    decision_threshold?: number | null;
    frame_threshold?: number | null;
  } | null;
}

export interface HealthStatus {
  status: "ok" | "degraded" | string;
  service: string;
  inference_mode: string;
  model: string;
  decision_threshold: number | null;
  max_upload_bytes?: number;
  retention_seconds?: number;
  sync_analysis?: boolean;
}

/** Matches the backend default; the live value comes from GET /health. */
export const DEFAULT_MAX_UPLOAD_BYTES = 32_000_000;
/** Matches the backend default RETENTION_SECONDS. */
export const DEFAULT_RETENTION_SECONDS = 3600;

/** A backend error with its HTTP status, the server's message and Retry-After (seconds), if any. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly retryAfterSeconds: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function waitText(seconds: number | null): string {
  if (!seconds) return "later";
  if (seconds < 90) return `in ${seconds} seconds`;
  return `in about ${Math.ceil(seconds / 60)} minutes`;
}

/** A message a user can act on, for the statuses the deployed backend returns on purpose. */
function errorMessage(status: number, detail: string | null, retryAfter: number | null): string {
  if (status === 413) return detail ?? "The file is too large for this server.";
  if (status === 429) return `Upload limit reached for now. Try again ${waitText(retryAfter)}.`;
  if (status === 503)
    return `The server is busy analyzing another video. Try again ${waitText(retryAfter)}.`;
  if (status === 415) return detail ?? "This file type is not supported.";
  return detail ?? `Backend request failed (${status})`;
}

const MY_ANALYSES_KEY = "dfs:my-analyses";
const MY_ANALYSES_LIMIT = 20;

/** IDs of analyses submitted from this browser, newest first (the server history is private). */
function myAnalysisIds(): string[] {
  try {
    const raw = window.localStorage.getItem(MY_ANALYSES_KEY);
    const ids: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(ids) ? ids.filter((id): id is string => typeof id === "string") : [];
  } catch {
    return [];
  }
}

function rememberAnalysis(id: string): void {
  try {
    const ids = [id, ...myAnalysisIds().filter((known) => known !== id)].slice(
      0,
      MY_ANALYSES_LIMIT,
    );
    window.localStorage.setItem(MY_ANALYSES_KEY, JSON.stringify(ids));
  } catch {
    // Storage can be unavailable (private mode); history then just stays empty.
  }
}

const COVERAGE_SIGNAL = "Face frame coverage";

/** Map evidence signals by name, so a signal keeps its kind if the order changes. */
function toEvidence(signals: BackendSignal[]): EvidenceSignal[] {
  return signals.map((signal, index): EvidenceSignal => {
    if (signal.name === COVERAGE_SIGNAL) {
      // Coverage measures input quality, not risk: full coverage is good news.
      const complete = signal.score >= 1;
      return {
        id: "face",
        label: signal.name,
        severity: complete ? "LOW" : "MEDIUM",
        badgeLabel: complete ? "COMPLETE" : "PARTIAL",
        score: Math.round(signal.score * 100),
        description: signal.explanation,
      };
    }
    return {
      id: index === 0 ? "visual" : "temporal",
      label: signal.name,
      severity: severity(signal.level),
      score: signal.score * 100,
      description: signal.explanation,
    };
  });
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
  const evidence = toEvidence(result?.signals ?? []);
  // The verdict compares the video-level fake score with the threshold; show that score, unrounded.
  const modelScore =
    result?.fake_probability != null
      ? result.fake_probability * 100
      : (result?.confidence ?? 0) * 100;
  const decision: VideoDecision | undefined =
    result?.fake_probability != null && result.model_name
      ? {
          score: result.fake_probability,
          threshold: result.decision_threshold ?? null,
          frameThreshold: result.frame_threshold ?? null,
          model: result.model_name,
        }
      : undefined;
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
        modelAttention: hasHeatmap
          ? "Grad-CAM, EfficientNet-B0 frame classifier, final conv block"
          : "Not provided",
        explanation: `Frame-level evidence (EfficientNet-B0): the face in this frame scored a ${score.toFixed(1)}% fake probability${
          flagged ? ", above the frame threshold" : ", below the frame threshold"
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
    confidence: modelScore,
    ...(decision ? { decision } : {}),
    createdAt: record.created_at,
    modelAnalysis: {
      models: result?.frames_analyzed
        ? [
            {
              id: "efficientnet-b0",
              label: "Video-level decision",
              // The first signal is named after the active serving model, e.g. "EfficientNet-B0 + MLP head".
              architecture: result.signals[0]?.name ?? "EfficientNet-B0",
              confidence: modelScore,
            },
          ]
        : [],
      overallConfidence: modelScore,
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
      finalAssessment: "Model scores are not calibrated probabilities and are not legal certainty.",
    },
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new ApiError(
      "Cannot reach the analysis server. It may still be starting up; try again in a moment.",
      0,
    );
  }
  if (!response.ok) {
    let detail: string | null = null;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON error body (e.g. a proxy page); fall back to the status message.
    }
    const retryHeader = Number(response.headers.get("Retry-After"));
    const retryAfter = Number.isFinite(retryHeader) && retryHeader > 0 ? retryHeader : null;
    throw new ApiError(
      errorMessage(response.status, detail, retryAfter),
      response.status,
      retryAfter,
    );
  }
  return response.json() as Promise<T>;
}

/** Why ``file`` cannot be uploaded, or null. Checked before upload: the hosting proxy rejects
 * oversized bodies before the API, without CORS headers, so the browser would only see a network error. */
export function uploadSizeError(file: File, maxBytes = DEFAULT_MAX_UPLOAD_BYTES): string | null {
  if (file.size <= maxBytes) return null;
  return `This file is ${(file.size / 1_000_000).toFixed(1)} MB; the limit is ${(maxBytes / 1_000_000).toFixed(0)} MB. Trim or compress the video and try again.`;
}

/** POST /api/v1/analyze */
export async function analyzeMedia(input: AnalyzeMediaInput): Promise<AnalyzeMediaResponse> {
  if (USING_MOCK_DATA) {
    const analysisId = Object.keys(MOCK_ANALYSES)[0] ?? "unknown";
    return { analysisId, status: "processing" };
  }
  if (!input.file) throw new Error("A media file is required for backend analysis");
  const sizeError = uploadSizeError(input.file, input.maxUploadBytes);
  if (sizeError) throw new ApiError(sizeError, 413);
  const form = new FormData();
  form.append("file", input.file, input.filename);
  const record = await request<{ analysis_id: string; status: "processing" }>("/api/v1/analyze", {
    method: "POST",
    body: form,
  });
  if (typeof window !== "undefined") {
    const { file: _file, ...summary } = input;
    window.sessionStorage.setItem(`dfs:submitted:${record.analysis_id}`, JSON.stringify(summary));
    rememberAnalysis(record.analysis_id);
  }
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
  return toEvidence(signals);
}

/** GET /api/v1/analyze/{analysis_id}/report */
export async function getReport(id: string): Promise<Analysis> {
  return getAnalysis(id);
}

export interface InvestigationList {
  items: AnalysisSummary[];
  /** "server": the full history; "browser": the server history is private, so only this browser's analyses. */
  scope: "server" | "browser";
}

/** Records for the analyses this browser submitted that the server still keeps. */
async function myRecords(): Promise<BackendRecord[]> {
  const records = await Promise.all(
    myAnalysisIds().map((id) =>
      request<BackendRecord>(`/api/v1/analyze/${encodeURIComponent(id)}`).catch(
        (error: unknown) => {
          if (error instanceof ApiError && error.status === 404) return null; // expired on the server
          throw error;
        },
      ),
    ),
  );
  return records.filter((record): record is BackendRecord => record !== null);
}

/** GET /api/v1/analyze (history); falls back to this browser's analyses when the history is private. */
export async function listInvestigations(): Promise<InvestigationList> {
  if (USING_MOCK_DATA) return { items: MOCK_INVESTIGATIONS, scope: "server" };
  let records: BackendRecord[];
  let scope: InvestigationList["scope"] = "server";
  try {
    records = await request<BackendRecord[]>("/api/v1/analyze");
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 401)) throw error;
    records = await myRecords();
    scope = "browser";
  }
  const items = records.map((record) => {
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
  return { items, scope };
}

export const analysisQuery = (id: string) => ({
  queryKey: ["analysis", id] as const,
  queryFn: () => getAnalysis(id),
});

/** GET /health. Throws when the backend is unreachable. */
export async function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

export const healthQuery = () => ({
  queryKey: ["health"] as const,
  queryFn: () => getHealth(),
  refetchInterval: 15_000,
  retry: false,
});

export const investigationsQuery = () => ({
  queryKey: ["investigations"] as const,
  queryFn: () => listInvestigations(),
});
