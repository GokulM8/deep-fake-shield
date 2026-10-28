"""Video-level heads over frozen EfficientNet-B0 frame embeddings (trained on Colab).

Both take ``x`` [B, n_frames, d_in] with embeddings in their sampling slot and ``mask`` [B, n_frames]
where True means the frame has a face (the opposite of ``TemporalTransformer``'s padding mask).
Module names match the checkpoints' state dict keys, so do not rename them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from torch import nn


def masked_mean(x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    m = mask.unsqueeze(-1).float()
    return (x * m).sum(1) / m.sum(1).clamp(min=1)


class TemporalHead(nn.Module):
    """LayerNorm + projection, learnable positions, pre-norm Transformer encoder, masked mean pooling."""

    def __init__(self, c: dict[str, Any]) -> None:
        super().__init__()
        self.proj = nn.Sequential(nn.LayerNorm(c["d_in"]), nn.Linear(c["d_in"], c["d_model"]))
        self.pos = nn.Parameter(torch.zeros(1, c["n_frames"], c["d_model"]))
        layer = nn.TransformerEncoderLayer(
            c["d_model"], c["heads"], 4 * c["d_model"], c["dropout"], batch_first=True, norm_first=True
        )
        # Pre-norm layers make the nested-tensor fast path inapplicable; say so to silence the warning.
        self.enc = nn.TransformerEncoder(layer, c["layers"], enable_nested_tensor=False)
        self.head = nn.Sequential(nn.LayerNorm(c["d_model"]), nn.Dropout(c["dropout"]), nn.Linear(c["d_model"], 2))

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        z = self.enc(self.proj(x) + self.pos, src_key_padding_mask=~mask)
        return self.head(masked_mean(z, mask))


class MeanPoolMLP(nn.Module):
    """Masked mean of the frame embeddings, then a two-layer MLP; frame order is ignored."""

    def __init__(self, c: dict[str, Any]) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(c["d_in"]), nn.Linear(c["d_in"], c["d_model"]), nn.GELU(), nn.Dropout(c["dropout"]),
            nn.Linear(c["d_model"], 2),
        )

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        return self.net(masked_mean(x, mask))


HEADS: dict[str, type[nn.Module]] = {"temporal_transformer": TemporalHead, "meanpool_mlp": MeanPoolMLP}


def load_head(path: Path, device: torch.device | str = "cpu") -> tuple[nn.Module, dict[str, Any]]:
    """Build the head named by ``checkpoint["head"]``, load its weights strictly, and return it in
    eval mode with the checkpoint (``threshold``, ``n_frames``, ``config``, ...)."""
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    kind = checkpoint.get("head")
    if kind not in HEADS:
        raise ValueError(f"{Path(path).name}: unknown head {kind!r}; expected one of {sorted(HEADS)}")
    for key in ("state_dict", "config", "threshold", "n_frames"):
        if key not in checkpoint:
            raise KeyError(f"{Path(path).name} is missing {key!r} (keys: {sorted(checkpoint)})")
    head = HEADS[kind](checkpoint["config"])
    head.load_state_dict(checkpoint["state_dict"])
    return head.to(device).eval(), checkpoint
