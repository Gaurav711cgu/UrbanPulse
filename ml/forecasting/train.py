"""
forecasting/train.py
────────────────────
Train the LSTM traffic demand forecaster.

Usage:
    python -m ml.forecasting.train --data data/traffic_history.csv --epochs 100
"""

import argparse
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from sklearn.preprocessing import MinMaxScaler

from ml.forecasting.lstm_model import LSTMForecaster


# ── Dataset ───────────────────────────────────────────────────

class TrafficDataset(Dataset):
    """
    Sliding window dataset from time-series traffic counts.
    X: [seq_len] historical counts
    y: [output_steps] future counts
    """
    def __init__(self, series: np.ndarray, seq_len: int = 30, output_steps: int = 3):
        self.X, self.y = [], []
        for i in range(len(series) - seq_len - output_steps):
            self.X.append(series[i : i + seq_len])
            self.y.append(series[i + seq_len : i + seq_len + output_steps])
        self.X = torch.tensor(np.array(self.X), dtype=torch.float32).unsqueeze(-1)
        self.y = torch.tensor(np.array(self.y), dtype=torch.float32)

    def __len__(self): return len(self.X)
    def __getitem__(self, idx): return self.X[idx], self.y[idx]


# ── Synthetic data generator (no CSV needed for demo) ─────────

def generate_synthetic_series(n_points: int = 5000) -> np.ndarray:
    """
    Simulate realistic daily traffic patterns.
    Two peaks: morning (9 AM) and evening (6 PM).
    """
    data = []
    for i in range(n_points):
        hour = (i * 5 / 60) % 24   # each sample = 5 min interval
        morning = math.exp(-0.5 * ((hour - 9) / 1.2) ** 2) * 80
        evening = math.exp(-0.5 * ((hour - 18) / 1.2) ** 2) * 70
        noise = random.gauss(0, 4)
        base = 5
        val = max(0, base + morning + evening + noise)
        data.append(val)
    return np.array(data, dtype=np.float32)


# ── Training loop ──────────────────────────────────────────────

def train(
    data_path: Optional[str] = None,
    epochs: int = 100,
    seq_len: int = 30,
    output_steps: int = 3,
    hidden_size: int = 64,
    num_layers: int = 2,
    batch_size: int = 64,
    lr: float = 1e-3,
    save_path: str = "ml/weights/lstm_forecaster.pt",
):
    # Load or generate data
    if data_path and Path(data_path).exists():
        df = pd.read_csv(data_path)
        series = df["vehicle_count"].values.astype(np.float32)
        print(f"Loaded {len(series)} records from {data_path}")
    else:
        print("No data file found — using synthetic training data")
        series = generate_synthetic_series(5000)

    # Normalize
    scaler = MinMaxScaler()
    series_scaled = scaler.fit_transform(series.reshape(-1, 1)).flatten()

    # Train/val split
    split = int(len(series_scaled) * 0.8)
    train_ds = TrafficDataset(series_scaled[:split], seq_len, output_steps)
    val_ds = TrafficDataset(series_scaled[split:], seq_len, output_steps)
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_dl = DataLoader(val_ds, batch_size=batch_size)

    # Model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = LSTMForecaster(hidden_size=hidden_size, num_layers=num_layers, output_steps=output_steps)
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    criterion = nn.MSELoss()

    best_val_loss = float("inf")
    print(f"\nTraining LSTM on {device} | {epochs} epochs | {len(train_ds)} train samples\n")

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for X, y in train_dl:
            X, y = X.to(device), y.to(device)
            optimizer.zero_grad()
            pred = model(X)
            loss = criterion(pred, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X, y in val_dl:
                X, y = X.to(device), y.to(device)
                val_loss += criterion(model(X), y).item()

        train_loss /= len(train_dl)
        val_loss /= len(val_dl)
        scheduler.step(val_loss)

        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{epochs}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            model.save(save_path)

    print(f"\nBest val loss: {best_val_loss:.4f} — weights saved to {save_path}")
    return model


if __name__ == "__main__":
    import sys
    from typing import Optional

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default=None)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--save", type=str, default="ml/weights/lstm_forecaster.pt")
    args = parser.parse_args()

    train(
        data_path=args.data,
        epochs=args.epochs,
        hidden_size=args.hidden,
        save_path=args.save,
    )
