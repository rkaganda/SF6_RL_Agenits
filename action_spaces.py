from itertools import product


def create_distinct_action_mapping():
    left_right_neutral = [(1,), (3,), ()]  # left right neutral
    up_down_neutral = [(0,), (2,), ()]  # up down neutral

    valid_direction_combinations = list(product(left_right_neutral, up_down_neutral))
    valid_direction_combinations = list(sum(item, ()) for item in valid_direction_combinations)

    button_ex = [(4,), (5,), (6,), (7,), (8,), (9,), (4, 5), (7, 9), ()]  # single button and ex

    valid_button_direction_comb = list(product(valid_direction_combinations, button_ex))
    valid_button_direction_comb = list(sum(item, ()) for item in valid_button_direction_comb)

    throw_and_di = [(4, 7), (6, 9)]
    drive_rush_parry = [(5, 8), (5, 8, 1), (5, 8, 3)]

    total_actions = valid_button_direction_comb + throw_and_di + drive_rush_parry

    return total_actions


def create_modern_luke_action_mapping():
    left_right_neutral = [(1,), (3,), ()]  # left right neutral
    up_down_neutral = [(0,), (2,), ()]  # up down neutral

    valid_directions = list(product(left_right_neutral, up_down_neutral))
    valid_directions = list(sum(item, ()) for item in valid_directions)

    # normal inputs (l, m, h)
    normal_inputs = [(4,), (7,), (8,)]

    # normal inputs + down (l, m, h)
    crouch_normals = [(4, 2), (7, 2), (8, 2)]

    # "command normals"
    command_normals = [
        (3, 2, 8),  # crouch heavy kick
        (3, 8),  # suppressor
        (3, 7),  # overhead
    ]

    special_commands = [
        (5,),  # medium sandblast sp
        (5, 1),  # flash knuckle b+sp
        (5, 3),  # rising uppercut f+sp
        (5, 2),  # avenger d+sp
    ]

    ex_specials = list(product(special_commands, [(9,)]))  # specials + auto
    ex_specials = list(sum(item, ()) for item in ex_specials)

    auto_combo = list(product(normal_inputs, [(9,)]))  # specials + auto
    auto_combo = list(sum(item, ()) for item in auto_combo)

    sa = [
        (5, 8, 3),  # sa1 f+h+sp
        (5, 8, 1),  # sa2 b+h+sp
        (5, 8, 2),  # sa3 d+h+sp
    ]

    throw_di = [(10,), (11,)]

    total_actions = (valid_directions + normal_inputs + crouch_normals + command_normals + special_commands +
                     ex_specials + auto_combo + sa + throw_di)

    # total_actions = throw_di + normal_inputs

    return total_actions
