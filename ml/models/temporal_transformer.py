"""Temporal Transformer over EfficientNet frame embeddings."""

from __future__ import annotations

import torch
from torch import nn


class TemporalTransformer(nn.Module):
    """Classify a video from a sequence of per-frame embeddings.

    With ``model_dim`` set, embeddings are first projected to that width; without it the encoder
    runs at ``embedding_dim`` (the original sanity-run configuration, so older checkpoints load).
    ``padding_mask`` marks frames to ignore (True = no face); pooling averages valid frames only.
    """

    def __init__(
        self,
        embedding_dim: int,
        heads: int = 4,
        layers: int = 2,
        max_length: int = 32,
        dropout: float = 0.1,
        model_dim: int | None = None,
        feedforward_dim: int = 2048,
    ) -> None:
        super().__init__()
        width = model_dim or embedding_dim
        self.projection = (
            nn.Sequential(nn.Linear(embedding_dim, width), nn.Dropout(dropout)) if model_dim else nn.Identity()
        )
        self.position = nn.Parameter(torch.zeros(1, max_length, width))
        encoder_layer = nn.TransformerEncoderLayer(
            width, heads, dim_feedforward=feedforward_dim, batch_first=True, dropout=dropout, norm_first=True
        )
        # Pre-norm layers make the nested-tensor fast path inapplicable; say so to silence the warning.
        self.encoder = nn.TransformerEncoder(encoder_layer, layers, enable_nested_tensor=False)
        self.classifier = nn.Sequential(nn.LayerNorm(width), nn.Linear(width, 2))

    def forward(self, embeddings: torch.Tensor, padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        sequence = self.projection(embeddings) + self.position[:, : embeddings.shape[1]]
        encoded = self.encoder(sequence, src_key_padding_mask=padding_mask)
        if padding_mask is None:
            pooled = encoded.mean(dim=1)
        else:
            valid = (~padding_mask).unsqueeze(-1)
            pooled = (encoded * valid).sum(dim=1) / valid.sum(dim=1).clamp_min(1)
        return self.classifier(pooled)
