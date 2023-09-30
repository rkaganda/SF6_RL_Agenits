from stable_baselines3.common.env_checker import check_env
from sf6_agent_env import SF6AgentEnv
import action_spaces

env = SF6AgentEnv(
    characters=['luke', 'luke'],
    action_space_mapping=action_spaces.create_distinct_action_mapping(),
    store_history=True
)

check_env(env)
env.reset()


while True:
    for n in range(0, env.action_space_size):
        for r in range(0, 80):
            env.step(n)




