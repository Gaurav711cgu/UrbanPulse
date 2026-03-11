"""
Backend unit tests.
Run with: pytest tests/ -v
"""

import pytest
from app.services.mock_data import MockDataService
from app.services.lstm_service import LSTMForecastService
from app.services.signal_controller import SignalController


class TestMockDataService:
    def setup_method(self):
        self.svc = MockDataService()

    def test_generate_tick_returns_events(self):
        events = self.svc.generate_tick(1)
        assert len(events) > 0

    def test_events_have_required_fields(self):
        events = self.svc.generate_tick(1)
        for e in events:
            assert "event_type" in e
            assert "payload" in e
            assert "timestamp" in e

    def test_event_types_are_valid(self):
        valid_types = {"traffic_update", "signal_change", "emergency", "stats"}
        for tick in range(1, 20):
            events = self.svc.generate_tick(tick)
            for e in events:
                assert e["event_type"] in valid_types

    def test_traffic_update_payload(self):
        events = self.svc.generate_tick(1)
        traffic = [e for e in events if e["event_type"] == "traffic_update"]
        assert len(traffic) > 0
        p = traffic[0]["payload"]
        assert "junction_id" in p
        assert "flows" in p
        assert "total_vehicles" in p
        assert "congestion_level" in p
        assert 0.0 <= p["congestion_level"] <= 1.0

    def test_congestion_level_normalized(self):
        for tick in range(1, 10):
            events = self.svc.generate_tick(tick)
            for e in events:
                if e["event_type"] == "traffic_update":
                    assert 0.0 <= e["payload"]["congestion_level"] <= 1.0

    def test_emergency_event_rare(self):
        """Emergency events should be infrequent."""
        emergency_count = 0
        for tick in range(1, 100):
            events = self.svc.generate_tick(tick)
            emergency_count += sum(1 for e in events if e["event_type"] == "emergency")
        assert emergency_count < 20  # less than 20% of ticks

    def test_stats_event_periodic(self):
        """Stats events should appear every 5 ticks."""
        for tick in [5, 10, 15, 20]:
            events = self.svc.generate_tick(tick)
            stats = [e for e in events if e["event_type"] == "stats"]
            assert len(stats) == 1

    def test_time_factor_between_0_and_1(self):
        tf = self.svc._time_factor()
        assert 0.0 <= tf <= 1.0


class TestLSTMForecastService:
    def setup_method(self):
        self.svc = LSTMForecastService()

    def test_heuristic_forecast_returns_correct_count(self):
        preds = self.svc.heuristic_forecast(15)
        assert len(preds) == 3  # 15 / 5 = 3 steps

    def test_heuristic_forecast_30min(self):
        preds = self.svc.heuristic_forecast(30)
        assert len(preds) == 6

    def test_heuristic_values_non_negative(self):
        preds = self.svc.heuristic_forecast(15)
        for p in preds:
            assert p.predicted_vehicles >= 0

    def test_heuristic_confidence_decreases(self):
        preds = self.svc.heuristic_forecast(30)
        confidences = [p.confidence for p in preds]
        # Generally confidence should decrease over horizon
        assert confidences[0] >= confidences[-1]

    def test_statistical_predict_empty_history(self):
        preds = self.svc._statistical_predict([], 15)
        assert len(preds) == 3

    def test_statistical_predict_with_history(self):
        history = [10, 12, 15, 14, 18, 20, 22, 19, 17, 16]
        preds = self.svc._statistical_predict(history, 15)
        assert len(preds) == 3
        for p in preds:
            assert p.predicted_vehicles >= 0
            assert 0.0 <= p.confidence <= 1.0

    def test_minutes_ahead_increments(self):
        preds = self.svc.heuristic_forecast(15)
        expected = [5, 10, 15]
        for p, exp in zip(preds, expected):
            assert p.minutes_ahead == exp


class TestSignalController:
    def setup_method(self):
        self.ctrl = SignalController()

    def test_observe_returns_6_values(self):
        state = self.ctrl._observe(1)
        assert len(state) == 6

    def test_heuristic_ns_green_when_ns_dominant(self):
        # NS count much higher than EW → should return NS Green (phase 0)
        state = [50, 5, 80, 10, 0, 20]
        action = self.ctrl._heuristic(state)
        assert action["phase"] == 0

    def test_heuristic_ew_green_when_ew_dominant(self):
        # EW count much higher → should return EW Green (phase 2)
        state = [5, 50, 10, 80, 2, 20]
        action = self.ctrl._heuristic(state)
        assert action["phase"] == 2

    def test_heuristic_duration_in_range(self):
        state = [30, 20, 50, 30, 0, 15]
        action = self.ctrl._heuristic(state)
        assert 10 <= action["duration"] <= 60
