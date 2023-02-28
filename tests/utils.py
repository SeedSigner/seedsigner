import sys
from mock import MagicMock

# Prevent importing modules w/Raspi hardware dependencies
sys.modules['seedsigner.gui.renderer'] = MagicMock()
sys.modules['seedsigner.gui.screens.screensaver'] = MagicMock()
sys.modules['seedsigner.hardware.buttons'] = MagicMock()
sys.modules['seedsigner.hardware.camera'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()

from seedsigner.controller import Controller


def reset_controller():
    """ Wipe and re-initialize the Controller singleton for each test run """
    Controller._instance = None
    Controller.configure_instance()
