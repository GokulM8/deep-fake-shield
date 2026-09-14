"""EfficientNet frame classifier used by the video baseline."""

from __future__ import annotations

import torch.nn as nn
from torchvision import models


def build_model(pretrained: bool = False, dropout: float = 0.3) -> nn.Module:
    weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
    model = models.efficientnet_b0(weights=weights)
    features = model.classifier[1].in_features
    model.classifier = nn.Sequential(nn.Dropout(dropout), nn.Linear(features, 2))
    return model
