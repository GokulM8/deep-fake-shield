# DeepFake Shield Architecture

These diagrams show the system **as implemented** on 2026-10-24, not the multimodal vision in `DeepFake Shield.pdf`. Dashed nodes are present in the code but not part of the live request path. For details, see [`PROJECT_TECHNICAL_DOCUMENTATION.md`](PROJECT_TECHNICAL_DOCUMENTATION.md).

---

## 1. High-level architecture

```mermaid
flowchart LR
    subgraph Browser
        UI["React 19 UI<br/>TanStack Router + Query"]
        BLOB[("Object URL of upload<br/>this tab only")]
    end
    subgraph FrontendServer["Frontend server (Vite dev / TanStack Start SSR)"]
        SSR["SSR render<br/>src/server.ts, src/start.ts"]
    end
    subgraph Backend["Backend (single Uvicorn process, :8000)"]
        API["FastAPI routes<br/>backend/app/main.py"]
        SVC["AnalysisService<br/>services/analysis.py"]
        DET["VideoDetector<br/>services/video_detector.py"]
        REPO[("AnalysisRepository<br/>in-memory dict + Lock")]
    end
    subgraph Disk["Local disk"]
        CKPT[("models/deepfake_shield_video_v1.pt")]
        TMP[("$TMPDIR uploads + frame/heatmap JPEGs")]
    end
    ML["ml/ package<br/>FaceCropper, sample_frame_indices, build_model"]

    UI -- "page requests" --> SSR
    UI -- "fetch API: upload, poll, images" --> API
    UI --- BLOB
    API --> REPO
    API -- "BackgroundTasks" --> SVC
    SVC --> REPO
    SVC --> DET
    DET --> ML
    DET --> CKPT
    API --> TMP
    DET --> TMP
```

**How to explain it:**

1. **The browser talks to two servers.**
   - The **frontend server** only renders pages.
   - The **FastAPI backend** does all the analysis. The browser calls it directly, which is why CORS is configured.
2. **The backend is one process with three layers:**
   - routes (HTTP and validation);
   - a service (orchestration);
   - a detector (the ML).
3. **State is held in two places only:** memory (records) and the temp directory (files). There is no database.

---

## 2. Module dependency diagram

```mermaid
flowchart TD
    main["backend/app/main.py"] --> schemas["backend/app/schemas.py"]
    main --> analysis["services/analysis.py"]
    main --> repo["services/repository.py"]
    main --> det["services/video_detector.py"]
    analysis --> schemas
    analysis --> repo
    analysis --> det
    repo --> schemas
    det --> vds["ml/data/video_dataset.py<br/>FaceCropper, sample_frame_indices"]
    det --> eff["ml/models/efficientnet_baseline.py<br/>build_model"]

    subgraph Offline["Offline ML scripts"]
        tb["scripts/train_baseline.py"] --> vds
        tb --> eff
        tb --> met["ml/evaluation/metrics.py"]
        ev["scripts/evaluate_baseline.py"] --> vinf["ml/inference/video_inference.py"]
        ev --> eff
        ev --> met
        vinf --> vds
        iv["scripts/infer_video.py"] --> vinf
        tt["scripts/train_temporal.py"] --> tr["ml/models/temporal_transformer.py"]
        tt --> eff
        tt --> vds
        sp["scripts/split_dataset.py"] --> spl["ml/data/split_dataset.py"]
        ins["scripts/inspect_dataset.py"] --> disc["ml/data/dataset_discovery.py"]
    end

    gc["ml/explainability/gradcam.py<br/>(unused)"]:::dead
    te["ml/training/train_efficientnet.py<br/>(legacy, incompatible head)"]:::dead
    classDef dead stroke-dasharray: 5 5,opacity:0.6
```

**Key point:** `video_detector.py` imports `FaceCropper` and `build_model` from the **same `ml/` code used for training**. This prevents "training/serving skew". The offline evaluator (`video_inference.py`) still differs in two ways: it falls back to the full frame when no face is found, and it defaults to 16 frames.

---

## 3. Frontend structure

```mermaid
flowchart TD
    root["routes/__root.tsx<br/>Navbar + Footer"] --> home["/ index.tsx"]
    root --> analyze["/analyze<br/>DropZone, FilePreview"]
    root --> proc["/analysis/$id/processing<br/>polls every 800 ms"]
    root --> dash["/analysis/$id<br/>dashboard"]
    root --> rep["/analysis/$id/report<br/>printable"]
    root --> inv["/investigations<br/>history"]
    root --> about["/about"]

    analyze -- "analyzeMedia()" --> apits["lib/api.ts"]
    proc -- "getAnalysis()" --> apits
    dash -- "analysisQuery() → toAnalysis()" --> apits
    rep --> apits
    inv -- "listInvestigations()" --> apits
    apits -- "VITE_USE_MOCK_DATA=true" --> mock["lib/mockData.ts"]

    dash --> comps["VerdictCard, ModelScores, EvidencePanel,<br/>VideoPlayer, VideoTimeline,<br/>SuspiciousFrames → FrameInspector → HeatmapViewer,<br/>ForensicPanels, FinalAssessment"]
    comps --> fp["FramePreview.tsx<br/>(aspect-ratio-correct overlays)"]
```

---

## 4. End-to-end data flow (video)

```mermaid
flowchart LR
    F["video file"] --> V{"validate<br/>extension · size ≤ 100 MiB ·<br/>magic bytes · non-empty"}
    V -- "fail" --> E4["400 / 413 / 415"]
    V -- "ok" --> S["save to $TMPDIR/uploads<br/>SHA-256"]
    S --> R1[("record: processing")]
    S --> SAMP["sample 16 frames<br/>linspace(0, n-1, 16)"]
    SAMP --> FACE["Haar face detect<br/>largest face + 20% pad"]
    FACE -- "no face in any frame" --> FAIL[("record: failed")]
    FACE --> PRE["BGR→RGB · resize 224 ·<br/>ImageNet normalize"]
    PRE --> NET["frozen EfficientNet-B0<br/>frame encoder"]
    NET --> EMB["1280-d embedding per face<br/>in its frame slot, no-face slots masked"]
    EMB --> HEAD["video-level head<br/>MLP (default) or Transformer"]
    NET --> SM["frame classifier p(fake) per frame<br/>flagged at ≥ 0.3654"]
    NET --> CAM["Grad-CAM<br/>features[-1], fake logit"]
    HEAD --> AGG["head p(fake) ≥ stored threshold → FAKE<br/>(MLP 0.9993, Transformer 0.8795)"]
    SM --> R2
    CAM --> ART["frame_ID.jpg + heatmap_ID.jpg<br/>max width 640"]
    AGG --> R2[("record: completed<br/>verdict, confidence, frame_scores")]
    ART --> R2
    R2 --> UI["UI: verdict, timeline,<br/>frame cards, inspector"]
    S -. "deleted after analysis" .-> X["upload removed"]
```

---

## 5. Request lifecycle (sequence)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Browser (analyze.tsx / api.ts)
    participant API as FastAPI (main.py)
    participant Repo as AnalysisRepository
    participant BG as BackgroundTask (thread pool)
    participant Det as VideoDetector

    User->>UI: drop video, click Analyze
    UI->>API: POST /api/v1/analyze (multipart)
    API->>API: safe_filename, classify_media, stream ≤100 MiB, validate_signature, sha256
    API->>Repo: create(record: processing)
    API-->>UI: 202 {analysis_id, status: processing}
    API->>BG: AnalysisService.run(id, path)
    UI->>UI: navigate to /analysis/{id}/processing
    loop every 800 ms
        UI->>API: GET /api/v1/analyze/{id}
        API->>Repo: get(id)
        API-->>UI: record (processing)
    end
    BG->>Det: predict(path, artifact_dir) (under the inference lock)
    Det->>Det: sample 16 → face crop → EfficientNet (embeddings, frame scores, Grad-CAM) → head → write JPEGs
    Det-->>BG: probabilities, frame_scores, metadata
    BG->>Repo: update(record: completed)
    BG->>BG: delete upload
    UI->>API: GET /api/v1/analyze/{id}
    API-->>UI: record (completed)
    UI->>UI: navigate to /analysis/{id}, toAnalysis()
    UI->>API: GET /api/v1/analyze/{id}/frames/{f}/frame and /heatmap
    API-->>UI: image/jpeg
```

**Failure branches:**

- A `VideoInferenceError` (no face, unreadable video, missing model) or an `OSError` → `record: failed` with the reason → the processing page stops.
- **Any other exception** is logged and the record is marked `failed` with a generic internal-error message (D3, fixed).
- In every case the upload is deleted (`try/finally` in `AnalysisService.run`).

---

## 6. Entity / data model

There is no database. These are the in-memory Pydantic models (`backend/app/schemas.py`):

```mermaid
erDiagram
    AnalysisRecord ||--o| AnalysisResult : "result (when completed)"
    AnalysisResult ||--|{ EvidenceSignal : signals
    AnalysisResult ||--o{ FrameScore : frame_scores
    FrameScore ||--o| FrameArtifacts : "thumbnail_url, heatmap_url"

    AnalysisRecord {
        string analysis_id PK "DF-YYYYMMDD-XXXXXXXX"
        string filename
        enum media_type "image|video|audio"
        string content_type
        int size_bytes
        string sha256
        enum status "processing|completed|failed"
        datetime created_at
        datetime completed_at
        string error
    }
    AnalysisResult {
        enum verdict
        float confidence "0-1"
        float fake_probability
        float real_probability
        int frames_analyzed
        float duration_seconds
        float frame_rate
        int width
        int height
        list suspicious_regions
        list suspicious_frames "timestamps"
        string provenance
    }
    EvidenceSignal {
        string name
        float score "0-1"
        string level
        string explanation
    }
    FrameScore {
        int frame_id
        float timestamp
        float fake_probability
        list face_box "left, top, right, bottom"
        string thumbnail_url
        string heatmap_url
    }
    FrameArtifacts {
        file frame_jpg "TMPDIR/deepfake-shield-artifacts/ID/frame_N.jpg"
        file heatmap_jpg "same size as frame"
    }
```

---

## 7. Offline ML pipeline

```mermaid
flowchart LR
    RAW[("datasets/raw<br/>6,529 mp4")] --> AUD["inspect_dataset.py<br/>label by folder, probe, SHA-256"]
    AUD --> REP[("artifacts/dataset_report.json")]
    REP --> SPL["split_dataset.py<br/>hash-grouped 70/15/15 per class, seed 42"]
    SPL --> CSV[("train 4,207 · val 902 · test 902")]
    CSV --> TR["train_baseline.py<br/>EfficientNet-B0, AdamW 1e-4,<br/>mean logits over frames, best by val ROC-AUC"]
    TR --> CK[("best_model.pt")]
    CK --> EV["evaluate_baseline.py<br/>predict_video, binary_metrics"]
    EV --> MET[("test_metrics.json, predictions, timelines")]
    CK -. "copied as" .-> PROD[("models/deepfake_shield_video_v1.pt<br/>(trained off-machine, epoch 2)")]
    PROD -. "frozen encoder" .-> EX["extract_embeddings.py (Colab T4)<br/>6,011 videos × 16 × 1280"]
    EX --> HD["head training (Colab)<br/>MLP + Transformer, 100 epochs,<br/>best epoch by inner-val ROC-AUC"]
    HD --> HK[("models/deepfake_shield_meanpool_mlp_v1.pt<br/>models/deepfake_shield_temporal_v1.pt")]
```

---

## 8. Vision vs. implementation

| Vision component (PDF) | Implemented? |
| --- | --- |
| Video deep-learning detector | Yes (frozen EfficientNet-B0 encoder + learned MLP head, 16 frames) |
| Explainable AI | Yes (Grad-CAM per frame, face boxes) |
| Temporal analysis | Transformer head trained and selectable (`DEEPFAKE_MODEL=temporal`); it does not beat the order-blind MLP |
| Image detector | Placeholder |
| Audio detector | Placeholder |
| Metadata / compression / provenance forensics | No (UI shows "Not available") |
| Evidence fusion, risk score | No (verdict comes from one model) |
| Database, authentication, deployment | No |
