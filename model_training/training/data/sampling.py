import random


def deterministic_shuffle(records, seed: int):
    result = list(records); random.Random(seed).shuffle(result); return result

