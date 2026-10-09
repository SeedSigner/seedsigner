"""BIP-39 numbers helpers (abandon=1 … zoo=2048)."""

BIT_WEIGHTS = (2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1)
BIT_COUNT = len(BIT_WEIGHTS)


def number_to_bits(number: int) -> list:
    return [(number & weight) != 0 for weight in BIT_WEIGHTS]


def bits_to_number(bits) -> int:
    total = 0
    for on, weight in zip(bits, BIT_WEIGHTS):
        if on:
            total += weight
    return total


def format_number(number: int) -> str:
    return f"{number:04d}"


def is_valid_number(number: int) -> bool:
    return isinstance(number, int) and 1 <= number <= 2048
