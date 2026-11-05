"""
Display rotation: the whole interface turned 180° (SETTING__DISPLAY_ROTATION), so
the device can be held with the joystick under the right hand.

The rest of the suite replaces the renderer and the buttons with mocks
(tests/base.py), so this file loads the real modules straight from their
source files under their own names, with a stand-in for RPi.GPIO, whatever
order the tests run in.
"""
import importlib.util
import sys
import types
from pathlib import Path

from PIL import Image

from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition


SRC = Path(__file__).resolve().parents[1] / "src" / "seedsigner"


def _fake_gpio(pressed_pin=None):
    gpio = types.ModuleType("RPi.GPIO")
    gpio.RPI_INFO = {"P1_REVISION": 3}
    gpio.LOW, gpio.HIGH = 0, 1
    gpio.BOARD, gpio.IN, gpio.PUD_UP = 10, 1, 22
    gpio.setmode = gpio.setup = lambda *a, **k: None
    gpio.input = lambda pin: gpio.LOW if pin == pressed_pin else gpio.HIGH
    return gpio


def _load(name, rel_path):
    spec = importlib.util.spec_from_file_location(name, SRC / rel_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_buttons():
    rpi = types.ModuleType("RPi")
    rpi.GPIO = _fake_gpio()
    saved = {k: sys.modules.get(k) for k in ("RPi", "RPi.GPIO")}
    sys.modules["RPi"], sys.modules["RPi.GPIO"] = rpi, rpi.GPIO
    try:
        return _load("_real_buttons", "hardware/buttons.py")
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def _set_rotation(value):
    Settings.get_instance().set_value(SettingsConstants.SETTING__DISPLAY_ROTATION, value)


def test_setting_is_off_by_default():
    entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__DISPLAY_ROTATION)
    assert entry.default_value == SettingsConstants.DISPLAY_ROTATION__0
    assert entry.visibility == SettingsConstants.VISIBILITY__HARDWARE
    assert [v for v, _ in entry.selection_options] == [0, 180]


def test_is_turned_follows_the_setting():
    from seedsigner.helpers.orientation import is_turned, display_rotation
    _set_rotation(SettingsConstants.DISPLAY_ROTATION__0)
    assert not is_turned() and display_rotation() == 0
    _set_rotation(SettingsConstants.DISPLAY_ROTATION__180)
    assert is_turned() and display_rotation() == 180
    # A SettingsQR or a saved settings file may carry it as text
    _set_rotation("180")
    assert is_turned()


def test_renderer_turns_the_whole_picture():
    renderer = _load("_real_renderer", "gui/renderer.py")
    img = Image.new("RGB", (2, 2), "black")
    img.putpixel((0, 0), (255, 0, 0))   # red at top left

    _set_rotation(SettingsConstants.DISPLAY_ROTATION__180)
    out = renderer.Renderer._turned(img)
    assert out.size == img.size
    assert out.getpixel((1, 1)) == (255, 0, 0)   # ends up bottom right
    assert out.getpixel((0, 0)) == (0, 0, 0)

    _set_rotation(SettingsConstants.DISPLAY_ROTATION__0)
    assert renderer.Renderer._turned(img) is img   # untouched, not even copied


def test_joystick_directions_swap_and_side_keys_stay():
    buttons = _load_buttons()
    c = buttons.HardwareButtonsConstants

    _set_rotation(SettingsConstants.DISPLAY_ROTATION__180)
    wiring = buttons.HardwareButtons._wiring()
    assert wiring == {c.KEY_UP: c.KEY_DOWN, c.KEY_DOWN: c.KEY_UP, c.KEY_LEFT: c.KEY_RIGHT, c.KEY_RIGHT: c.KEY_LEFT}
    for key in (c.KEY_PRESS, c.KEY1, c.KEY2, c.KEY3):
        assert key not in wiring

    _set_rotation(SettingsConstants.DISPLAY_ROTATION__0)
    assert buttons.HardwareButtons._wiring() == {}


def test_pushing_towards_the_users_top_reads_as_up_when_turned():
    buttons = _load_buttons()
    c = buttons.HardwareButtonsConstants
    hb = buttons.HardwareButtons.__new__(buttons.HardwareButtons)
    hb.last_input_time = 0

    # Turned: the user pushes towards the top of what they see, which closes
    # the switch the board calls DOWN.
    hb.GPIO = _fake_gpio(pressed_pin=c.KEY_DOWN)
    _set_rotation(SettingsConstants.DISPLAY_ROTATION__180)
    assert hb.check_for_low(key=c.KEY_UP)
    assert not hb.check_for_low(key=c.KEY_DOWN)

    # Not turned: the same switch is plain DOWN again.
    _set_rotation(SettingsConstants.DISPLAY_ROTATION__0)
    assert hb.check_for_low(key=c.KEY_DOWN)
    assert not hb.check_for_low(key=c.KEY_UP)

    # A side button is the same switch either way.
    hb.GPIO = _fake_gpio(pressed_pin=c.KEY1)
    for value in (0, 180):
        _set_rotation(value)
        assert hb.check_for_low(key=c.KEY1)


def test_camera_picture_turns_with_the_screen():
    camera = _load("_real_camera", "hardware/camera.py")
    _set_rotation(SettingsConstants.DISPLAY_ROTATION__180)
    assert camera.Camera._display_turn() == 180
    _set_rotation(SettingsConstants.DISPLAY_ROTATION__0)
    assert camera.Camera._display_turn() == 0
