/**
 * Centralised mock data. NOTHING here is a real model prediction — every value
 * is a fixture used to exercise the UI until the FastAPI backend is wired in.
 */
import sampleFrame from "@/assets/sample-frame.jpg";
import type {
  Analysis,
  AnalysisSummary,
  ProcessingStage,
  SuspiciousFrame,
  TimelinePoint,
} from "./types";

export const PRIMARY_ANALYSIS_ID = "DF-2026-000124";

export const PROCESSING_STAGES: ProcessingStage[] = [
  { id: "upload", label: "Uploading" },
  { id: "identify", label: "Media identification" },
  { id: "frames", label: "Frame extraction" },
  { id: "faces", label: "Face detection" },
  { id: "dl", label: "Deep learning analysis" },
  { id: "temporal", label: "Temporal analysis" },
  { id: "forensic", label: "Forensic analysis" },
  { id: "fusion", label: "Evidence fusion" },
  { id: "report", label: "Report generation" },
];

export const IMAGE_PROCESSING_STAGES: ProcessingStage[] = [
  { id: "upload", label: "Uploading" },
  { id: "identify", label: "Media identification" },
  { id: "faces", label: "Face detection" },
  { id: "dl", label: "Deep learning analysis" },
  { id: "frequency", label: "Frequency analysis" },
  { id: "forensic", label: "Forensic analysis" },
  { id: "fusion", label: "Evidence fusion" },
  { id: "report", label: "Report generation" },
];

const RAW_TIMELINE: [number, number][] = [
  [0, 8],
  [0.5, 9],
  [1, 11],
  [1.5, 13],
  [2, 16],
  [2.5, 34],
  [3, 63],
  [3.5, 74],
  [4, 81],
  [4.5, 88],
  [5, 92],
  [5.5, 90],
  [6, 88],
  [6.5, 66],
  [7, 42],
  [7.5, 31],
  [8, 25],
  [8.5, 49],
  [9, 78],
  [9.5, 82],
  [10, 84],
  [10.5, 61],
  [11, 33],
  [11.5, 19],
  [12, 14],
];

export const MOCK_TIMELINE: TimelinePoint[] = RAW_TIMELINE.map(([time, score]) => ({
  time,
  frame: Math.round(time * 30),
  score,
}));

export function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  const cs = Math.round((seconds % 1) * 100);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(cs).padStart(2, "0")}`;
}

const MOCK_SUSPICIOUS_FRAMES: SuspiciousFrame[] = [
  {
    id: "f-091",
    frame: 91,
    timestamp: "00:03.04",
    time: 3.04,
    score: 89,
    severity: "HIGH",
    thumbnailUrl: sampleFrame,
    heatmapUrl: null,
    suspiciousRegion: "Face boundary",
    modelAttention: "Jawline / cheek",
    explanation:
      "The model assigned higher importance to the jawline and lower facial boundary, where blending transitions are typically introduced.",
  },
  {
    id: "f-120",
    frame: 120,
    timestamp: "00:04.00",
    time: 4.0,
    score: 94,
    severity: "HIGH",
    thumbnailUrl: sampleFrame,
    heatmapUrl: null,
    suspiciousRegion: "Face boundary",
    modelAttention: "Eyes / Mouth",
    explanation:
      "The model assigned higher importance to facial boundary and facial feature regions.",
  },
  {
    id: "f-150",
    frame: 150,
    timestamp: "00:05.00",
    time: 5.0,
    score: 92,
    severity: "HIGH",
    thumbnailUrl: sampleFrame,
    heatmapUrl: null,
    suspiciousRegion: "Mouth region",
    modelAttention: "Mouth / Teeth",
    explanation:
      "Attention concentrated around the mouth interior, a region commonly affected by frame-to-frame resynthesis.",
  },
  {
    id: "f-270",
    frame: 270,
    timestamp: "00:09.00",
    time: 9.0,
    score: 86,
    severity: "HIGH",
    thumbnailUrl: sampleFrame,
    heatmapUrl: null,
    suspiciousRegion: "Periocular region",
    modelAttention: "Eyes",
    explanation:
      "Elevated attention around the eye region alongside reduced temporal consistency with adjacent frames.",
  },
  {
    id: "f-312",
    frame: 312,
    timestamp: "00:10.40",
    time: 10.4,
    score: 79,
    severity: "MEDIUM",
    thumbnailUrl: sampleFrame,
    heatmapUrl: null,
    suspiciousRegion: "Hairline",
    modelAttention: "Forehead / Hairline",
    explanation:
      "Moderate attention along the hairline boundary where texture frequency differs from the surrounding scene.",
  },
];

export const MOCK_ANALYSIS: Analysis = {
  id: PRIMARY_ANALYSIS_ID,
  filename: "deepfake_sample.mp4",
  mediaType: "video",
  status: "completed",
  verdict: "Likely Manipulated",
  confidence: 91.7,
  createdAt: "2026-09-14T10:24:00Z",
  modelAnalysis: {
    models: [
      {
        id: "frame",
        label: "Frame Model",
        architecture: "EfficientNet-B4",
        confidence: 91.2,
      },
      {
        id: "temporal",
        label: "Temporal Model",
        architecture: "Temporal Transformer",
        confidence: 88.4,
      },
    ],
    overallConfidence: 91.7,
    inputFrames: 360,
    framesAnalyzed: 120,
    facesDetected: 117,
    facesAnalyzed: 117,
  },
  evidence: [
    {
      id: "visual",
      label: "Visual Analysis",
      severity: "HIGH",
      score: 91,
      description: "Strong spatial anomaly response across sampled facial frames.",
    },
    {
      id: "temporal",
      label: "Temporal Analysis",
      severity: "HIGH",
      score: 88,
      description: "Inconsistent identity signal between consecutive frame windows.",
    },
    {
      id: "face",
      label: "Face Anomalies",
      severity: "HIGH",
      score: 86,
      description: "Blending and boundary irregularities detected in face crops.",
    },
    {
      id: "compression",
      label: "Compression",
      severity: "MEDIUM",
      score: 74,
      description: "Evidence of recompression with uneven block consistency.",
    },
    {
      id: "metadata",
      label: "Metadata",
      severity: "LOW",
      score: 20,
      description: "Sparse container metadata; no conclusive editing trace.",
    },
    {
      id: "provenance",
      label: "Provenance",
      severity: "UNKNOWN",
      description: "No content credentials or cryptographic provenance detected.",
    },
  ],
  suspiciousFrames: MOCK_SUSPICIOUS_FRAMES,
  timeline: MOCK_TIMELINE,
  metadata: {
    filename: "deepfake_sample.mp4",
    format: "MP4",
    size: "18.4 MB",
    resolution: "1920 × 1080",
    frameRate: "30 FPS",
    videoCodec: "H.264",
    audioCodec: "AAC",
    duration: "00:12",
    creationTime: "Unknown",
    softwareTag: "Unknown",
  },
  compression: {
    recompression: "Detected",
    blockingArtifacts: "LOW",
    compressionConsistency: "MEDIUM",
    artifacts: [
      { label: "Face boundaries", severity: "HIGH" },
      { label: "Texture anomalies", severity: "MEDIUM" },
      { label: "Lighting consistency", severity: "LOW" },
      { label: "Blending artifacts", severity: "MEDIUM" },
    ],
  },
  provenance: {
    status: "UNKNOWN",
    contentCredentials: "Not detected",
    c2pa: "Not detected",
    cryptographicProvenance: "Not detected",
  },
  report: {
    generatedAt: "14 September 2026",
    executiveAssessment:
      "The submitted video was analysed across visual, temporal and forensic signal domains. The available evidence indicates that the media is likely manipulated, with the strongest anomaly response concentrated between 00:03 and 00:06 and a secondary cluster near 00:09.",
    finalAssessment:
      "The available evidence indicates that the media is likely manipulated. Visual and temporal analysis produced strong anomaly signals.",
  },
};

export const IMAGE_ANALYSIS: Analysis = {
  ...MOCK_ANALYSIS,
  id: "DF-2026-000125",
  filename: "portrait_photo.jpg",
  mediaType: "image",
  verdict: "Likely Manipulated",
  confidence: 88.6,
  createdAt: "2026-09-14T11:36:00Z",
  modelAnalysis: {
    models: [
      {
        id: "spatial",
        label: "Spatial Model",
        architecture: "EfficientNet-B4",
        confidence: 89.4,
      },
      {
        id: "frequency",
        label: "Frequency Model",
        architecture: "FFT Residual CNN",
        confidence: 85.1,
      },
    ],
    overallConfidence: 88.6,
    inputFrames: 1,
    framesAnalyzed: 1,
    facesDetected: 1,
    facesAnalyzed: 1,
  },
  evidence: [
    {
      id: "visual",
      label: "Visual Analysis",
      severity: "HIGH",
      score: 89,
      description: "Strong spatial anomaly response across the facial region.",
    },
    {
      id: "face",
      label: "Face Anomalies",
      severity: "HIGH",
      score: 87,
      description: "Blending and boundary irregularities detected in the face crop.",
    },
    {
      id: "frequency",
      label: "Frequency Artifacts",
      severity: "MEDIUM",
      score: 76,
      description: "GAN-like spectral peaks in the high-frequency residual band.",
    },
    {
      id: "compression",
      label: "Compression",
      severity: "MEDIUM",
      score: 68,
      description: "Double-JPEG quantization signature around the face boundary.",
    },
    {
      id: "metadata",
      label: "Metadata",
      severity: "MEDIUM",
      score: 61,
      description: "EXIF stripped; encoder tag inconsistent with declared format.",
    },
    {
      id: "provenance",
      label: "Provenance",
      severity: "UNKNOWN",
      description: "No content credentials or cryptographic provenance detected.",
    },
  ],
  suspiciousFrames: MOCK_SUSPICIOUS_FRAMES.slice(0, 3).map((f, i) => ({
    ...f,
    id: `img-${i}`,
    frame: 0,
    timestamp: "Still image",
    time: 0,
  })),
  timeline: [],
  metadata: {
    filename: "portrait_photo.jpg",
    format: "JPEG",
    size: "4.2 MB",
    resolution: "2048 × 2048",
    frameRate: "—",
    videoCodec: "—",
    audioCodec: "—",
    duration: "Still image",
    creationTime: "Unknown",
    softwareTag: "Unknown",
  },
  report: {
    generatedAt: "14 September 2026",
    executiveAssessment:
      "The submitted image was analysed across spatial, frequency and forensic signal domains. The available evidence indicates that the media is likely manipulated, with the strongest anomaly response concentrated on the facial boundary and mouth region.",
    finalAssessment:
      "The available evidence indicates that the media is likely manipulated. Spatial and frequency analysis produced strong anomaly signals.",
  },
};

const SECONDARY_ANALYSIS: Analysis = {
  ...MOCK_ANALYSIS,
  id: "DF-2026-000123",
  filename: "sample_video.mp4",
  verdict: "Likely Authentic",
  confidence: 87.3,
  createdAt: "2026-09-13T16:02:00Z",
};

export const MOCK_ANALYSES: Record<string, Analysis> = {
  [MOCK_ANALYSIS.id]: MOCK_ANALYSIS,
  [SECONDARY_ANALYSIS.id]: SECONDARY_ANALYSIS,
  [IMAGE_ANALYSIS.id]: IMAGE_ANALYSIS,
};

export const MOCK_INVESTIGATIONS: AnalysisSummary[] = [
  {
    id: "DF-2026-000124",
    filename: "deepfake_sample.mp4",
    mediaType: "video",
    verdict: "Likely Manipulated",
    confidence: 91.7,
    createdAt: "14 Sep 2026 · 10:24",
    status: "completed",
  },
  {
    id: "DF-2026-000125",
    filename: "portrait_photo.jpg",
    mediaType: "image",
    verdict: "Likely Manipulated",
    confidence: 88.6,
    createdAt: "14 Sep 2026 · 11:36",
    status: "completed",
  },
  {
    id: "DF-2026-000123",
    filename: "sample_video.mp4",
    mediaType: "video",
    verdict: "Likely Authentic",
    confidence: 87.3,
    createdAt: "13 Sep 2026 · 16:02",
    status: "completed",
  },
  {
    id: "DF-2026-000122",
    filename: "press_conference_clip.mov",
    mediaType: "video",
    verdict: "Inconclusive",
    confidence: 54.1,
    createdAt: "12 Sep 2026 · 09:47",
    status: "completed",
  },
  {
    id: "DF-2026-000121",
    filename: "statement_recording.mp4",
    mediaType: "video",
    verdict: "Likely Manipulated",
    confidence: 83.9,
    createdAt: "11 Sep 2026 · 18:15",
    status: "completed",
  },
];
