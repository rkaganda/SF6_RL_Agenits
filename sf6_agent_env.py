import gymnasium as gym
import numpy as np
from gymnasium import spaces

from game_state import SF6GameState
import game_state
import state_spaces
from typing import Dict, Any, Tuple


class SF6AgentEnv(gym.Env):
    def __init__(self, characters, action_space_mapping=None, keep_prev_action=True):
        super().__init__()
        self.keep_prev_action = keep_prev_action
        self.action_space_mapping = action_space_mapping

        if self.action_space_mapping is None:
            raise Exception("No action space mapping defined.")

        self.action_space_size = len(self.action_space_mapping)

        # 4 directions 6 buttons
        self.action_space = spaces.Discrete(self.action_space_size)

        self.features = [
            'mActionId',
            'act_st',
            'current_HP',
            'posX',
            'posY',
            'mActionFrame',
            'dir',
            'super',
            'drive',
        ]
        obs_space = {}  # create dict to store observation spaces

        for feature in self.features:  # for each feature we want to capture
            # for each player
            for player_index in [0, 1]:
                # create an action space
                obs_space[f"{player_index}_{feature}"] = game_state.create_state_space(
                    feature_mappings=state_spaces.create_feature_mapping_for_character(characters[player_index]),
                    feature=feature,
                )

        if self.keep_prev_action:
            #  add an action space for the previous action
            obs_space['prev_action'] = gym.spaces.Box(0, 1, (self.action_space_size,), dtype=np.int8)

        # create the observation space
        self.observation_space = spaces.Dict(obs_space)
        
        self.total_steps = 0
        self.action_history = []
        self.last_action = None
        self.is_success = False
        self.terminate = False

        self.last_game_env_frame = None
        self.current_game_env_frame = None

        self.game_env_state = SF6GameState(
            feature_mapping={
                0: state_spaces.create_feature_mapping_for_character(characters[0]),
                1: state_spaces.create_feature_mapping_for_character(characters[1])
            },
            game_env_player_features={0: self.features, 1: self.features}
        )
        
        # used to calculate reward 
        self.last_0_current_HP = 10000
        self.current_0_current_HP = 10000
        self.last_1_current_HP = 10000
        self.current_1_current_HP = 10000

    def _get_obs(self) -> Dict[str, np.array]:
        observation = {}
        # append last actions
        if self.keep_prev_action:
            if len(self.action_history) == 0:  # if there are no actions
                observation['prev_action'] = np.zeros(self.action_space_size, dtype=np.int8)  # create empty action
            else:
                observation['prev_action'] = self.action_history[-1]  # append last action

        current_features = self.game_env_state.get_current_game_state()
        observation.update(current_features)
        
        # used to calculate reward 
        self.current_0_current_HP = observation['0_current_HP'][0]
        self.current_1_current_HP = observation['1_current_HP'][0]
        
        return observation

    def _get_info(self) -> Dict[str, Any]:
        info = {
            "total_steps": self.total_steps,
        }
        return info

    def _get_terminated(self) -> bool:
        if self.current_0_current_HP <= 0 or self.current_1_current_HP <= 0:
            self.terminate = True

        return self.terminate

    def _calc_reward(self) -> float:
        reward = 0

        # used to calculate reward
        p_0_hp_change = self.current_0_current_HP - self.last_0_current_HP
        # if p_0_hp_change != 0:
        #     print(f"p_0_hp_change={p_0_hp_change}")
        p_1_hp_change = self.current_1_current_HP - self.last_1_current_HP
        # if p_1_hp_change != 0:
        #     print(f"p_1_hp_change={p_1_hp_change}")
        reward = reward + p_0_hp_change - p_1_hp_change
        if reward != 0:
            pass
            # print(f"reward={reward}")
            # print("--------------")
        self.last_0_current_HP = self.current_0_current_HP
        self.last_1_current_HP = self.current_1_current_HP

        reward = float(reward)

        return reward

    def step(self, action: int) -> Tuple[Dict[str, np.array], float, bool, bool, Dict[str, Any]]:
        action_mapping = self.action_space_mapping[action]

        # convert inputs into action array
        action_array = [1 if i in action_mapping else 0 for i in range(len(self.game_env_state.action_event_mapping))]

        self.game_env_state.send_actions(action_array)
        self.game_env_state.wait_for_game_env_update()

        observation = self._get_obs()
        reward = self._calc_reward()
        terminated = self._get_terminated()

        # convert action to sparse array
        sparse_action_array = [1 if i == action else 0 for i in range(self.action_space_size)]
        self.action_history.append(np.array(sparse_action_array, dtype=np.int8))
        self.last_action = action
        self.total_steps += 1

        return observation, reward, terminated, False, self._get_info()

    def reset(self, seed=None, options=None):
        self.game_env_state.send_reset()  # set reset to env
        self.game_env_state.wait_for_game_env_update()  # wait for game to update
        
        # used to calculate reward 
        self.last_0_current_HP = 10000
        self.current_0_current_HP = 10000
        self.last_1_current_HP = 10000
        self.current_1_current_HP = 10000
        self.terminate = False

        self.total_steps = 0
        self.action_history = []
        obs = self._get_obs()

        return obs, self._get_info()


gym.envs.register(
    id='SF6AgentEnv',
    entry_point='sf6_agent_env:SF6AgentEnv',
)


