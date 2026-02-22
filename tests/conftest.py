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
