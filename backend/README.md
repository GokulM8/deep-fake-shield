# DeepFake Shield Backend

Backend-first MVP for the DeepFake Shield forensic analysis platform.

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive OpenAPI docs are at `/docs`.

## Endpoints

- `POST /api/v1/analyze` accepts image, video, and audio uploads up to 100 MB.
- `GET /api/v1/analyze/{analysis_id}` returns job status and the completed assessment.
- `GET /api/v1/analyze/{analysis_id}/evidence` returns individual evidence signals.
- `GET /api/v1/analyze/{analysis_id}/report` returns the report payload.
- `GET /api/v1/analyze/{analysis_id}/frames/{frame_id}/{frame|heatmap}` returns an analyzed frame or its
  Grad-CAM heatmap as JPEG.

Video uploads use the EfficientNet-B0 checkpoint at `../models/deepfake_shield_video_v1.pt`.
The model is loaded once at startup, samples two representative frames, applies the training
face crop and ImageNet normalization, and returns the aggregated result through the existing
analysis polling endpoints. Image and audio analysis remain placeholder signals.

For each analyzed frame, the detector also computes Grad-CAM on the final convolutional block and
writes `frame_<id>.jpg` and a same-sized `heatmap_<id>.jpg` to the system temp directory
(`deepfake-shield-artifacts/<analysis_id>/`). Each `frame_scores` entry carries `face_box`,
`thumbnail_url`, and `heatmap_url`. Artifacts are cleared on startup, because analysis records are
held in memory.

Run the tests with `python -m pytest -q` (13 tests).
