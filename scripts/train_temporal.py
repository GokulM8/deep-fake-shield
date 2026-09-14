"""Train a temporal Transformer over frozen EfficientNet frame embeddings."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
from data.video_dataset import VideoFrameDataset
from evaluation.metrics import binary_metrics
from models.efficientnet_baseline import build_model
from models.temporal_transformer import TemporalTransformer


def run_epoch(backbone, temporal, loader, device, optimizer=None):
    training = optimizer is not None
    temporal.train(training)
    backbone.eval()
    criterion = nn.CrossEntropyLoss()
    labels, probabilities, losses = [], [], []
    for frames, targets in loader:
        batch, steps, channels, height, width = frames.shape
        frames, targets = frames.to(device), targets.to(device)
        with torch.no_grad():
            features = backbone.features(frames.reshape(batch * steps, channels, height, width))
            features = nn.functional.adaptive_avg_pool2d(features, 1).flatten(1)
            features = features.reshape(batch, steps, -1)
        with torch.set_grad_enabled(training):
            logits = temporal(features)
            loss = criterion(logits, targets)
            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        losses.append(float(loss.item()) * batch)
        labels.extend(targets.detach().cpu().tolist())
        probabilities.extend(torch.softmax(logits, dim=1)[:, 1].detach().cpu().tolist())
    metrics = binary_metrics(labels, probabilities)
    metrics["loss"] = sum(losses) / max(len(labels), 1)
    return metrics


def balanced_indices(records, limit: int) -> list[int]:
    if not limit or limit >= len(records):
        return list(range(len(records)))
    by_label = {0: [], 1: []}
    for index, record in enumerate(records):
        by_label[int(record["label"])].append(index)
    per_class = limit // 2
    return sorted(by_label[0][:per_class] + by_label[1][:per_class])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", type=Path, default=ROOT / "artifacts/splits/train.csv")
    parser.add_argument("--val-csv", type=Path, default=ROOT / "artifacts/splits/val.csv")
    parser.add_argument("--video-root", type=Path, help="Mounted dataset root containing the raw dataset folders")
    parser.add_argument("--backbone-checkpoint", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--frames", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/experiments/temporal")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    transform = transforms.Compose([
        transforms.Resize((224, 224)), transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    train = VideoFrameDataset(args.train_csv, args.frames, transform, args.video_root)
    validation = VideoFrameDataset(args.val_csv, args.frames, transform, args.video_root)
    if args.limit:
        train = Subset(train, balanced_indices(train.records, args.limit))
        validation = Subset(validation, balanced_indices(validation.records, args.limit))
    train_loader = DataLoader(train, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(validation, batch_size=args.batch_size, shuffle=False, num_workers=0)
    backbone = build_model().to(device)
    checkpoint = torch.load(args.backbone_checkpoint, map_location=device, weights_only=False)
    backbone.load_state_dict(checkpoint["model_state_dict"])
    for parameter in backbone.parameters():
        parameter.requires_grad = False
    embedding_dim = backbone.classifier[1].in_features
    temporal = TemporalTransformer(embedding_dim, max_length=args.frames).to(device)
    optimizer = torch.optim.AdamW(temporal.parameters(), lr=1e-4, weight_decay=1e-4)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    history, best_auc = [], -1.0
    for epoch in range(args.epochs):
        train_metrics = run_epoch(backbone, temporal, train_loader, device, optimizer)
        val_metrics = run_epoch(backbone, temporal, val_loader, device)
        state = {"model_state_dict": temporal.state_dict(), "epoch": epoch + 1, "metrics": val_metrics, "embedding_dim": embedding_dim}
        torch.save(state, args.output_dir / "last_temporal_model.pt")
        if val_metrics["roc_auc"] is not None and val_metrics["roc_auc"] > best_auc:
            best_auc = val_metrics["roc_auc"]
            torch.save(state, args.output_dir / "best_temporal_model.pt")
        history.append({"epoch": epoch + 1, "train": train_metrics, "validation": val_metrics})
        print(json.dumps(history[-1], indent=2))
    if not (args.output_dir / "best_temporal_model.pt").exists():
        torch.save(state, args.output_dir / "best_temporal_model.pt")
    (args.output_dir / "temporal_training_history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    print(f"device={device} output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
