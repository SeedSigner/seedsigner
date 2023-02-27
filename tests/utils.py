import sys
from mock import MagicMock

# Prevent importing modules w/Raspi hardware dependencies
sys.modules['seedsigner.gui.renderer'] = MagicMock()
sys.modules['seedsigner.gui.screens.screensaver'] = MagicMock()
sys.modules['seedsigner.hardware.buttons'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()

from seedsigner.controller import Controller


def reset_controller():
    Controller._instance = None
    Controller.configure_instance()
