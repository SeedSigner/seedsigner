"""
Entropy quality screening for SeedSigner's seed-generation input sources.

Approach adapted from Krux (selfcustody/krux), which applies quality gates to
its camera and dice entropy sources:
  - camera:  src/krux/pages/capture_entropy.py
  - dice:    src/krux/pages/new_mnemonic/dice_rolls.py

Nothing in this module alters mnemonic derivation. It only informs the user
and, for clearly degenerate input, asks for an explicit "Proceed anyway"
confirmation before that input is hashed into a seed.

Scope and honest limitations: these are statistical *screens* against
accidental or careless input (patterned keypad entry, a heavily biased die, a
lens-cap/flat camera capture, a frozen sensor). No test computed from a small
sample can certify true randomness; a deterministic sequence with no
short-range structure will pass. BIP-39's checksum validates transcription,
not source quality -- these checks address the latter gap.

Dice checks:
  1. Frequency Shannon entropy of the face counts (catches a skewed die).
  2. First-order Markov (conditional) entropy of roll-to-roll transitions
     with a Miller-Madow small-sample bias correction (catches cyclic or
     sequential input such as 123456123456..., which has perfectly flat face
     counts). The verdict uses the more conservative of the two.
  3. Krux's derivative-based pattern detection as an independent flag.

Image checks:
  1. Shannon entropy (bits/pixel) of the pixel-value distribution and the RMS
     of per-channel standard deviations, with Krux's thresholds (catches
     flat/dark/uniform captures).
  2. Frame differencing: the entropy of the pixel-wise difference between two
     back-to-back captures with locked exposure. Scene content cancels out of
     the difference; what remains approximates the temporal sensor noise that
     actually makes a camera capture unpredictable. Two identical frames
     (frozen/replayed sensor output) score 0.0 and fail -- a fault that scene
     statistics alone cannot detect.
"""

import math
from dataclasses import dataclass


# --- Image thresholds, ported from Krux where an equivalent exists ----------

# krux/pages/capture_entropy.py
INSUFFICIENT_SHANNON_BITS_PER_PIXEL_TH = 3.0   # bits/pixel
INSUFFICIENT_VARIANCE_TH = 5                    # RMS of channel stdevs
POOR_VARIANCE_TH = 10                           # RMS of channel stdevs

# Image Shannon-entropy calc is O(pixels) and the final capture frame is ~4x
# the screen's pixel count; measure on a downsampled copy. (The full-res
# image is still what gets hashed -- the copy is measurement-only.)
SHANNON_SAMPLE_MAX_DIM = 160

# Frame differencing: center-crop size for the noise measurement and the
# floor below which two back-to-back captures are considered suspiciously
# identical. A healthy sensor always exhibits temporal noise; JPEG
# compression attenuates it but does not eliminate it in real captures.
FRAME_NOISE_SAMPLE_DIM = 160
INSUFFICIENT_NOISE_BITS_PER_PIXEL_TH = 0.05

# --- Dice thresholds --------------------------------------------------------

# krux/pages/new_mnemonic/dice_rolls.py
PATTERN_DETECT_TOLERANCE_PCT = 30
DICE_NUM_SIDES = 6

# Verdict floors for the conservative (min of frequency/Markov) entropy
# estimate, keyed by mnemonic length. Calibrated empirically over 20,000
# fair-die simulations at SeedSigner's standard roll counts (50 / 99):
#   50 rolls: honest minimum observed 87.2 bits; worst adversarial reference
#             (die rolling one face ~55% of the time) 82.9 -> floor 85.
#   99 rolls: honest minimum observed 212.6 bits; same adversarial reference
#             175.5 -> floor 205.
# i.e. false-positive rate for honest rolls is < ~1/20,000, while heavily
# skewed or patterned input lands well below the floor.
DICE_INSUFFICIENT_EFFECTIVE_BITS = {12: 85, 24: 205}


class EntropyQuality:
    INSUFFICIENT = 0
    POOR = 1
    GOOD = 2


@dataclass
class DiceEntropyResult:
    effective_bits: float
    insufficient_floor: float
    pattern_detected: bool

    @property
    def passed(self) -> bool:
        return self.effective_bits >= self.insufficient_floor and not self.pattern_detected

    @property
    def warning_text(self) -> str:
        parts = []
        if self.pattern_detected:
            parts.append("Pattern detected in rolls!")
        if self.effective_bits < self.insufficient_floor:
            parts.append("Rolls are statistically inconsistent with a fair die!")
        return "\n".join(parts)


@dataclass
class ImageEntropyResult:
    quality: int
    shannon_bits_per_pixel: float
    deviation_index: int
    # Temporal sensor-noise estimate from frame differencing; None when no
    # second reference frame was available to measure against.
    noise_bits_per_pixel: float = None

    @property
    def passed(self) -> bool:
        return self.quality != EntropyQuality.INSUFFICIENT

    @property
    def frames_suspiciously_identical(self) -> bool:
        return (
            self.noise_bits_per_pixel is not None
            and self.noise_bits_per_pixel < INSUFFICIENT_NOISE_BITS_PER_PIXEL_TH
        )

    @property
    def warning_text(self) -> str:
        if self.quality == EntropyQuality.INSUFFICIENT:
            text = "Insufficient entropy!"
            if self.frames_suspiciously_identical:
                text += "\nNo sensor noise detected!"
            return text
        if self.quality == EntropyQuality.POOR:
            return "Poor entropy!"
        return ""


# --- Dice entropy ------------------------------------------------------------

def dice_shannon_entropy_bits(rolls: str, num_sides: int = DICE_NUM_SIDES) -> float:
    """
    Shannon entropy (total bits) of the roll-value frequency distribution.
    Adapted from krux/pages/new_mnemonic/dice_rolls.py::calculate_entropy.
    Catches a skewed die but NOT patterned input -- 123456123456... has
    perfectly flat face counts. See dice_markov_entropy_bits for that case.
    """
    total = len(rolls)
    if total == 0:
        return 0.0
    counts = [0] * num_sides
    for ch in rolls:
        counts[int(ch) - 1] += 1

    unit_entropy = 0.0
    for count in counts:
        if count:
            p = count / total
            unit_entropy -= p * math.log2(p)
    return unit_entropy * total


def dice_markov_entropy_bits(rolls: str, num_sides: int = DICE_NUM_SIDES) -> float:
    """
    First-order (Markov) total-entropy estimate: the conditional entropy of
    each roll given the previous roll, H(X_i | X_{i-1}), times the number of
    rolls, with a Miller-Madow correction for finite-sample bias.

    A cyclic keypad walk (123456123456...) uses every face equally often, so
    the frequency estimate reports near-maximum entropy for it -- but every
    roll is fully determined by the one before it, so its conditional entropy
    is ~0. Taking min(frequency, markov) yields a conservative estimate that
    neither a skewed die nor a repeating pattern can inflate.
    """
    total = len(rolls)
    if total < 2:
        return dice_shannon_entropy_bits(rolls, num_sides)

    pair_counts = {}
    prev_counts = {}
    for i in range(1, total):
        pair = (rolls[i - 1], rolls[i])
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
        prev_counts[rolls[i - 1]] = prev_counts.get(rolls[i - 1], 0) + 1

    n = total - 1

    h_joint = 0.0
    for count in pair_counts.values():
        p = count / n
        h_joint -= p * math.log2(p)

    h_prev = 0.0
    for count in prev_counts.values():
        p = count / n
        h_prev -= p * math.log2(p)

    # Conditional entropy in bits per roll. The plug-in estimate is biased low
    # for small samples (the num_sides^2-cell transition histogram is sparsely
    # populated); Miller-Madow adds back ~(K-1)/(2N ln2) per estimate, where K
    # is the number of occupied bins -- the marginal's share cancels in the
    # joint-minus-marginal difference.
    h_cond = h_joint - h_prev
    correction = (len(pair_counts) - len(prev_counts)) / (2 * n * math.log(2))
    h_cond = min(h_cond + correction, math.log2(num_sides))

    return max(0.0, h_cond) * total


def effective_dice_entropy_bits(rolls: str, num_sides: int = DICE_NUM_SIDES) -> float:
    """
    The more conservative of the two estimators. A repeating pattern fools the
    frequency estimate but not the Markov estimate; a skewed die fools neither.
    """
    return min(
        dice_shannon_entropy_bits(rolls, num_sides),
        dice_markov_entropy_bits(rolls, num_sides),
    )


def dice_pattern_detected(rolls: str, num_sides: int = DICE_NUM_SIDES) -> bool:
    """
    Shannon entropy of the first-derivative sequence (roll[i] - roll[i-1]);
    flags sequential/cyclic input whose derivative distribution is too
    concentrated. Ported from
    krux/pages/new_mnemonic/dice_rolls.py::pattern_detection.
    """
    if len(rolls) < 2:
        return False

    derivatives = [int(rolls[i]) - int(rolls[i - 1]) for i in range(1, len(rolls))]
    min_d, max_d = -num_sides + 1, num_sides - 1
    d_range = max_d - min_d + 1
    counts = [0] * d_range
    for d in derivatives:
        counts[d - min_d] += 1

    total = len(derivatives)
    d_entropy = 0.0
    for count in counts:
        if count:
            p = count / total
            d_entropy -= p * math.log2(p)

    max_entropy = math.log2(d_range)
    normalized_deficit_pct = (max_entropy - d_entropy) / max_entropy * 100
    return normalized_deficit_pct > PATTERN_DETECT_TOLERANCE_PCT


def assess_dice_entropy(rolls: str, mnemonic_length: int) -> DiceEntropyResult:
    return DiceEntropyResult(
        effective_bits=effective_dice_entropy_bits(rolls),
        insufficient_floor=DICE_INSUFFICIENT_EFFECTIVE_BITS[mnemonic_length],
        pattern_detected=dice_pattern_detected(rolls),
    )


# --- Image entropy (camera source) -----------------------------------------

def _rms(values) -> float:
    return math.sqrt(sum(v ** 2 for v in values) / len(values))


def pixel_deviation_index(image) -> int:
    """
    RMS of per-channel standard deviation. Mirrors Krux's L/A/B stdev RMS,
    computed on whatever bands the PIL image already has (a flat image has
    low stdev in any color space).
    """
    from PIL import ImageStat
    stat = ImageStat.Stat(image)
    return int(_rms(stat.stddev))


def shannon_entropy_bits_per_pixel(image) -> float:
    """
    Shannon entropy of the pixel-value distribution, in bits/pixel.
    Run this on a downsampled copy (see SHANNON_SAMPLE_MAX_DIM); it is
    O(pixels) and a full-res capture is too large to histogram interactively
    on a Pi Zero.
    """
    pixels = list(image.getdata())
    total = len(pixels)
    if total == 0:
        return 0.0

    counts = {}
    for p in pixels:
        counts[p] = counts.get(p, 0) + 1

    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy


def frame_noise_entropy_bits_per_pixel(frame_a, frame_b) -> float:
    """
    Shannon entropy (bits per channel-sample) of the pixel-wise difference
    between two back-to-back captures of the same scene with locked exposure.

    Scene structure is identical in both frames and cancels out; what remains
    approximates the temporal sensor noise (shot noise, thermal noise) plus
    residual handshake -- the part of a capture that is unpredictable even to
    an observer who knows the scene. Scene statistics alone cannot detect a
    frozen or replayed sensor feed; this can (identical frames return 0.0).

    Uses a center CROP rather than a resize: downsampling averages adjacent
    pixels, which would suppress exactly the noise being measured. Captures
    are JPEG-compressed, which attenuates low-amplitude noise -- treat the
    result as a lower bound.
    """
    from PIL import ImageChops

    if frame_a.size != frame_b.size or frame_a.mode != frame_b.mode:
        # Shouldn't happen (same camera, same mode, back-to-back) but don't
        # crash the seed flow over a measurement.
        frame_b = frame_b.convert(frame_a.mode).resize(frame_a.size)

    w, h = frame_a.size
    crop_w, crop_h = min(w, FRAME_NOISE_SAMPLE_DIM), min(h, FRAME_NOISE_SAMPLE_DIM)
    left, top = (w - crop_w) // 2, (h - crop_h) // 2
    box = (left, top, left + crop_w, top + crop_h)

    diff = ImageChops.difference(frame_a.crop(box), frame_b.crop(box))

    # diff.histogram() concatenates one 256-bin histogram per band. Merge them
    # bin-wise into a single distribution over |difference| values -- without
    # this, band identity itself contributes log2(num_bands) of phantom
    # entropy and identical frames would score ~1.58 instead of 0.
    hist = diff.histogram()
    num_bands = max(1, len(hist) // 256)
    combined = [0] * 256
    for band in range(num_bands):
        for i in range(256):
            combined[i] += hist[band * 256 + i]

    total = sum(combined)
    if total == 0:
        return 0.0

    entropy = 0.0
    for count in combined:
        if count:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def assess_image_entropy(full_res_image, noise_reference_frame=None) -> ImageEntropyResult:
    """
    Run the Krux-equivalent scene gates against a captured PIL.Image.
    Downsamples internally for the Shannon calc; deviation index is cheap
    enough to run on the downsampled copy too.

    If a second back-to-back capture is supplied as noise_reference_frame,
    also measures temporal sensor noise via frame differencing; two
    suspiciously identical frames downgrade the verdict to INSUFFICIENT.
    """
    img = full_res_image
    w, h = img.size
    max_dim = max(w, h)
    if max_dim > SHANNON_SAMPLE_MAX_DIM:
        scale = SHANNON_SAMPLE_MAX_DIM / max_dim
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))

    shannon = shannon_entropy_bits_per_pixel(img)
    deviation = pixel_deviation_index(img)

    noise = None
    if noise_reference_frame is not None:
        noise = frame_noise_entropy_bits_per_pixel(full_res_image, noise_reference_frame)

    if shannon < INSUFFICIENT_SHANNON_BITS_PER_PIXEL_TH or deviation < INSUFFICIENT_VARIANCE_TH:
        quality = EntropyQuality.INSUFFICIENT
    elif noise is not None and noise < INSUFFICIENT_NOISE_BITS_PER_PIXEL_TH:
        quality = EntropyQuality.INSUFFICIENT
    elif deviation < POOR_VARIANCE_TH:
        quality = EntropyQuality.POOR
    else:
        quality = EntropyQuality.GOOD

    return ImageEntropyResult(quality=quality, shannon_bits_per_pixel=shannon, deviation_index=deviation, noise_bits_per_pixel=noise)
