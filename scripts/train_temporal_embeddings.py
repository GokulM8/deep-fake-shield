"""Hybrid model on precomputed embeddings: frame-score aggregation ablation and a temporal Transformer.

Inputs are the ``<split>.npz`` files from ``extract_embeddings.py``. Videos with no face frame are
excluded everywhere (and counted), as in ``evaluate_full.py``.

Leakage control: the Transformer early-stops on an inner-val set carved from TRAIN (15%, stratified
by label, grouped by the split hash). The original val split is used only to tune the decision
threshold, and test only for the final report.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
sys.path.insert(0, str(ROOT / "scripts"))
from models.temporal_transformer import TemporalTransformer  # noqa: E402

from evaluate_full import resolve_device, split_summary, write_evaluation  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

EVAL_SPLITS = ("val", "test")
AGGREGATIONS: dict[str, tuple[str, Callable[[np.ndarray], float]]] = {
    "mean": ("mean fake probability over face frames", lambda p: float(np.mean(p))),
    "max": ("max fake probability over face frames", lambda p: float(np.max(p))),
    "top3": ("mean of the 3 highest frame fake probabilities", lambda p: float(np.mean(np.sort(p)[-3:]))),
    "median": ("median fake probability over face frames", lambda p: float(np.median(p))),
}


def load_split(embeddings_dir: Path, split: str) -> dict[str, np.ndarray]:
    with np.load(embeddings_dir / f"{split}.npz") as data:
        return {key: data[key] for key in data.files}


def describe(data: dict[str, np.ndarray], scores: np.ndarray | None) -> list[dict[str, str]]:
    """Per-video records in the shape ``evaluate_full.split_summary`` expects."""
    valid = data["mask"].sum(axis=1)
    return [
        {
            "label": str(int(label)),
            "fake_prob": f"{scores[index]:.6f}" if scores is not None and count else "",
            "n_valid_frames": str(int(count)),
            "error": str(data["errors"][index]),
        }
        for index, (label, count) in enumerate(zip(data["labels"], valid))
    ]


def report(
    out_dir: Path,
    splits: dict[str, dict[str, np.ndarray]],
    scores: dict[str, np.ndarray],
    splits_dir: Path,
    run_info: dict[str, Any],
) -> dict[str, Any]:
    """``scores[split]`` has one entry per video (NaN for no-face videos, which are excluded)."""
    summaries, arrays = {}, {}
    for split in EVAL_SPLITS:
        records = describe(splits[split], scores[split])
        summaries[split] = split_summary(split, splits_dir / f"{split}.csv", records, records)
        keep = splits[split]["mask"].any(axis=1)
        arrays[split] = (splits[split]["labels"][keep], scores[split][keep])
    return write_evaluation(out_dir, summaries, arrays, run_info)


def aggregation_ablation(
    embeddings_dir: Path, evaluations_dir: Path, splits_dir: Path, prefix: str = "baseline_f16"
) -> dict[str, dict[str, Any]]:
    """Score val/test with each aggregation of the saved per-frame baseline probabilities."""
    meta = json.loads((embeddings_dir / "meta.json").read_text())
    splits = {split: load_split(embeddings_dir, split) for split in EVAL_SPLITS}
    results = {}
    for name, (description, aggregate) in AGGREGATIONS.items():
        scores = {}
        for split, data in splits.items():
            scores[split] = np.array([
                aggregate(probs[mask]) if mask.any() else np.nan
                for probs, mask in zip(data["frame_probs"], data["mask"])
            ])
        results[name] = report(evaluations_dir / f"{prefix}_{name}", splits, scores, splits_dir, {
            "checkpoint": f"models/{meta['checkpoint']}",
            "checkpoint_sha256": meta["checkpoint_sha256"],
            "frames": meta["frames"],
            "model": "efficientnet_b0",
            "aggregation": description,
            "preprocessing": meta["preprocessing"],
            "device": meta["device"],
            "autocast_fp16": meta["autocast_fp16"],
            "limit": meta.get("limit"),
            "source": "per-frame probabilities saved by extract_embeddings.py",
        })
    return results


def inner_val_split(labels: np.ndarray, groups: np.ndarray, fraction: float, seed: int) -> np.ndarray:
    """Boolean mask choosing ~``fraction`` of each class for inner-val, never splitting a hash group."""
    rng = random.Random(seed)
    chosen = np.zeros(len(labels), dtype=bool)
    for label in np.unique(labels):
        members: dict[str, list[int]] = {}
        for index in np.flatnonzero(labels == label):
            members.setdefault(str(groups[index]), []).append(int(index))
        keys = sorted(members)
        rng.shuffle(keys)
        target, taken = round(fraction * int((labels == label).sum())), 0
        for key in keys:
            if taken >= target:
                break
            chosen[members[key]] = True
            taken += len(members[key])
    return chosen


def artifacts_relative(path: Path) -> str:
    """``/any/root/artifacts/x/y`` -> ``artifacts/x/y``, so Drive and repo runs record the same path."""
    parts = path.resolve().parts
    return Path(*parts[parts.index("artifacts"):]).as_posix() if "artifacts" in parts else str(path)


def set_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def predict(model: nn.Module, x: torch.Tensor, mask: torch.Tensor, device: torch.device, batch_size: int,
            amp: bool, criterion: nn.Module | None = None, y: torch.Tensor | None = None) -> tuple[np.ndarray, float | None]:
    model.eval()
    probabilities, loss_sum = [], 0.0
    with torch.inference_mode():
        for start in range(0, len(x), batch_size):
            xb = x[start : start + batch_size].to(device).float()
            pad = ~mask[start : start + batch_size].to(device)
            with torch.autocast("cuda", dtype=torch.float16, enabled=amp):
                logits = model(xb, pad)
            logits = logits.float()
            if criterion is not None and y is not None:
                loss_sum += float(criterion(logits, y[start : start + batch_size].to(device))) * len(xb)
            probabilities.append(torch.softmax(logits, dim=1)[:, 1].cpu().numpy())
    loss = loss_sum / len(x) if criterion is not None else None
    return np.concatenate(probabilities), loss


def balanced_accuracy(labels: np.ndarray, scores: np.ndarray, threshold: float = 0.5) -> float:
    predictions = scores >= threshold
    recalls = [float((predictions[labels == c] == bool(c)).mean()) for c in (0, 1) if (labels == c).any()]
    return float(np.mean(recalls))


def plot_training(history: list[dict[str, float]], best_epoch: int, path: Path) -> None:
    epochs = [row["epoch"] for row in history]
    fig, (loss_ax, score_ax) = plt.subplots(1, 2, figsize=(10, 4))
    loss_ax.plot(epochs, [row["train_loss"] for row in history], label="train loss")
    loss_ax.plot(epochs, [row["inner_val_loss"] for row in history], label="inner-val loss")
    score_ax.plot(epochs, [row["inner_val_roc_auc"] for row in history], label="inner-val ROC-AUC")
    score_ax.plot(epochs, [row["inner_val_balanced_accuracy"] for row in history], label="inner-val balanced acc (0.5)")
    for ax, title in ((loss_ax, "Weighted cross-entropy"), (score_ax, "Inner-val metrics")):
        ax.axvline(best_epoch, color="tab:red", linestyle="--", linewidth=1, label=f"best epoch {best_epoch}")
        ax.set(xlabel="Epoch", title=title)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def train_temporal(
    embeddings_dir: Path,
    experiment_dir: Path,
    evaluation_dir: Path,
    splits_dir: Path,
    device_name: str = "auto",
    max_epochs: int = 100,
    patience: int = 10,
    batch_size: int = 32,
    lr: float = 1e-4,
    weight_decay: float = 1e-2,
    dropout: float = 0.2,
    model_dim: int = 256,
    feedforward_dim: int = 512,
    heads: int = 4,
    layers: int = 2,
    inner_val_fraction: float = 0.15,
    seed: int = 42,
) -> dict[str, Any]:
    set_seeds(seed)
    device = resolve_device(device_name)
    amp = device.type == "cuda"
    meta = json.loads((embeddings_dir / "meta.json").read_text())
    train_all = load_split(embeddings_dir, "train")
    usable = train_all["mask"].any(axis=1)
    inner = inner_val_split(train_all["labels"], train_all["sha256"], inner_val_fraction, seed) & usable
    fit = usable & ~inner

    def tensors(selection: np.ndarray) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return (torch.from_numpy(train_all["embeddings"][selection]),
                torch.from_numpy(train_all["mask"][selection]),
                torch.from_numpy(train_all["labels"][selection]))

    x_fit, m_fit, y_fit = tensors(fit)
    x_inner, m_inner, y_inner = tensors(inner)
    counts = torch.bincount(y_fit, minlength=2).float()
    class_weights = (counts.sum() / (2 * counts)).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    frames = int(train_all["mask"].shape[1])
    config = {
        "model": "TemporalTransformer over frozen EfficientNet-B0 embeddings",
        "embedding_dim": int(train_all["embeddings"].shape[2]),
        "frames": frames,
        "model_dim": model_dim,
        "feedforward_dim": feedforward_dim,
        "heads": heads,
        "layers": layers,
        "dropout": dropout,
        "pooling": "masked mean over face frames",
        "positional_encoding": "learnable",
        "loss": "cross-entropy, inverse-frequency class weights",
        "class_weights": class_weights.cpu().tolist(),
        "optimizer": "AdamW",
        "lr": lr,
        "weight_decay": weight_decay,
        "schedule": f"cosine annealing over max_epochs={max_epochs} (stepped per epoch)",
        "batch_size": batch_size,
        "max_epochs": max_epochs,
        "early_stopping": f"inner-val ROC-AUC (ties broken by lower inner-val loss), patience {patience}",
        "inner_val": f"{inner_val_fraction:.0%} of train, stratified by label, grouped by sha256, seed {seed}",
        "fit_videos": int(fit.sum()),
        "fit_class_counts": {"real": int((y_fit == 0).sum()), "fake": int((y_fit == 1).sum())},
        "inner_val_videos": int(inner.sum()),
        "inner_val_class_counts": {"real": int((y_inner == 0).sum()), "fake": int((y_inner == 1).sum())},
        "train_no_face_excluded": int((~usable).sum()),
        "seed": seed,
        "device": str(device),
        "amp_fp16": amp,
        "backbone_checkpoint_sha256": meta["checkpoint_sha256"],
        "embeddings_meta": meta,
    }
    experiment_dir.mkdir(parents=True, exist_ok=True)
    (experiment_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"fit {config['fit_videos']} {config['fit_class_counts']}, inner-val {config['inner_val_videos']} "
          f"{config['inner_val_class_counts']}, class weights {[round(w, 3) for w in config['class_weights']]}")

    model = TemporalTransformer(config["embedding_dim"], heads=heads, layers=layers, max_length=frames,
                                dropout=dropout, model_dim=model_dim, feedforward_dim=feedforward_dim).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs)
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    generator = torch.Generator().manual_seed(seed)

    history: list[dict[str, float]] = []
    best_auc, best_loss, best_epoch, stale = -1.0, float("inf"), 0, 0
    checkpoint_path = experiment_dir / "best_temporal_model.pt"
    for epoch in range(1, max_epochs + 1):
        model.train()
        order = torch.randperm(len(x_fit), generator=generator)
        loss_sum = 0.0
        for start in range(0, len(order), batch_size):
            index = order[start : start + batch_size]
            xb, pad, yb = x_fit[index].to(device).float(), ~m_fit[index].to(device), y_fit[index].to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=amp):
                logits = model(xb, pad)
            loss = criterion(logits.float(), yb)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            loss_sum += float(loss.detach()) * len(index)
        scheduler.step()

        inner_scores, inner_loss = predict(model, x_inner, m_inner, device, 256, amp, criterion, y_inner)
        labels = y_inner.numpy()
        row = {
            "epoch": epoch,
            "lr": optimizer.param_groups[0]["lr"],
            "train_loss": loss_sum / len(x_fit),
            "inner_val_loss": float(inner_loss),
            "inner_val_roc_auc": float(roc_auc_score(labels, inner_scores)),
            "inner_val_balanced_accuracy": balanced_accuracy(labels, inner_scores),
        }
        history.append(row)
        # ROC-AUC decides; on a tie (it saturates on easy inner-val sets) the lower inner-val loss wins.
        improved = row["inner_val_roc_auc"] > best_auc or (
            row["inner_val_roc_auc"] == best_auc and row["inner_val_loss"] < best_loss
        )
        if improved:
            best_auc, best_loss, best_epoch, stale = row["inner_val_roc_auc"], row["inner_val_loss"], epoch, 0
            torch.save({"model_state_dict": model.state_dict(), "config": config, "epoch": epoch,
                        "inner_val": row}, checkpoint_path)
        else:
            stale += 1
        print(f"epoch {epoch:3d}  train {row['train_loss']:.4f}  inner-val loss {row['inner_val_loss']:.4f}  "
              f"AUC {row['inner_val_roc_auc']:.4f}  bal-acc {row['inner_val_balanced_accuracy']:.4f}"
              f"{'  *' if improved else ''}", flush=True)
        if stale >= patience:
            print(f"Early stop at epoch {epoch}: no inner-val ROC-AUC gain for {patience} epochs (best {best_epoch})")
            break

    with (experiment_dir / "history.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)
    plot_training(history, best_epoch, experiment_dir / "training_curves.png")

    state = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(state["model_state_dict"])
    splits, scores = {}, {}
    for split in EVAL_SPLITS:
        data = load_split(embeddings_dir, split)
        keep = data["mask"].any(axis=1)
        probabilities, _ = predict(model, torch.from_numpy(data["embeddings"][keep]), torch.from_numpy(data["mask"][keep]),
                                   device, 256, amp)
        full = np.full(len(keep), np.nan)
        full[keep] = probabilities
        splits[split], scores[split] = data, full
    return report(evaluation_dir, splits, scores, splits_dir, {
        "checkpoint": artifacts_relative(checkpoint_path),
        "backbone_checkpoint": f"models/{meta['checkpoint']}",
        "backbone_checkpoint_sha256": meta["checkpoint_sha256"],
        "frames": frames,
        "model": "efficientnet_b0 + temporal_transformer",
        "aggregation": "temporal Transformer, masked mean pooling over face frames",
        "preprocessing": meta["preprocessing"],
        "device": str(device),
        "limit": meta.get("limit"),
        "best_epoch": best_epoch,
        "stopped_epoch": history[-1]["epoch"],
        "max_epochs": max_epochs,
        "best_inner_val_roc_auc": best_auc,
        "early_stopping_split": "inner-val (15% of train)",
        "training_config": {key: value for key, value in config.items() if key != "embeddings_meta"},
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--embeddings-dir", type=Path, required=True)
    parser.add_argument("--evaluations-dir", type=Path, default=ROOT / "artifacts/evaluations")
    parser.add_argument("--experiment-dir", type=Path, default=ROOT / "artifacts/experiments/temporal_transformer_f16")
    parser.add_argument("--splits-dir", type=Path, default=ROOT / "artifacts/splits")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-epochs", type=int, default=100)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-aggregation", action="store_true")
    parser.add_argument("--skip-temporal", action="store_true")
    args = parser.parse_args()
    if not args.skip_aggregation:
        aggregation_ablation(args.embeddings_dir, args.evaluations_dir, args.splits_dir)
    if not args.skip_temporal:
        train_temporal(args.embeddings_dir, args.experiment_dir, args.evaluations_dir / "temporal_f16", args.splits_dir,
                       args.device, args.max_epochs, args.patience, seed=args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
