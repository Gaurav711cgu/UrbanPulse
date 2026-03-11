"""
forecasting/lstm_model.py
─────────────────────────
LSTM-based traffic demand forecaster.

Architecture:
    Input  → [batch, seq_len, 1]  (vehicle counts)
    LSTM   → 2 layers, hidden=64
    Linear → multi-step output    [batch, horizon_steps]

Usage:
    model = LSTMForecaster(hidden_size=64, num_layers=2, output_steps=3)
    # output_steps=3  →  predicts t+5, t+10, t+15 minutes
"""

from __future__ import annotations

import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from typing import Optional


class LSTMForecaster(nn.Module):
    def __init__(
        self,
        input_size: int = 1,
        hidden_size: int = 64,
        num_layers: int = 2,
        output_steps: int = 3,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.output_steps = output_steps

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.bn = nn.BatchNorm1d(hidden_size)
        self.head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, output_steps),
        )

    def forward(self, x: torch.Tensor, steps: Optional[int] = None) -> torch.Tensor:
        """
        Args:
            x: [batch, seq_len, input_size]
            steps: Override output steps (for variable horizon at inference).

        Returns:
            [batch, output_steps]
        """
        out, _ = self.lstm(x)
        last = out[:, -1, :]             # take last timestep
        last = self.bn(last)
        preds = self.head(last)
        return preds

    def save(self, path: str | Path):
        torch.save({"state_dict": self.state_dict(), "config": {
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "output_steps": self.output_steps,
        }}, path)

    @classmethod
    def load(cls, path: str | Path) -> "LSTMForecaster":
        ckpt = torch.load(path, map_location="cpu")
        cfg = ckpt["config"]
        model = cls(**cfg)
        model.load_state_dict(ckpt["state_dict"])
        return model
