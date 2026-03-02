import os
import platform
import sys
from unittest.mock import MagicMock

# Global mocks for hardware modules not available on dev machines.
# The project's tests/base.py mocks SeedSigner-level modules; these mock
# the underlying RPi hardware so that imports succeed before base.py runs.
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['board'] = MagicMock()
sys.modules['digitalio'] = MagicMock()
sys.modules['adafruit_ssd1306'] = MagicMock()
sys.modules['spidev'] = MagicMock()
sys.modules['smbus'] = MagicMock()
sys.modules['smbus2'] = MagicMock()
sys.modules['gpiozero'] = MagicMock()
sys.modules['numpy'] = MagicMock()

# On macOS with Homebrew, ctypes.util.find_library('zbar') returns None even
# when the library is installed, because Homebrew ARM installs to /opt/homebrew
# which is outside the default library search paths. Patch find_library so that
# pyzbar can find the shared library during tests.
if platform.system() == 'Darwin':
    import ctypes.util
    _orig_find_library = ctypes.util.find_library
    def _patched_find_library(name):
        result = _orig_find_library(name)
        if result is None and name == 'zbar':
            # Try Homebrew ARM and Intel paths
            for path in ['/opt/homebrew/lib/libzbar.dylib', '/usr/local/lib/libzbar.dylib']:
                if os.path.exists(path):
                    return path
        return result
    ctypes.util.find_library = _patched_find_library
