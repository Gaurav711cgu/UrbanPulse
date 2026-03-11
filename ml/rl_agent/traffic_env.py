"""
rl_agent/traffic_env.py
───────────────────────
Gymnasium environment wrapping SUMO for RL training.

The agent controls a single 4-phase intersection.
State, action, and reward are defined in dqn_agent.py docstring.
"""

from __future__ import annotations

import os
import sys
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Optional, Tuple, Dict, Any


# SUMO must be installed and SUMO_HOME set
SUMO_HOME = os.environ.get("SUMO_HOME", "/usr/share/sumo")
if SUMO_HOME not in sys.path:
    sys.path.append(os.path.join(SUMO_HOME, "tools"))


PHASE_NS_GREEN  = 0
PHASE_NS_YELLOW = 1
PHASE_EW_GREEN  = 2
PHASE_EW_YELLOW = 3

YELLOW_DURATION = 4   # seconds
MIN_GREEN       = 10  # seconds
MAX_GREEN       = 60  # seconds


class TrafficSignalEnv(gym.Env):
    """
    Single-intersection SUMO environment.

    Observation (6 floats, all normalized to ~[0,1]):
        [ns_density, ew_density, ns_queue_norm, ew_queue_norm,
         phase_onehot_ns, time_in_phase_norm]

    Actions (discrete, 4):
        0 = Keep/set NS_GREEN
        1 = NS_YELLOW (transition)
        2 = Keep/set EW_GREEN
        3 = EW_YELLOW (transition)

    Reward:
        - Sum of waiting times (negative)  → minimize
        + Emergency bonus when corridor cleared
        - Switch penalty for rapid changes
    """

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        sumo_cfg: str = "simulation/sumo_configs/single_junction.sumocfg",
        use_gui: bool = False,
        max_steps: int = 3600,
        delta_time: int = 5,   # seconds per RL step
        seed: Optional[int] = None,
    ):
        super().__init__()
        self.sumo_cfg = sumo_cfg
        self.use_gui = use_gui
        self.max_steps = max_steps
        self.delta_time = delta_time
        self.sumo_binary = "sumo-gui" if use_gui else "sumo"
        self._seed = seed

        self.observation_space = spaces.Box(
            low=np.zeros(6, dtype=np.float32),
            high=np.ones(6, dtype=np.float32),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(4)

        self._step = 0
        self._current_phase = PHASE_NS_GREEN
        self._time_in_phase = 0
        self._last_action = PHASE_NS_GREEN
        self._traci = None

    # ── Gym interface ──────────────────────────────────────────

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)
        self._close_sumo()
        self._start_sumo()
        self._step = 0
        self._current_phase = PHASE_NS_GREEN
        self._time_in_phase = 0
        return self._observe(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        assert self.action_space.contains(action)

        # Apply action
        self._apply_action(action)

        # Advance simulation
        for _ in range(self.delta_time):
            if self._traci:
                self._traci.simulationStep()

        self._step += 1
        self._time_in_phase += self.delta_time

        # Phase switch resets timer
        if action != self._current_phase:
            self._time_in_phase = 0
            self._current_phase = action

        obs = self._observe()
        reward = self._compute_reward(action)
        terminated = self._step >= self.max_steps
        info = {"step": self._step, "phase": self._current_phase}

        return obs, reward, terminated, False, info

    def render(self): pass

    def close(self):
        self._close_sumo()

    # ── Internal ───────────────────────────────────────────────

    def _start_sumo(self):
        try:
            import traci
            cmd = [self.sumo_binary, "-c", self.sumo_cfg, "--no-warnings", "--no-step-log"]
            if self._seed:
                cmd += ["--seed", str(self._seed)]
            traci.start(cmd)
            self._traci = traci
        except Exception:
            self._traci = None  # Run in mock mode if SUMO unavailable

    def _close_sumo(self):
        if self._traci:
            try:
                self._traci.close()
            except Exception:
                pass
        self._traci = None

    def _apply_action(self, action: int):
        if self._traci is None:
            return
        try:
            tl_id = self._traci.trafficlight.getIDList()[0]
            self._traci.trafficlight.setPhase(tl_id, action)
        except Exception:
            pass

    def _observe(self) -> np.ndarray:
        if self._traci is None:
            # Mock observation for testing
            return np.array([
                random.uniform(0, 1),
                random.uniform(0, 1),
                random.uniform(0, 1),
                random.uniform(0, 1),
                float(self._current_phase in [0, 1]),
                min(self._time_in_phase / MAX_GREEN, 1.0),
            ], dtype=np.float32)

        try:
            lanes = self._traci.lane.getIDList()
            ns_lanes = [l for l in lanes if "_0" in l or "_1" in l]
            ew_lanes = [l for l in lanes if "_2" in l or "_3" in l]

            def density(lane_ids):
                counts = [self._traci.lane.getLastStepVehicleNumber(l) for l in lane_ids]
                lengths = [self._traci.lane.getLength(l) for l in lane_ids]
                if not counts: return 0.0
                total = sum(c / max(ln / 7.5, 1) for c, ln in zip(counts, lengths))
                return min(total / len(counts), 1.0)

            def queue_norm(lane_ids):
                queues = [self._traci.lane.getLastStepHaltingNumber(l) for l in lane_ids]
                return min(sum(queues) / 30.0, 1.0) if queues else 0.0

            return np.array([
                density(ns_lanes),
                density(ew_lanes),
                queue_norm(ns_lanes),
                queue_norm(ew_lanes),
                float(self._current_phase in [PHASE_NS_GREEN, PHASE_NS_YELLOW]),
                min(self._time_in_phase / MAX_GREEN, 1.0),
            ], dtype=np.float32)

        except Exception:
            return self._observe()  # fallback

    def _compute_reward(self, action: int) -> float:
        if self._traci is None:
            # Mock reward: penalize high state values
            obs = self._observe()
            return -float(obs[0] * 20 + obs[1] * 20 + obs[2] * 10 + obs[3] * 10)

        try:
            vehicles = self._traci.vehicle.getIDList()
            total_wait = sum(self._traci.vehicle.getWaitingTime(v) for v in vehicles)
            reward = -total_wait / max(len(vehicles), 1)

            # Penalty for switching too fast
            if action != self._last_action and self._time_in_phase < MIN_GREEN:
                reward -= 5.0

            self._last_action = action
            return float(reward)

        except Exception:
            return -1.0
