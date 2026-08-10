import hashlib
import hmac


PROTOCOL_NAME = "SeedSigner Hybrid Entropy v1"

CAMERA_DOMAIN = b"SeedSigner Hybrid Camera RGB v1\x00"
CAMERA_COMMITMENT_DOMAIN = b"SeedSigner Hybrid Camera Commitment v1\x00"

DICE_ROLLS = 100
OUTPUT_BITS = 256
OUTPUT_SIZE = 1 << OUTPUT_BITS
DICE_INPUT_SIZE = 6 ** DICE_ROLLS
DICE_PREIMAGES_PER_OUTPUT = DICE_INPUT_SIZE // OUTPUT_SIZE
DICE_ACCEPTANCE_LIMIT = DICE_PREIMAGES_PER_OUTPUT * OUTPUT_SIZE


class DiceExtractionRejected(ValueError):
    """The roll block fell outside the exact-uniform rejection interval."""


def _canonical_camera_header(width: int, height: int, rgb_bytes: bytes) -> bytes:
    if not 0 < width < 2**32 or not 0 < height < 2**32:
        raise ValueError("Camera dimensions must be positive 32-bit values")
    if not isinstance(rgb_bytes, bytes):
        raise TypeError("Canonical camera pixels must be bytes")

    expected_length = width * height * 3
    if len(rgb_bytes) != expected_length:
        raise ValueError(
            f"RGB payload must contain exactly {expected_length} bytes"
        )

    return b"".join([
        CAMERA_DOMAIN,
        width.to_bytes(4, "big"),
        height.to_bytes(4, "big"),
        len(rgb_bytes).to_bytes(8, "big"),
    ])


def canonical_camera_bytes(width: int, height: int, rgb_bytes: bytes) -> bytes:
    """
    Encode one RGB frame without file metadata or compression.

    Pixels are row-major, top-to-bottom, with three bytes per pixel in R, G, B
    channel order. Width and height are unsigned 32-bit big-endian values; the
    pixel payload length is an unsigned 64-bit big-endian value.
    """
    return _canonical_camera_header(width, height, rgb_bytes) + rgb_bytes


def camera256_from_rgb(width: int, height: int, rgb_bytes: bytes) -> bytes:
    """Hash a canonical RGB frame into the protocol's 256-bit camera value."""
    digest = hashlib.sha256()
    digest.update(_canonical_camera_header(width, height, rgb_bytes))
    digest.update(rgb_bytes)
    return digest.digest()


def camera_commitment(camera256: bytes | bytearray) -> bytes:
    """Create the binding value that is recorded before dice are generated."""
    if len(camera256) != 32:
        raise ValueError("Camera value must be exactly 32 bytes")

    digest = hashlib.sha256()
    digest.update(CAMERA_COMMITMENT_DOMAIN)
    digest.update(camera256)
    return digest.digest()


def verify_camera_commitment(
    camera256: bytes | bytearray,
    commitment: bytes,
) -> bool:
    return hmac.compare_digest(camera_commitment(camera256), commitment)


def dice_block_to_integer(rolls: str) -> int:
    """
    Interpret 100 die faces as a big-endian base-6 integer.

    Faces 1 through 6 map to digits 0 through 5. The first roll is the most
    significant digit.
    """
    if len(rolls) != DICE_ROLLS:
        raise ValueError(f"Dice input must contain exactly {DICE_ROLLS} rolls")
    if any(roll not in "123456" for roll in rolls):
        raise ValueError("Dice input contains an invalid face")

    value = 0
    for roll in rolls:
        value = value * 6 + (ord(roll) - ord("1"))
    return value


def extract_uniform_dice256(rolls: str) -> bytes:
    """
    Extract an exactly uniform 256-bit value from an accepted 100-roll block.

    Five equally likely base-6 inputs map to each 256-bit output. Values in
    the incomplete sixth bucket are rejected so no output is overrepresented.
    """
    value = dice_block_to_integer(rolls)
    if value >= DICE_ACCEPTANCE_LIMIT:
        raise DiceExtractionRejected(
            "Dice block is outside the exact-uniform acceptance interval"
        )
    return (value % OUTPUT_SIZE).to_bytes(32, "big")


def xor256(left: bytes | bytearray, right: bytes | bytearray) -> bytes:
    if len(left) != 32 or len(right) != 32:
        raise ValueError("XOR inputs must both be exactly 32 bytes")
    return bytes(a ^ b for a, b in zip(left, right))


def combine_camera_and_dice(
    camera256: bytes | bytearray,
    rolls: str,
) -> bytes:
    """Return the protocol's 256-bit XOR result for an accepted dice block."""
    return xor256(camera256, extract_uniform_dice256(rolls))


def commitment_record(commitment: bytes) -> str:
    if len(commitment) != 32:
        raise ValueError("Commitment must be exactly 32 bytes")
    return f"seedsigner-hybrid-v1:camera-commitment:{commitment.hex()}"


def camera_reveal_record(camera256: bytes | bytearray) -> str:
    if len(camera256) != 32:
        raise ValueError("Camera value must be exactly 32 bytes")
    return f"seedsigner-hybrid-v1:camera-reveal:{bytes(camera256).hex()}"
