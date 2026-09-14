"""Train a small, reproducible EfficientNet face/frame baseline."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
from data.video_dataset import VideoFrameDataset
from evaluation.metrics import binary_metrics
from models.efficientnet_baseline import build_model


def run_epoch(model, loader, device, optimizer=None):
    training = optimizer is not None
    model.train(training)
    criterion = nn.CrossEntropyLoss()
    labels, probabilities, losses = [], [], []
    for frames, targets in loader:
        batch, steps, channels, height, width = frames.shape
        frames, targets = frames.to(device), targets.to(device)
        with torch.set_grad_enabled(training):
            logits = model(frames.reshape(batch * steps, channels, height, width))
            logits = logits.reshape(batch, steps, 2).mean(dim=1)
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", type=Path, default=ROOT / "artifacts/splits/train.csv")
    parser.add_argument("--val-csv", type=Path, default=ROOT / "artifacts/splits/val.csv")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--limit", type=int, default=20, help="Limit each split for a sanity run; 0 means all rows")
    parser.add_argument("--frames-per-video", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/experiments/baseline")
    parser.add_argument("--pretrained", action="store_true")
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
    train = VideoFrameDataset(args.train_csv, args.frames_per_video, transform)
    validation = VideoFrameDataset(args.val_csv, args.frames_per_video, transform)
    if args.limit:
        train = Subset(train, range(min(args.limit, len(train))))
        validation = Subset(validation, range(min(args.limit, len(validation))))
    train_loader = DataLoader(train, batch_size=args.batch_size, shuffle=True, num_workers=args.workers)
    val_loader = DataLoader(validation, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)
    model = build_model(pretrained=args.pretrained).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    history = []
    best_auc = -1.0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for epoch in range(args.epochs):
        train_metrics = run_epoch(model, train_loader, device, optimizer)
        val_metrics = run_epoch(model, val_loader, device)
        history.append({"epoch": epoch + 1, "train": train_metrics, "validation": val_metrics})
        print(json.dumps(history[-1], indent=2))
        last_state = {"model_state_dict": model.state_dict(), "epoch": epoch + 1, "metrics": val_metrics}
        torch.save(last_state, args.output_dir / "last_model.pt")
        if val_metrics["roc_auc"] is not None and val_metrics["roc_auc"] > best_auc:
            best_auc = val_metrics["roc_auc"]
            torch.save(last_state, args.output_dir / "best_model.pt")
    if not (args.output_dir / "best_model.pt").exists():
        torch.save(last_state, args.output_dir / "best_model.pt")
    (args.output_dir / "training_history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "config.json").write_text(json.dumps(vars(args), default=str, indent=2) + "\n", encoding="utf-8")
    print(f"device={device} output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
