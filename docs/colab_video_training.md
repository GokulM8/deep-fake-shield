# Colab Video Training

Use a Colab GPU runtime for the staged video experiments. In Colab, choose **Runtime > Change runtime type > T4 GPU** or another available GPU before running the cells.

## 1. Clone and install

```python
%cd /content
!git clone https://github.com/GokulM8/deep-fake-shield.git
%cd /content/deep-fake-shield
!pip install -r ml/requirements.txt
```

## 2. Provide the dataset

The split CSVs in the repository contain the verified video-level assignments, but their paths point to the original Mac workspace. Mount Google Drive and copy the raw folders into a matching location, or download the licensed dataset with Kaggle credentials.

```python
from google.colab import drive
drive.mount('/content/drive')
```

Recommended layout:

```text
/content/drive/MyDrive/deep-fake-data/raw/Celeb-real/
/content/drive/MyDrive/deep-fake-data/raw/Celeb-Youtube-fake/
/content/drive/MyDrive/deep-fake-data/raw/YouTube-real/
```

The commands below use `/content/drive/MyDrive/deep-fake-data/raw` as `--video-root`. The loader remaps the CSV paths after `datasets/raw/` to this mounted root; the raw files are never copied into GitHub.

## 3. Verify GPU and paths

```python
!nvidia-smi
from pathlib import Path
root = Path('/content/drive/MyDrive/deep-fake-data/raw')
assert (root / 'Celeb-real').exists()
assert (root / 'Celeb-Youtube-fake').exists()
```

## 4. Batch 3 continuation

The local CPU run completed epoch 1 and saved a model-only checkpoint at `artifacts/experiments/batch_003_pretrained_500/last_model.pt`. Copy that directory to the Colab repository if you want to initialize from it. The current trainer does not restore optimizer state, so treat it as a model initialization and record that in the experiment notes.

For a clean GPU run, use ImageNet weights:

```python
!python scripts/train_baseline.py \
  --train-csv artifacts/splits/train.csv \
  --val-csv artifacts/splits/val.csv \
  --video-root /content/drive/MyDrive/deep-fake-data/raw \
  --pretrained --epochs 5 --limit 500 \
  --frames-per-video 8 --batch-size 16 --workers 2 \
  --output-dir /content/drive/MyDrive/deep-fake-experiments/batch_003_gpu
```

## 5. Evaluate the held-out test split

```python
!python scripts/evaluate_baseline.py \
  --csv artifacts/splits/test.csv \
  --video-root /content/drive/MyDrive/deep-fake-data/raw \
  --checkpoint /content/drive/MyDrive/deep-fake-experiments/batch_003_gpu/best_model.pt \
  --frames 8 --output-dir /content/drive/MyDrive/deep-fake-experiments/batch_003_eval
```

Do not tune on this test output. Use the validation ROC-AUC to select checkpoints and reserve the test split for the final report.

## 6. Temporal stage

```python
!python scripts/train_temporal.py \
  --train-csv artifacts/splits/train.csv \
  --val-csv artifacts/splits/val.csv \
  --video-root /content/drive/MyDrive/deep-fake-data/raw \
  --backbone-checkpoint /content/drive/MyDrive/deep-fake-experiments/batch_003_gpu/best_model.pt \
  --epochs 5 --limit 500 --frames 16 --batch-size 8 \
  --output-dir /content/drive/MyDrive/deep-fake-experiments/batch_003_temporal
```

Copy the generated `artifacts/` experiment results back into the project only when they are small enough and appropriate to version. Never commit raw videos, credentials, or fabricated metrics.