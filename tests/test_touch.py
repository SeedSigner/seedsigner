"""
Tests for TouchInput coordinate transformation and event parsing.

Tests the pure logic in seedsigner.hardware.touch without requiring
any hardware (no /dev/input, no evdev, no touchscreen).
"""

import struct
import pytest
from unittest.mock import patch, MagicMock

from seedsigner.hardware.touch import (
    TouchInput,
    TOUCH_WIDTH, TOUCH_HEIGHT,
    EV_SYN, EV_ABS, ABS_MT_TRACKING_ID, ABS_MT_POSITION_X, ABS_MT_POSITION_Y,
)


class TestTouchInputTransform:
    """Test _transform() coordinate mapping from raw touch panel to screen coords."""

    def _make_touch(self, **kwargs):
        """Create a TouchInput with device init disabled."""
        with patch.object(TouchInput, '_init_device'):
            return TouchInput(**kwargs)

    def test_center_point(self):
        """Center of touch panel maps to center of screen."""
        t = self._make_touch(screen_width=480, screen_height=640)
        x, y = t._transform(TOUCH_WIDTH // 2, TOUCH_HEIGHT // 2)
        assert x == 240
        assert y == 320

    def test_origin(self):
        """Origin (0,0) maps to (0,0)."""
        t = self._make_touch(screen_width=480, screen_height=640)
        x, y = t._transform(0, 0)
        assert x == 0
        assert y == 0

    def test_max_point(self):
        """Maximum raw coords map to near screen max."""
        t = self._make_touch(screen_width=480, screen_height=640)
        x, y = t._transform(TOUCH_WIDTH - 1, TOUCH_HEIGHT - 1)
        # Should be close to but not exceeding screen bounds
        assert 0 <= x <= 479
        assert 0 <= y <= 639

    def test_scaling(self):
        """Raw coords scale proportionally to screen dimensions."""
        t = self._make_touch(screen_width=480, screen_height=640)
        # Quarter point on touch panel
        x, y = t._transform(TOUCH_WIDTH // 4, TOUCH_HEIGHT // 4)
        assert x == 120  # 480/4
        assert y == 160  # 640/4

    def test_swap_xy(self):
        """swap_xy swaps the output coordinates."""
        t = self._make_touch(screen_width=480, screen_height=640, swap_xy=True)
        x, y = t._transform(TOUCH_WIDTH // 2, 0)
        # After scaling: x=240, y=0, then swap: x=0, y=240
        assert x == 0
        assert y == 240

    def test_invert_x(self):
        """invert_x mirrors the X axis."""
        t = self._make_touch(screen_width=480, screen_height=640, invert_x=True)
        x, y = t._transform(0, 0)
        assert x == 479  # screen_width - 1 - 0
        assert y == 0

    def test_invert_y(self):
        """invert_y mirrors the Y axis."""
        t = self._make_touch(screen_width=480, screen_height=640, invert_y=True)
        x, y = t._transform(0, 0)
        assert x == 0
        assert y == 639  # screen_height - 1 - 0

    def test_invert_both(self):
        """Both axes inverted flips the whole screen."""
        t = self._make_touch(screen_width=480, screen_height=640,
                             invert_x=True, invert_y=True)
        x, y = t._transform(0, 0)
        assert x == 479
        assert y == 639

    def test_clamping_negative(self):
        """Negative raw values get clamped to 0."""
        t = self._make_touch(screen_width=480, screen_height=640)
        x, y = t._transform(-100, -100)
        assert x == 0
        assert y == 0

    def test_clamping_overflow(self):
        """Values beyond touch panel range get clamped to screen max."""
        t = self._make_touch(screen_width=480, screen_height=640)
        x, y = t._transform(TOUCH_WIDTH * 2, TOUCH_HEIGHT * 2)
        assert x == 479
        assert y == 639


class TestTouchInputPoll:
    """Test poll() event parsing from raw Linux input_event structs."""

    def _make_touch(self):
        """Create a TouchInput with a fake fd."""
        with patch.object(TouchInput, '_init_device'):
            t = TouchInput(screen_width=480, screen_height=640)
            t.fd = 999  # Fake file descriptor
            return t

    def _make_event(self, ev_type, ev_code, ev_value):
        """Build a raw 16-byte Linux input_event struct."""
        # tv_sec(4) + tv_usec(4) + type(2) + code(2) + value(4) = 16 bytes
        return struct.pack("IIHHi", 0, 0, ev_type, ev_code, ev_value)

    def test_poll_no_device(self):
        """poll() returns None when no device is open."""
        with patch.object(TouchInput, '_init_device'):
            t = TouchInput()
            t.fd = None
            assert t.poll() is None

    def test_poll_touch_down(self):
        """Touch down event produces ('down', x, y)."""
        t = self._make_touch()
        # os.read is called per EVENT_SIZE (16 bytes) in a loop
        events = [
            self._make_event(EV_ABS, ABS_MT_TRACKING_ID, 1),   # finger down
            self._make_event(EV_ABS, ABS_MT_POSITION_X, 320),  # raw x
            self._make_event(EV_ABS, ABS_MT_POSITION_Y, 240),  # raw y
            self._make_event(EV_SYN, 0, 0),                     # sync
        ]
        with patch('select.select', return_value=([t.fd], [], [])):
            with patch('os.read', side_effect=events + [BlockingIOError()]):
                result = t.poll()
        assert result is not None
        event_type, x, y = result
        assert event_type == "down"
        assert t.touching is True

    def test_poll_touch_up(self):
        """Touch up event produces ('up', x, y)."""
        t = self._make_touch()
        t.touching = True
        events = [
            self._make_event(EV_ABS, ABS_MT_TRACKING_ID, -1),  # finger up
            self._make_event(EV_SYN, 0, 0),                     # sync
        ]
        with patch('select.select', return_value=([t.fd], [], [])):
            with patch('os.read', side_effect=events + [BlockingIOError()]):
                result = t.poll()
        assert result is not None
        event_type, x, y = result
        assert event_type == "up"
        assert t.touching is False

    def test_poll_no_data(self):
        """poll() returns None when select says no data ready."""
        t = self._make_touch()
        with patch('select.select', return_value=([], [], [])):
            assert t.poll() is None
