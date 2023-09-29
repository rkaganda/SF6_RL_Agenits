from stable_baselines3.common.env_checker import check_env
from torch.utils.tensorboard import SummaryWriter
from sf6_agent_env import SF6AgentEnv
import action_spaces
from datetime import datetime
import numpy as np

characters = ['luke', 'luke']

env = SF6AgentEnv(
    characters=characters,
    action_space_mapping=action_spaces.create_distinct_action_mapping()
)

check_env(env)
env.reset()


run_name = f"{characters[0]}_{characters[1]}_random"
run_name = f"{run_name}_{datetime.now().strftime('%Y%m%d_%H%M')}"
stats_writer = SummaryWriter(f"runs/{run_name}")
step_total = 400000
total_reward = 0
eps_count = 1
eps_size = 20000
ep_window = 100
ep_rewards = []

for step_num in range(1, step_total):
    action = env.action_space.sample()
    observation, reward, terminated, _, _ = env.step(action)
    total_reward = total_reward + reward
    if step_num % eps_size == 0:
        print(f"logged {eps_count}/{step_num}")
        stats_writer.add_scalar('eval/mean_reward', np.mean(ep_rewards[:ep_window]), step_num)
        stats_writer.add_scalar('eval/mean_ep_length', step_num / eps_count, step_num)
    if terminated:
        print(f"TERM {eps_count}/{step_num}")
        eps_count = eps_count + 1
        ep_rewards.append(total_reward)
        total_reward = 0
        _, _ = env.reset()

