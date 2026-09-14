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
