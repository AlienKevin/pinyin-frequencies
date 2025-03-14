import json
from enum import Enum, IntEnum
from dataclasses import dataclass
import random
from itertools import product
from typing import Optional
from final_groups import only_jqx_final, no_jqx_group, only_gkh_group, no_gkh_group

# first: 0 = left hand, 1 = right hand
# second: 1 = index finger, 2 = index finger, 3 = middle finger, 4 = ring finger, 5 = little finger
# third: 0 = upper row, 1 = home row, 2 = bottom row
Location = tuple[int, int, int]

Key = str

# Fixed keyboard layout inherited from QWERTY

qwerty_layout: dict[Key, Location] = {
    # 0-Upper Row
    "q": (0, 0, 5),
    "w": (0, 0, 4),
    "e": (0, 0, 3),
    "r": (0, 0, 2),
    "t": (0, 0, 1),
    "y": (1, 0, 1),
    "u": (1, 0, 2),
    "i": (1, 0, 3),
    "o": (1, 0, 4),
    "p": (1, 0, 5),
    # 1-Home Row
    "a": (0, 1, 5),
    "s": (0, 1, 4),
    "d": (0, 1, 3),
    "f": (0, 1, 2),
    "g": (0, 1, 1),
    "h": (1, 1, 1),
    "j": (1, 1, 2),
    "k": (1, 1, 3),
    "l": (1, 1, 4),
    # 2-Bottom Row
    "z": (0, 2, 5),
    "x": (0, 2, 4),
    "c": (0, 2, 3),
    "v": (0, 2, 2),
    "b": (0, 2, 1),
    "n": (1, 2, 1),
    "m": (1, 2, 2),
}

ideal_workload_distribution: dict[tuple[int, int, int], float] = {
    # 0-Upper Row
    (0, 0, 5): 1.168,
    (0, 0, 4): 3.170,
    (0, 0, 3): 4.060,
    (0, 0, 2): 2.724,
    (0, 0, 1): 1.835,
    (1, 0, 1): 1.835,
    (1, 0, 2): 2.724,
    (1, 0, 3): 4.060,
    (1, 0, 4): 3.170,
    (1, 0, 5): 1.168,
    # 1-Home Row
    (0, 1, 5): 2.854,
    (0, 1, 4): 7.747,
    (0, 1, 3): 9.922,
    (0, 1, 2): 6.657,
    (0, 1, 1): 4.486,
    (1, 1, 1): 4.486,
    (1, 1, 2): 6.657,
    (1, 1, 3): 9.922,
    (1, 1, 4): 7.747,
    # 2-Bottom Row
    (0, 2, 5): 0.907,
    (0, 2, 4): 2.463,
    (0, 2, 3): 3.155,
    (0, 2, 2): 2.117,
    (0, 2, 1): 1.427,
    (1, 2, 1): 1.427,
    (1, 2, 2): 2.117,
}

single_freqs: dict[str, float] = json.load(
    open("../results/zhihu/frequencies/single_freqs.json", "r")
)
pair_freqs: dict[tuple[str, str], float] = {
    tuple(k.split("+")): v
    for k, v in json.load(
        open("../results/zhihu/frequencies/pair_freqs.json", "r")
    ).items()
}


class Choice(Enum):
    LEFT = True
    RIGHT = False


def is_zero_consonant_final(final: str) -> bool:
    return final.endswith("F")


def strip_zero_consonant_final_tag(final: str) -> str:
    return final[:-1]


def add_zero_consonant_final_tag(final: str) -> str:
    return final + "F"


class Finger(IntEnum):
    INDEX = 0
    MIDDLE = 1
    RING = 2
    LITTLE = 3


def get_finger(key: Key) -> Finger:
    i = qwerty_layout[key][1]
    if i == 1 or i == 2:
        return Finger.INDEX
    elif i == 3:
        return Finger.MIDDLE
    elif i == 4:
        return Finger.RING
    else:
        return Finger.LITTLE


def is_same_finger(i: Key, j: Key) -> bool:
    return get_finger(i) == get_finger(j)


def is_same_hand(i: Key, j: Key) -> bool:
    return qwerty_layout[i][0] == qwerty_layout[j][0]


# Manhattan distance between letter i and letter j
# distance(i, j) = |col(loc(i)) − col(loc(j))| + |row(loc(i)) − row(loc(j))|
def distance(i: Key, j: Key) -> int:
    return abs(qwerty_layout[i][2] - qwerty_layout[j][2]) + abs(
        qwerty_layout[i][1] - qwerty_layout[j][1]
    )


# Preferred hit direction is from little finger to index finger
def is_preferred_hit_direction(i: Key, j: Key) -> bool:
    return get_finger(i) >= get_finger(j)


penalty_coefficient_for_big_steps: dict[tuple[Finger, Finger], int] = {
    # first finger is index
    (Finger.INDEX, Finger.INDEX): 0,
    (Finger.INDEX, Finger.MIDDLE): 5,
    (Finger.INDEX, Finger.RING): 8,
    (Finger.INDEX, Finger.LITTLE): 6,
    # second finger is middle
    (Finger.MIDDLE, Finger.INDEX): 5,
    (Finger.MIDDLE, Finger.MIDDLE): 0,
    (Finger.MIDDLE, Finger.RING): 9,
    (Finger.MIDDLE, Finger.LITTLE): 7,
    # third finger is ring
    (Finger.RING, Finger.INDEX): 8,
    (Finger.RING, Finger.MIDDLE): 9,
    (Finger.RING, Finger.RING): 0,
    (Finger.RING, Finger.LITTLE): 10,
    # fourth finger is little
    (Finger.LITTLE, Finger.INDEX): 6,
    (Finger.LITTLE, Finger.MIDDLE): 7,
    (Finger.LITTLE, Finger.RING): 10,
    (Finger.LITTLE, Finger.LITTLE): 0,
}


def get_big_step_penalty(i: Key, j: Key) -> int:
    return penalty_coefficient_for_big_steps[(get_finger(i), get_finger(j))]


@dataclass
class ShuangpinConfig:
    # Maps standard finals to keys
    final_layout: dict[str, str]
    # digraph initials' keys must be unique among all digraph initials
    # but they can share the keys with finals
    digraph_initial_layout: dict[str, str]
    zero_consonant_final_layout: dict[str, tuple[str, str]]
    # Map variant finals to standard finals
    # REQUIRES: the standard final values must be unique
    variant_to_standard_finals: dict[str, str]
    # Map initials to a set of finals they can be assigned to
    initial_constraints: Optional[dict[str, set[str]]] = None


@dataclass
class Scores:
    tapping_workload_distribution: float
    hand_alternation: float
    finger_alternation: float
    avoidance_of_big_steps: float
    hit_direction: float

    def __add__(self, other):
        return Scores(
            tapping_workload_distribution=self.tapping_workload_distribution
            + other.tapping_workload_distribution,
            hand_alternation=self.hand_alternation + other.hand_alternation,
            finger_alternation=self.finger_alternation + other.finger_alternation,
            avoidance_of_big_steps=self.avoidance_of_big_steps
            + other.avoidance_of_big_steps,
            hit_direction=self.hit_direction + other.hit_direction,
        )

    def __truediv__(self, other):
        return Scores(
            tapping_workload_distribution=self.tapping_workload_distribution / other,
            hand_alternation=self.hand_alternation / other,
            finger_alternation=self.finger_alternation / other,
            avoidance_of_big_steps=self.avoidance_of_big_steps / other,
            hit_direction=self.hit_direction / other,
        )


# Follows xiaohe and ziranma
default_variant_to_standard_finals: dict[str, str] = {
    "ve": "ue",
    "o": "uo",
    "iong": "ong",
    "ing": "uai",
    "iang": "uang",
    "ia": "ua",
    "v": "ui",
}

# constraints need to be ordered by length
# initials with the smallest number of constraints go first
default_initial_constraints = {
    # n + g is illegal
    "g": {"ia", "ua", "iong", "uai", "ui", "uang"},
    # z/c/s + h is illegal
    "h": {
        "ia",
        "ua",
        "ie",
        "iao",
        "iu",
        "ian",
        "in",
        "iang",
        "uang",
        "uai",
        "ing",
        "ue",
        "ve",
        "iong",
    },
}

fixed_variant_to_standard_finals: dict[str, str] = {
    "ve": "ue",
    "o": "uo",
    "v": "ui",
}


digraph_initials: list[str] = ["zh", "ch", "sh"]


def is_digraph_initial(initial: str) -> bool:
    return initial in digraph_initials


fixed_finals: list[str] = ["a", "e", "i", "o", "u", "v"]
fixed_finals_to_keys: dict[str, Key] = {
    "a": "a",
    "e": "e",
    "i": "i",
    "o": "o",
    "u": "u",
    "v": "v",
}

# Can take on other finals
# e.g. "o" can take on "uo" and "o"
# e.g. "v" can take on "ui" and "v"
productive_fixed_final_keys: set[Key] = {"o", "v"}

flexible_finals: list[str] = [
    "iu",
    "ei",
    "uan",
    "ue",
    "un",
    "uo",
    "ie",
    "ong",
    "ai",
    "en",
    "eng",
    "ang",
    "an",
    "uai",
    "uang",
    "ou",
    "ua",
    "ao",
    "ui",
    "in",
    "iao",
    "ian",
    "ve",
    "iong",
    "ing",
    "iang",
    "ia",
]

finals: list[str] = flexible_finals + fixed_finals


def get_random_final_layout(
    variant_to_standard_finals: dict[str, str],
    initial_constraints: Optional[dict[str, set[str]]] = None,
) -> Optional[dict[str, str]]:
    random_layout: dict[str, str] = dict()
    fixed_keys = set(fixed_finals_to_keys.values())
    flexible_final_keys: set[Key] = set(qwerty_layout.keys()) - fixed_keys
    standard_to_variant_finals = {v: k for k, v in variant_to_standard_finals.items()}
    standard_finals = [
        final for final in finals if final not in variant_to_standard_finals.keys()
    ]
    flexible_standard_finals = standard_finals.copy()
    if initial_constraints is not None:
        used_standard_finals: set[str] = set()
        for initial, acceptable_finals in initial_constraints.items():
            acceptable_standard_finals = set(
                map(
                    lambda final: variant_to_standard_finals.get(final, final),
                    filter(
                        lambda final: variant_to_standard_finals[final]
                        in acceptable_finals
                        if final in variant_to_standard_finals
                        else (
                            standard_to_variant_finals[final] in acceptable_finals
                            if final in standard_to_variant_finals
                            else True
                        ),
                        acceptable_finals,
                    ),
                )
            )
            # print("acceptable_standard_finals:", acceptable_standard_finals)
            possible_standard_finals = acceptable_standard_finals - used_standard_finals
            # The variant_to_standard_finals is incompatible with the initial_constraints
            if len(possible_standard_finals) == 0:
                return None
            standard_final = random.choice(list(possible_standard_finals))
            # assumes that the initials are not digraph initials
            # so they map directly to the same keys
            random_layout[standard_final] = initial
            used_standard_finals.add(standard_final)
            flexible_standard_finals.remove(standard_final)
            flexible_final_keys.remove(initial)
            # print("standard_final:", standard_final)
            # print("initial:", initial)
    # print(len(flexible_standard_finals))
    # print(flexible_standard_finals)
    # print(len(flexible_final_keys))
    # print(flexible_final_keys)
    # print(standard_to_variant_finals)
    for standard_final in flexible_standard_finals:
        if standard_final in fixed_finals:
            # print("fixed_final:", fixed_finals)
            random_layout[standard_final] = fixed_finals_to_keys[standard_final]
        elif standard_to_variant_finals.get(standard_final) in fixed_finals:
            variant_final = standard_to_variant_finals[standard_final]
            # print("variant_final:", variant_final)
            random_layout[standard_final] = fixed_finals_to_keys[variant_final]
        else:
            # print("standard_final:", standard_final)
            random_layout[standard_final] = random.choice(list(flexible_final_keys))
            flexible_final_keys.remove(random_layout[standard_final])
    # Sort the layout by standard final keys so that the final layout in chromosomes are consistent
    return dict(
        sorted(
            random_layout.items(),
            key=lambda item: standard_finals.index(item[0]),
        )
    )


# print(
#     get_random_final_layout(
#         default_variant_to_standard_finals,
#         default_initial_constraints,
#     )
# )


def get_random_digraph_initial_layout() -> dict[str, str]:
    random_layout = dict()
    flexible_digraph_initial_keys = {"a", "e", "i", "o", "u", "v"}
    for initial in digraph_initials:
        random_layout[initial] = random.choice(list(flexible_digraph_initial_keys))
        flexible_digraph_initial_keys.remove(random_layout[initial])
    return random_layout


# print(get_random_digraph_initial_layout())

fixed_zero_consonant_finals: list[str] = [
    "ai",
    "ei",
    "ou",
    "an",
    "en",
    "ao",
    "er",
]


def get_fixed_final_key_pair(final: str) -> tuple[Key, Key]:
    return (final[0], final[1])


fixed_key_pairs = set(
    get_fixed_final_key_pair(final) for final in fixed_zero_consonant_finals
)

flexible_zero_consonant_finals = ["a", "e", "o", "ang", "eng"]
flexible_first_keys = ["a", "e", "o"]

zero_consonant_finals = flexible_zero_consonant_finals + fixed_zero_consonant_finals


def get_random_zero_consonant_final_layout() -> dict[str, tuple[str, str]]:
    random_layout = dict()
    flexible_key_pairs_dict: dict[str, set[tuple[str, str]]] = {
        k: (set(product({k}, qwerty_layout.keys())) - fixed_key_pairs)
        for k in flexible_first_keys
    }

    for final in zero_consonant_finals:
        if final in flexible_zero_consonant_finals:
            # first key is restricted to the first letter of the final
            first_key = final[0]
            random_layout[final] = random.choice(
                list(flexible_key_pairs_dict[first_key])
            )
            flexible_key_pairs_dict[first_key].remove(random_layout[final])
        else:
            random_layout[final] = get_fixed_final_key_pair(final)
    return random_layout


# print(get_random_zero_consonant_final_layout())


def get_random_variant_to_standard_finals() -> dict[str, str]:
    mapping = fixed_variant_to_standard_finals.copy()
    mapping[only_jqx_final] = random.choice(list(no_jqx_group))
    no_gkh_finals = list(no_gkh_group)
    for only_gkh_final in only_gkh_group:
        no_gkh_final = random.choice(no_gkh_finals)
        mapping[only_gkh_final] = no_gkh_final
        no_gkh_finals.remove(no_gkh_final)
    return mapping


# print(get_random_variant_to_standard_finals())


def get_random_config(
    initial_constraints: Optional[dict[str, set[str]]] = None
) -> ShuangpinConfig:
    variant_to_standard_finals = get_random_variant_to_standard_finals()
    final_layout = get_random_final_layout(
        variant_to_standard_finals, initial_constraints
    )
    if final_layout is None:
        return get_random_config(initial_constraints)
    else:
        return ShuangpinConfig(
            final_layout=final_layout,
            digraph_initial_layout=get_random_digraph_initial_layout(),
            zero_consonant_final_layout=get_random_zero_consonant_final_layout(),
            variant_to_standard_finals=variant_to_standard_finals,
        )


def get_score(
    config: ShuangpinConfig,
) -> float:
    scores = get_scores(config)
    # Generated using get_average_scores(4000)
    average_scores = Scores(
        tapping_workload_distribution=0.025301075426633263,
        hand_alternation=0.5841655834657751,
        finger_alternation=0.5459557691028307,
        avoidance_of_big_steps=1.6827515700073905,
        hit_direction=0.12495240024105278,
    )
    return (
        scores.tapping_workload_distribution
        / average_scores.tapping_workload_distribution
        * 0.45
        + scores.hand_alternation / average_scores.hand_alternation * 1.0
        + scores.finger_alternation / average_scores.finger_alternation * 0.8
        + scores.avoidance_of_big_steps / average_scores.avoidance_of_big_steps * 0.7
        + scores.hit_direction / average_scores.hit_direction * 0.6
    )


def get_scores(
    config: ShuangpinConfig,
) -> Scores:
    def get_standard_final(final: str) -> str:
        return config.variant_to_standard_finals.get(final, final)

    def get_key(i: str, zero_consonant_choice: Choice) -> str:
        if is_zero_consonant_final(i):
            final = strip_zero_consonant_final_tag(i)
            return config.zero_consonant_final_layout[final][
                0 if zero_consonant_choice == Choice.LEFT else 1
            ]
        elif is_digraph_initial(i):
            return config.digraph_initial_layout[i]
        else:
            standard_final = get_standard_final(i)
            return config.final_layout.get(standard_final, standard_final)

    standard_single_freqs: dict[str, float] = single_freqs.copy()
    standard_pair_freqs: dict[tuple[str, str], float] = pair_freqs.copy()

    for variant, standard in config.variant_to_standard_finals.items():
        standard_single_freqs[standard] += standard_single_freqs[variant]
        standard_single_freqs.pop(variant)

    for pair in standard_pair_freqs.copy():
        standard_pair = (
            get_standard_final(pair[0]),
            get_standard_final(pair[1]),
        )
        if pair != standard_pair:
            variant_freq = standard_pair_freqs.pop(pair)
            standard_pair_freqs[standard_pair] = (
                standard_pair_freqs.get(standard_pair, 0) + variant_freq
            )

    def tapping_workload_distribution() -> float:
        key_freqs: dict[Key, float] = dict()
        for i, freq in standard_single_freqs.items():
            if is_zero_consonant_final(i):
                final = strip_zero_consonant_final_tag(i)
                (first_key, second_key) = config.zero_consonant_final_layout[final]
                key_freqs[first_key] = key_freqs.get(first_key, 0) + freq
                key_freqs[second_key] = key_freqs.get(second_key, 0) + freq
            else:
                # The zero consonant choice doesn't matter because we handled it above
                key = get_key(i, Choice.LEFT)
                key_freqs[key] = key_freqs.get(key, 0) + freq
        I1 = 0.0
        for key, freq in key_freqs.items():
            key_location = qwerty_layout[key]
            I1 += ((freq - ideal_workload_distribution[key_location]) / 100) ** 2
        return I1

    def hand_alternation() -> float:
        I2 = 0.0
        for (i, j) in standard_pair_freqs:
            i_key = get_key(i, Choice.RIGHT)
            j_key = get_key(j, Choice.LEFT)
            if is_same_hand(i_key, j_key):
                # Gives penalty if the two keys are on the same hand
                I2 += standard_pair_freqs[(i, j)]
        # add zero-consonant hand alternations
        for final, key_pair in config.zero_consonant_final_layout.items():
            if is_same_hand(key_pair[0], key_pair[1]):
                I2 += standard_single_freqs.get(add_zero_consonant_final_tag(final), 0)
        return I2 / 100

    def finger_alternation() -> float:
        I3 = 0.0
        for (i, j) in standard_pair_freqs:
            i_key = get_key(i, Choice.RIGHT)
            j_key = get_key(j, Choice.LEFT)
            if is_same_hand(i_key, j_key) and is_same_finger(i_key, j_key):
                # Gives penalty if the pair is on the same hand and the same finger
                I3 += standard_pair_freqs[(i, j)] * distance(i_key, j_key)
        # add zero-consonant finger alternations
        for final, key_pair in config.zero_consonant_final_layout.items():
            if is_same_hand(key_pair[0], key_pair[1]) and is_same_finger(
                key_pair[0], key_pair[1]
            ):
                I3 += standard_single_freqs.get(
                    add_zero_consonant_final_tag(final), 0
                ) * distance(key_pair[0], key_pair[1])
        return I3 / 100

    def avoidance_of_big_steps() -> float:
        I4 = 0.0
        for (i, j) in standard_pair_freqs:
            i_key = get_key(i, Choice.RIGHT)
            j_key = get_key(j, Choice.LEFT)
            if is_same_hand(i_key, j_key):
                # Gives penalty if the pair is on the same hand
                I4 += standard_pair_freqs[(i, j)] * get_big_step_penalty(i_key, j_key)
        # add zero-consonant finger alternations
        for final, key_pair in config.zero_consonant_final_layout.items():
            if is_same_hand(key_pair[0], key_pair[1]):
                I4 += standard_single_freqs.get(
                    add_zero_consonant_final_tag(final), 0
                ) * get_big_step_penalty(key_pair[0], key_pair[1])
        return I4 / 100

    def hit_direction() -> float:
        I5 = 0.0
        for (i, j) in standard_pair_freqs:
            i_key = get_key(i, Choice.RIGHT)
            j_key = get_key(j, Choice.LEFT)
            if is_same_hand(i_key, j_key) and not is_preferred_hit_direction(
                i_key, j_key
            ):
                # Gives penalty if the pair is on the same hand and not in preferred hit direction
                I5 += standard_pair_freqs[(i, j)]
        # add zero-consonant finger alternations
        for final, key_pair in config.zero_consonant_final_layout.items():
            if is_same_hand(
                key_pair[0], key_pair[1]
            ) and not is_preferred_hit_direction(key_pair[0], key_pair[1]):
                I5 += standard_single_freqs.get(add_zero_consonant_final_tag(final), 0)
        return I5 / 100

    return Scores(
        tapping_workload_distribution=tapping_workload_distribution(),
        hand_alternation=hand_alternation(),
        finger_alternation=finger_alternation(),
        avoidance_of_big_steps=avoidance_of_big_steps(),
        hit_direction=hit_direction(),
    )


def get_average_scores(num_of_random_scores: int) -> Scores:
    total_scores = Scores(0, 0, 0, 0, 0)
    for _ in range(num_of_random_scores):
        config = get_random_config()
        total_scores += get_scores(config)
    return total_scores / num_of_random_scores


# print(get_average_scores(4000))
