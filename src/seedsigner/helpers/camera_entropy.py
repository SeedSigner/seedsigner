import hashlib
import logging
import math
import os
import time

logger = logging.getLogger(__name__)

"""
    Entropy derivation for the camera ("image entropy") seed generation flow.

    This logic lives here rather than inline in the View so that it can be unit
    tested without the GUI or camera hardware stack.

    Threat model note: the camera sensor remains the headline entropy source.
    Everything else mixed into the chain below is either non-secret (CPU serial),
    weak (wall clock on a device with no RTC), or defense-in-depth (the OS
    CSPRNG). None of them are relied upon individually.
"""

# The full-res capture is hashed as raw pixel bytes. These thresholds are a
# *smoke test* for gross failure of the sensor (lens capped, total darkness,
# frozen/blank frame buffer), NOT a min-entropy certification: Shannon entropy
# over a byte histogram is an upper bound on min-entropy, not a substitute for
# it (cf. NIST SP 800-90B). A real scene lit well enough to see on the preview
# screen sits comfortably above 6 bits/byte; a capped lens collapses toward 0.
MIN_SHANNON_BITS_PER_BYTE = 4.0
MIN_DISTINCT_BYTE_VALUES = 64

# The live preview frames are a secondary source, but an empty list means the
# preview stage silently produced nothing, which we must never hash over in
# silence.
MIN_PREVIEW_FRAMES = 1

CPU_INFO_PATH = "/proc/cpuinfo"


class EntropyHealthError(Exception):
    """ Raised when an entropy source fails a basic health check.

        Callers MUST surface this to the user and abort seed generation. It must
        never be swallowed and never fall back to a default/constant value; that
        silent-fallback pattern is exactly what produced the July 2026 COLDCARD
        RNG failure.
    """
    pass



def shannon_bits_per_byte(histogram: list[int]) -> float:
    """ Shannon entropy, in bits per byte, of a 256-bin byte histogram. """
    total = sum(histogram)
    if total == 0:
        return 0.0

    entropy = 0.0
    for count in histogram:
        if count == 0:
            continue
        p = count / total
        entropy -= p * math.log2(p)

    return entropy



def analyze_image_histogram(image) -> tuple[float, int]:
    """ Returns (mean bits-per-byte across bands, distinct byte values seen).

        PIL returns a flat list of 256 bins per band, so an RGB image yields 768
        entries. Bands are scored separately and averaged; scoring the
        concatenated list would allow up to log2(768) bits and mask a flat band.
    """
    histogram = image.histogram()

    if len(histogram) % 256 != 0:
        raise EntropyHealthError(f"Unexpected histogram length: {len(histogram)}")

    bands = [histogram[i:i + 256] for i in range(0, len(histogram), 256)]
    band_entropies = [shannon_bits_per_byte(band) for band in bands]

    distinct = max(len([count for count in band if count > 0]) for band in bands)

    return sum(band_entropies) / len(band_entropies), distinct



def assert_image_healthy(image) -> None:
    """ Rejects a degenerate capture (capped lens, darkness, dead sensor). """
    if image is None:
        raise EntropyHealthError("No final image was captured")

    bits_per_byte, distinct = analyze_image_histogram(image)

    if bits_per_byte < MIN_SHANNON_BITS_PER_BYTE or distinct < MIN_DISTINCT_BYTE_VALUES:
        # Deliberately does not log the measured values at anything above debug:
        # they are a (weak) function of the entropy that seeds a private key.
        logger.debug(f"Image entropy health check failed: {bits_per_byte:.2f} bits/byte, {distinct} distinct values")
        raise EntropyHealthError(
            "The captured image does not contain enough variation to be used as "
            "entropy. Retake the photo of a well-lit, detailed subject."
        )



def assert_preview_frames_healthy(preview_frames) -> None:
    """ Rejects an empty or frozen preview buffer. """
    if not preview_frames or len(preview_frames) < MIN_PREVIEW_FRAMES:
        raise EntropyHealthError("The camera preview produced no frames")

    if len(preview_frames) > 1:
        digests = {hashlib.sha256(frame.tobytes()).digest() for frame in preview_frames}
        if len(digests) == 1:
            raise EntropyHealthError("The camera preview frames are all identical")



def get_cpu_serial() -> bytes:
    """ Device-unique but NOT secret; contributes uniqueness, not entropy.

        Returns b"" if unavailable. An empty prefix is honest about contributing
        nothing; a constant like b"0" merely looks like a value.
    """
    try:
        with open(CPU_INFO_PATH, "r") as f:
            for line in f:
                if "Serial" in line:
                    return line.split(":")[-1].strip().encode("utf-8")
    except Exception as e:
        logger.info(repr(e), exc_info=True)

    logger.info("CPU serial unavailable; continuing without it")
    return b""



def derive_entropy_bytes(preview_frames, final_image, num_bytes: int = 32, cpu_serial: bytes = None, csprng_bytes: bytes = None) -> bytes:
    """ Derives `num_bytes` of seed entropy from a camera capture.

        Sources are chained through SHA-256, so adding a source can never reduce
        the entropy of the result. Health checks run BEFORE any hashing so a
        failure aborts rather than silently producing a weak seed.

        `cpu_serial` and `csprng_bytes` are injectable for testing only.
    """
    if num_bytes not in (16, 32):
        raise ValueError(f"num_bytes must be 16 or 32, got {num_bytes}")

    assert_preview_frames_healthy(preview_frames)
    assert_image_healthy(final_image)

    # Hardware-level uniqueness via the CPU serial (non-secret).
    hash_bytes = hashlib.sha256(cpu_serial if cpu_serial is not None else get_cpu_serial()).digest()

    # Modest entropy via wall clock. Weak on a device with no RTC and no NTP:
    # treat as a nonce, not as an entropy source.
    hash_bytes = hashlib.sha256(hash_bytes + str(time.time()).encode("utf-8")).digest()

    # Better entropy by chaining the preview frames.
    for frame in preview_frames:
        hash_bytes = hashlib.sha256(hash_bytes + frame.tobytes()).digest()

    # Headline entropy: the full-res capture.
    hash_bytes = hashlib.sha256(hash_bytes + final_image.tobytes()).digest()

    # Defense in depth: mix the OS CSPRNG (Linux ChaCha20 DRBG, itself seeded
    # from the BCM2835 hardware RNG). SeedSigner does not *trust* this source and
    # does not need it to be good -- hashing it in can only add. The point is to
    # remove the single-source failure mode, not to shift the trust model.
    hash_bytes = hashlib.sha256(hash_bytes + (csprng_bytes if csprng_bytes is not None else os.urandom(32))).digest()

    return hash_bytes[:num_bytes]
