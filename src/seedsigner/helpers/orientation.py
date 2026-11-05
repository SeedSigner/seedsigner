"""
How far the whole interface is turned: 0 (as designed) or 180 degrees.

With the device turned upside down, the joystick sits under the right hand and
the three buttons under the left. Turning the picture 180° keeps everything
upright for the user; the joystick directions are swapped to match
(see hardware/buttons.py) and the camera preview is turned with the screen
(see hardware/camera.py). The three side buttons need nothing: their on-screen
labels turn with the picture and stay next to them.
"""
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants


def display_rotation() -> int:
    try:
        return int(Settings.get_instance().get_value(SettingsConstants.SETTING__DISPLAY_ROTATION))
    except Exception:
        return 0


def is_turned() -> bool:
    return display_rotation() == SettingsConstants.DISPLAY_ROTATION__180
