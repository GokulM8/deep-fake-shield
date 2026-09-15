# DeepFake Shield

> **Detect. Localize. Explain. Investigate.**

DeepFake Shield is a forensic analysis platform for digital media authenticity. The **video path is now live**: the existing frontend uploads a video to FastAPI, the backend runs the trained EfficientNet-B0 checkpoint, and the result returns through the existing analysis and report workflow.

![DeepFake Shield architecture](https://img.shields.io/badge/status-video%20inference%20live-1f8a70?style=flat-square)
![PyTorch](https://img.shields.io/badge/model-PyTorch%20%7C%20EfficientNet--B0-ee4c2c?style=flat-square)
![Tests](https://img.shields.io/badge/backend%20tests-10%20passed-2ea44f?style=flat-square)

## What is live

| Modality | Status | Current capability |
| --- | --- | --- |
| **Video** | **Production-integrated** | Face-aware two-frame EfficientNet-B0 prediction through the web UI and FastAPI |
| Image | Planned | Existing upload contract remains available; model work comes later |
| Audio | Planned | Existing upload contract remains available; model work comes later |

## Model card

| Item | Value |
| --- | --- |
| Architecture | EfficientNet-B0 |
| Framework | PyTorch |
| Input | Face crop, resized to `224x224` |
| Frames per video | 2 representative frames |
| Classifier | 2-class `REAL` / `FAKE` head |
| Checkpoint | `models/deepfake_shield_video_v1.pt` |
| Threshold | `0.5` fake-probability threshold |
| Device | CUDA when available, otherwise CPU |

### Test-set results

These are the reported results of the trained checkpoint, not generated or estimated values.

| Metric | Score |
| --- | ---: |
| Accuracy | **55.43%** |
| Precision | **97.35%** |
| Recall | **50.82%** |
| F1 | **66.78%** |
| ROC-AUC | **83.01%** |
| PR-AUC | **96.79%** |

> `confidence` is the selected class probability from the model. It is not a calibrated probability and is not legal certainty.

## Inference flow

```mermaid
flowchart LR
		A[Frontend upload] --> B[POST /api/v1/analyze]
		B --> C[Secure temporary file]
		C --> D[Sample 2 video frames]
		D --> E[Haar face crop + margin]
		E --> F[RGB, 224x224, ImageNet normalization]
		F --> G[EfficientNet-B0]
		G --> H[Mean fake probability]
		H --> I[Analysis result + report UI]
```

The detector reuses the training preprocessing in `ml/data/video_dataset.py` and the model definition in `ml/models/efficientnet_baseline.py`. Frames without detectable faces are skipped; videos with no valid face crops fail cleanly instead of producing a fabricated result.

## Quick start

### 1. Start the backend

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. OpenAPI docs are available at `http://127.0.0.1:8000/docs`.

The checkpoint is resolved from `models/deepfake_shield_video_v1.pt`. To use another checkpoint without changing code:

```bash
DEEPFAKE_MODEL_PATH=/absolute/path/to/model.pt uvicorn app.main:app --reload
```

### 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://127.0.0.1:8000`. Override it with `VITE_API_BASE_URL` when needed. Mock mode is opt-in only:

```bash
VITE_USE_MOCK_DATA=true npm run dev
```

### 3. Upload a real video

The existing frontend uses this same request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
	-F "file=@datasets/raw/test/00272.mp4"
```

The endpoint returns an analysis ID immediately. Poll the returned ID:

```bash
curl http://127.0.0.1:8000/api/v1/analyze/DF-YYYYMMDD-XXXXXXXX
```

The video result includes:

```json
{
	"verdict": "likely_authentic",
	"confidence": 0.941162,
	"fake_probability": 0.058838,
	"real_probability": 0.941162,
	"frames_analyzed": 2
}
```

## API surface

The existing asynchronous API is preserved:

- `POST /api/v1/analyze` - upload image, video, or audio
- `GET /api/v1/analyze/{analysis_id}` - poll status and retrieve the result
- `GET /api/v1/analyze/{analysis_id}/evidence` - retrieve evidence signals
- `GET /api/v1/analyze/{analysis_id}/report` - retrieve the report payload
- `GET /health` - service and inference-mode status

No duplicate `/predict` endpoint was added. The frontend continues to use the established upload and polling contract in `frontend/src/lib/api.ts`.

## Verify the integration

Run the backend tests:

```bash
cd backend
python3 -m pytest -q
```

Run direct inference with the repository helper:

```bash
cd ..
python3 scripts/infer_video.py \
	--video datasets/raw/test/00272.mp4 \
	--checkpoint models/deepfake_shield_video_v1.pt \
	--frames 2
```

Build and lint the frontend:

```bash
cd frontend
npm run lint
npm run build
```

The current backend verification covers model loading, CPU execution, face extraction, preprocessing, real-video inference, API upload, response fields, and no-face handling.

## Dataset and research workflow

The workspace contains `6,529` `.mp4` videos under `datasets/raw/`. Raw data is never modified. Generated reports, splits, experiments, and evaluation artifacts belong under `artifacts/`.

Inspect and split the dataset from the repository root:

```bash
python3 scripts/inspect_dataset.py
python3 scripts/split_dataset.py
```

Run a bounded training sanity check:

```bash
python3 scripts/train_baseline.py --epochs 1 --limit 20 --frames-per-video 4
python3 scripts/evaluate_baseline.py --checkpoint artifacts/experiments/baseline/best_model.pt
```

Research safeguards:

- Split at the video or source level, never at the frame level.
- Keep model confidence separate from the broader forensic assessment.
- Treat Grad-CAM as an explanation aid, not proof of manipulation.
- Review dataset licenses before downloading or redistributing media.

## Dataset links

- [Deepfake Detection Challenge dataset](https://www.kaggle.com/c/deepfake-detection/data) - video deepfake detection data.
- [Real and Fake Face Detection dataset](https://www.kaggle.com/datasets/ciplab/real-and-fake-face-detection) - real/fake face image data.
