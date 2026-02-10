"""
Tests for TouchButtons coordinate-to-key mapping and button hit detection.

Tests the pure logic in seedsigner.hardware.touchbuttons without requiring
any hardware or the full SeedSigner stack.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Mock hardware dependencies before importing TouchButtons
sys.modules['seedsigner.hardware.touch'] = MagicMock()

from seedsigner.hardware.touchbuttons import (
    TouchButtons,
    HardwareButtonsConstants,
    get_buttons,
)


class TestCoordsToNavKey:
    """Test _coords_to_nav_key() mapping of screen coordinates to key codes."""

    def _make_buttons(self):
        """Create a TouchButtons instance with mocked touch device."""
        # Reset singleton
        TouchButtons._instance = None
        tb = TouchButtons.get_instance()
        return tb

    # --- Touch bar (y >= 480) maps to KEY1/KEY2/KEY3 ---

    def test_touch_bar_left(self):
        """Left third of touch bar returns KEY1."""
        tb = self._make_buttons()
        assert tb._coords_to_nav_key(80, 560) == tb.KEY1

    def test_touch_bar_center(self):
        """Center third of touch bar returns KEY2."""
        tb = self._make_buttons()
        assert tb._coords_to_nav_key(240, 560) == tb.KEY2

    def test_touch_bar_right(self):
        """Right third of touch bar returns KEY3."""
        tb = self._make_buttons()
        assert tb._coords_to_nav_key(400, 560) == tb.KEY3

    def test_touch_bar_boundary(self):
        """Exactly at touch bar top (y=480) maps to touch bar."""
        tb = self._make_buttons()
        key = tb._coords_to_nav_key(240, 480)
        assert key == tb.KEY2

    # --- UI area top 20% (y < 96 of 480) maps to KEY_UP ---

    def test_ui_top_center(self):
        """Top center of UI area returns KEY_UP."""
        tb = self._make_buttons()
        assert tb._coords_to_nav_key(240, 40) == tb.KEY_UP

    def test_ui_top_left(self):
        """Top left of UI area still returns KEY_UP."""
        tb = self._make_buttons()
        assert tb._coords_to_nav_key(20, 40) == tb.KEY_UP

    # --- UI area bottom 40% (y > 288 of 480) ---

    def test_ui_bottom_center(self):
        """Bottom center of UI area returns KEY_DOWN."""
        tb = self._make_buttons()
        # y > 0.60 * 480 = 288, center x (0.25 < px < 0.75)
        assert tb._coords_to_nav_key(240, 400) == tb.KEY_DOWN

    def test_ui_bottom_left(self):
        """Bottom left of UI area returns KEY_LEFT."""
        tb = self._make_buttons()
        # y > 288, px < 0.25 (x < 120)
        assert tb._coords_to_nav_key(50, 400) == tb.KEY_LEFT

    def test_ui_bottom_right(self):
        """Bottom right of UI area returns KEY_RIGHT."""
        tb = self._make_buttons()
        # y > 288, px > 0.75 (x > 360)
        assert tb._coords_to_nav_key(430, 400) == tb.KEY_RIGHT

    # --- UI area middle 40% (96 <= y <= 288) ---

    def test_ui_center(self):
        """Center of UI area returns KEY_PRESS (select)."""
        tb = self._make_buttons()
        # 0.20 < py < 0.60, 0.25 < px < 0.75
        assert tb._coords_to_nav_key(240, 200) == tb.KEY_PRESS

    def test_ui_middle_left(self):
        """Middle left of UI area returns KEY_LEFT."""
        tb = self._make_buttons()
        # 0.20 < py < 0.60, px < 0.25
        assert tb._coords_to_nav_key(50, 200) == tb.KEY_LEFT

    def test_ui_middle_right(self):
        """Middle right of UI area returns KEY_RIGHT."""
        tb = self._make_buttons()
        # 0.20 < py < 0.60, px > 0.75
        assert tb._coords_to_nav_key(430, 200) == tb.KEY_RIGHT


class TestBackAndPowerButtons:
    """Test corner tap detection for back and power buttons."""

    def _make_buttons(self):
        TouchButtons._instance = None
        return TouchButtons.get_instance()

    # --- Back button (top-left, native < 48x48 = screen < 96x96) ---

    def test_back_button_top_left_corner(self):
        """Tap at (10, 10) hits back button."""
        tb = self._make_buttons()
        assert tb._check_back_button_tap(10, 10) is True

    def test_back_button_at_boundary(self):
        """Tap at native (47, 47) = screen (94, 94) still hits."""
        tb = self._make_buttons()
        assert tb._check_back_button_tap(94, 94) is True

    def test_back_button_miss_right(self):
        """Tap at screen (200, 10) misses back button."""
        tb = self._make_buttons()
        assert tb._check_back_button_tap(200, 10) is False

    def test_back_button_miss_below(self):
        """Tap at screen (10, 200) misses back button."""
        tb = self._make_buttons()
        assert tb._check_back_button_tap(10, 200) is False

    # --- Power button (top-right, native y < 48 and x > 192) ---

    def test_power_button_top_right(self):
        """Tap at screen (460, 10) hits power button."""
        tb = self._make_buttons()
        assert tb._check_power_button_tap(460, 10) is True

    def test_power_button_miss_left(self):
        """Tap at screen (200, 10) misses power button."""
        tb = self._make_buttons()
        assert tb._check_power_button_tap(200, 10) is False

    def test_power_button_miss_below(self):
        """Tap at screen (460, 200) misses power button."""
        tb = self._make_buttons()
        assert tb._check_power_button_tap(460, 200) is False


class TestButtonTapDetection:
    """Test _check_button_tap() with registered button rectangles."""

    def _make_buttons(self):
        TouchButtons._instance = None
        return TouchButtons.get_instance()

    def _mock_button(self, screen_x, screen_y, width, height):
        """Create a mock button object with position attributes."""
        btn = MagicMock()
        btn.screen_x = screen_x
        btn.screen_y = screen_y
        btn.width = width
        btn.height = height
        btn.scroll_y = 0
        return btn

    def test_no_buttons_registered(self):
        """Returns -1 when no buttons are registered."""
        tb = self._make_buttons()
        assert tb._check_button_tap(240, 240) == -1

    def test_tap_hits_button(self):
        """Tap inside a registered button returns its index."""
        tb = self._make_buttons()
        # Register a button at native (60, 60) with size 120x40
        btn = self._mock_button(60, 60, 120, 40)
        tb.register_buttons([btn])
        # Tap at screen (240, 160) = native (120, 80), inside the button
        assert tb._check_button_tap(240, 160) == 0

    def test_tap_misses_button(self):
        """Tap outside registered buttons returns -1."""
        tb = self._make_buttons()
        btn = self._mock_button(60, 60, 120, 40)
        tb.register_buttons([btn])
        # Tap at screen (20, 20) = native (10, 10), above the button
        assert tb._check_button_tap(20, 20) == -1

    def test_tap_in_touch_bar_ignored(self):
        """Taps in touch bar area (y >= 480) always return -1."""
        tb = self._make_buttons()
        btn = self._mock_button(0, 0, 240, 240)
        tb.register_buttons([btn])
        assert tb._check_button_tap(240, 500) == -1

    def test_multiple_buttons(self):
        """With multiple buttons, correct index is returned."""
        tb = self._make_buttons()
        btn0 = self._mock_button(0, 60, 240, 40)
        btn1 = self._mock_button(0, 110, 240, 40)
        btn2 = self._mock_button(0, 160, 240, 40)
        tb.register_buttons([btn0, btn1, btn2])
        # Tap on btn1: native (120, 130) = screen (240, 260)
        assert tb._check_button_tap(240, 260) == 1

    def test_clear_buttons(self):
        """clear_buttons() removes all registered buttons."""
        tb = self._make_buttons()
        btn = self._mock_button(60, 60, 120, 40)
        tb.register_buttons([btn])
        tb.clear_buttons()
        assert tb._check_button_tap(240, 160) == -1
        assert tb.get_tapped_button_index() == -1


class TestTapStateReadAndReset:
    """Test that tap state flags reset after being read."""

    def _make_buttons(self):
        TouchButtons._instance = None
        return TouchButtons.get_instance()

    def test_tapped_button_index_resets(self):
        """get_tapped_button_index() returns value then resets to -1."""
        tb = self._make_buttons()
        tb._tapped_button_index = 2
        assert tb.get_tapped_button_index() == 2
        assert tb.get_tapped_button_index() == -1

    def test_back_button_tapped_resets(self):
        """was_back_button_tapped() returns True then resets."""
        tb = self._make_buttons()
        tb._back_button_tapped = True
        assert tb.was_back_button_tapped() is True
        assert tb.was_back_button_tapped() is False

    def test_power_button_tapped_resets(self):
        """was_power_button_tapped() returns True then resets."""
        tb = self._make_buttons()
        tb._power_button_tapped = True
        assert tb.was_power_button_tapped() is True
        assert tb.was_power_button_tapped() is False

    def test_touch_bar_back_tapped_resets(self):
        """was_touch_bar_back_tapped() returns True then resets."""
        tb = self._make_buttons()
        tb._touch_bar_back_tapped = True
        assert tb.was_touch_bar_back_tapped() is True
        assert tb.was_touch_bar_back_tapped() is False

    def test_last_tap_native_coords_resets(self):
        """get_last_tap_native_coords() returns coords then resets to (-1, -1)."""
        tb = self._make_buttons()
        tb._last_tap_native_x = 100
        tb._last_tap_native_y = 50
        assert tb.get_last_tap_native_coords() == (100, 50)
        assert tb.get_last_tap_native_coords() == (-1, -1)

    def test_clear_pending_input(self):
        """clear_pending_input() resets all state."""
        tb = self._make_buttons()
        tb._tapped_button_index = 3
        tb._back_button_tapped = True
        tb._power_button_tapped = True
        tb._touch_bar_back_tapped = True
        tb._last_tap_native_x = 100
        tb._last_tap_native_y = 50
        tb.touch_down = True

        # touch.poll() must return None to break the drain loop
        tb.touch.poll.return_value = None

        tb.clear_pending_input()

        assert tb._tapped_button_index == -1
        assert tb._back_button_tapped is False
        assert tb._power_button_tapped is False
        assert tb._touch_bar_back_tapped is False
        assert tb._last_tap_native_x == -1
        assert tb._last_tap_native_y == -1
        assert tb.touch_down is False


class TestGetButtonsFactory:
    """Test the get_buttons() factory function."""

    def test_returns_touchbuttons_when_env_set(self):
        """With SEEDSIGNER_TOUCH=1, returns TouchButtons."""
        TouchButtons._instance = None
        with patch.dict(os.environ, {'SEEDSIGNER_TOUCH': '1'}):
            buttons = get_buttons()
            assert isinstance(buttons, TouchButtons)

    def test_returns_hardwarebuttons_when_env_unset(self):
        """Without SEEDSIGNER_TOUCH, returns HardwareButtons (mocked)."""
        # Mock the HardwareButtons import since RPi.GPIO isn't available
        mock_hw_buttons = MagicMock()
        mock_hw_instance = MagicMock()
        mock_hw_buttons.HardwareButtons.get_instance.return_value = mock_hw_instance
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict(sys.modules, {'seedsigner.hardware.buttons': mock_hw_buttons}):
                buttons = get_buttons()
                assert not isinstance(buttons, TouchButtons)
