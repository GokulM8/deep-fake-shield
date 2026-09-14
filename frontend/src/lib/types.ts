/**
 * DEEPFAKE SHIELD — shared domain types.
 *
 * These types mirror the contract that the future FastAPI backend will expose
 * (POST /api/v1/analyze, GET /api/v1/analyze/{id}, .../evidence, .../report).
 * Components read ONLY from these types, never from raw mock literals.
 */

export type MediaType = "video" | "image" | "audio";

export type AnalysisStatus = "queued" | "processing" | "completed" | "failed";

export type Verdict =
  "Likely Authentic" | "Likely Manipulated" | "Likely Synthetic" | "Inconclusive";

export type Severity = "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";

export type EvidenceKind =
  "visual" | "temporal" | "face" | "frequency" | "compression" | "metadata" | "provenance";

export interface EvidenceSignal {
  id: EvidenceKind;
  label: string;
  severity: Severity;
  /** 0–100. Undefined when the signal is not scoreable (e.g. provenance). */
  score?: number;
  description: string;
}

export interface ModelResult {
  id: string;
  label: string;
  architecture: string;
  confidence: number;
}

export interface ModelAnalysis {
  models: ModelResult[];
  overallConfidence: number;
  inputFrames: number;
  framesAnalyzed: number;
  facesDetected: number;
  facesAnalyzed: number;
}

export interface TimelinePoint {
  /** Seconds from media start. */
  time: number;
  frame: number;
  /** Manipulation probability, 0–100. */
  score: number;
}

export interface SuspiciousFrame {
  id: string;
  frame: number;
  timestamp: string;
  time: number;
  score: number;
  severity: Severity;
  /** Replace with a real frame URL once the backend serves extracted frames. */
  thumbnailUrl: string;
  /** Replace with the real Grad-CAM output URL from the backend. */
  heatmapUrl: string | null;
  suspiciousRegion: string;
  modelAttention: string;
  explanation: string;
}

export interface MediaMetadata {
  filename: string;
  format: string;
  size: string;
  resolution: string;
  frameRate: string;
  videoCodec: string;
  audioCodec: string;
  duration: string;
  creationTime: string;
  softwareTag: string;
}

export interface CompressionAnalysis {
  recompression: string;
  blockingArtifacts: Severity;
  compressionConsistency: Severity;
  artifacts: { label: string; severity: Severity }[];
}

export interface Provenance {
  status: Severity;
  contentCredentials: string;
  c2pa: string;
  cryptographicProvenance: string;
}

export interface Analysis {
  id: string;
  filename: string;
  mediaType: MediaType;
  status: AnalysisStatus;
  verdict: Verdict;
  /** Model confidence, 0–100. Distinct from the forensic assessment. */
  confidence: number;
  createdAt: string;
  modelAnalysis: ModelAnalysis;
  evidence: EvidenceSignal[];
  suspiciousFrames: SuspiciousFrame[];
  timeline: TimelinePoint[];
  metadata: MediaMetadata;
  compression: CompressionAnalysis;
  provenance: Provenance;
  report: {
    generatedAt: string;
    executiveAssessment: string;
    finalAssessment: string;
  };
}

export interface AnalysisSummary {
  id: string;
  filename: string;
  mediaType: MediaType;
  verdict: Verdict;
  confidence: number;
  createdAt: string;
  status: AnalysisStatus;
}

export interface ProcessingStage {
  id: string;
  label: string;
}
