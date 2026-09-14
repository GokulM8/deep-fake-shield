#!/usr/bin/env python3
"""
Training script for EfficientNet-based deepfake detection.
Uses frame-level features aggregated to video-level predictions.
"""

import argparse
import os
import random
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from tqdm import tqdm


class VideoFrameDataset(Dataset):
    """Dataset that loads videos and extracts frames for EfficientNet."""

    def __init__(
        self,
        csv_path: Path,
        video_root: Path,
        frames_per_video: int = 10,
        transform=None,
    ):
        """
        Args:
            csv_path: Path to CSV file with columns: video_path, label, ...
            video_root: Root directory where videos are stored.
            frames_per_video: Number of frames to extract per video.
            transform: Transform to apply to each frame.
        """
        self.df = pd.read_csv(csv_path)
        self.video_root = video_root
        self.frames_per_video = frames_per_video
        self.transform = transform

        # Prepare list of (video_path, label)
        self.samples = []
        for _, row in self.df.iterrows():
            video_path = self.video_root / row['video_path']
            if not video_path.exists():
                # Try relative to current directory
                video_path = Path(row['video_path'])
            label = int(row['label'])
            self.samples.append((str(video_path), label))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        video_path, label = self.samples[idx]
        frames = self.extract_frames_uniform(video_path, self.frames_per_video)
        if self.transform:
            frames = [self.transform(frame) for frame in frames]
        # Stack frames into a tensor: (T, C, H, W)
        frames_tensor = torch.stack(frames) if frames else torch.zeros(
            (self.frames_per_video, 3, 224, 224)
        )
        return frames_tensor, label

    @staticmethod
    def extract_frames_uniform(video_path: str, n_frames: int) -> List[np.ndarray]:
        """Extract n_frames uniformly spaced frames from a video."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            # Return black frames if video cannot be opened
            return [np.zeros((224, 224, 3), dtype=np.uint8) for _ in range(n_frames)]

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return [np.zeros((224, 224, 3), dtype=np.uint8) for _ in range(n_frames)]

        # Calculate indices of frames to extract
        indices = np.linspace(0, total_frames - 1, n_frames, dtype=int)
        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Resize to 224x224
                frame = cv2.resize(frame, (224, 224))
                frames.append(frame)
            else:
                # Use black frame if read fails
                frames.append(np.zeros((224, 224, 3), dtype=np.uint8))
        cap.release()
        return frames


def get_efficientnet_model(pretrained: bool = True) -> nn.Module:
    """Load EfficientNet-B0 and replace the classifier head."""
    weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
    model = models.efficientnet_b0(weights=weights)
    # Replace the classifier
    num_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.2, inplace=True),
        nn.Linear(num_features, 1),  # Binary classification
    )
    return model


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    num_epochs: int = 10,
    save_path: Path = None,
) -> None:
    """Training loop with validation."""
    best_val_acc = 0.0
    for epoch in range(num_epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for frames, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs} [Train]"):
            frames = frames.to(device)  # (B, T, C, H, W)
            labels = labels.float().to(device).unsqueeze(1)  # (B, 1)

            optimizer.zero_grad()

            # Process each frame through the backbone and aggregate features
            batch_size, t, c, h, w = frames.shape
            frames_flat = frames.view(batch_size * t, c, h, w)  # (B*T, C, H, W)
            features = model.features(frames_flat)  # (B*T, C, h', w')
            features = nn.functional.adaptive_avg_pool2d(features, (1, 1))  # (B*T, C, 1, 1)
            features = features.view(batch_size, t, -1)  # (B, T, C)
            # Average features across frames
            video_features = torch.mean(features, dim=1)  # (B, C)
            outputs = model.classifier(video_features)  # (B, 1)

            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * frames.size(0)
            preds = torch.sigmoid(outputs) > 0.5
            train_correct += preds.eq(labels.view_as(preds)).sum().item()
            train_total += frames.size(0)

        train_loss = train_loss / train_total
        train_acc = train_correct / train_total

        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for frames, labels in tqdm(val_loader, desc=f"Epoch {epoch+1}/{num_epochs} [Val]"):
                frames = frames.to(device)
                labels = labels.float().to(device).unsqueeze(1)

                batch_size, t, c, h, w = frames.shape
                frames_flat = frames.view(batch_size * t, c, h, w)
                features = model.features(frames_flat)
                features = nn.functional.adaptive_avg_pool2d(features, (1, 1))
                features = features.view(batch_size, t, -1)
                video_features = torch.mean(features, dim=1)
                outputs = model.classifier(video_features)

                loss = criterion(outputs, labels)

                val_loss += loss.item() * frames.size(0)
                preds = torch.sigmoid(outputs) > 0.5
                val_correct += preds.eq(labels.view_as(preds)).sum().item()
                val_total += frames.size(0)

        val_loss = val_loss / val_total
        val_acc = val_correct / val_total

        print(
            f"Epoch {epoch+1}/{num_epochs} - "
            f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f} - "
            f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}"
        )

        # Save best model
        if val_acc > best_val_acc and save_path:
            best_val_acc = val_acc
            torch.save(model.state_dict(), save_path)
            print(f"Saved best model to {save_path}")


def main():
    parser = argparse.ArgumentParser(description="Train EfficientNet for deepfake detection")
    parser.add_argument(
        "--train-csv",
        type=str,
        default="/Users/gokulmallabathula/deep-fake/artifacts/splits/train.csv",
        help="Path to training CSV split",
    )
    parser.add_argument(
        "--val-csv",
        type=str,
        default="/Users/gokulmallabathula/deep-fake/artifacts/splits/val.csv",
        help="Path to validation CSV split",
    )
    parser.add_argument(
        "--video-root",
        type=str,
        default="/Users/gokulmallabathula/deep-fake/datasets/raw",
        help="Root directory of video datasets",
    )
    parser.add_argument(
        "--frames-per-video",
        type=int,
        default=10,
        help="Number of frames to extract per video",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size for training",
    )
    parser.add_argument(
        "--num-epochs",
        type=int,
        default=10,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.001,
        help="Learning rate",
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        default="/Users/gokulmallabathula/deep-fake/ml/training",
        help="Directory to save model checkpoints",
    )
    parser.add_argument(
        "--no-pretrained",
        action="store_true",
        help="Do not use pretrained weights",
    )
    args = parser.parse_args()

    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Define transforms for EfficientNet
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        ),
    ])

    # Create datasets
    train_dataset = VideoFrameDataset(
        csv_path=Path(args.train_csv),
        video_root=Path(args.video_root),
        frames_per_video=args.frames_per_video,
        transform=transform,
    )
    val_dataset = VideoFrameDataset(
        csv_path=Path(args.val_csv),
        video_root=Path(args.video_root),
        frames_per_video=args.frames_per_video,
        transform=transform,
    )

    print(f"Training samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
    )

    # Initialize model
    model = get_efficientnet_model(pretrained=not args.no_pretrained)
    model = model.to(device)

    # Loss and optimizer
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)

    # Create save directory
    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / "efficientnet_b0_deepfake.pth"

    # Train model
    train_model(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        device=device,
        num_epochs=args.num_epochs,
        save_path=save_path,
    )

    print("Training completed!")


if __name__ == "__main__":
    main()