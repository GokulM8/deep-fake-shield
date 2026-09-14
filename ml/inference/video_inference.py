"""Frame sampling and video-level aggregation for trained checkpoints."""

from __future__ import annotations

from pathlib import Path

import cv2
import torch
from PIL import Image
from torchvision import transforms

from data.video_dataset import FaceCropper, sample_frame_indices


def predict_video(model, video_path: str | Path, device: torch.device, frames: int = 16) -> dict:
    model.eval()
    capture = cv2.VideoCapture(str(video_path))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    cropper = FaceCropper()
    transform = transforms.Compose([
        transforms.Resize((224, 224)), transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    images, timeline = [], []
    for frame_index in sample_frame_indices(frame_count, frames):
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        ok, frame = capture.read()
        if not ok:
            continue
        crop = cropper.crop(frame)
        image = crop if crop is not None else frame
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        images.append(transform(Image.fromarray(image)))
        timeline.append({"frame_id": int(frame_index), "timestamp": round(frame_index / fps, 3) if fps else None})
    capture.release()
    if not images:
        return {"fake_probability": None, "frame_scores": [], "suspicious_frames": []}
    with torch.inference_mode():
        logits = model(torch.stack(images).to(device))
        probabilities = torch.softmax(logits, dim=1)[:, 1].cpu().tolist()
    for item, probability in zip(timeline, probabilities):
        item["fake_probability"] = round(float(probability), 6)
        item["prediction"] = int(probability >= 0.5)
    mean_probability = sum(probabilities) / len(probabilities)
    suspicious = [item for item in timeline if item["fake_probability"] >= 0.7]
    return {
        "fake_probability": round(mean_probability, 6),
        "frame_scores": timeline,
        "suspicious_frames": suspicious,
    }
