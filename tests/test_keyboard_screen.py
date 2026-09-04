import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

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


def make_keyboard_screen(monkeypatch, inputs, *, user_input="", confirm_inputs=None,
                         return_after_n_chars=1, show_save_button=False):
    monkeypatch.setattr(screen_module, "HardwareButtonsConstants", HardwareInputs)

    screen = object.__new__(KeyboardScreen)
    screen.user_input = user_input
    screen.key_confirm_inputs = confirm_inputs or [HardwareInputs.KEY_PRESS]
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
    screen.render_key_confirmation_feedback = MagicMock()
    screen.update_title = MagicMock(return_value=False)

    if show_save_button:
        screen.save_button = MagicMock()

    return screen


def test_dedicated_key1_confirms_die_and_joystick_press_does_not(monkeypatch):
    screen = make_keyboard_screen(
        monkeypatch,
        inputs=[HardwareInputs.KEY_PRESS, HardwareInputs.KEY1],
        confirm_inputs=[HardwareInputs.KEY1],
    )
    screen.keyboard.update_from_input.side_effect = ["die", "die"]

    assert screen._run() == "1"
    screen.render_key_confirmation_feedback.assert_called_once_with()

    waited_for_keys = screen.hw_inputs.wait_for.call_args_list[0].args[0]
    assert HardwareInputs.KEY1 in waited_for_keys
    assert HardwareInputs.KEY2 not in waited_for_keys
    assert HardwareInputs.KEY3 not in waited_for_keys


def test_dice_screen_renders_key1_confirm_without_narrowing_grid(monkeypatch):
    monkeypatch.setattr(screen_module, "HardwareButtonsConstants", HardwareInputs)
    monkeypatch.setattr(tools_screens, "HardwareButtonsConstants", HardwareInputs)

    def fake_keyboard_post_init(screen):
        screen.canvas_width = 240
        screen.top_nav = SimpleNamespace(height=48)
        screen.text_entry_display = SimpleNamespace(rect=(8, 48, 232, 78))
        screen.keyboard = SimpleNamespace(rect=(8, 86, 232, 231))
        screen.components = []
        screen.renderer = MagicMock()

    def fake_icon_button(**kwargs):
        return SimpleNamespace(height=32, **kwargs)

    monkeypatch.setattr(KeyboardScreen, "__post_init__", fake_keyboard_post_init)
    monkeypatch.setattr(tools_screens, "IconButton", fake_icon_button)

    screen = ToolsDiceEntropyEntryScreen(return_after_n_chars=50)

    assert screen.key_confirm_inputs == [HardwareInputs.KEY1]
    assert screen.text_entry_display.rect == (8, 48, 180, 78)
    assert screen.keyboard.rect == (8, 86, 232, 231)
    assert (
        screen.confirm_button.screen_x,
        screen.confirm_button.screen_y,
        screen.confirm_button.width,
        screen.confirm_button.height,
    ) == (188, 48, 60, 32)


def test_key1_is_ignored_for_delete_but_joystick_press_deletes(monkeypatch):
    screen = make_keyboard_screen(
        monkeypatch,
        inputs=[HardwareInputs.KEY1, HardwareInputs.KEY_PRESS, HardwareInputs.KEY1],
        user_input="12",
        confirm_inputs=[HardwareInputs.KEY1],
        return_after_n_chars=2,
    )
    screen.keyboard.update_from_input.side_effect = [
        Keyboard.KEY_BACKSPACE["code"],
        Keyboard.KEY_BACKSPACE["code"],
        "die",
    ]

    assert screen._run() == "11"
    screen.render_key_confirmation_feedback.assert_called_once_with()


def test_key1_is_ignored_for_back_but_joystick_press_goes_back(monkeypatch):
    screen = make_keyboard_screen(
        monkeypatch,
        inputs=[HardwareInputs.KEY1, HardwareInputs.KEY_PRESS],
        confirm_inputs=[HardwareInputs.KEY1],
    )
    screen.top_nav.is_selected = True

    assert screen._run() == RET_CODE__BACK_BUTTON
    screen.keyboard.update_from_input.assert_not_called()


def test_default_keyboard_still_confirms_with_joystick_press(monkeypatch):
    screen = make_keyboard_screen(
        monkeypatch,
        inputs=[HardwareInputs.KEY_PRESS],
    )
    screen.keyboard.update_from_input.return_value = "die"

    assert screen._run() == "1"


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
