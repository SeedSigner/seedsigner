import hashlib
import os
import time

import pytest
from PIL import Image

from seedsigner.helpers import camera_entropy
from seedsigner.helpers.camera_entropy import EntropyHealthError


def noisy_image(width: int = 64, height: int = 64) -> Image.Image:
    """ A well-lit, detailed capture: raw sensor noise across all bands. """
    return Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))


def flat_image(width: int = 64, height: int = 64, color=(0, 0, 0)) -> Image.Image:
    """ A capped lens / dead sensor: every pixel identical. """
    return Image.new("RGB", (width, height), color)


def near_flat_image(width: int = 64, height: int = 64) -> Image.Image:
    """ Near-total darkness: only a handful of distinct byte values. """
    pixels = bytes([i % 4 for i in range(width * height * 3)])
    return Image.frombytes("RGB", (width, height), pixels)


"""****************************************************************************
    shannon_bits_per_byte
****************************************************************************"""
def test_shannon_uniform_histogram_is_8_bits():
    assert camera_entropy.shannon_bits_per_byte([1] * 256) == pytest.approx(8.0)


def test_shannon_single_value_histogram_is_zero():
    histogram = [0] * 256
    histogram[42] = 1000
    assert camera_entropy.shannon_bits_per_byte(histogram) == pytest.approx(0.0)


def test_shannon_empty_histogram_is_zero():
    assert camera_entropy.shannon_bits_per_byte([0] * 256) == 0.0


def test_shannon_two_values_is_1_bit():
    histogram = [0] * 256
    histogram[0] = histogram[255] = 500
    assert camera_entropy.shannon_bits_per_byte(histogram) == pytest.approx(1.0)


"""****************************************************************************
    Image health checks
****************************************************************************"""
def test_noisy_image_passes_health_check():
    camera_entropy.assert_image_healthy(noisy_image())


def test_flat_black_image_is_rejected():
    with pytest.raises(EntropyHealthError):
        camera_entropy.assert_image_healthy(flat_image(color=(0, 0, 0)))


def test_flat_white_image_is_rejected():
    """ A blown-out / overexposed capture is just as degenerate as darkness. """
    with pytest.raises(EntropyHealthError):
        camera_entropy.assert_image_healthy(flat_image(color=(255, 255, 255)))


def test_near_flat_image_is_rejected():
    with pytest.raises(EntropyHealthError):
        camera_entropy.assert_image_healthy(near_flat_image())


def test_missing_image_is_rejected():
    with pytest.raises(EntropyHealthError):
        camera_entropy.assert_image_healthy(None)


def test_flat_band_is_not_masked_by_other_bands():
    """ Per-band scoring: a stuck channel must not be hidden by noisy ones. """
    noisy = noisy_image()
    r, g, _b = noisy.split()
    stuck_blue = Image.merge("RGB", (r, g, Image.new("L", noisy.size, 0)))
    bits_per_byte, _distinct = camera_entropy.analyze_image_histogram(stuck_blue)
    # Mean across bands: two good bands (~8) plus one dead band (0) -> ~5.3
    assert bits_per_byte < 6.0


"""****************************************************************************
    Preview frame health checks
****************************************************************************"""
def test_empty_preview_frames_are_rejected():
    """ Regression: the old loop iterated an empty list silently. """
    with pytest.raises(EntropyHealthError):
        camera_entropy.assert_preview_frames_healthy([])


def test_none_preview_frames_are_rejected():
    with pytest.raises(EntropyHealthError):
        camera_entropy.assert_preview_frames_healthy(None)


def test_identical_preview_frames_are_rejected():
    """ A frozen preview buffer contributes nothing but looks like N sources. """
    frame = flat_image()
    with pytest.raises(EntropyHealthError):
        camera_entropy.assert_preview_frames_healthy([frame, frame, frame])


def test_distinct_preview_frames_pass():
    camera_entropy.assert_preview_frames_healthy([noisy_image() for _ in range(4)])


def test_single_preview_frame_passes():
    camera_entropy.assert_preview_frames_healthy([noisy_image()])


"""****************************************************************************
    derive_entropy_bytes
****************************************************************************"""
def test_derive_returns_correct_lengths():
    frames = [noisy_image() for _ in range(3)]
    final = noisy_image()
    assert len(camera_entropy.derive_entropy_bytes(frames, final, num_bytes=16)) == 16
    assert len(camera_entropy.derive_entropy_bytes(frames, final, num_bytes=32)) == 32


def test_derive_rejects_invalid_length():
    with pytest.raises(ValueError):
        camera_entropy.derive_entropy_bytes([noisy_image()], noisy_image(), num_bytes=24)


def test_derive_aborts_on_degenerate_image():
    """ The whole point: a bad capture must abort, not produce a weak seed. """
    with pytest.raises(EntropyHealthError):
        camera_entropy.derive_entropy_bytes([noisy_image()], flat_image())


def test_derive_aborts_on_empty_frames():
    with pytest.raises(EntropyHealthError):
        camera_entropy.derive_entropy_bytes([], noisy_image())


def test_derive_is_not_deterministic_across_calls():
    """ Same inputs, different output: the CSPRNG step must actually be mixed in. """
    frames = [noisy_image() for _ in range(2)]
    final = noisy_image()
    results = {camera_entropy.derive_entropy_bytes(frames, final) for _ in range(8)}
    assert len(results) == 8


def test_derive_is_deterministic_when_all_sources_are_pinned(monkeypatch):
    """ With the clock and CSPRNG pinned, the chain is reproducible. """
    monkeypatch.setattr(time, "time", lambda: 1234567890.0)
    frames = [noisy_image() for _ in range(2)]
    final = noisy_image()
    kwargs = dict(cpu_serial=b"deadbeef", csprng_bytes=b"\x01" * 32)
    assert camera_entropy.derive_entropy_bytes(frames, final, **kwargs) == \
        camera_entropy.derive_entropy_bytes(frames, final, **kwargs)


def test_derive_matches_reference_hash_chain(monkeypatch):
    """ Pins the exact chain order, so any reordering is caught.

        serial -> clock -> preview frames -> final image -> CSPRNG
    """
    monkeypatch.setattr(time, "time", lambda: 1234567890.0)
    frames = [noisy_image() for _ in range(3)]
    final = noisy_image()
    serial = b"0000000012345678"
    csprng = bytes(range(32))

    expected = hashlib.sha256(serial).digest()
    expected = hashlib.sha256(expected + b"1234567890.0").digest()
    for frame in frames:
        expected = hashlib.sha256(expected + frame.tobytes()).digest()
    expected = hashlib.sha256(expected + final.tobytes()).digest()
    expected = hashlib.sha256(expected + csprng).digest()

    assert camera_entropy.derive_entropy_bytes(
        frames, final, num_bytes=32, cpu_serial=serial, csprng_bytes=csprng
    ) == expected


def test_derive_12_word_is_prefix_of_24_word(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 1234567890.0)
    frames = [noisy_image()]
    final = noisy_image()
    kwargs = dict(cpu_serial=b"abc", csprng_bytes=b"\x02" * 32)
    short = camera_entropy.derive_entropy_bytes(frames, final, num_bytes=16, **kwargs)
    long = camera_entropy.derive_entropy_bytes(frames, final, num_bytes=32, **kwargs)
    assert long[:16] == short


"""****************************************************************************
    CPU serial
****************************************************************************"""
def test_missing_cpuinfo_returns_empty_not_constant(monkeypatch):
    """ Regression: the old code fell back to the constant b'0' on any error. """
    monkeypatch.setattr(camera_entropy, "CPU_INFO_PATH", "/nonexistent/cpuinfo")
    assert camera_entropy.get_cpu_serial() == b""


def test_cpuinfo_without_serial_line_returns_empty(tmp_path, monkeypatch):
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text("processor\t: 0\nmodel name\t: ARMv6-compatible\n")
    monkeypatch.setattr(camera_entropy, "CPU_INFO_PATH", str(cpuinfo))
    assert camera_entropy.get_cpu_serial() == b""


def test_cpuinfo_serial_is_parsed(tmp_path, monkeypatch):
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text("processor\t: 0\nSerial\t\t: 00000000abcdef01\n")
    monkeypatch.setattr(camera_entropy, "CPU_INFO_PATH", str(cpuinfo))
    assert camera_entropy.get_cpu_serial() == b"00000000abcdef01"
