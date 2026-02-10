"""
Tests for DPI28 framebuffer driver pixel conversion and config parsing.

Tests the pure logic in seedsigner.hardware.DPI28 without requiring
a real framebuffer device (/dev/fb0).
"""

import sys
import struct
import pytest
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO
from PIL import Image

# Mock linux-only modules before importing DPI28
sys.modules['fcntl'] = MagicMock()

from seedsigner.hardware.DPI28 import DPI28


class TestWrite32bitPython:
    """Test _write_32bit_python() RGB to BGRA conversion."""

    def _make_driver(self):
        """Create a DPI28 instance with framebuffer init disabled."""
        with patch.object(DPI28, '_init_framebuffer'):
            driver = DPI28()
            # Set up a BytesIO as the fake framebuffer
            driver.fb = BytesIO(bytearray(480 * 640 * 4))
            driver.length = 480 * 640 * 4
            driver.bits_per_pixel = 32
            return driver

    def test_single_red_pixel(self):
        """Pure red (255,0,0) becomes BGRA (0,0,255,255)."""
        driver = self._make_driver()
        img = Image.new('RGB', (1, 1), (255, 0, 0))

        # Adjust length for tiny image
        driver.length = 4
        driver.fb = BytesIO(bytearray(4))

        driver._write_32bit_python(img)
        driver.fb.seek(0)
        b, g, r, a = struct.unpack('BBBB', driver.fb.read(4))
        assert (b, g, r, a) == (0, 0, 255, 255)

    def test_single_blue_pixel(self):
        """Pure blue (0,0,255) becomes BGRA (255,0,0,255)."""
        driver = self._make_driver()
        img = Image.new('RGB', (1, 1), (0, 0, 255))

        driver.length = 4
        driver.fb = BytesIO(bytearray(4))

        driver._write_32bit_python(img)
        driver.fb.seek(0)
        b, g, r, a = struct.unpack('BBBB', driver.fb.read(4))
        assert (b, g, r, a) == (255, 0, 0, 255)

    def test_single_green_pixel(self):
        """Pure green (0,255,0) stays BGRA (0,255,0,255) - green unchanged."""
        driver = self._make_driver()
        img = Image.new('RGB', (1, 1), (0, 255, 0))

        driver.length = 4
        driver.fb = BytesIO(bytearray(4))

        driver._write_32bit_python(img)
        driver.fb.seek(0)
        b, g, r, a = struct.unpack('BBBB', driver.fb.read(4))
        assert (b, g, r, a) == (0, 255, 0, 255)

    def test_white_pixel(self):
        """White (255,255,255) stays BGRA (255,255,255,255)."""
        driver = self._make_driver()
        img = Image.new('RGB', (1, 1), (255, 255, 255))

        driver.length = 4
        driver.fb = BytesIO(bytearray(4))

        driver._write_32bit_python(img)
        driver.fb.seek(0)
        b, g, r, a = struct.unpack('BBBB', driver.fb.read(4))
        assert (b, g, r, a) == (255, 255, 255, 255)

    def test_alpha_always_255(self):
        """Alpha channel is always 255 (fully opaque)."""
        driver = self._make_driver()
        img = Image.new('RGB', (1, 1), (42, 128, 200))

        driver.length = 4
        driver.fb = BytesIO(bytearray(4))

        driver._write_32bit_python(img)
        driver.fb.seek(0)
        data = driver.fb.read(4)
        assert data[3] == 255  # Alpha byte

    def test_multi_pixel_image(self):
        """A 2x2 image gets correctly converted pixel by pixel."""
        driver = self._make_driver()
        img = Image.new('RGB', (2, 2))
        img.putpixel((0, 0), (255, 0, 0))    # Red
        img.putpixel((1, 0), (0, 255, 0))    # Green
        img.putpixel((0, 1), (0, 0, 255))    # Blue
        img.putpixel((1, 1), (128, 64, 32))  # Mixed

        driver.length = 2 * 2 * 4
        driver.fb = BytesIO(bytearray(driver.length))

        driver._write_32bit_python(img)
        driver.fb.seek(0)
        data = driver.fb.read(driver.length)

        # Pixel (0,0): RGB(255,0,0) -> BGRA(0,0,255,255)
        assert data[0:4] == bytes([0, 0, 255, 255])
        # Pixel (1,0): RGB(0,255,0) -> BGRA(0,255,0,255)
        assert data[4:8] == bytes([0, 255, 0, 255])
        # Pixel (0,1): RGB(0,0,255) -> BGRA(255,0,0,255)
        assert data[8:12] == bytes([255, 0, 0, 255])
        # Pixel (1,1): RGB(128,64,32) -> BGRA(32,64,128,255)
        assert data[12:16] == bytes([32, 64, 128, 255])


class TestWrite16bitPython:
    """Test _write_16bit_python() RGB to RGB565 conversion."""

    def _make_driver(self):
        with patch.object(DPI28, '_init_framebuffer'):
            driver = DPI28()
            driver.bits_per_pixel = 16
            return driver

    def test_red_pixel_rgb565(self):
        """Pure red (255,0,0) encodes to RGB565 correctly."""
        driver = self._make_driver()
        img = Image.new('RGB', (1, 1), (255, 0, 0))

        driver.fb = BytesIO(bytearray(2))

        driver._write_16bit_python(img)
        driver.fb.seek(0)
        data = driver.fb.read(2)
        value = data[0] | (data[1] << 8)
        # Red: (255 & 0xF8) << 8 = 0xF800
        assert value == 0xF800

    def test_green_pixel_rgb565(self):
        """Pure green (0,255,0) encodes to RGB565 correctly."""
        driver = self._make_driver()
        img = Image.new('RGB', (1, 1), (0, 255, 0))

        driver.fb = BytesIO(bytearray(2))

        driver._write_16bit_python(img)
        driver.fb.seek(0)
        data = driver.fb.read(2)
        value = data[0] | (data[1] << 8)
        # Green: (255 & 0xFC) << 3 = 0x07E0
        assert value == 0x07E0

    def test_blue_pixel_rgb565(self):
        """Pure blue (0,0,255) encodes to RGB565 correctly."""
        driver = self._make_driver()
        img = Image.new('RGB', (1, 1), (0, 0, 255))

        driver.fb = BytesIO(bytearray(2))

        driver._write_16bit_python(img)
        driver.fb.seek(0)
        data = driver.fb.read(2)
        value = data[0] | (data[1] << 8)
        # Blue: 255 >> 3 = 0x001F
        assert value == 0x001F

    def test_black_pixel_rgb565(self):
        """Black (0,0,0) encodes to 0x0000."""
        driver = self._make_driver()
        img = Image.new('RGB', (1, 1), (0, 0, 0))

        driver.fb = BytesIO(bytearray(2))

        driver._write_16bit_python(img)
        driver.fb.seek(0)
        data = driver.fb.read(2)
        value = data[0] | (data[1] << 8)
        assert value == 0x0000


class TestReadConfig:
    """Test _read_config() sysfs file parsing."""

    def _make_driver(self):
        with patch.object(DPI28, '_init_framebuffer'):
            return DPI28()

    def test_parse_virtual_size(self):
        """Parses '480,640' into [480, 640]."""
        driver = self._make_driver()
        with patch('builtins.open', mock_open(read_data='480,640\n')):
            result = driver._read_config('/sys/class/graphics/fb0/virtual_size')
        assert result == [480, 640]

    def test_parse_single_value(self):
        """Parses '32' into [32]."""
        driver = self._make_driver()
        with patch('builtins.open', mock_open(read_data='32\n')):
            result = driver._read_config('/sys/class/graphics/fb0/bits_per_pixel')
        assert result == [32]

    def test_missing_file_returns_empty(self):
        """Missing sysfs file returns empty list."""
        driver = self._make_driver()
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = driver._read_config('/sys/class/graphics/fb0/nonexistent')
        assert result == []


class TestShowImageScaling:
    """Test that show_image() correctly scales 240x240 to 480x640."""

    def _make_driver(self):
        with patch.object(DPI28, '_init_framebuffer'):
            driver = DPI28()
            driver.fb = BytesIO(bytearray(480 * 640 * 4))
            driver.length = 480 * 640 * 4
            driver.bits_per_pixel = 32
            return driver

    def test_show_image_accepts_240x240(self):
        """show_image() works with the standard 240x240 SeedSigner image."""
        driver = self._make_driver()
        img = Image.new('RGB', (240, 240), (100, 100, 100))

        # Patch _write_to_fb to capture the composed image
        composed = []
        def capture_write(image):
            composed.append(image)
        driver._write_to_fb = capture_write

        driver.show_image(img)

        assert len(composed) == 1
        assert composed[0].size == (480, 640)

    def test_show_image_no_fb_is_noop(self):
        """show_image() does nothing when framebuffer is not initialized."""
        driver = self._make_driver()
        driver.fb = None
        img = Image.new('RGB', (240, 240))
        # Should not raise
        driver.show_image(img)


class TestTouchBarCache:
    """Test touch bar caching behavior."""

    def _make_driver(self):
        with patch.object(DPI28, '_init_framebuffer'):
            return DPI28()

    def test_same_preset_returns_cached(self):
        """Same preset returns the same cached image object."""
        driver = self._make_driver()
        bar1 = driver._get_touch_bar(DPI28.TOUCH_BAR_DEFAULT)
        bar2 = driver._get_touch_bar(DPI28.TOUCH_BAR_DEFAULT)
        assert bar1 is bar2

    def test_different_preset_creates_new(self):
        """Different preset creates a new image."""
        driver = self._make_driver()
        bar1 = driver._get_touch_bar(DPI28.TOUCH_BAR_DEFAULT)
        bar2 = driver._get_touch_bar(DPI28.TOUCH_BAR_HIDDEN)
        assert bar1 is not bar2

    def test_touch_bar_dimensions(self):
        """Touch bar image has correct dimensions (480x160)."""
        driver = self._make_driver()
        bar = driver._create_touch_bar()
        assert bar.size == (480, 160)

    def test_set_touch_bar_labels_updates(self):
        """set_touch_bar_labels() switches to new preset."""
        driver = self._make_driver()
        original = driver._touch_bar
        driver.set_touch_bar_labels(DPI28.TOUCH_BAR_KEYBOARD)
        assert driver._current_labels == DPI28.TOUCH_BAR_KEYBOARD
        assert driver._touch_bar is not original

    def test_set_touch_bar_labels_same_noop(self):
        """set_touch_bar_labels() with same preset is a no-op."""
        driver = self._make_driver()
        original = driver._touch_bar
        driver.set_touch_bar_labels(DPI28.TOUCH_BAR_DEFAULT)
        assert driver._touch_bar is original


class TestDriverConstants:
    """Test that DPI28 reports correct dimensions."""

    def _make_driver(self):
        with patch.object(DPI28, '_init_framebuffer'):
            return DPI28()

    def test_native_dimensions(self):
        """Driver reports 240x240 native size to SeedSigner."""
        driver = self._make_driver()
        assert driver.width == 240
        assert driver.height == 240

    def test_display_constants(self):
        """Display constants match Waveshare 2.8" specs."""
        assert DPI28.DISPLAY_WIDTH == 480
        assert DPI28.DISPLAY_HEIGHT == 640
        assert DPI28.UI_HEIGHT == 480
        assert DPI28.TOUCH_BAR_HEIGHT == 160
        assert DPI28.UI_HEIGHT + DPI28.TOUCH_BAR_HEIGHT == DPI28.DISPLAY_HEIGHT
