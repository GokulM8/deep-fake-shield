# DeepFake Shield Project Review

**Review date:** 2026-09-24  
**Project:** DeepFake Shield  
**Repository:** `deep-fake`

## 1. Executive Summary

DeepFake Shield is an AI-assisted digital-media authenticity and forensic-analysis platform. The repository combines a React/Vite investigation interface, a FastAPI upload and analysis service, and a PyTorch video classifier.

The project is currently **video-first**:

- Video uploads use a trained EfficientNet-B0 checkpoint.
- The backend samples two representative frames, detects faces, classifies the face crops, and averages the fake probability.
- The frontend uploads files, polls the asynchronous analysis endpoint, and displays verdict, confidence, evidence, timeline, metadata, and report views.
- Image and audio endpoints exist, but their analysis is currently deterministic placeholder logic based on the uploaded file hash.

The codebase is a credible MVP and integration demonstrator. It should not yet be described as a production-grade forensic detector: the recorded evaluation artifacts show unstable and weak classification performance, the dataset is strongly imbalanced, identity-level leakage cannot be ruled out, and analysis history is not durable.

## 2. Current Capability At A Glance

| Area | Status | Notes |
| --- | --- | --- |
| Video upload | Working | FastAPI accepts supported video files up to 100 MB. |
| Video inference | Working | EfficientNet-B0 checkpoint, face-aware preprocessing, two sampled frames. |
| Video result UI | Working | Frontend polls the backend and maps the result into analysis/report screens. |
| Image analysis | Placeholder | No trained image model is connected. |
| Audio analysis | Placeholder | No trained audio model is connected. |
| Evidence endpoint | Working | Returns model and face-coverage signals for video. |
| Report endpoint | Working | Returns the analysis record; report fields are partly UI-oriented. |
| Persistent investigations | Not implemented | Records are held in memory and disappear after restart. |
| Authentication and authorization | Not implemented | The API is local-development oriented. |
| Model explanation | Limited | Suspicious timestamps and signal descriptions exist; Grad-CAM or verified heatmaps are not connected. |

## 3. Technology Stack

### Frontend

- React 19 and TypeScript.
- Vite 8 development/build tooling.
- TanStack Router/Start and TanStack React Query.
- Tailwind CSS 4.
- Radix UI components.
- Lucide React icons.
- Recharts for charting.
- ESLint and Prettier for code quality.

Important frontend locations:

- `frontend/src/start.ts` - application entry point.
- `frontend/src/router.tsx` - route configuration.
- `frontend/src/routes/analyze.tsx` - upload and analysis workflow.
- `frontend/src/lib/api.ts` - backend contract, polling data mapping, and optional mock mode.
- `frontend/src/lib/types.ts` - frontend analysis types.

### Backend

- Python with FastAPI and Uvicorn.
- Pydantic 2 schemas.
- PyTorch and Torchvision for model inference.
- OpenCV for video decoding and Haar face detection.
- Pillow for image conversion and preprocessing.
- Multipart upload handling.
- Pytest and FastAPI TestClient for API tests.

Important backend locations:

- `backend/app/main.py` - API application, upload validation, and routes.
- `backend/app/services/analysis.py` - analysis orchestration and result construction.
- `backend/app/services/video_detector.py` - production video inference.
- `backend/app/services/repository.py` - in-memory analysis storage.
- `backend/app/schemas.py` - request/response models.
- `backend/tests/test_api.py` - integration tests.

### Machine Learning

- EfficientNet-B0 image backbone from Torchvision.
- Two-class classifier head: `REAL` and `FAKE`.
- Dropout: `0.3`.
- Input size: `224 x 224`.
- ImageNet normalization.
- AdamW training in the baseline script.
- Optional ImageNet-pretrained initialization.
- Scikit-learn metrics: accuracy, precision, recall, F1, ROC-AUC, PR-AUC, false-positive rate, and false-negative rate.
- Experimental temporal Transformer over EfficientNet embeddings; it is not used by the deployed API.

## 4. End-to-End Working Flow

```mermaid
flowchart LR
    A[User selects video] --> B[React frontend]
    B --> C[POST /api/v1/analyze]
    C --> D[Validate extension, size, and file signature]
    D --> E[Save temporary upload]
    E --> F[Create processing record]
    F --> G[FastAPI background task]
    G --> H[Sample two representative frames]
    H --> I[Detect largest face with Haar cascade]
    I --> J[Crop with margin, RGB, resize 224x224]
    J --> K[EfficientNet-B0]
    K --> L[Average fake probability]
    L --> M[Store result in memory]
    M --> N[Frontend polls GET /api/v1/analyze/{id}]
    N --> O[Analysis and report screens]
```

### Upload and API processing

1. The frontend sends a multipart upload to `POST /api/v1/analyze`.
2. The backend accepts image, video, and audio extensions and enforces a 100 MB maximum.
3. The filename is reduced to its final path component to prevent path traversal through the uploaded name.
4. The backend checks the file signature against the extension.
5. The file is stored temporarily under the operating-system temp directory.
6. The backend creates an analysis ID and returns HTTP `202 Accepted` with `processing` status.
7. A FastAPI background task performs the analysis and removes the temporary file afterward.
8. The frontend polls `GET /api/v1/analyze/{analysis_id}` and then requests evidence/report data as needed.

### Video preprocessing and inference

For the production API:

1. Open the video with OpenCV.
2. Read frame count, frame rate, width, and height.
3. Select two evenly spaced representative frame indices.
4. Detect faces with OpenCV's `haarcascade_frontalface_default.xml`.
5. Select the largest detected face and add a 20% crop margin.
6. Convert BGR to RGB.
7. Resize to `224 x 224`.
8. Convert to a tensor and apply ImageNet mean/std normalization.
9. Run EfficientNet-B0 in evaluation mode without gradients.
10. Convert logits to probabilities with softmax and use class index `1` as fake.
11. Average the fake probabilities across usable frames.
12. Apply a `0.5` threshold to produce `REAL` or `FAKE`.
13. Return confidence, probabilities, frame scores, timestamps, video metadata, and evidence signals.

Frames without a detectable face are skipped. If no sampled frame contains a face, the analysis fails with an explicit error rather than inventing a result.

### Image and audio behavior

Image and audio are accepted by the same API contract, but they do not use trained detectors. The service creates deterministic placeholder scores from the SHA-256 digest of the uploaded bytes. These values are scaffolding and must not be presented as real model predictions.

## 5. Dataset And Data Preparation

The checked-in dataset report records:

| Property | Value |
| --- | ---: |
| Total videos | 6,529 |
| Readable videos | 6,529 |
| Corrupt/unreadable videos | 0 |
| Fake videos | 5,299 |
| Real videos | 712 |
| Unknown/test videos | 518 |
| Average duration | 12.643 seconds |
| Duration range | 0.033 to 24.667 seconds |
| Average frame rate | 29.99 FPS |

Dataset groups:

- `Celeb-Youtube-fake`: 5,299 fake videos.
- `Celeb-real`: 482 real videos.
- `YouTube-real`: 230 real videos.
- `test`: 518 videos with unknown labels.

The dataset is heavily imbalanced: among labeled videos, fake examples substantially outnumber real examples. This makes accuracy alone a poor measure of detector quality and makes precision/recall tradeoffs especially important.

The split pipeline uses seed `42`, splits at video level, and attempts to avoid duplicate file hashes crossing splits. The generated split sizes are:

- Train: 4,207 records.
- Validation: 902 records.
- Test: 902 records.

A major limitation is that source metadata or identity metadata is not available. Therefore, the project cannot guarantee that the same person or source does not appear across train, validation, and test sets. Duplicate filenames are also present across dataset groups, so paths and hashes must be handled carefully.

## 6. Training And Experiment Workflow

Primary scripts:

- `scripts/inspect_dataset.py` - inspect media readability and dataset composition.
- `scripts/split_dataset.py` - generate deterministic train/validation/test CSV files.
- `scripts/train_baseline.py` - train or sanity-check the EfficientNet baseline.
- `scripts/evaluate_baseline.py` - evaluate a saved checkpoint.
- `scripts/train_temporal.py` - experiment with temporal Transformer modeling.
- `scripts/infer_video.py` - run direct command-line video inference.

The baseline training entry point defaults to a small bounded run suitable for a sanity check:

- One epoch.
- Two frames per video.
- Batch size `2`.
- Dataset limit `20`.
- AdamW with learning rate `1e-4`.
- Best checkpoint selected using validation ROC-AUC.

The repository also contains an older EfficientNet training implementation with a different one-logit/BCE setup and different frame behavior. Its checkpoint format should not be assumed compatible with the deployed two-class checkpoint without explicit conversion or validation.

The temporal Transformer is research code. It uses frozen EfficientNet features and Transformer encoder layers, but the FastAPI service currently uses the simpler two-frame EfficientNet classifier.

## 7. Model And Artifact Inventory

- Production checkpoint: `models/deepfake_shield_video_v1.pt`.
- Production architecture: EfficientNet-B0 with a two-output classifier head.
- Generated dataset report: `artifacts/dataset_report.json`.
- Generated splits: `artifacts/splits/train.csv`, `val.csv`, and `test.csv`.
- Experiment outputs: `artifacts/experiments/`.
- Evaluation outputs: `artifacts/evaluation/`.
- Timeline JSON files: `artifacts/timelines/`.
- Research reports: `reports/` and `notebooks/`.

The model checkpoint is loaded once when the backend imports the application. `DEEPFAKE_MODEL_PATH` can override the default checkpoint path.

## 8. Evaluation Review

The README contains headline metrics of 55.43% accuracy, 97.35% precision, 50.82% recall, 66.78% F1, 83.01% ROC-AUC, and 96.79% PR-AUC. Those values should be clearly tied to a specific evaluation run before being treated as the canonical project result.

The checked-in evaluation files show the following separate results:

| Evaluation artifact | Support | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `batch_001` | 100 | 50.0% | 50.0% | 100.0% | 66.7% | 44.2% | 46.1% |
| `batch_002` | 100 | 54.0% | 61.1% | 22.0% | 32.4% | 61.3% | 63.0% |
| `sanity` | 2 | 0.0% | 0.0% | 0.0% | 0.0% | Not available | Not available |

### Interpretation

- The checked-in batch results are not strong enough to support production forensic use.
- `batch_001` predicts every positive example successfully but has a 100% false-positive rate.
- `batch_002` has a 78% false-negative rate, so it misses most positive examples in that sample.
- The small sanity run has no meaningful statistical value.
- ROC-AUC and PR-AUC are more informative than accuracy for this imbalanced dataset, but both still vary materially between batches.
- The README headline metrics and artifact metrics are inconsistent or come from different runs. The project should record the checkpoint, dataset split, threshold, sample count, and exact command next to every reported metric.

## 9. API Surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service status and inference mode. |
| `POST` | `/api/v1/analyze` | Upload a supported media file and create an analysis job. |
| `GET` | `/api/v1/analyze/{analysis_id}` | Retrieve job status and completed result. |
| `GET` | `/api/v1/analyze/{analysis_id}/evidence` | Retrieve evidence signals. |
| `GET` | `/api/v1/analyze/{analysis_id}/report` | Retrieve the report payload. |
| `GET` | `/docs` | FastAPI interactive OpenAPI documentation. |

The frontend preserves the asynchronous upload/polling contract and can switch between real backend mode and mock fixture mode with `VITE_USE_MOCK_DATA`.

## 10. How To Run The Project

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend URLs:

- API: `http://127.0.0.1:8000`
- Swagger/OpenAPI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend normally runs at the Vite development URL and calls `http://127.0.0.1:8000`. Set `VITE_API_BASE_URL` when the backend is hosted elsewhere. Mock mode is opt-in through:

```bash
VITE_USE_MOCK_DATA=true npm run dev
```

### Direct video inference

```bash
python3 scripts/infer_video.py \
  --video datasets/raw/test/00272.mp4 \
  --checkpoint models/deepfake_shield_video_v1.pt \
  --frames 2
```

### Dataset and training commands

```bash
python3 scripts/inspect_dataset.py
python3 scripts/split_dataset.py
python3 scripts/train_baseline.py --epochs 1 --limit 20 --frames-per-video 4
python3 scripts/evaluate_baseline.py --checkpoint artifacts/experiments/baseline/best_model.pt
```

## 11. Verification Status

The backend test suite covers:

- Health response.
- CORS for a local frontend.
- Upload and completed analysis behavior.
- Evidence retrieval.
- Unsupported extensions.
- Mismatched file content.
- Real video upload and model result fields.

Recommended verification commands:

```bash
cd backend
python3 -m pytest -q

cd ../frontend
npm run lint
npm run build
```

## 12. Strengths

1. The repository has a clear separation between frontend, API service, ML code, datasets, experiments, and generated artifacts.
2. The production video path uses the same general face-crop and ImageNet preprocessing family as the training pipeline.
3. The upload API validates extensions, file size, and basic magic signatures.
4. The model is loaded once and inference runs in evaluation/no-gradient mode.
5. The API returns more than a binary label: probabilities, frame scores, timestamps, evidence, and metadata are represented.
6. The frontend can use the real backend without changing its main analysis UI contract.
7. The code explicitly labels confidence as model output rather than legal certainty.
8. The test suite exercises a real video upload instead of only mocking model behavior.

## 13. Risks And Gaps

### High priority

- **Model performance:** checked-in batch metrics are weak and inconsistent.
- **Metric traceability:** the README headline metrics are not mapped to a named artifact, checkpoint, split, and command.
- **Dataset leakage risk:** identity/source-level separation cannot be verified.
- **Limited temporal evidence:** two frames cannot reliably establish temporal manipulation patterns.
- **Placeholder modalities:** image/audio results are not real predictions and need prominent product-level labeling.

### Medium priority

- **In-memory storage:** all analysis records disappear on restart and do not support multi-process deployment.
- **No authentication:** any client able to reach the API can submit files and read analysis IDs.
- **Background task scalability:** FastAPI in-process background tasks are not a durable job queue.
- **Resource controls:** model inference and video decoding need operational timeouts, concurrency limits, and cleanup safeguards for hostile or very long media.
- **Face detector sensitivity:** Haar detection can miss profiles, small faces, occlusions, or poor-quality frames.
- **Frontend evidence mapping:** the current UI may display unavailable fields as `Not provided` or `Not analyzed`; it does not imply that those forensic signals were actually computed.

### Lower priority

- Add a database-backed case and investigation model.
- Add structured logging, request IDs, and model/version metadata to every result.
- Add calibration analysis and threshold selection based on an explicit validation objective.
- Add reproducible experiment manifests and confusion matrices.
- Add model-serving health diagnostics that distinguish missing checkpoint, CPU fallback, and inference failure.

## 14. Recommended Next Steps

1. **Reconcile evaluation reporting.** Select one canonical evaluation run and publish its checkpoint hash, split definition, class counts, threshold, and complete metrics.
2. **Build identity-aware splits.** Add source/person metadata or a defensible grouping strategy before claiming generalization.
3. **Improve temporal coverage.** Evaluate more frames per video and compare the baseline with the temporal Transformer under the same split and metrics.
4. **Calibrate and select thresholds.** Report confusion matrices, precision-recall curves, operating points, and confidence calibration instead of relying on `0.5` by default.
5. **Separate supported from placeholder modalities.** Keep image/audio endpoints if useful for the UI, but return an explicit capability status rather than a result that resembles a trained prediction.
6. **Harden service operation.** Add durable storage, authentication, rate limits, file lifecycle controls, and a real worker queue before deployment beyond local use.
7. **Expand explainability carefully.** Add verified frame-level localization or Grad-CAM only when the output is technically connected to the model and clearly labeled as an explanation aid, not proof.
8. **Add regression coverage.** Test no-face videos, malformed containers, oversized files, missing checkpoints, model output shape, cleanup after failure, and frontend real-backend polling.

## 15. Final Assessment

DeepFake Shield is a well-structured research/MVP project with a functioning video inference integration and a usable forensic-style frontend. The strongest claim supported by the repository is:

> The project provides a local video-analysis workflow that runs an EfficientNet-B0 classifier on two face-cropped frames and exposes the result through a FastAPI service and React frontend.

The repository does not yet support the stronger claim that it is a reliable, production-ready deepfake forensic system. The next milestone should be reproducible, identity-aware evaluation and operational hardening, followed by broader temporal modeling and genuine image/audio detectors.
