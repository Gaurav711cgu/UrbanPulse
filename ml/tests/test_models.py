"""
ML unit tests.
Run with: pytest ml/tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
import torch
import numpy as np
from ml.rl_agent.dqn_agent import DQNAgent, DQNetwork, ReplayBuffer
from ml.forecasting.lstm_model import LSTMForecaster


class TestDQNetwork:
    def test_output_shape(self):
        net = DQNetwork(state_size=6, action_size=4)
        x = torch.randn(8, 6)  # batch=8
        out = net(x)
        assert out.shape == (8, 4)

    def test_no_nan_output(self):
        net = DQNetwork(6, 4)
        x = torch.randn(4, 6)
        out = net(x)
        assert not torch.isnan(out).any()


class TestReplayBuffer:
    def test_push_and_len(self):
        buf = ReplayBuffer(capacity=100)
        for i in range(10):
            buf.push([0]*6, 0, 1.0, [0]*6, False)
        assert len(buf) == 10

    def test_capacity_limit(self):
        buf = ReplayBuffer(capacity=5)
        for i in range(10):
            buf.push([i]*6, 0, 0.0, [i]*6, False)
        assert len(buf) == 5

    def test_sample_correct_size(self):
        buf = ReplayBuffer()
        for _ in range(100):
            buf.push([0]*6, 0, 0.0, [0]*6, False)
        states, actions, rewards, next_states, dones = buf.sample(32)
        assert len(states) == 32
        assert len(actions) == 32


class TestDQNAgent:
    def test_act_returns_valid_action(self):
        agent = DQNAgent(state_size=6, action_size=4)
        state = [0.5] * 6
        action = agent.act(state, explore=False)
        assert 0 <= action < 4

    def test_act_explore_returns_valid_action(self):
        agent = DQNAgent(state_size=6, action_size=4, epsilon_start=1.0)
        for _ in range(20):
            action = agent.act([0.5]*6, explore=True)
            assert 0 <= action < 4

    def test_learn_returns_none_when_buffer_small(self):
        agent = DQNAgent(state_size=6, action_size=4, batch_size=64)
        agent.remember([0]*6, 0, 0.0, [0]*6, False)
        loss = agent.learn()
        assert loss is None

    def test_learn_returns_float_with_enough_samples(self):
        agent = DQNAgent(state_size=6, action_size=4, batch_size=8)
        for _ in range(20):
            agent.remember([0.5]*6, 0, -1.0, [0.4]*6, False)
        loss = agent.learn()
        assert isinstance(loss, float)
        assert loss >= 0

    def test_epsilon_decays(self):
        agent = DQNAgent(state_size=6, action_size=4, batch_size=4, epsilon_decay=0.9)
        for _ in range(20):
            agent.remember([0.5]*6, 0, -1.0, [0.4]*6, False)
        eps_before = agent.epsilon
        agent.learn()
        assert agent.epsilon < eps_before


class TestLSTMForecaster:
    def test_forward_shape(self):
        model = LSTMForecaster(hidden_size=32, num_layers=1, output_steps=3)
        x = torch.randn(4, 30, 1)  # batch=4, seq=30, features=1
        out = model(x)
        assert out.shape == (4, 3)

    def test_no_nan_in_output(self):
        model = LSTMForecaster(hidden_size=32, num_layers=1, output_steps=3)
        x = torch.randn(2, 30, 1)
        out = model(x)
        assert not torch.isnan(out).any()

    def test_save_and_load(self, tmp_path):
        model = LSTMForecaster(hidden_size=32, num_layers=1, output_steps=3)
        path = tmp_path / "test_lstm.pt"
        model.save(str(path))
        loaded = LSTMForecaster.load(str(path))
        assert loaded.hidden_size == 32
        assert loaded.output_steps == 3
