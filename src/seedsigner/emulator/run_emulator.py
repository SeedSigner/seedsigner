"""
SeedSigner Touchscreen Emulator

Runs SeedSigner with mocked Raspberry Pi hardware for PC development.

Usage:
    python run_emulator.py [--slow]

Options:
    --slow    Simulate Pi framebuffer speed (~7fps, 143ms per frame)

Requirements:
    pip install pillow pygame numpy embit pyzbar urtypes

Controls:
    - Click to touch
    - ESC to quit
"""

import sys
import os

# Set environment BEFORE any imports
os.environ['SEEDSIGNER_DISPLAY'] = 'dpi28'
os.environ['SEEDSIGNER_TOUCH'] = '1'

# Add src to path (emulator is in src/seedsigner/emulator, so go up 3 levels)
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if os.path.exists(src_path):
    sys.path.insert(0, src_path)


# =============================================================================
# Mock Raspberry Pi Hardware
# =============================================================================

class MockGPIO:
    """Mock RPi.GPIO module"""
    BOARD = 10
    BCM = 11
    IN = 1
    OUT = 0
    HIGH = 1
    LOW = 0
    PUD_UP = 22
    PUD_DOWN = 21
    RISING = 31
    FALLING = 32
    BOTH = 33

    RPI_INFO = {'P1_REVISION': 3, 'RAM': '1G', 'MANUFACTURER': 'Emulator'}

    @classmethod
    def setmode(cls, mode): pass

    @classmethod
    def setwarnings(cls, warn): pass

    @classmethod
    def setup(cls, pin, mode, pull_up_down=None, initial=None): pass

    @classmethod
    def output(cls, pin, state): pass

    @classmethod
    def input(cls, pin):
        return cls.HIGH

    @classmethod
    def add_event_detect(cls, pin, edge, callback=None, bouncetime=None): pass

    @classmethod
    def remove_event_detect(cls, pin): pass

    @classmethod
    def event_detected(cls, pin):
        return False

    @classmethod
    def cleanup(cls, pin=None): pass


# Install GPIO mock
mock_rpi = type(sys)('RPi')
mock_rpi.GPIO = MockGPIO
sys.modules['RPi'] = mock_rpi
sys.modules['RPi.GPIO'] = MockGPIO


class MockSpiDev:
    """Mock spidev module"""
    def __init__(self, bus=0, device=0):
        pass

    def open(self, bus, device): pass
    def close(self): pass
    def writebytes(self, data): pass
    def writebytes2(self, data): pass
    def readbytes(self, n): return [0] * n
    def xfer(self, data): return [0] * len(data)
    def xfer2(self, data): return [0] * len(data)


mock_spidev = type(sys)('spidev')
mock_spidev.SpiDev = MockSpiDev
sys.modules['spidev'] = mock_spidev


# Mock picamera
class MockPiCamera:
    def __init__(self, resolution=None, framerate=None):
        self.resolution = resolution or (480, 480)
        self.framerate = framerate or 30

    def start_preview(self): pass
    def stop_preview(self): pass
    def capture(self, output, format=None, use_video_port=False): pass
    def close(self): pass
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class MockPiRGBArray:
    def __init__(self, camera, size=None):
        import numpy as np
        size = size or camera.resolution
        self.array = np.zeros((size[1], size[0], 3), dtype=np.uint8)

    def truncate(self, size=0): pass
    def seek(self, pos): pass


mock_picamera = type(sys)('picamera')
mock_picamera.PiCamera = MockPiCamera
mock_picamera.__path__ = []
sys.modules['picamera'] = mock_picamera

mock_picamera_array = type(sys)('picamera.array')
mock_picamera_array.PiRGBArray = MockPiRGBArray
mock_picamera.array = mock_picamera_array
sys.modules['picamera.array'] = mock_picamera_array


class MockPiVideoStream:
    """Mock video stream that returns gray frames"""
    def __init__(self, resolution=(320, 240), framerate=32, **kwargs):
        import numpy as np
        self.resolution = resolution
        self.frame = np.full((resolution[1], resolution[0], 3), 40, dtype=np.uint8)

    def start(self): return self
    def read(self): return self.frame
    def stop(self): pass


mock_pivideostream = type(sys)('seedsigner.hardware.pivideostream')
mock_pivideostream.PiVideoStream = MockPiVideoStream
sys.modules['seedsigner.hardware.pivideostream'] = mock_pivideostream


# =============================================================================
# Pygame-based Display and Touch Emulation
# =============================================================================

import pygame
from PIL import Image, ImageDraw, ImageFont
import threading
import time

# Global pygame state
_pygame_screen = None
_pygame_lock = threading.Lock()
_touch_events = []
_pending_touch_event = None  # Store touch event detected during ShowImage for poll() to pick up

# Emulation settings
_emulate_slow_framebuffer = False  # Set via --slow flag
_frame_delay_ms = 143  # ~7fps like real Pi framebuffer


def _init_pygame():
    global _pygame_screen
    if _pygame_screen is None:
        pygame.init()
        _pygame_screen = pygame.display.set_mode((480, 640))
        pygame.display.set_caption("SeedSigner Touchscreen Emulator")


class EmulatedDPI28:
    """Emulates DPI28 framebuffer display using pygame"""

    NATIVE_WIDTH = 240
    NATIVE_HEIGHT = 240
    DISPLAY_WIDTH = 480
    DISPLAY_HEIGHT = 640
    UI_HEIGHT = 480
    TOUCH_BAR_HEIGHT = 160

    # Touch bar label presets: (labels_tuple, colors_tuple) - same as DPI28
    TOUCH_BAR_DEFAULT = (('▲', 'SELECT', '▼'), ('#ff9416', '#ff9416', '#ff9416'))  # All active (orange)
    TOUCH_BAR_UP_DISABLED = (('▲', 'SELECT', '▼'), ('#444444', '#ff9416', '#ff9416'))  # At top of list
    TOUCH_BAR_DOWN_DISABLED = (('▲', 'SELECT', '▼'), ('#ff9416', '#ff9416', '#444444'))  # At bottom of list
    TOUCH_BAR_SELECT_ONLY = (('', 'SELECT', ''), ('#1a1a1a', '#ff9416', '#1a1a1a'))  # Only SELECT visible
    TOUCH_BAR_KEYBOARD = (('DEL', 'WORD', '▼'), ('#444444', '#444444', '#ff9416'))  # DEL/WORD inactive, down active
    TOUCH_BAR_KEYBOARD_DOWN_DISABLED = (('DEL', 'WORD', '▼'), ('#444444', '#444444', '#444444'))  # All inactive (at bottom)
    TOUCH_BAR_KEYBOARD_WORD_ACTIVE = (('DEL', 'WORD', '▼'), ('#444444', '#ff9416', '#ff9416'))  # WORD active, DEL grey
    TOUCH_BAR_KEYBOARD_DEL_ACTIVE = (('DEL', 'WORD', '▼'), ('#ff9416', '#444444', '#ff9416'))  # DEL active, WORD grey
    TOUCH_BAR_KEYBOARD_BOTH_ACTIVE = (('DEL', 'WORD', '▼'), ('#ff9416', '#ff9416', '#ff9416'))  # All active (orange)
    TOUCH_BAR_KEYBOARD_BOTH_ACTIVE_DOWN_DISABLED = (('DEL', 'WORD', '▼'), ('#ff9416', '#ff9416', '#444444'))  # DEL/WORD active, down grey
    TOUCH_BAR_HIDDEN = (('', '', ''), ('#1a1a1a', '#1a1a1a', '#1a1a1a'))  # All buttons hidden

    def __init__(self, fb_device=None):
        self.width = self.NATIVE_WIDTH
        self.height = self.NATIVE_HEIGHT
        self._current_labels = self.TOUCH_BAR_DEFAULT
        self._touch_bar_cache = {}
        self._touch_bar = self._get_touch_bar(self.TOUCH_BAR_DEFAULT)
        _init_pygame()
        print("[Emulator] Display initialized (480x640)")

    def _get_touch_bar(self, preset: tuple) -> Image.Image:
        """Get touch bar from cache or create new one"""
        if preset not in self._touch_bar_cache:
            self._touch_bar_cache[preset] = self._create_touch_bar(preset)
        return self._touch_bar_cache[preset]

    def set_touch_bar_labels(self, preset: tuple):
        """Set the touch bar labels"""
        if preset != self._current_labels:
            self._current_labels = preset
            self._touch_bar = self._get_touch_bar(preset)

    def _create_touch_bar(self, preset: tuple = None) -> Image.Image:
        """Create the touch bar with custom labels and colors"""
        if preset is None:
            preset = self.TOUCH_BAR_DEFAULT

        labels, colors = preset

        bar = Image.new('RGB', (self.DISPLAY_WIDTH, self.TOUCH_BAR_HEIGHT), '#1a1a1a')
        draw = ImageDraw.Draw(bar)

        btn_width = self.DISPLAY_WIDTH // 3
        btn_height = 100
        btn_y = (self.TOUCH_BAR_HEIGHT - btn_height) // 2

        for i, (label, color) in enumerate(zip(labels, colors)):
            x = i * btn_width
            draw.rounded_rectangle(
                [x + 10, btn_y, x + btn_width - 10, btn_y + btn_height],
                radius=15,
                fill=color
            )
            # Use black text on orange buttons, white on grey
            text_color = 'black' if color == '#ff9416' else 'white'
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), label, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_x = x + (btn_width - text_w) // 2
            text_y = btn_y + (btn_height - text_h) // 2
            draw.text((text_x, text_y), label, fill=text_color, font=font)

        return bar

    def show_image(self, image: Image.Image, x: int = 0, y: int = 0):
        global _pygame_screen, _emulate_slow_framebuffer, _frame_delay_ms

        # Scale 240x240 -> 480x480
        scaled = image.resize((self.UI_HEIGHT, self.UI_HEIGHT), Image.NEAREST)

        # Create full display
        display = Image.new('RGB', (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT))
        display.paste(scaled, (0, 0))
        display.paste(self._touch_bar, (0, self.UI_HEIGHT))

        # Simulate slow framebuffer if enabled
        if _emulate_slow_framebuffer:
            time.sleep(_frame_delay_ms / 1000.0)

        # Blit to pygame
        with _pygame_lock:
            global _pending_touch_event
            # Process pygame events to keep window responsive (especially during screensaver)
            # Also capture mouse clicks so has_any_input() can detect them
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    os._exit(0)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    _pending_touch_event = ('down', event.pos[0], event.pos[1])
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    _pending_touch_event = ('up', event.pos[0], event.pos[1])
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    os._exit(0)

            data = display.tobytes()
            surface = pygame.image.fromstring(data, display.size, 'RGB')
            _pygame_screen.blit(surface, (0, 0))
            pygame.display.flip()

    def clear(self):
        global _pygame_screen
        with _pygame_lock:
            _pygame_screen.fill((0, 0, 0))
            pygame.display.flip()


class EmulatedTouchInput:
    """Emulates evdev touch input using pygame mouse"""

    def __init__(self, device_path=None, screen_width=480, screen_height=640, **kwargs):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x = 0
        self.y = 0
        self.touching = False
        _init_pygame()
        print("[Emulator] Touch input initialized (mouse emulation)")

    def poll(self):
        """Poll for touch events"""
        global _pending_touch_event

        # First check for events captured during ShowImage (for screensaver wake)
        if _pending_touch_event is not None:
            event_type, x, y = _pending_touch_event
            _pending_touch_event = None
            self.x, self.y = x, y
            if event_type == 'down':
                self.touching = True
            elif event_type == 'up':
                self.touching = False
            return (event_type, x, y)

        result = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("[Emulator] Window closed")
                pygame.quit()
                os._exit(0)  # Force exit to avoid thread hangs

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.x, self.y = event.pos
                self.touching = True
                result = ('down', self.x, self.y)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.touching = False
                result = ('up', self.x, self.y)

            elif event.type == pygame.MOUSEMOTION and self.touching:
                self.x, self.y = event.pos
                result = ('move', self.x, self.y)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    print("[Emulator] ESC pressed")
                    pygame.quit()
                    os._exit(0)  # Force exit to avoid thread hangs

        return result

    def close(self): pass


# =============================================================================
# Patch SeedSigner Modules
# =============================================================================

def patch_seedsigner():
    """Replace hardware modules with emulated versions"""

    # Force DPI28 display configuration in settings
    try:
        from seedsigner.models.settings import Settings
        from seedsigner.models.settings_definition import SettingsConstants
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__DISPLAY_CONFIGURATION,
                          SettingsConstants.DISPLAY_CONFIGURATION__DPI28__240x240)
        print("[Emulator] Set display to DPI28")
    except Exception as e:
        print(f"[Emulator] Warning: Could not set display config: {e}")

    # Patch DPI28
    try:
        import seedsigner.hardware.DPI28 as dpi_module
        dpi_module.DPI28 = EmulatedDPI28
        print("[Emulator] Patched DPI28")
    except ImportError as e:
        print(f"[Emulator] Warning: Could not patch DPI28: {e}")

    # Patch touch input
    try:
        import seedsigner.hardware.touch as touch_module
        touch_module.TouchInput = EmulatedTouchInput
        print("[Emulator] Patched TouchInput")
    except ImportError as e:
        print(f"[Emulator] Warning: Could not patch touch: {e}")


# =============================================================================
# Main
# =============================================================================

def main():
    global _emulate_slow_framebuffer

    # Parse arguments
    if '--slow' in sys.argv:
        _emulate_slow_framebuffer = True

    print("=" * 60)
    print("SeedSigner Touchscreen Emulator")
    print("=" * 60)
    print()
    if _emulate_slow_framebuffer:
        print("Mode: SLOW (simulating ~7fps Pi framebuffer)")
    else:
        print("Mode: FAST (use --slow to simulate Pi speed)")
    print()
    print("Controls:")
    print("  - Click to touch")
    print("  - ESC to quit")
    print()

    # Check dependencies
    deps = ['numpy', 'embit', 'pyzbar', 'urtypes']
    missing = []
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)

    if missing:
        print(f"[Error] Missing dependencies: {', '.join(missing)}")
        print(f"Run: pip install {' '.join(missing)}")
        sys.exit(1)

    # Apply patches
    patch_seedsigner()

    try:
        from seedsigner.controller import Controller

        print("[Emulator] Starting SeedSigner...")
        print("-" * 60)

        controller = Controller.get_instance()
        controller.start()

    except KeyboardInterrupt:
        print("\n[Emulator] Interrupted by user")
        pygame.quit()
        sys.exit(0)

    except ImportError as e:
        print(f"\n[Error] Could not import SeedSigner: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    except Exception as e:
        print(f"\n[Error] {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
