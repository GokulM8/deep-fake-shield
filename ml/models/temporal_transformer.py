"""Temporal Transformer over EfficientNet frame embeddings."""

from __future__ import annotations

import torch
from torch import nn


class TemporalTransformer(nn.Module):
    def __init__(self, embedding_dim: int, heads: int = 4, layers: int = 2, max_length: int = 32, dropout: float = 0.1) -> None:
        super().__init__()
        self.position = nn.Parameter(torch.zeros(1, max_length, embedding_dim))
        encoder_layer = nn.TransformerEncoderLayer(embedding_dim, heads, batch_first=True, dropout=dropout, norm_first=True)
        self.encoder = nn.TransformerEncoder(encoder_layer, layers)
        self.classifier = nn.Sequential(nn.LayerNorm(embedding_dim), nn.Linear(embedding_dim, 2))

    def forward(self, embeddings: torch.Tensor, padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        sequence = embeddings + self.position[:, : embeddings.shape[1]]
        encoded = self.encoder(sequence, src_key_padding_mask=padding_mask)
        if padding_mask is None:
            pooled = encoded.mean(dim=1)
        else:
            valid = (~padding_mask).unsqueeze(-1)
            pooled = (encoded * valid).sum(dim=1) / valid.sum(dim=1).clamp_min(1)
        return self.classifier(pooled)
