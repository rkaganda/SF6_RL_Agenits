from sf6_agent_env import SF6AgentEnv
from datetime import datetime
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env.vec_frame_stack import VecFrameStack
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, CallbackList
import os
import action_spaces


paths = {
    "logs_path": 'logs',
    "runs_path": 'runs',
    "models_path": 'models'
}
for d in paths.values():
    os.makedirs(d, exist_ok=True)


def train_eval_model(frame_stack, env_num=1):
    run_name = f"luke_luke_LR5e-4_distinct"
    run_name = f"{run_name}_{datetime.now().strftime('%Y%m%d_%H%M')}"

    paths['models_path'] = f"{paths['models_path']}/{run_name}"
    paths['logs_path'] = f"{paths['logs_path']}/{run_name}"
    os.makedirs(paths['models_path'], exist_ok=True)
    os.makedirs(paths['logs_path'], exist_ok=True)

    def make_env():
        e = gym.make('SF6AgentEnv', **{
            "characters": ['luke', 'luke'],
            "action_space_mapping": action_spaces.create_distinct_action_mapping(),
            "keep_prev_action": True,
            "store_history": True
        })
        return Monitor(e)
    env = DummyVecEnv([lambda: make_env()])
    env = VecFrameStack(env, n_stack=frame_stack)
    env = VecNormalize(env)

    checkpoint_callback = CheckpointCallback(
        save_freq=20000,
        save_path=paths['logs_path'],
        name_prefix="ppo_",
    )

    eval_callback = EvalCallback(env, best_model_save_path=paths['models_path'],
                                 log_path=paths['logs_path'], eval_freq=max(20000 // env_num, 1),
                                 n_eval_episodes=5, deterministic=True,
                                 render=False)

    callback = CallbackList([checkpoint_callback, eval_callback])

    policy_kwargs = dict(net_arch=dict(pi=[32, 32], vf=[32, 32]))

    model = PPO("MultiInputPolicy", env,
                verbose=False,
                tensorboard_log=paths['runs_path'],
                device='cuda',
                learning_rate=5e-4,
                n_steps=4096,
                policy_kwargs=policy_kwargs)

    model.learn(
        total_timesteps=2000000,
        tb_log_name=f"{run_name}",
        reset_num_timesteps=False,
        callback=callback)


if __name__ == "__main__":
    train_eval_model(frame_stack=3)


