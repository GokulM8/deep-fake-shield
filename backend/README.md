# DeepFake Shield Backend

Backend-first MVP for the DeepFake Shield forensic analysis platform.

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive OpenAPI docs are at `/docs`.

## Endpoints

- `POST /api/v1/analyze` accepts image, video, and audio uploads up to 100 MB.
- `GET /api/v1/analyze/{analysis_id}` returns job status and the completed assessment.
- `GET /api/v1/analyze/{analysis_id}/evidence` returns individual evidence signals.
- `GET /api/v1/analyze/{analysis_id}/report` returns the report payload.

The inference result is deliberately marked `placeholder` in `/health`. It is deterministic scaffolding for wiring real image, video, audio, metadata, provenance, and evidence-fusion engines later; it is not a trained detector.
