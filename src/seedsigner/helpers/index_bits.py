"""BIP-39 index helpers (abandon=1 … zoo=2048)."""

BIT_WEIGHTS = (2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1)
BIT_COUNT = len(BIT_WEIGHTS)


def index_to_bits(index1: int) -> list:
    return [(index1 & weight) != 0 for weight in BIT_WEIGHTS]


def bits_to_index(bits) -> int:
    total = 0
    for on, weight in zip(bits, BIT_WEIGHTS):
        if on:
            total += weight
    return total


def format_index1(index1: int) -> str:
    return f"{index1:04d}"


def is_valid_index1(index1: int) -> bool:
    return isinstance(index1, int) and 1 <= index1 <= 2048
