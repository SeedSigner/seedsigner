"""
Entropy conditioning and regression tests for SeedSigner's seed-generation code:

* Camera image entropy (production UI path): the SHA-256 hash chain in
  ToolsImageEntropyMnemonicLengthView (src/seedsigner/views/tools_views.py),
  driven through the real View code.
* Dice roll entropy (production UI path): mnemonic_generation.generate_mnemonic_from_dice
* Coin flip conditioning helper: mnemonic_generation.generate_mnemonic_from_coin_flips
  (used by the tools/mnemonic.py CLI; not currently wired into a UI seed-creation flow)
* Final word / partial entropy helper: mnemonic_generation.get_partial_final_word
  (the UI calc-final-word flow itself is FlowTest territory)

Each conditioned output stream is run through a subset of the NIST SP 800-22 tests
(monobit, block frequency, runs, longest run, cumulative sums, approximate entropy)
plus a chi-square byte-distribution test. The pure-Python implementations are
validated against the worked examples published in NIST SP 800-22 Rev 1a itself
(see TestNistReferenceVectors).

Known-answer vectors pin the exact conditioning algorithms — including the vectors
published in docs/dice_verification.md — so any change to an entropy pipeline
(different hash, different truncation, silent switch to another RNG) fails loudly.

All statistical inputs are derived from a fixed-seed SHA-256 counter PRF, so every
p-value is deterministic: no flaky CI runs.

Scope: these tests validate the conditioning algorithms and guard against code
regressions (wrong hash, wrong truncation, silent switch to a weak RNG). They do
NOT validate the physical entropy sources: because every pipeline is SHA-256
conditioned, almost any non-degenerate input passes the statistical battery.
Fair dice, honest coin flips, and real camera sensor noise are still required
from the user and hardware at runtime.
"""
# Must import test base before any SeedSigner imports to mock hardware deps
from base import BaseTest

import hashlib
import io
import math
import os
import re
import inspect
import pytest
from unittest.mock import patch

from embit import bip39
from PIL import Image

from seedsigner.helpers import mnemonic_generation
from seedsigner.models.seed import Seed
from seedsigner.views import tools_views


ALPHA = 0.01       # NIST SP 800-22 recommended significance level
ALPHA_LIVE = 1e-6  # for the (non-deterministic) host OS RNG sanity check


"""****************************************************************************
    Deterministic input generation (SHA-256 counter PRF)
****************************************************************************"""

def prf_bytes(tag: str, num_bytes: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < num_bytes:
        out += hashlib.sha256(tag.encode() + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:num_bytes]


def prf_bits(tag: str, num_bits: int) -> str:
    raw = prf_bytes(tag, (num_bits + 7) // 8)
    return "".join(format(b, "08b") for b in raw)[:num_bits]


def prf_dice_rolls(tag: str, num_rolls: int) -> str:
    return "".join(str(b % 6 + 1) for b in prf_bytes(tag, num_rolls))


"""****************************************************************************
    NIST SP 800-22 statistical tests (pure Python; no new dependencies)
****************************************************************************"""

def _igamc(a: float, x: float) -> float:
    """ Regularized upper incomplete gamma Q(a, x); needed for several NIST p-values. """
    if x <= 0.0:
        return 1.0
    log_prefix = -x + a * math.log(x) - math.lgamma(a)
    if x < a + 1.0:
        # series expansion for P(a, x); Q = 1 - P
        term = 1.0 / a
        total = term
        n = a
        while abs(term) > abs(total) * 1e-16:
            n += 1.0
            term *= x / n
            total += term
        return 1.0 - total * math.exp(log_prefix)
    else:
        # continued fraction for Q(a, x) (modified Lentz)
        tiny = 1e-300
        b = x + 1.0 - a
        c = 1.0 / tiny
        d = 1.0 / b
        h = d
        for i in range(1, 1000):
            an = -i * (i - a)
            b += 2.0
            d = an * d + b
            if abs(d) < tiny:
                d = tiny
            c = b + an / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < 1e-16:
                break
        return math.exp(log_prefix) * h


def _std_normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _to_bits(data: bytes) -> list:
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def nist_monobit(bits: list) -> float:
    """ SP 800-22 2.1: Frequency (Monobit) Test """
    n = len(bits)
    s = abs(2 * sum(bits) - n)
    return math.erfc(s / math.sqrt(2 * n))


def nist_block_frequency(bits: list, M: int = 128) -> float:
    """ SP 800-22 2.2: Frequency Test within a Block """
    n = len(bits)
    N = n // M
    chi2 = 4.0 * M * sum(
        (sum(bits[i * M:(i + 1) * M]) / M - 0.5) ** 2 for i in range(N)
    )
    return _igamc(N / 2.0, chi2 / 2.0)


def nist_runs(bits: list) -> float:
    """ SP 800-22 2.3: Runs Test """
    n = len(bits)
    pi = sum(bits) / n
    if abs(pi - 0.5) >= 2.0 / math.sqrt(n):
        return 0.0  # monobit prerequisite failed
    v_obs = 1 + sum(1 for i in range(n - 1) if bits[i] != bits[i + 1])
    return math.erfc(
        abs(v_obs - 2.0 * n * pi * (1 - pi)) / (2.0 * math.sqrt(2.0 * n) * pi * (1 - pi))
    )


def nist_longest_run(bits: list, M: int = 128) -> float:
    """ SP 800-22 2.4: Longest Run of Ones in a Block (M=8 needs n >= 128; M=128 needs n >= 6272) """
    if M == 8:
        pi = [0.2148, 0.3672, 0.2305, 0.1875]  # v <= 1, 2, 3, >= 4
        v_lo, v_hi = 1, 4
    elif M == 128:
        pi = [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124]  # v <= 4, 5, 6, 7, 8, >= 9
        v_lo, v_hi = 4, 9
    else:
        raise ValueError("Only M=8 and M=128 parameter sets are implemented")
    K = len(pi) - 1
    N = len(bits) // M
    v = [0] * len(pi)
    for i in range(N):
        block = bits[i * M:(i + 1) * M]
        longest = run = 0
        for bit in block:
            run = run + 1 if bit else 0
            longest = max(longest, run)
        v[min(max(longest, v_lo), v_hi) - v_lo] += 1
    chi2 = sum((v[k] - N * pi[k]) ** 2 / (N * pi[k]) for k in range(len(pi)))
    return _igamc(K / 2.0, chi2 / 2.0)


def nist_cumulative_sums(bits: list, reverse: bool = False) -> float:
    """ SP 800-22 2.13: Cumulative Sums (Cusum) Test """
    n = len(bits)
    seq = bits[::-1] if reverse else bits
    s = z = 0
    for bit in seq:
        s += 2 * bit - 1
        z = max(z, abs(s))
    sqrt_n = math.sqrt(n)
    p = 1.0
    for k in range((-n // z + 1) // 4, (n // z - 1) // 4 + 1):
        p -= (_std_normal_cdf((4 * k + 1) * z / sqrt_n)
              - _std_normal_cdf((4 * k - 1) * z / sqrt_n))
    for k in range((-n // z - 3) // 4, (n // z - 1) // 4 + 1):
        p += (_std_normal_cdf((4 * k + 3) * z / sqrt_n)
              - _std_normal_cdf((4 * k + 1) * z / sqrt_n))
    return p


def nist_approximate_entropy(bits: list, m: int = 2) -> float:
    """ SP 800-22 2.12: Approximate Entropy Test """
    n = len(bits)

    def phi(block_len: int) -> float:
        counts = {}
        # overlapping patterns with wraparound
        extended = bits + bits[:block_len - 1]
        pattern = 0
        mask = (1 << block_len) - 1
        for i in range(block_len):
            pattern = (pattern << 1) | extended[i]
        counts[pattern] = 1
        for i in range(1, n):
            pattern = ((pattern << 1) | extended[i + block_len - 1]) & mask
            counts[pattern] = counts.get(pattern, 0) + 1
        return sum((c / n) * math.log(c / n) for c in counts.values())

    ap_en = phi(m) - phi(m + 1)
    chi2 = 2.0 * n * (math.log(2.0) - ap_en)
    return _igamc(2 ** (m - 1), chi2 / 2.0)


def chi_square_bytes(data: bytes) -> float:
    """ Chi-square goodness-of-fit over the byte distribution (255 degrees of freedom). """
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    expected = len(data) / 256.0
    chi2 = sum((c - expected) ** 2 / expected for c in counts)
    return _igamc(255 / 2.0, chi2 / 2.0)


def run_battery(data: bytes) -> dict:
    bits = _to_bits(data)
    return {
        "monobit": nist_monobit(bits),
        "block_frequency": nist_block_frequency(bits),
        "runs": nist_runs(bits),
        "longest_run": nist_longest_run(bits),
        "cusum_forward": nist_cumulative_sums(bits),
        "cusum_backward": nist_cumulative_sums(bits, reverse=True),
        "approximate_entropy": nist_approximate_entropy(bits),
        "chi_square_bytes": chi_square_bytes(data),
    }


def assert_battery_passes(data: bytes, label: str, alpha: float = ALPHA):
    results = run_battery(data)
    failures = {name: p for name, p in results.items() if p < alpha}
    assert not failures, f"{label} failed NIST battery (alpha={alpha}): {failures}; all results: {results}"


def mnemonic_to_entropy_bytes(mnemonic: list) -> bytes:
    return bip39.mnemonic_to_bytes(" ".join(mnemonic))


"""****************************************************************************
    Validate our NIST implementations against NIST's own published examples
****************************************************************************"""

class TestNistReferenceVectors:
    """ Each p-value below is the worked example printed in NIST SP 800-22 Rev 1a
        (sections 2.x.8). If our implementations drift from the spec, these fail. """

    # First 100 binary digits of pi; input for examples 2.1.8, 2.2.8, 2.3.8, 2.12.8, 2.13.8
    PI_100_BITS = [int(b) for b in
                   "1100100100001111110110101010001000100001011010001100001000110100"
                   "110001001100011001100010100010111000"]

    # 128-bit input from example 2.4.8 (Longest Run of Ones, M=8)
    LONGEST_RUN_128_BITS = [int(b) for b in
                            "11001100000101010110110001001100111000000000001001"
                            "00110101010001000100111101011010000000110101111100"
                            "1100111001101101100010110010"]

    def test_monobit_reference(self):
        assert nist_monobit(self.PI_100_BITS) == pytest.approx(0.109599, abs=1e-4)

    def test_block_frequency_reference(self):
        assert nist_block_frequency(self.PI_100_BITS, M=10) == pytest.approx(0.706438, abs=1e-4)

    def test_runs_reference(self):
        assert nist_runs(self.PI_100_BITS) == pytest.approx(0.500798, abs=1e-4)

    def test_longest_run_reference(self):
        assert nist_longest_run(self.LONGEST_RUN_128_BITS, M=8) == pytest.approx(0.180609, abs=1e-4)

    def test_approximate_entropy_reference(self):
        assert nist_approximate_entropy(self.PI_100_BITS, m=2) == pytest.approx(0.235301, abs=1e-4)

    def test_cumulative_sums_reference(self):
        assert nist_cumulative_sums(self.PI_100_BITS) == pytest.approx(0.219194, abs=1e-4)
        assert nist_cumulative_sums(self.PI_100_BITS, reverse=True) == pytest.approx(0.114866, abs=1e-4)



"""****************************************************************************
    Statistical tests over each production entropy pipeline
****************************************************************************"""

class TestDiceEntropyStatistics:
    def test_dice_pipeline_nist_battery(self):
        """ SHA-256 conditioned dice roll entropy must pass the NIST battery. """
        stream = b""
        for i in range(600):
            rolls = prf_dice_rolls(f"dice-battery-{i}", mnemonic_generation.DICE__NUM_ROLLS__24WORD)
            mnemonic = mnemonic_generation.generate_mnemonic_from_dice(rolls)
            stream += mnemonic_to_entropy_bytes(mnemonic)
        assert len(stream) == 600 * 32
        assert_battery_passes(stream, "dice roll pipeline")


    def test_dice_pipeline_no_collisions(self):
        """ Distinct roll sequences must never map to the same entropy. """
        outputs = set()
        for i in range(600):
            rolls = prf_dice_rolls(f"dice-battery-{i}", mnemonic_generation.DICE__NUM_ROLLS__24WORD)
            outputs.add(tuple(mnemonic_generation.generate_mnemonic_from_dice(rolls)))
        assert len(outputs) == 600


    def test_dice_avalanche(self):
        """ Changing a single die roll must flip ~half of the 256 entropy bits. """
        distances = []
        for i in range(20):
            rolls = prf_dice_rolls(f"dice-avalanche-{i}", mnemonic_generation.DICE__NUM_ROLLS__24WORD)
            position = i * 4 % len(rolls)
            altered = rolls[:position] + str((int(rolls[position])) % 6 + 1) + rolls[position + 1:]
            assert altered != rolls
            a = mnemonic_to_entropy_bytes(mnemonic_generation.generate_mnemonic_from_dice(rolls))
            b = mnemonic_to_entropy_bytes(mnemonic_generation.generate_mnemonic_from_dice(altered))
            distance = bin(int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).count("1")
            # Binomial(256, 0.5): ~128 expected; 80-176 is > 6 sigma
            assert 80 <= distance <= 176, f"weak diffusion: {distance} bits flipped"
            distances.append(distance)
        assert 112 <= sum(distances) / len(distances) <= 144



class TestCoinFlipEntropyStatistics:
    def test_coin_flip_pipeline_nist_battery(self):
        """ SHA-256 conditioned coin flip entropy must pass the NIST battery. """
        stream = b""
        for i in range(600):
            flips = prf_bits(f"coin-battery-{i}", 256)
            mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(flips)
            stream += mnemonic_to_entropy_bytes(mnemonic)
        assert len(stream) == 600 * 32
        assert_battery_passes(stream, "coin flip pipeline")


    def test_coin_flip_pipeline_no_collisions(self):
        outputs = set()
        for i in range(600):
            flips = prf_bits(f"coin-battery-{i}", 256)
            outputs.add(tuple(mnemonic_generation.generate_mnemonic_from_coin_flips(flips)))
        assert len(outputs) == 600



class ImageEntropyTestBase(BaseTest):
    """ Drives the real camera-entropy conditioning code in
        ToolsImageEntropyMnemonicLengthView rather than a reimplementation. """

    @staticmethod
    def _make_frames(tag: str):
        preview_frames = [
            Image.frombytes("RGB", (32, 32), prf_bytes(f"{tag}-preview-{i}", 32 * 32 * 3))
            for i in range(5)
        ]
        final_image = Image.frombytes("RGB", (64, 64), prf_bytes(f"{tag}-final", 64 * 64 * 3))
        return preview_frames, final_image


    def _run_image_entropy_view(self, preview_frames, final_image, fake_time: float, menu_selection: int,
                                cpu_serial: str = None) -> list:
        """ Runs the actual View with mocked screen/camera/clock inputs; returns the resulting mnemonic. """
        self.controller.image_entropy_preview_frames = preview_frames
        self.controller.image_entropy_final_image = final_image

        real_open = open
        def deterministic_open(file, *args, **kwargs):
            # Deterministic /proc/cpuinfo on every platform: either the given CPU
            # serial or the no-serial fallback
            if file == "/proc/cpuinfo":
                if cpu_serial is None:
                    raise FileNotFoundError(file)
                return io.StringIO(f"processor\t: 0\nSerial\t\t: {cpu_serial}\n")
            return real_open(file, *args, **kwargs)

        view = tools_views.ToolsImageEntropyMnemonicLengthView()
        with patch.object(tools_views.ToolsImageEntropyMnemonicLengthView, "run_screen", return_value=menu_selection), \
             patch("time.time", return_value=fake_time), \
             patch("builtins.open", side_effect=deterministic_open):
            view.run()

        return self.controller.storage.get_pending_seed().mnemonic_list



class TestImageEntropyStatistics(ImageEntropyTestBase):
    def test_image_pipeline_nist_battery(self):
        """ The camera image hash chain output must pass the NIST battery. """
        stream = b""
        for i in range(250):
            preview_frames, final_image = self._make_frames(f"image-battery-{i}")
            mnemonic = self._run_image_entropy_view(
                preview_frames, final_image, fake_time=1700000000.0 + i, menu_selection=1)
            assert len(mnemonic) == 24
            stream += mnemonic_to_entropy_bytes(mnemonic)
        assert len(stream) == 250 * 32
        assert_battery_passes(stream, "camera image pipeline")


    def test_image_pipeline_clears_image_buffers(self):
        """ Camera frames must not linger in the Controller after seed creation. """
        preview_frames, final_image = self._make_frames("image-cleanup")
        self._run_image_entropy_view(preview_frames, final_image, fake_time=1700000000.0, menu_selection=1)
        assert self.controller.image_entropy_preview_frames is None
        assert self.controller.image_entropy_final_image is None


    def test_image_pipeline_stops_loading_screen_on_error(self):
        """ The "Calculating..." spinner must stop even if entropy generation fails. """
        self.controller.image_entropy_preview_frames = None  # simulates missing camera data
        self.controller.image_entropy_final_image = None
        view = tools_views.ToolsImageEntropyMnemonicLengthView()
        with patch("seedsigner.gui.screens.screen.LoadingScreenThread") as mock_loading_screen, \
             patch.object(tools_views.ToolsImageEntropyMnemonicLengthView, "run_screen", return_value=1), \
             pytest.raises(TypeError):
            view.run()
        mock_loading_screen.return_value.stop.assert_called_once()



class TestHostRngSanity:
    def test_os_urandom_sanity(self):
        """ Catastrophic-failure check of the host OS RNG the test PRF stands in for.
            Non-deterministic input, so alpha is tiny to keep CI stable. """
        assert_battery_passes(os.urandom(16384), "os.urandom", alpha=ALPHA_LIVE)


    def test_battery_detects_degenerate_input(self):
        """ Self-test: the battery must reject obviously broken entropy. """
        results = run_battery(b"\x00" * 4096)
        assert results["monobit"] < ALPHA
        results = run_battery(b"\xaa" * 4096)  # perfect 1010... alternation
        assert results["runs"] < ALPHA
        results = run_battery(prf_bytes("battery-self-test", 2048)[:64] * 64)  # short cycle
        assert results["approximate_entropy"] < ALPHA


"""****************************************************************************
    Known-answer tests: pin the exact conditioning algorithm of each pipeline
****************************************************************************"""

class TestDiceKnownAnswers:
    # Published SeedSigner verification vectors (docs/dice_verification.md)
    DOC_ROLLS_24 = "655152231316521321611331544441236164664431121534415633526456254462245546236542364246312613322234612"
    DOC_MNEMONIC_24 = ("eyebrow obvious such suggest poet seven breeze blame virtual frown dynamic donor "
                       "harsh pigeon express broccoli easy apology scatter force recipe shadow claim radio")
    DOC_ROLLS_12 = "65515223131652132161133154444123616466443112153441"
    DOC_MNEMONIC_12 = "hole luggage safe present express tragic orbit shed switch metal identify path"
    DOC_FINGERPRINT_12 = "8d9cced8"

    def test_dice_24_word_doc_vector(self):
        mnemonic = mnemonic_generation.generate_mnemonic_from_dice(self.DOC_ROLLS_24)
        assert " ".join(mnemonic) == self.DOC_MNEMONIC_24

    def test_dice_12_word_doc_vector(self):
        mnemonic = mnemonic_generation.generate_mnemonic_from_dice(self.DOC_ROLLS_12)
        assert " ".join(mnemonic) == self.DOC_MNEMONIC_12

    def test_dice_12_word_doc_vector_fingerprint(self):
        seed = Seed(mnemonic=self.DOC_MNEMONIC_12.split())
        assert seed.get_fingerprint() == self.DOC_FINGERPRINT_12

    def test_dice_entropy_is_sha256_of_roll_string(self):
        """ Independent reimplementation: entropy must be exactly SHA-256 of the
            ASCII roll string ("Base 10" mode; see docs/dice_verification.md). """
        for i in range(20):
            rolls = prf_dice_rolls(f"dice-kat-{i}", mnemonic_generation.DICE__NUM_ROLLS__24WORD)
            mnemonic = mnemonic_generation.generate_mnemonic_from_dice(rolls)
            assert mnemonic_to_entropy_bytes(mnemonic) == hashlib.sha256(rolls.encode()).digest()

    def test_dice_12_word_uses_first_16_bytes(self):
        """ 12-word truncation rule: first 128 bits of the SHA-256 digest. """
        rolls = prf_dice_rolls("dice-truncation", mnemonic_generation.DICE__NUM_ROLLS__12WORD)
        mnemonic = mnemonic_generation.generate_mnemonic_from_dice(rolls)
        assert len(mnemonic) == 12
        assert mnemonic_to_entropy_bytes(mnemonic) == hashlib.sha256(rolls.encode()).digest()[:16]



class TestCoinFlipKnownAnswers:
    KAT_FLIPS_128 = prf_bits("seedsigner-coinflip-kat-128", 128)
    KAT_MNEMONIC_12 = "welcome patrol south inform seat scene cricket segment hour expand slot medal"
    KAT_FLIPS_256 = prf_bits("seedsigner-coinflip-kat-256", 256)
    KAT_MNEMONIC_24 = ("midnight corn multiply thing roast soup ketchup wear example panel airport proud "
                       "dust moment loan else magic weasel heavy gloom dish science bronze crumble")

    def test_coin_flip_12_word_vector(self):
        mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(self.KAT_FLIPS_128)
        assert " ".join(mnemonic) == self.KAT_MNEMONIC_12

    def test_coin_flip_24_word_vector(self):
        mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(self.KAT_FLIPS_256)
        assert " ".join(mnemonic) == self.KAT_MNEMONIC_24

    def test_coin_flip_entropy_is_sha256_of_flip_string(self):
        """ Independent reimplementation: entropy must be exactly SHA-256 of the
            ASCII "0"/"1" string ("Binary" mode). """
        for i in range(20):
            flips = prf_bits(f"coin-kat-{i}", 256)
            mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(flips)
            assert mnemonic_to_entropy_bytes(mnemonic) == hashlib.sha256(flips.encode()).digest()

    def test_final_word_partial_entropy(self):
        """ Coin flips select the top bits of the final word; checksum fills the rest. """
        # 7 flips (12-word seed): 1111111 + 0000 padding -> index 0b11111110000 = 2032
        assert mnemonic_generation.get_partial_final_word("1" * 7) == bip39.WORDLIST[2032]
        # 3 flips (24-word seed): 111 + 00000000 padding -> index 0b11100000000 = 1792
        assert mnemonic_generation.get_partial_final_word("1" * 3) == bip39.WORDLIST[1792]
        assert mnemonic_generation.get_partial_final_word("0" * 7) == bip39.WORDLIST[0]



class TestImageEntropyKnownAnswers(ImageEntropyTestBase):
    """ Pins the camera pipeline's exact hash chain:
        sha256(cpu_serial) -> +time -> chained preview frames -> +final image. """

    KAT_TIME = 1700000000.0
    KAT_MNEMONIC_24 = ("venue try vehicle valid uniform right weekend sustain myself unique nephew laundry "
                       "reveal upon forget fury doll resist penalty fringe glance also phrase maximum")
    KAT_MNEMONIC_12 = "venue try vehicle valid uniform right weekend sustain myself unique nephew ladder"

    @staticmethod
    def _make_kat_frames():
        preview_frames = [
            Image.frombytes("RGB", (240, 240), prf_bytes(f"camera-kat-preview-{i}", 240 * 240 * 3))
            for i in range(10)
        ]
        final_image = Image.frombytes("RGB", (720, 480), prf_bytes("camera-kat-final", 720 * 480 * 3))
        return preview_frames, final_image

    def test_image_entropy_24_word_vector(self):
        preview_frames, final_image = self._make_kat_frames()
        mnemonic = self._run_image_entropy_view(preview_frames, final_image, self.KAT_TIME, menu_selection=1)
        assert " ".join(mnemonic) == self.KAT_MNEMONIC_24

    def test_image_entropy_12_word_vector(self):
        preview_frames, final_image = self._make_kat_frames()
        mnemonic = self._run_image_entropy_view(preview_frames, final_image, self.KAT_TIME, menu_selection=0)
        assert " ".join(mnemonic) == self.KAT_MNEMONIC_12

    def test_image_entropy_hash_chain_reimplementation(self):
        """ Independent reimplementation of the full chain must match the View's output. """
        preview_frames, final_image = self._make_kat_frames()
        hash_bytes = b"0"  # no CPU serial available
        hash_bytes = hashlib.sha256(hash_bytes + str(self.KAT_TIME).encode("utf-8")).digest()
        for frame in preview_frames:
            hash_bytes = hashlib.sha256(hash_bytes + frame.tobytes()).digest()
        final_hash = hashlib.sha256(hash_bytes + final_image.tobytes()).digest()

        mnemonic = self._run_image_entropy_view(preview_frames, final_image, self.KAT_TIME, menu_selection=1)
        assert mnemonic_to_entropy_bytes(mnemonic) == final_hash


    def test_image_entropy_with_cpu_serial(self):
        """ When /proc/cpuinfo exposes a CPU serial (as on a real Pi), it must seed the
            hash chain as sha256(serial) instead of the b"0" fallback. """
        cpu_serial = "00000000a1b2c3d4"
        preview_frames, final_image = self._make_frames("serial-kat")

        hash_bytes = hashlib.sha256(cpu_serial.encode("utf-8")).digest()
        hash_bytes = hashlib.sha256(hash_bytes + str(self.KAT_TIME).encode("utf-8")).digest()
        for frame in preview_frames:
            hash_bytes = hashlib.sha256(hash_bytes + frame.tobytes()).digest()
        final_hash = hashlib.sha256(hash_bytes + final_image.tobytes()).digest()

        mnemonic = self._run_image_entropy_view(
            preview_frames, final_image, self.KAT_TIME, menu_selection=1, cpu_serial=cpu_serial)
        assert mnemonic_to_entropy_bytes(mnemonic) == final_hash

        # Same inputs without a serial must produce a different seed
        no_serial_mnemonic = self._run_image_entropy_view(
            preview_frames, final_image, self.KAT_TIME, menu_selection=1)
        assert no_serial_mnemonic != mnemonic


"""****************************************************************************
    Regression guards: entropy code paths and libraries must not silently change
****************************************************************************"""

class TestEntropyRegressionGuards:
    def test_dice_roll_counts_unchanged(self):
        """ 50 rolls ~= 129 bits, 99 rolls ~= 256 bits of raw input entropy. """
        assert mnemonic_generation.DICE__NUM_ROLLS__12WORD == 50
        assert mnemonic_generation.DICE__NUM_ROLLS__24WORD == 99

    def test_no_weak_rng_in_seed_generation_modules(self):
        """ The Mersenne Twister `random` module must never appear in any module that
            touches seed entropy. (seed_views.py's backup-verification quiz uses it
            for UI-only word shuffling and is intentionally excluded.) """
        from seedsigner.helpers import embit_utils
        from seedsigner.models import seed, seed_storage

        modules = [mnemonic_generation, seed, seed_storage, embit_utils, tools_views]
        forbidden = [
            re.compile(r"^\s*import random\b", re.MULTILINE),
            re.compile(r"^\s*from random\b", re.MULTILINE),
            re.compile(r"\brandom\.(random|randint|randrange|getrandbits|choice|shuffle|seed|uniform)\("),
        ]
        for module in modules:
            source = inspect.getsource(module)
            for pattern in forbidden:
                assert not pattern.search(source), f"weak RNG usage found in {module.__name__}"

    def test_pipelines_are_deterministic(self):
        """ Same input entropy must always yield the same mnemonic (no hidden RNG mixing). """
        rolls = prf_dice_rolls("determinism", 99)
        flips = prf_bits("determinism", 256)
        entropy = prf_bytes("determinism", 32)
        for _ in range(3):
            assert mnemonic_generation.generate_mnemonic_from_dice(rolls) == \
                   mnemonic_generation.generate_mnemonic_from_dice(rolls)
            assert mnemonic_generation.generate_mnemonic_from_coin_flips(flips) == \
                   mnemonic_generation.generate_mnemonic_from_coin_flips(flips)
            assert mnemonic_generation.generate_mnemonic_from_bytes(entropy) == \
                   mnemonic_generation.generate_mnemonic_from_bytes(entropy)

    def test_embit_entropy_roundtrip(self):
        """ embit bip39 entropy <-> mnemonic conversion must be a lossless inverse. """
        for i in range(50):
            for num_bytes in (16, 32):
                entropy = prf_bytes(f"roundtrip-{i}", num_bytes)
                mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(entropy)
                assert len(mnemonic) == 12 if num_bytes == 16 else 24
                assert bip39.mnemonic_is_valid(" ".join(mnemonic))
                assert bip39.mnemonic_to_bytes(" ".join(mnemonic)) == entropy

    def test_12_word_entropy_is_prefix_of_sha256(self):
        """ Both string-conditioned pipelines truncate the same digest for 12 words. """
        rolls50 = prf_dice_rolls("prefix-check", 50)
        assert mnemonic_to_entropy_bytes(
            mnemonic_generation.generate_mnemonic_from_dice(rolls50)
        ) == hashlib.sha256(rolls50.encode()).digest()[:16]

        flips128 = prf_bits("prefix-check", 128)
        assert mnemonic_to_entropy_bytes(
            mnemonic_generation.generate_mnemonic_from_coin_flips(flips128)
        ) == hashlib.sha256(flips128.encode()).digest()[:16]
