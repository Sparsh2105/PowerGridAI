"""
Gymnasium-compatible RL Environment wrapper around the LangGraph Power Grid system.

Current state: step() runs the full LangGraph pipeline and returns (obs, reward, done, info).
Future state: Train a PPO/DQN policy with stable-baselines3:

    from stable_baselines3 import PPO
    env = PowerGridEnv()
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=10000)
    model.save("power_grid_ppo")
"""

import os
import sys
import numpy as np
import gymnasium as gym
from gymnasium import spaces

sys.path.append(os.path.dirname(__file__))
from graph import POWER_GRID_GRAPH, PowerGridState


class PowerGridEnv(gym.Env):
    """
    RL Environment for the Power Grid Intelligence System.

    Observation space (6 floats, all normalized 0-1):
      [avg_capacity_norm, avg_efficiency_norm, plant_health_ratio,
       degraded_lines_ratio, total_capacity_norm, demand_forecast_norm]

    Action space (Discrete 3):
      0 = conservative  → prefer maintenance, reduce risky plants
      1 = balanced      → standard operation
      2 = aggressive    → maximize output, defer non-critical maintenance

    Reward:
      +1.0 per plant with health_score > 70
      +0.5 per line with efficiency_score > 80
      -1.0 per plant with urgent maintenance status
      -0.5 per flagged transmission line
      +0.3 per well-matched decision
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, max_steps: int = 2):
        super().__init__()

        self.max_steps = max_steps
        self.current_step = 0
        self._last_info = {}

        # Observation: 6-dim normalized float vector
        self.observation_space = spaces.Box(
            low=np.zeros(6, dtype=np.float32),
            high=np.ones(6, dtype=np.float32),
            dtype=np.float32,
        )

        # Action: 0=conservative, 1=balanced, 2=aggressive
        self.action_space = spaces.Discrete(3)

        # Default starting observation
        self._current_obs = np.array(
            [0.70, 0.82, 0.75, 0.30, 0.68, 0.50], dtype=np.float32
        )

    # ------------------------------------------------------------------
    # Gym interface
    # ------------------------------------------------------------------

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self._current_obs = np.array(
            [0.70, 0.82, 0.75, 0.30, 0.68, 0.50], dtype=np.float32
        )
        self._last_info = {"step": 0, "rl_action": None}
        return self._current_obs.copy(), {}

    def step(self, action: int):
        """
        Runs one full LangGraph pipeline cycle.
        action: 0, 1, or 2
        Returns: (observation, reward, terminated, truncated, info)
        """
        assert self.action_space.contains(action), f"Invalid action: {action}"
        self.current_step += 1

        action_label = ["conservative", "balanced", "aggressive"][action]
        query = (
            f"Run full power grid analysis. RL action={action} ({action_label}). "
            f"Step {self.current_step}/{self.max_steps}. "
            "Check all plants, health, and transmission lines. Make optimal decisions."
        )

        # Dynamic Grid Perturbation: Simulate real-time sensor fluctuation before analysis
        try:
            from database.db_setup import get_connection
            import random
            conn = get_connection()
            # Fetch current values to apply clipped noise
            row = conn.execute("SELECT plant_id, vibration_index, temperature_celsius, current_capacity_percent FROM plant_health").fetchall()
            
            for r in row:
                v_new = max(0.0, min(1.0, r[1] + (random.random() - 0.5) * 0.1))
                t_new = max(40.0, min(110.0, r[2] + (random.random() - 0.5) * 5.0))
                c_new = max(10.0, min(100.0, r[3] + (random.random() - 0.5) * 8.0))
                
                conn.execute("""
                    UPDATE plant_health 
                    SET vibration_index = ?,
                        temperature_celsius = ?,
                        current_capacity_percent = ?
                    WHERE plant_id = ?
                """, (v_new, t_new, c_new, r[0]))
                
            conn.commit()
            conn.close()
        except Exception as e:
            # We fail silently to avoid crashing the whole RL stream if DB is locked
            print(f"[RANDOMIZER LOG] {e}")

        initial_state: PowerGridState = {
            "user_query": query,
            "rl_action": action,
            "current_observation": self._current_obs.tolist(),
            "demand_decisions": None,
            "health_report": None,
            "transmission_report": None,
            "unified_report": None,
            "final_decisions": None,
            "rl_reward": None,
            "next_observation": None,
            "messages": [],
        }

        try:
            result = POWER_GRID_GRAPH.invoke(initial_state)

            # Extract reward — try direct field first, then parse final_decisions JSON
            raw_reward = result.get("rl_reward")
            if raw_reward is not None:
                reward = float(raw_reward)
            else:
                # Try to parse from final_decisions JSON string
                fd = result.get("final_decisions", "")
                try:
                    import json, re
                    cleaned = re.search(r"(\{[\s\S]*\})", fd)
                    if cleaned:
                        parsed = json.loads(cleaned.group(1))
                        reward = float(parsed.get("rl_reward", 1.0))
                    else:
                        reward = 1.0
                except Exception:
                    reward = 1.0

            # Extract next observation
            next_obs_list = result.get("next_observation")
            if next_obs_list and len(next_obs_list) == 6:
                next_obs = np.array(next_obs_list, dtype=np.float32)
            else:
                # Slightly perturb current obs to show change
                noise = np.random.uniform(-0.02, 0.02, size=6).astype(np.float32)
                next_obs = np.clip(self._current_obs + noise, 0.0, 1.0)

            next_obs = np.clip(next_obs, 0.0, 1.0)
            final_decisions = result.get("final_decisions", "")

            info = {
                "step": self.current_step,
                "rl_action": action,
                "rl_action_label": action_label,
                "unified_report": result.get("unified_report", {}),
                "health_report": result.get("health_report", "{}"),
                "transmission_report": result.get("transmission_report", "{}"),
                "final_decisions": final_decisions,
            }
            print(f"[ENV] Step {self.current_step} complete — reward={reward:.3f}")

        except Exception as e:
            import traceback
            print(f"[ENV] Graph error at step {self.current_step}: {e}")
            print(traceback.format_exc())
            reward = 0.0
            noise = np.random.uniform(-0.02, 0.02, size=6).astype(np.float32)
            next_obs = np.clip(self._current_obs + noise, 0.0, 1.0)
            info = {"error": str(e), "step": self.current_step, "final_decisions": ""}

        self._current_obs = next_obs
        self._last_info = info

        terminated = False
        truncated = self.current_step >= self.max_steps

        return next_obs.copy(), reward, terminated, truncated, info

    def render(self):
        print("\n" + "=" * 60)
        print(f"  POWER GRID ENV  |  Step {self.current_step}/{self.max_steps}")
        print("=" * 60)
        obs = self._current_obs
        labels = [
            "avg_capacity      ",
            "avg_efficiency    ",
            "plant_health_ratio",
            "degraded_lines    ",
            "total_capacity    ",
            "demand_forecast   ",
        ]
        for label, val in zip(labels, obs):
            bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
            print(f"  {label}: [{bar}] {val:.3f}")
        info = self._last_info
        if info.get("rl_action") is not None:
            print(f"\n  Last action : {info['rl_action']} ({info.get('rl_action_label', '')})")
        print("=" * 60)

    def close(self):
        pass


# ---------------------------------------------------------------------------
# Future: plug in stable-baselines3
# ---------------------------------------------------------------------------
#
# from stable_baselines3 import PPO
# from stable_baselines3.common.env_checker import check_env
#
# env = PowerGridEnv(max_steps=20)
# check_env(env)  # validate the env first
#
# model = PPO("MlpPolicy", env, verbose=1, n_steps=64, batch_size=32)
# model.learn(total_timesteps=5000)
# model.save("power_grid_ppo_policy")
#
# obs, _ = env.reset()
# for _ in range(10):
#     action, _ = model.predict(obs, deterministic=True)
#     obs, reward, terminated, truncated, info = env.step(action)
#     env.render()
#     if terminated or truncated:
#         break


if __name__ == "__main__":
    env = PowerGridEnv(max_steps=3)
    obs, _ = env.reset()
    env.render()

    for step in range(3):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"\n[Step {step+1}] action={action}, reward={reward:.3f}")
        env.render()
        if terminated or truncated:
            break