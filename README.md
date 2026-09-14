# DeepFake Shield

Detect. Localize. Explain. Investigate.

Research-oriented platform for AI-assisted digital media authenticity and forensic analysis. The first milestone is an actual video baseline with video-level splits, face crops, EfficientNet training, Grad-CAM, and temporal evaluation.

## Current dataset status

The workspace currently contains 6,529 `.mp4` videos under `datasets/raw/`: 5,299 fake videos in `Celeb-Youtube-fake`, 482 real videos in `Celeb-real`, 230 real videos in `YouTube-real`, and 518 unlabeled videos in `test`. All videos passed the OpenCV audit. The dataset is flat and has no source or identity metadata, so source-level separation cannot currently be enforced. The unlabeled `test` directory is excluded from supervised splits until its labels are verified.

Raw data is discovered from:

```text
datasets/raw/
```

Raw data is never modified. Processed artifacts belong under `datasets/processed/`.

## Dataset links

- [Deepfake Detection Challenge dataset](https://www.kaggle.com/c/deepfake-detection/data?utm_source=chatgpt.com&select=deep-fake-dataset) - video deepfake detection data.
- [Real and Fake Face Detection dataset](https://www.kaggle.com/datasets/ciplab/real-and-fake-face-detection) - real/fake face image data.

Review each dataset's license and usage terms before downloading or redistributing media. Downloaded datasets should remain under `datasets/raw/` and are excluded from Git.

## Inspect datasets

From the repository root:

```bash
python3 scripts/inspect_dataset.py
python3 scripts/split_dataset.py
```

The audit writes `artifacts/dataset_report.json`; the deterministic video-level split writes `artifacts/splits/train.csv`, `val.csv`, and `test.csv`. The tooling accepts arbitrary nested layouts, records media paths and labels conservatively, probes video metadata, hashes files for duplicate detection, and does not download, move, or rewrite dataset files.

## ML baseline commands

Run the bounded CPU sanity test first:

```bash
python3 scripts/train_baseline.py --epochs 1 --limit 20 --frames-per-video 4
python3 scripts/evaluate_baseline.py --checkpoint artifacts/experiments/baseline/best_model.pt
```

For a full experiment, set `--limit 0` and choose batch size, frame count, workers, and output directory for the available hardware. The baseline saves checkpoints, configuration, history, video-level predictions, frame timelines, and metrics under `artifacts/`. Metrics are generated from the actual run; no values are prefilled.

The temporal stage uses frozen EfficientNet embeddings:

```bash
python3 scripts/train_temporal.py --backbone-checkpoint artifacts/experiments/baseline/best_model.pt --limit 20
```

Analyze one video after training:

```bash
python3 scripts/infer_video.py --video path/to/video.mp4 --checkpoint artifacts/experiments/baseline/best_model.pt
```

Grad-CAM support is available through `ml/explainability/gradcam.py`. It explains model activation patterns and is not proof of manipulation. The FastAPI service remains on placeholder inference until a full baseline experiment is explicitly selected for integration.

## Backend

The backend MVP is in `backend/`. It provides secure upload validation, asynchronous analysis-job wiring, evidence contracts, and report/status endpoints. Its inference mode is intentionally marked `placeholder` until the trained baseline is connected.

```bash
cd backend
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Research rules

- Split at the video/source level, never at the frame level.
- Train on FaceForensics++ and evaluate externally on Celeb-DF v2.
- Preserve individual model, forensic, metadata, provenance, and temporal signals.
- Report model confidence separately from the overall forensic assessment.
- Never present a confidence score as legal certainty or generate fabricated metrics.
