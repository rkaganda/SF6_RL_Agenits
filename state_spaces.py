import numpy as np
import json

with open("data/act_st.json") as f:
    act_st_file = json.load(f)
    act_st = {key: index for index, key in enumerate(act_st_file)}


def create_action_id_for_characters(character_name: str):
    with open(f"data/{character_name}.json") as file:
        action_ids = json.load(file)
        action_id_mapping = {str(int(key)): index for index, key in enumerate(action_ids)}

    return action_id_mapping


def create_feature_mapping_for_character(character_name: str):
    feature_mappings = {
        'act_st': (act_st, np.int32),
        'dir': ({
            '0': 0,
            '1': 1,
        }, np.int32),
        'current_HP': ([0, 10000], np.int32),
        'posY': ([0, 3], np.float32),
        'posX': ([-7.65, 1.38], np.float32),
        'super': ([0, 30000], np.int32),
        'drive': ([0, 60000], np.int32),
        'mActionId': (create_action_id_for_characters(character_name), np.int32),
        'mActionFrame': ([0, 335], np.int32)
    }

    return feature_mappings

