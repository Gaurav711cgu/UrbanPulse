"""
LSTMForecastService — wraps the LSTM model for API use.
Falls back to a statistical heuristic if model weights are not loaded.
"""

import math
import random
from datetime import datetime
from pathlib import Path

from app.schemas.schemas import ForecastPoint
from app.core.config import settings


class LSTMForecastService:
    def __init__(self):
        self._model = None
        self._scaler = None
        self._load()

    def _load(self):
        weights = Path(settings.LSTM_WEIGHTS)
        if weights.exists():
            try:
                import torch
                from ml.forecasting.lstm_model import LSTMForecaster
                self._model = LSTMForecaster.load(weights)
                self._model.eval()
            except Exception as e:
                pass  # will use heuristic

    def predict(self, history: list[int], horizon_minutes: int = 15) -> list[ForecastPoint]:
        """
        Predict future vehicle counts from a history sequence.
        Uses the LSTM model when available, otherwise statistical heuristic.
        """
        if self._model:
            return self._model_predict(history, horizon_minutes)
        return self._statistical_predict(history, horizon_minutes)

    def _model_predict(self, history: list[int], horizon_minutes: int) -> list[ForecastPoint]:
        import torch
        import numpy as np

        x = torch.tensor(history[-30:], dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
        with torch.no_grad():
            preds = self._model(x, steps=horizon_minutes // 5)

        return [
            ForecastPoint(
                minutes_ahead=(i + 1) * 5,
                predicted_vehicles=round(float(preds[0, i]), 1),
                confidence=round(0.92 - i * 0.02, 2),
            )
            for i in range(len(preds[0]))
        ]

    def _statistical_predict(self, history: list[int], horizon_minutes: int) -> list[ForecastPoint]:
        """Simple moving-average + trend forecast as fallback."""
        if not history:
            return self.heuristic_forecast(horizon_minutes)

        window = history[-10:] if len(history) >= 10 else history
        avg = sum(window) / len(window)
        trend = (window[-1] - window[0]) / max(len(window), 1)
        steps = horizon_minutes // 5

        points = []
        for i in range(steps):
            pred = avg + trend * (i + 1) + random.uniform(-2, 2)
            pred = max(0, round(pred, 1))
            confidence = round(max(0.6, 0.92 - i * 0.05), 2)
            points.append(ForecastPoint(
                minutes_ahead=(i + 1) * 5,
                predicted_vehicles=pred,
                confidence=confidence,
            ))
        return points

    def heuristic_forecast(self, horizon_minutes: int) -> list[ForecastPoint]:
        """Pure heuristic based on time-of-day patterns."""
        hour = datetime.now().hour
        base = 30 + 20 * math.sin((hour - 8) * math.pi / 12)
        steps = horizon_minutes // 5
        return [
            ForecastPoint(
                minutes_ahead=(i + 1) * 5,
                predicted_vehicles=round(max(0, base + random.uniform(-3, 3)), 1),
                confidence=round(0.75 - i * 0.03, 2),
            )
            for i in range(steps)
        ]
