"""
rl_agent/dqn_agent.py
─────────────────────
Deep Q-Network agent for adaptive traffic signal control.

State space  (6 values):
  [ns_count, ew_count, ns_queue_m, ew_queue_m, current_phase, time_in_phase]

Action space (4 discrete):
  0 = NS_GREEN   (North-South green, East-West red)
  1 = NS_YELLOW  (transition)
  2 = EW_GREEN   (East-West green, North-South red)
  3 = EW_YELLOW  (transition)

Reward:
  - Negative total waiting time across all lanes
  - Bonus for clearing emergency vehicles
  - Penalty for excessive phase switching
"""

from __future__ import annotations

import random
from collections import deque
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


# ── Neural network ─────────────────────────────────────────────

class DQNetwork(nn.Module):
    def __init__(self, state_size: int = 6, action_size: int = 4, hidden: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden // 2),
            nn.ReLU(),
            nn.Linear(hidden // 2, action_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ── Replay buffer ──────────────────────────────────────────────

class ReplayBuffer:
    def __init__(self, capacity: int = 50_000):
        self.buffer: deque = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.float32),
        )

    def __len__(self): return len(self.buffer)


# ── DQN Agent ─────────────────────────────────────────────────

class DQNAgent:
    """
    Double DQN with experience replay and target network.

    Args:
        state_size: Dimension of state vector.
        action_size: Number of discrete actions.
        lr: Learning rate.
        gamma: Discount factor.
        epsilon_start: Initial exploration rate.
        epsilon_end: Minimum exploration rate.
        epsilon_decay: Multiplicative decay per step.
        batch_size: Minibatch size for training.
        target_update_freq: Steps between target network syncs.
    """

    def __init__(
        self,
        state_size: int = 6,
        action_size: int = 4,
        lr: float = 1e-3,
        gamma: float = 0.95,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.995,
        batch_size: int = 64,
        target_update_freq: int = 100,
        device: str = "cpu",
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.device = torch.device(device)
        self.steps = 0

        self.q_net = DQNetwork(state_size, action_size).to(self.device)
        self.target_net = DQNetwork(state_size, action_size).to(self.device)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        self.loss_fn = nn.SmoothL1Loss()
        self.memory = ReplayBuffer()

    def act(self, state: list[float], explore: bool = True) -> int:
        """
        Choose action via ε-greedy policy.
        Set explore=False during inference (production).
        """
        if explore and random.random() < self.epsilon:
            return random.randrange(self.action_size)

        state_t = torch.tensor(state, dtype=torch.float32).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.q_net(state_t)
        return int(q_values.argmax(dim=1).item())

    def remember(self, state, action, reward, next_state, done):
        self.memory.push(state, action, reward, next_state, done)

    def learn(self) -> Optional[float]:
        """Sample a minibatch and update Q-network."""
        if len(self.memory) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)

        states_t = torch.tensor(states).to(self.device)
        actions_t = torch.tensor(actions).to(self.device)
        rewards_t = torch.tensor(rewards).to(self.device)
        next_states_t = torch.tensor(next_states).to(self.device)
        dones_t = torch.tensor(dones).to(self.device)

        # Current Q values
        q_vals = self.q_net(states_t).gather(1, actions_t.unsqueeze(1)).squeeze(1)

        # Double DQN: select action with online net, evaluate with target net
        with torch.no_grad():
            best_actions = self.q_net(next_states_t).argmax(1)
            target_q = self.target_net(next_states_t).gather(1, best_actions.unsqueeze(1)).squeeze(1)
            targets = rewards_t + self.gamma * target_q * (1 - dones_t)

        loss = self.loss_fn(q_vals, targets)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), 1.0)
        self.optimizer.step()

        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        self.steps += 1

        # Sync target network
        if self.steps % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.q_net.state_dict())

        return loss.item()

    def save(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "q_net": self.q_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "epsilon": self.epsilon,
            "steps": self.steps,
            "config": {
                "state_size": self.state_size,
                "action_size": self.action_size,
                "gamma": self.gamma,
            }
        }, path)

    @classmethod
    def load(cls, path: str | Path) -> "DQNAgent":
        ckpt = torch.load(path, map_location="cpu")
        cfg = ckpt["config"]
        agent = cls(state_size=cfg["state_size"], action_size=cfg["action_size"], gamma=cfg["gamma"])
        agent.q_net.load_state_dict(ckpt["q_net"])
        agent.target_net.load_state_dict(ckpt["target_net"])
        agent.epsilon = ckpt["epsilon"]
        agent.steps = ckpt["steps"]
        return agent
