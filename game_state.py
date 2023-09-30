import json
from datetime import datetime
import gymnasium as gym
from typing import Dict, List
import numpy as np
import warnings
import os

env_path = "C:/SteamLibrary/steamapps/common/Street Fighter 6/reframework/data/env/"

action_event_buffer_path = f"{env_path}actions_buffer.buf"
game_env_buffer_path = f"{env_path}game_env_buffer.buf"
game_env_format_path = f"{env_path}game_env.format"
action_key_mapping_path = f"{env_path}action_key_mapping.json"


def create_state_space(feature_mappings: dict, feature: str) -> gym.spaces:
    if feature in feature_mappings:
        feature_map, dtype = feature_mappings[feature]
        if type(feature_map) == dict:
            # hot one encoding so use box space
            return gym.spaces.Box(low=0, high=1, shape=(len(feature_map),), dtype=dtype)
        elif type(feature_map) == list:
            # continuous space
            return gym.spaces.Box(low=feature_map[0], high=feature_map[1], shape=(1,), dtype=dtype)
        else:
            raise TypeError(f"No space {feature} for this type {type(feature_map)}.")
    else:
        raise KeyError(f"{feature} not found in feature mapping.")


class SF6GameState:
    def __init__(self, game_env_player_features, feature_mapping):
        self.last_game_env_frame = None  # last env frame read
        self.current_game_env_frame = None  # the current frame being read 
        self.current_game_state = None  # the current game state

        self.game_env_buffer = open(game_env_buffer_path, 'r')
        self.action_event_buffer = open(action_event_buffer_path, 'r+')

        with open(game_env_format_path, 'r') as f:
            self.game_env_format = f.readline().strip().split(",")

        with open(action_key_mapping_path, 'r') as f:
            self.action_event_mapping = json.load(f)

        self.feature_mapping = feature_mapping

        self.game_env_player_features = game_env_player_features
        for player_id in [0, 1]:
            for name in self.game_env_player_features[player_id]:
                if name not in self.game_env_format:
                    raise KeyError(f"No feature named {name}.")

        self.wait_for_game_env_update()  # read the game state

    def wait_for_game_env_update(self):
        last_timestamp = 0

        while True:
            current_timestamp = os.path.getmtime(game_env_buffer_path)
            if current_timestamp != last_timestamp:
                self.game_env_buffer.seek(0)
                current_content = self.game_env_buffer.readline().strip().split(",")
                self.current_game_env_frame = current_content[0]
                if self.current_game_env_frame != self.last_game_env_frame:
                    expected_length = (len(self.game_env_format) * 2) + 1
                    if len(current_content) == expected_length:
                        self.current_game_state = current_content
                        return  # Exit after processing the new game state
                    else:
                        warnings.warn(
                            f"Invalid game state length expected={expected_length} actual={len(current_content)}")

    def get_player_features(self, player_idx: int) -> List[str]:
        # calculate slice indices for this player's features
        start_idx = 1 if player_idx == 0 else 1 + len(self.game_env_format)
        end_idx = start_idx + len(self.game_env_format)

        # extract features for the current player
        player_features = self.current_game_state[start_idx:end_idx]

        return player_features

    def in_stun(self) -> Dict[int, bool]:
        is_stunned = {}
        for player_idx in [0, 1]:
            try:
                player_features = self.get_player_features(player_idx)
                player_hitstun = int(player_features[self.game_env_format.index('hitstun')])
                player_blockstun = int(player_features[self.game_env_format.index('blockstun')])
            except IndexError:
                print("bad in stun")
                player_hitstun = 0
                player_blockstun = 0

            if player_hitstun > 0 or player_blockstun > 0:
                is_stunned[player_idx] = True
            else:
                is_stunned[player_idx] = False
        return is_stunned

    def get_hitstop(self) -> Dict[int, int]:
        player_hitstop = {}
        for player_idx in [0, 1]:
            player_features = self.get_player_features(player_idx)
            try:
                player_hitstop[player_idx] = int(player_features[self.game_env_format.index('hitstop')])
            except IndexError:
                print("bad hitstop")
                player_hitstop[player_idx] = 0

        return player_hitstop

    def get_current_game_state(self) -> Dict[str, np.array]:
        player_features = {}

        for player_id in [0, 1]:
            # if the player's features should be captured
            if player_id in self.game_env_player_features:
                player_vals = self.get_player_features(player_id)

                # iterate through the list of features to be captured for this player
                for feature_name in self.game_env_player_features[player_id]:
                    # find index of this feature
                    feature_index = self.game_env_format.index(feature_name)

                    # get the feature value
                    feature_value = player_vals[feature_index]

                    # encode the feature
                    encoded_feature = self.encode_feature(
                        p_idx=player_id,
                        feature=feature_name,
                        value=feature_value)

                    player_features[f"{player_id}_{feature_name}"] = encoded_feature

        return player_features

    def send_actions(self, actions: list):
        action_status = [str(self.current_game_env_frame)] + list(actions) + [0]

        self.write_action_status(action_status)

    def send_reset(self):
        state_features = self.current_game_state[1:]
        p_0_health = int(state_features[self.game_env_format.index('current_HP')])
        p_1_health = int(state_features[self.game_env_format.index('current_HP')+len(self.game_env_format)])
        old_0_health = p_0_health
        old_1_health = p_1_health
        action_array_size = len(self.action_event_mapping)

        while True:
            action_status = [str(self.current_game_env_frame)] + ([0]*(action_array_size-1)) + [1]
            self.write_action_status(action_status)
            self.wait_for_game_env_update()

            action_status = [str(self.current_game_env_frame)] + ([0]*(action_array_size-1)) + [1]
            self.write_action_status(action_status)
            self.wait_for_game_env_update()

            action_status = [str(self.current_game_env_frame)] + ([0]*(action_array_size-1)) + [0]
            self.write_action_status(action_status)
            self.wait_for_game_env_update()

            action_status = [str(self.current_game_env_frame)] + ([0]*(action_array_size-1)) + [0]
            self.write_action_status(action_status)
            self.wait_for_game_env_update()

            if p_0_health > old_0_health or p_1_health > old_1_health or p_0_health >= 10000 and p_1_health >= 10000:
                break

            state_features = self.current_game_state[1:]
            p_0_health = int(state_features[self.game_env_format.index('current_HP')])
            p_1_health = int(state_features[self.game_env_format.index('current_HP') + len(self.game_env_format)])

    def write_action_status(self, action_status: list):
        action_status = ','.join(map(str, action_status))
        self.action_event_buffer.seek(0)  # start of file
        self.action_event_buffer.write(action_status)
        self.action_event_buffer.truncate()  # remove old data
        self.action_event_buffer.flush()  # flush
        self.last_game_env_frame = self.current_game_env_frame

    def encode_feature(self, p_idx: int, feature: str, value: str) -> np.array:
        if feature in self.feature_mapping[p_idx]:
            feature_map, dtype = self.feature_mapping[p_idx][feature]
            if type(feature_map) == dict:
                # create a numpy array to one hot encode feature
                arr = np.zeros(len(feature_map), dtype=dtype)

                # if the feature is in map
                if value in feature_map:
                    encoding_index = feature_map[value]
                    # encode the feature
                    arr[encoding_index] = 1
                else:
                    warnings.warn(f"Invalid mapping value:{value} for feature:{feature}.")

                return arr
            elif type(feature_map) == list:
                try:
                    # continuous space
                    return np.array([value], dtype=dtype).clip(feature_map[0], feature_map[1])
                except ValueError as v:
                    print(f"feature={feature} value={value}")
                    return np.array([0], dtype=dtype).clip(feature_map[0], feature_map[1])
            else:
                raise TypeError(f"No encoding {feature} for this type {type(feature_map)}.")
        else:
            raise KeyError(f"{feature} not found in feature mapping.")






