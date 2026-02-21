import sys
from unittest.mock import MagicMock

# Global mocks for ALL tests on macOS / non-Pi machines
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

# Mock the translate module (fixes your failing test)
sys.modules['seedsigner.helpers.translate'] = MagicMock()

print("✅ All macOS hardware + translate mocks loaded")
