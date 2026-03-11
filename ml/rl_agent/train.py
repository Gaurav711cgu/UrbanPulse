"""
rl_agent/train.py
─────────────────
Train the DQN agent on the SUMO traffic environment.

Usage:
    python -m ml.rl_agent.train --episodes 500 --save ml/weights/dqn_agent.pt
"""

import argparse
import random
import numpy as np
from collections import deque
from pathlib import Path

from ml.rl_agent.dqn_agent import DQNAgent
from ml.rl_agent.traffic_env import TrafficSignalEnv


def train(
    episodes: int = 500,
    max_steps: int = 3600,
    save_path: str = "ml/weights/dqn_agent.pt",
    eval_every: int = 50,
    sumo_cfg: str = "simulation/sumo_configs/single_junction.sumocfg",
    seed: int = 42,
):
    random.seed(seed)
    np.random.seed(seed)

    env = TrafficSignalEnv(sumo_cfg=sumo_cfg, max_steps=max_steps, seed=seed)
    agent = DQNAgent(
        state_size=env.observation_space.shape[0],
        action_size=env.action_space.n,
        lr=1e-3,
        gamma=0.95,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay=0.997,
        batch_size=64,
        target_update_freq=100,
    )

    reward_history = deque(maxlen=50)
    best_avg_reward = float("-inf")

    print(f"Training DQN | {episodes} episodes | {max_steps} steps/ep\n")
    print(f"{'Episode':>8} {'Reward':>10} {'Avg50':>10} {'Epsilon':>8} {'Loss':>8}")
    print("-" * 55)

    for ep in range(1, episodes + 1):
        obs, _ = env.reset()
        total_reward = 0.0
        total_loss = 0.0
        loss_count = 0

        for _ in range(max_steps):
            action = agent.act(obs.tolist(), explore=True)
            next_obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated

            agent.remember(obs.tolist(), action, reward, next_obs.tolist(), done)
            loss = agent.learn()
            if loss is not None:
                total_loss += loss
                loss_count += 1

            obs = next_obs
            total_reward += reward
            if done:
                break

        reward_history.append(total_reward)
        avg_reward = sum(reward_history) / len(reward_history)
        avg_loss = total_loss / max(loss_count, 1)

        if ep % 10 == 0 or ep == 1:
            print(f"{ep:>8} {total_reward:>10.1f} {avg_reward:>10.1f} {agent.epsilon:>8.3f} {avg_loss:>8.4f}")

        # Save best model
        if avg_reward > best_avg_reward and len(reward_history) >= 10:
            best_avg_reward = avg_reward
            agent.save(save_path)

        # Full evaluation run
        if ep % eval_every == 0:
            eval_reward = _evaluate(agent, env, n=3)
            print(f"\n  [Eval ep={ep}] avg_reward={eval_reward:.1f}  best_so_far={best_avg_reward:.1f}\n")

    env.close()
    print(f"\nTraining complete. Best avg reward: {best_avg_reward:.1f}")
    print(f"Weights saved to: {save_path}")


def _evaluate(agent: DQNAgent, env: TrafficSignalEnv, n: int = 3) -> float:
    total = 0.0
    for _ in range(n):
        obs, _ = env.reset()
        ep_reward = 0.0
        done = False
        while not done:
            action = agent.act(obs.tolist(), explore=False)
            obs, reward, terminated, truncated, _ = env.step(action)
            ep_reward += reward
            done = terminated or truncated
        total += ep_reward
    return total / n


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--steps", type=int, default=3600)
    parser.add_argument("--save", type=str, default="ml/weights/dqn_agent.pt")
    parser.add_argument("--eval-every", type=int, default=50)
    parser.add_argument("--cfg", type=str, default="simulation/sumo_configs/single_junction.sumocfg")
    args = parser.parse_args()

    train(
        episodes=args.episodes,
        max_steps=args.steps,
        save_path=args.save,
        eval_every=args.eval_every,
        sumo_cfg=args.cfg,
    )
