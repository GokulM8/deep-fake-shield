"""Grad-CAM for the EfficientNet fake-class output."""

from __future__ import annotations

import torch
import torch.nn.functional as F


class GradCAM:
    def __init__(self, model: torch.nn.Module, target_layer: torch.nn.Module) -> None:
        self.model = model
        self.activations = None
        self.gradients = None
        target_layer.register_forward_hook(self._save_activations)
        target_layer.register_full_backward_hook(self._save_gradients)

    def _save_activations(self, _module, _inputs, output) -> None:
        self.activations = output

    def _save_gradients(self, _module, _inputs, output) -> None:
        self.gradients = output[0]

    def __call__(self, image: torch.Tensor) -> torch.Tensor:
        self.model.zero_grad(set_to_none=True)
        logits = self.model(image)
        logits[:, 1].sum().backward()
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        heatmap = F.relu((weights * self.activations).sum(dim=1, keepdim=True))
        heatmap = F.interpolate(heatmap, size=image.shape[-2:], mode="bilinear", align_corners=False)
        return heatmap / heatmap.amax(dim=(2, 3), keepdim=True).clamp_min(1e-8)
