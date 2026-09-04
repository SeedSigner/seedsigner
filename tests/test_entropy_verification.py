import random

from PIL import Image

from seedsigner.helpers import entropy_verification



def _random_rolls(num_rolls: int, seed: int = 0) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("123456") for _ in range(num_rolls))



class TestDiceEntropy:
    def test_honest_rolls_pass(self):
        """ Fair, independent rolls at the standard counts should pass the verdict. """
        for num_rolls, mnemonic_length in [(50, 12), (99, 24)]:
            for seed in range(25):
                rolls = _random_rolls(num_rolls, seed=seed)
                result = entropy_verification.assess_dice_entropy(rolls, mnemonic_length)
                assert result.passed, f"honest {num_rolls}-roll entry flagged (seed={seed})"


    def test_cyclic_pattern_fails(self):
        """ 123456123456... has flat face counts but must fail: the Markov
            estimate is ~0 and the pattern detector fires. """
        for num_rolls, mnemonic_length in [(50, 12), (99, 24)]:
            rolls = ("123456" * 20)[:num_rolls]
            result = entropy_verification.assess_dice_entropy(rolls, mnemonic_length)
            assert not result.passed
            assert result.pattern_detected
            assert entropy_verification.effective_dice_entropy_bits(rolls) < 1.0


    def test_repeated_face_fails(self):
        result = entropy_verification.assess_dice_entropy("1" * 99, 24)
        assert not result.passed
        assert entropy_verification.dice_shannon_entropy_bits("1" * 99) == 0.0


    def test_alternating_pair_fails(self):
        result = entropy_verification.assess_dice_entropy(("12" * 50)[:99], 24)
        assert not result.passed


    def test_heavily_biased_die_fails(self):
        """ A die rolling one face ~55% of the time lands below the verdict floor. """
        rng = random.Random(42)
        rolls = "".join(rng.choices("123456", weights=[60, 8, 8, 8, 8, 8])[0] for _ in range(99))
        result = entropy_verification.assess_dice_entropy(rolls, 24)
        assert not result.passed


    def test_markov_estimate_is_conservative_for_patterns(self):
        """ The frequency estimate is fooled by cyclic input; the Markov
            estimate must not be. """
        rolls = ("123456" * 17)[:99]
        freq = entropy_verification.dice_shannon_entropy_bits(rolls)
        markov = entropy_verification.dice_markov_entropy_bits(rolls)
        assert freq > 250.0     # flat face counts look near-perfect
        assert markov < 1.0     # every roll is determined by the previous one


    def test_degenerate_inputs(self):
        assert entropy_verification.dice_shannon_entropy_bits("") == 0.0
        assert entropy_verification.dice_markov_entropy_bits("3") <= entropy_verification.dice_shannon_entropy_bits("3") + 1e-9
        assert not entropy_verification.dice_pattern_detected("5")



class TestImageEntropy:
    @staticmethod
    def _noise_image(width: int = 320, height: int = 240, seed: int = 0) -> Image.Image:
        rng = random.Random(seed)
        return Image.frombytes("RGB", (width, height), bytes(rng.getrandbits(8) for _ in range(width * height * 3)))


    def test_noisy_capture_passes(self):
        result = entropy_verification.assess_image_entropy(self._noise_image())
        assert result.quality == entropy_verification.EntropyQuality.GOOD
        assert result.passed


    def test_flat_capture_fails(self):
        """ Lens cap / uniform wall: no pixel variety. """
        flat = Image.new("RGB", (320, 240), (128, 128, 128))
        result = entropy_verification.assess_image_entropy(flat)
        assert result.quality == entropy_verification.EntropyQuality.INSUFFICIENT
        assert not result.passed


    def test_identical_frames_fail(self):
        """ A frozen/replayed sensor produces a scene that can look perfect
            but zero temporal noise between back-to-back frames. """
        frame = self._noise_image(seed=1)
        result = entropy_verification.assess_image_entropy(frame, noise_reference_frame=frame.copy())
        assert result.noise_bits_per_pixel == 0.0
        assert result.frames_suspiciously_identical
        assert result.quality == entropy_verification.EntropyQuality.INSUFFICIENT


    def test_distinct_frames_pass(self):
        """ Two captures differing by per-pixel noise: sensor noise must be
            detected and the verdict remain GOOD. """
        result = entropy_verification.assess_image_entropy(
            self._noise_image(seed=2), noise_reference_frame=self._noise_image(seed=3))
        assert result.noise_bits_per_pixel > entropy_verification.INSUFFICIENT_NOISE_BITS_PER_PIXEL_TH
        assert result.quality == entropy_verification.EntropyQuality.GOOD


    def test_identical_frames_score_exactly_zero_noise(self):
        """ Regression: PIL concatenates per-band histograms; if they are
            pooled without merging bins, band identity contributes log2(3)
            phantom bits and identical frames score ~1.58 instead of 0. """
        frame = self._noise_image(seed=4)
        assert entropy_verification.frame_noise_entropy_bits_per_pixel(frame, frame.copy()) == 0.0


    def test_no_noise_frame_is_backward_compatible(self):
        result = entropy_verification.assess_image_entropy(self._noise_image(seed=5))
        assert result.noise_bits_per_pixel is None
        assert not result.frames_suspiciously_identical
