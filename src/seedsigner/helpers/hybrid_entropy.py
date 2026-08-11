import hashlib
import hmac
import math
from dataclasses import dataclass


PROTOCOL_NAME = "SeedSigner Hybrid Entropy v1"

CAMERA_DOMAIN = b"SeedSigner Hybrid Camera RGB v1\x00"
CAMERA_COMMITMENT_DOMAIN = b"SeedSigner Hybrid Camera Commitment v1\x00"

DICE_ROLLS = 100
OUTPUT_BITS = 256
OUTPUT_SIZE = 1 << OUTPUT_BITS
DICE_INPUT_SIZE = 6 ** DICE_ROLLS
DICE_PREIMAGES_PER_OUTPUT = DICE_INPUT_SIZE // OUTPUT_SIZE
DICE_ACCEPTANCE_LIMIT = DICE_PREIMAGES_PER_OUTPUT * OUTPUT_SIZE

# PR #993-compatible camera quality screening. The second frame is used only
# for measurement; camera256 continues to commit to the first canonical frame.
CAMERA_SHANNON_SAMPLE_MAX_DIM = 160
CAMERA_NOISE_SAMPLE_DIM = 160
CAMERA_INSUFFICIENT_SHANNON_BITS_PER_PIXEL = 3.0
CAMERA_INSUFFICIENT_DEVIATION = 5
CAMERA_POOR_DEVIATION = 10
CAMERA_INSUFFICIENT_NOISE_BITS_PER_PIXEL = 0.05


class CameraEntropyQuality:
    INSUFFICIENT = 0
    POOR = 1
    GOOD = 2


@dataclass(frozen=True)
class CameraEntropyResult:
    quality: int
    shannon_bits_per_pixel: float
    deviation_index: int
    noise_bits_per_pixel: float

    @property
    def passed(self) -> bool:
        return self.quality != CameraEntropyQuality.INSUFFICIENT


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


def _shannon_entropy_from_counts(counts, total: int) -> float:
    if total == 0:
        return 0.0
    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in counts
        if count
    )
    # Avoid presenting identical frames as the confusing string "-0.00".
    return 0.0 if entropy == 0.0 else entropy


def camera_frame_noise_bits_per_pixel(frame_a, frame_b) -> float:
    """Measure PR #993-style temporal noise using two back-to-back frames.

    The calculation uses the center crop and the absolute per-channel pixel
    difference. Channel histograms are merged bin-wise so identical RGB frames
    score exactly 0.0 instead of gaining phantom entropy from band identity.
    """
    from PIL import ImageChops

    if frame_a.size != frame_b.size or frame_a.mode != frame_b.mode:
        frame_b = frame_b.convert(frame_a.mode).resize(frame_a.size)

    width, height = frame_a.size
    crop_width = min(width, CAMERA_NOISE_SAMPLE_DIM)
    crop_height = min(height, CAMERA_NOISE_SAMPLE_DIM)
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    crop_box = (left, top, left + crop_width, top + crop_height)
    difference = ImageChops.difference(
        frame_a.crop(crop_box),
        frame_b.crop(crop_box),
    )

    histogram = difference.histogram()
    band_count = max(1, len(histogram) // 256)
    combined = [0] * 256
    for band in range(band_count):
        for value in range(256):
            combined[value] += histogram[(band * 256) + value]
    return _shannon_entropy_from_counts(combined, sum(combined))


def assess_hybrid_camera_entropy(frame_a, frame_b) -> CameraEntropyResult:
    """Screen the hybrid capture using the scene and frame checks from #993.

    This is measurement-only. Only ``frame_a`` is passed to
    :func:`camera256_from_rgb`; ``frame_b`` must be cleared after assessment.
    """
    from PIL import ImageStat

    sample = frame_a
    width, height = sample.size
    maximum_dimension = max(width, height)
    if maximum_dimension > CAMERA_SHANNON_SAMPLE_MAX_DIM:
        scale = CAMERA_SHANNON_SAMPLE_MAX_DIM / maximum_dimension
        sample = sample.resize((
            max(1, int(width * scale)),
            max(1, int(height * scale)),
        ))

    pixels = list(sample.getdata())
    pixel_counts = {}
    for pixel in pixels:
        pixel_counts[pixel] = pixel_counts.get(pixel, 0) + 1
    shannon = _shannon_entropy_from_counts(pixel_counts.values(), len(pixels))

    channel_deviations = ImageStat.Stat(sample).stddev
    deviation = int(math.sqrt(
        sum(value ** 2 for value in channel_deviations)
        / len(channel_deviations)
    ))
    noise = camera_frame_noise_bits_per_pixel(frame_a, frame_b)

    if (
        shannon < CAMERA_INSUFFICIENT_SHANNON_BITS_PER_PIXEL
        or deviation < CAMERA_INSUFFICIENT_DEVIATION
        or noise < CAMERA_INSUFFICIENT_NOISE_BITS_PER_PIXEL
    ):
        quality = CameraEntropyQuality.INSUFFICIENT
    elif deviation < CAMERA_POOR_DEVIATION:
        quality = CameraEntropyQuality.POOR
    else:
        quality = CameraEntropyQuality.GOOD

    return CameraEntropyResult(
        quality=quality,
        shannon_bits_per_pixel=shannon,
        deviation_index=deviation,
        noise_bits_per_pixel=noise,
    )


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
