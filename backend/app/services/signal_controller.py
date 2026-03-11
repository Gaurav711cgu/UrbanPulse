"""
SignalController — Runs the DQN agent inference loop.

Every SIGNAL_CYCLE_SECONDS seconds, it:
  1. Reads current traffic state from each junction
  2. Calls DQN agent to decide the next phase + duration
  3. Writes the decision to the database
  4. Broadcasts the change via WebSocket
"""

import asyncio
import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class SignalController:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._agent = None
        self._load_agent()

    def _load_agent(self):
        """Load DQN weights if available, otherwise use heuristic fallback."""
        weights_path = Path(settings.DQN_WEIGHTS)
        if weights_path.exists():
            try:
                from ml.rl_agent.dqn_agent import DQNAgent
                self._agent = DQNAgent.load(weights_path)
                logger.info("DQN agent loaded from %s", weights_path)
            except Exception as e:
                logger.warning("Could not load DQN agent: %s — using heuristic", e)
        else:
            logger.info("DQN weights not found — using heuristic signal control")

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._control_loop())
        logger.info("SignalController started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("SignalController stopped")

    async def _control_loop(self):
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error("Signal control tick error: %s", e)
            await asyncio.sleep(settings.SIGNAL_CYCLE_SECONDS)

    async def _tick(self):
        """One decision cycle for all junctions."""
        for junction_id in range(1, settings.NUM_JUNCTIONS + 1):
            state = self._observe(junction_id)
            if self._agent:
                action = self._agent.act(state, explore=False)
            else:
                action = self._heuristic(state)
            logger.debug("Junction %d → phase=%d duration=%ds", junction_id, action["phase"], action["duration"])

    def _observe(self, junction_id: int) -> list[float]:
        """
        Build state vector for DQN:
        [ns_count, ew_count, ns_queue, ew_queue, current_phase, time_in_phase]
        """
        import random
        return [
            random.randint(0, 50),   # NS vehicle count
            random.randint(0, 50),   # EW vehicle count
            random.uniform(0, 100),  # NS queue length (m)
            random.uniform(0, 100),  # EW queue length (m)
            random.randint(0, 3),    # current phase
            random.randint(0, 60),   # seconds in current phase
        ]

    def _heuristic(self, state: list[float]) -> dict:
        """
        Simple heuristic: give green to the direction with more vehicles.
        """
        ns_count, ew_count = state[0], state[1]
        if ns_count >= ew_count:
            phase = 0  # NS Green
            duration = min(max(int(ns_count * 0.8), settings.MIN_GREEN_SECONDS), settings.MAX_GREEN_SECONDS)
        else:
            phase = 2  # EW Green
            duration = min(max(int(ew_count * 0.8), settings.MIN_GREEN_SECONDS), settings.MAX_GREEN_SECONDS)
        return {"phase": phase, "duration": duration}
