"""
Unit tests for Keyboard navigation, including skip-over-inactive (grayed-out) keys.

These tests exercise the pure navigation logic with a small in-memory keyboard and
do not require Raspberry Pi hardware.
"""
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

# Must import test base before most SeedSigner modules (mocks hardware deps).
from base import BaseTest

from seedsigner.gui.keyboard import Keyboard
from seedsigner.hardware.buttons import HardwareButtonsConstants


def _dummy_font(*args, **kwargs):
    """Avoid depending on packaged .ttf/.otf paths in CI/dev machines."""
    return ImageFont.load_default()


class TestKeyboardNavigation(BaseTest):
    """
    Layout under test (3x3 letter grid, no additional keys for clarity):

        a b c
        d e f
        g h i

    After deactivating b, e, h (middle column), usable keys are:
        a   c
        d   f
        g   i
    """

    def _make_keyboard(self, charset="abcdefghi", selected="e", rows=3, cols=3):
        image = Image.new("RGB", (240, 240), "black")
        draw = ImageDraw.Draw(image)
        with patch("seedsigner.gui.keyboard.Fonts.get_font", side_effect=_dummy_font):
            kb = Keyboard(
                draw=draw,
                charset=charset,
                selected_char=selected,
                rows=rows,
                cols=cols,
                rect=(0, 0, 240, 240),
                additional_keys=[],
                auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
                render_now=True,
            )
        return kb

    def _code(self, kb) -> str:
        return kb.get_selected_key().code

    def _usable(self, kb) -> bool:
        key = kb.get_selected_key()
        return key is not None and (key.is_active or key.is_additional_key)

    def test_right_skips_inactive_in_same_row(self):
        kb = self._make_keyboard(selected="a")
        # Deactivate b so a → right should land on c
        kb.update_active_keys(active_keys=list("acdefghi"))  # no b
        kb.render_keys()

        kb.set_selected_key("a")
        result = kb.update_from_input(HardwareButtonsConstants.KEY_RIGHT)

        assert result == "c"
        assert self._code(kb) == "c"
        assert self._usable(kb)

    def test_left_skips_inactive_in_same_row(self):
        kb = self._make_keyboard(selected="c")
        kb.update_active_keys(active_keys=list("acdefghi"))  # no b
        kb.render_keys()

        kb.set_selected_key("c")
        result = kb.update_from_input(HardwareButtonsConstants.KEY_LEFT)

        assert result == "a"
        assert self._code(kb) == "a"
        assert self._usable(kb)

    def test_down_goes_to_nearest_usable_not_strict_column(self):
        """
        From 'b' (inactive neighbors in column), with middle column deactivated,
        down from 'a' should reach a usable key in a lower row near that x —
        e.g. 'd' (not jump unpredictably or exit).
        """
        kb = self._make_keyboard(selected="a")
        # Deactivate entire middle column: b, e, h
        kb.update_active_keys(active_keys=list("acdfgi"))
        kb.render_keys()

        kb.set_selected_key("a")
        result = kb.update_from_input(HardwareButtonsConstants.KEY_DOWN)

        assert result not in Keyboard.EXIT_DIRECTIONS
        assert self._usable(kb)
        # Nearest usable in the next row to column of 'a' (x=0) is 'd'
        assert self._code(kb) == "d"

    def test_up_goes_to_nearest_usable(self):
        kb = self._make_keyboard(selected="g")
        kb.update_active_keys(active_keys=list("acdfgi"))  # no b,e,h
        kb.render_keys()

        kb.set_selected_key("g")
        result = kb.update_from_input(HardwareButtonsConstants.KEY_UP)

        assert result not in Keyboard.EXIT_DIRECTIONS
        assert self._usable(kb)
        assert self._code(kb) == "d"

    def test_never_lands_on_inactive_key(self):
        kb = self._make_keyboard(selected="a")
        # Only corners active
        kb.update_active_keys(active_keys=list("acgi"))
        kb.render_keys()

        kb.set_selected_key("a")
        path = ["a"]
        # Crawl around the keyboard; every stop must be usable
        for direction in [
            HardwareButtonsConstants.KEY_RIGHT,
            HardwareButtonsConstants.KEY_DOWN,
            HardwareButtonsConstants.KEY_LEFT,
            HardwareButtonsConstants.KEY_UP,
            HardwareButtonsConstants.KEY_RIGHT,
            HardwareButtonsConstants.KEY_RIGHT,
            HardwareButtonsConstants.KEY_DOWN,
            HardwareButtonsConstants.KEY_LEFT,
        ]:
            ret = kb.update_from_input(direction)
            if ret in Keyboard.EXIT_DIRECTIONS:
                # Re-enter from the opposite edge if we exited
                if ret == Keyboard.EXIT_TOP:
                    kb.update_from_input(Keyboard.ENTER_TOP)
                elif ret == Keyboard.EXIT_BOTTOM:
                    kb.update_from_input(Keyboard.ENTER_BOTTOM)
                elif ret == Keyboard.EXIT_LEFT:
                    kb.update_from_input(Keyboard.ENTER_LEFT)
                elif ret == Keyboard.EXIT_RIGHT:
                    kb.update_from_input(Keyboard.ENTER_RIGHT)
            assert self._usable(kb), f"Landed on unusable key after {direction}; path={path}"
            path.append(self._code(kb))

    def test_wrap_right_to_left_within_row_skips_inactive(self):
        kb = self._make_keyboard(selected="c")
        # Row 0: a b c — deactivate a so wrapping from c goes... only c is active
        # in that row if a and b inactive; stay or wrap to only usable.
        kb.update_active_keys(active_keys=list("cdefghi"))  # no a, b
        kb.render_keys()

        kb.set_selected_key("c")
        # Right from c with WRAP_RIGHT should wrap; a and b inactive → only c in row
        # so we stay on c (no other usable in row after full scan)
        result = kb.update_from_input(HardwareButtonsConstants.KEY_RIGHT)
        assert result not in Keyboard.EXIT_DIRECTIONS
        assert self._code(kb) == "c"
        assert self._usable(kb)

    def test_active_neighbor_still_one_step(self):
        """With all keys active, right from a is still b (no over-skip)."""
        kb = self._make_keyboard(selected="a")
        kb.update_active_keys(active_keys=list("abcdefghi"))
        kb.render_keys()

        kb.set_selected_key("a")
        result = kb.update_from_input(HardwareButtonsConstants.KEY_RIGHT)
        assert result == "b"
        assert self._code(kb) == "b"
