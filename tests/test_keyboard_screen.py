import sys
from unittest.mock import MagicMock

import pytest

# Keep this test runnable on non-Raspberry Pi hardware, including in isolation.
sys.modules.setdefault("RPi", MagicMock())
sys.modules.setdefault("RPi.GPIO", MagicMock())
sys.modules.setdefault("seedsigner.hardware.ST7789", MagicMock())
sys.modules.setdefault("picamera", MagicMock())
sys.modules.setdefault("picamera.array", MagicMock())


from seedsigner.gui.keyboard import Keyboard
from seedsigner.gui.screens import screen as screen_module
from seedsigner.gui.screens import tools_screens
from seedsigner.gui.screens.screen import KeyboardScreen, RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.tools_screens import ToolsDiceEntropyEntryScreen


class HardwareInputs:
    KEY_LEFT = 1
    KEY_RIGHT = 2
    KEY_UP = 3
    KEY_DOWN = 4
    KEY_PRESS = 5
    KEY1 = 6
    KEY2 = 7
    KEY3 = 8

    KEYS__LEFT_RIGHT_UP_DOWN = [KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN]
    KEYS__ANYCLICK = [KEY_PRESS, KEY1, KEY2, KEY3]


def make_keyboard_screen(monkeypatch, inputs, *, user_input="", confirm_inputs=None,
                         return_after_n_chars=1, show_save_button=False):
    monkeypatch.setattr(screen_module, "HardwareButtonsConstants", HardwareInputs)

    screen = object.__new__(KeyboardScreen)
    screen.user_input = user_input
    screen.key_confirm_inputs = (
        confirm_inputs if confirm_inputs is not None else [HardwareInputs.KEY_PRESS]
    )
    screen.return_after_n_chars = return_after_n_chars
    screen.show_save_button = show_save_button
    screen.keys_to_values = {"die": "1"}

    screen.hw_inputs = MagicMock()
    screen.hw_inputs.wait_for.side_effect = inputs

    screen.top_nav = MagicMock()
    screen.top_nav.is_selected = False

    screen.keyboard = MagicMock()
    screen.text_entry_display = MagicMock()
    screen.renderer = MagicMock()
    screen.update_title = MagicMock(return_value=False)

    if show_save_button:
        screen.save_button = MagicMock()

    return screen


def test_dice_screen_enables_anyclick_confirmation(monkeypatch):
    monkeypatch.setattr(screen_module, "HardwareButtonsConstants", HardwareInputs)
    monkeypatch.setattr(tools_screens, "HardwareButtonsConstants", HardwareInputs)

    # Skip the real GUI construction; only the input configuration matters here.
    monkeypatch.setattr(KeyboardScreen, "__post_init__", lambda self: None)

    screen = ToolsDiceEntropyEntryScreen(return_after_n_chars=50)

    assert screen.key_confirm_inputs == HardwareInputs.KEYS__ANYCLICK


@pytest.mark.parametrize(
    "confirm_input",
    [HardwareInputs.KEY_PRESS, HardwareInputs.KEY1, HardwareInputs.KEY2, HardwareInputs.KEY3],
)
def test_any_click_locks_in_the_highlighted_die(monkeypatch, confirm_input):
    screen = make_keyboard_screen(
        monkeypatch,
        inputs=[confirm_input],
        confirm_inputs=HardwareInputs.KEYS__ANYCLICK,
    )
    screen.keyboard.update_from_input.return_value = "die"

    assert screen._run() == "1"

    waited_for_keys = screen.hw_inputs.wait_for.call_args_list[0].args[0]
    assert HardwareInputs.KEY1 in waited_for_keys
    assert HardwareInputs.KEY2 in waited_for_keys
    assert HardwareInputs.KEY3 in waited_for_keys
    assert HardwareInputs.KEY_PRESS in waited_for_keys


def test_default_keyboard_confirms_with_joystick_press_only(monkeypatch):
    monkeypatch.setattr(screen_module, "HardwareButtonsConstants", HardwareInputs)

    default_factory = KeyboardScreen.__dataclass_fields__["key_confirm_inputs"].default_factory
    assert default_factory() == [HardwareInputs.KEY_PRESS]

    screen = make_keyboard_screen(monkeypatch, inputs=[HardwareInputs.KEY_PRESS])
    screen.keyboard.update_from_input.return_value = "die"

    assert screen._run() == "1"

    waited_for_keys = screen.hw_inputs.wait_for.call_args_list[0].args[0]
    assert HardwareInputs.KEY1 not in waited_for_keys
    assert HardwareInputs.KEY2 not in waited_for_keys
    assert HardwareInputs.KEY3 not in waited_for_keys


def test_side_button_returns_back_when_top_nav_is_selected(monkeypatch):
    screen = make_keyboard_screen(
        monkeypatch,
        inputs=[HardwareInputs.KEY2],
        confirm_inputs=HardwareInputs.KEYS__ANYCLICK,
    )
    screen.top_nav.is_selected = True

    assert screen._run() == RET_CODE__BACK_BUTTON
    screen.keyboard.update_from_input.assert_not_called()


def test_side_button_still_deletes_when_backspace_is_highlighted(monkeypatch):
    screen = make_keyboard_screen(
        monkeypatch,
        inputs=[HardwareInputs.KEY3, HardwareInputs.KEY1],
        user_input="12",
        confirm_inputs=HardwareInputs.KEYS__ANYCLICK,
        return_after_n_chars=2,
    )
    screen.keyboard.update_from_input.side_effect = [
        Keyboard.KEY_BACKSPACE["code"],
        "die",
    ]

    assert screen._run() == "11"


def test_show_save_button_still_uses_key3(monkeypatch):
    screen = make_keyboard_screen(
        monkeypatch,
        inputs=[HardwareInputs.KEY3],
        user_input="42",
        return_after_n_chars=10,
        show_save_button=True,
    )

    assert screen._run() == "42"
    assert screen.save_button.is_selected is True
    screen.save_button.render.assert_called_once_with()

    waited_for_keys = screen.hw_inputs.wait_for.call_args_list[0].args[0]
    assert HardwareInputs.KEY3 in waited_for_keys
