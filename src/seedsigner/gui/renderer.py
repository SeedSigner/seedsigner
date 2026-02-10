import logging
import os
from PIL import Image, ImageDraw
from threading import Lock

logger = logging.getLogger(__name__)

from seedsigner.hardware.displays.display_driver import ALL_DISPLAY_TYPES, DISPLAY_TYPE__DPI28, DISPLAY_TYPE__ILI9341, DISPLAY_TYPE__ILI9486, DISPLAY_TYPE__ST7789, DisplayDriver
# Note: ili9341 import removed - was causing crash on ST7789/DPI28 due to RPi.GPIO import at module level
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.models.singleton import ConfigurableSingleton


def _detect_display_type() -> str:
    """
    Auto-detect display type based on hardware.

    Returns 'dpi28' if Waveshare 2.8" DPI LCD is detected.
    Can be overridden by SEEDSIGNER_DISPLAY environment variable.
    """
    # Allow manual override
    env_display = os.environ.get('SEEDSIGNER_DISPLAY')
    if env_display:
        return env_display

    # Auto-detect DPI LCD by checking framebuffer
    try:
        # Check if framebuffer exists with expected size for DPI LCD (480x640)
        if os.path.exists('/dev/fb0'):
            with open('/sys/class/graphics/fb0/virtual_size', 'r') as f:
                size = f.read().strip()
                if size == '480,640':
                    logger.info("Auto-detected DPI28 framebuffer (480x640)")
                    return 'dpi28'
    except (IOError, FileNotFoundError):
        pass

    return None  # Let Settings decide


def _detect_touch_mode() -> bool:
    """
    Auto-detect if touch input is available.

    Returns True if capacitive touch device is found, False otherwise.
    Can be overridden by SEEDSIGNER_TOUCH environment variable.
    """
    # Allow manual override
    env_touch = os.environ.get("SEEDSIGNER_TOUCH")
    if env_touch:
        return env_touch == "1"

    # If DPI28 display is detected, assume touch is available
    # (the DPI28 Waveshare display includes integrated touch)
    if _detect_display_type() == "dpi28":
        logger.info("DPI28 display detected - enabling touch mode")
        return True

    # Auto-detect touch input device via sysfs (no evdev needed)
    try:
        for i in range(10):
            name_path = f"/sys/class/input/event{i}/device/name"
            try:
                with open(name_path, "r") as f:
                    name = f.read().strip()
                    # Look for common touch device names
                    if any(keyword in name.lower() for keyword in ["touch", "goodix", "ft5", "edt-ft5"]):
                        logger.info(f"Auto-detected touch device: {name}")
                        return True
            except (IOError, FileNotFoundError):
                continue
    except Exception:
        pass

    return False

# Auto-detect touch mode
TOUCH_MODE = _detect_touch_mode()

# Set environment variable so other modules can check it
if TOUCH_MODE and 'SEEDSIGNER_TOUCH' not in os.environ:
    os.environ['SEEDSIGNER_TOUCH'] = '1'

# Check for auto-detected DPI28 display
_auto_detected_display = _detect_display_type()
if _auto_detected_display == 'dpi28' and 'SEEDSIGNER_DISPLAY' not in os.environ:
    os.environ['SEEDSIGNER_DISPLAY'] = 'dpi28'


class Renderer(ConfigurableSingleton):
    buttons = None
    canvas_width = 0
    canvas_height = 0
    canvas: Image.Image = None
    draw: ImageDraw.ImageDraw = None
    disp = None
    lock = Lock()


    @property
    def is_screenshot_generator(self) -> bool:
        return False


    @classmethod
    def configure_instance(cls):
        # Instantiate the one and only Renderer instance
        renderer = cls.__new__(cls)
        cls._instance = renderer

        renderer.initialize_display()


    def initialize_display(self):
        # May be called while already running with a previous display driver; must
        # prevent any other screen writes while we're changing the display driver.
        self.lock.acquire()
        try:
            # Check for auto-detected display first
            env_display = os.environ.get("SEEDSIGNER_DISPLAY")
            if env_display == "dpi28":
                display_config = "dpi28_240x240"
                logger.info("Using auto-detected DPI28 display")
            else:
                display_config = Settings.get_instance().get_value(SettingsConstants.SETTING__DISPLAY_CONFIGURATION, default_if_none=True)
            self.display_type = display_config.split("_")[0]
            if self.display_type not in ALL_DISPLAY_TYPES:
                raise Exception(f"Invalid display type: {self.display_type}")

            width, height = display_config.split("_")[1].split("x")
            self.disp = DisplayDriver(self.display_type, width=int(width), height=int(height))

            if Settings.get_instance().get_value(SettingsConstants.SETTING__DISPLAY_COLOR_INVERTED, default_if_none=True) == SettingsConstants.OPTION__ENABLED:
                self.disp.invert()

            if self.display_type in [DISPLAY_TYPE__ST7789, DISPLAY_TYPE__DPI28]:
                # ST7789 and DPI28 both report 240x240 native size
                self.canvas_width = self.disp.width
                self.canvas_height = self.disp.height

            elif self.display_type in [DISPLAY_TYPE__ILI9341, DISPLAY_TYPE__ILI9486]:
                # Swap for the natively portrait-oriented displays
                self.canvas_width = self.disp.height
                self.canvas_height = self.disp.width

            self.canvas = Image.new('RGB', (self.canvas_width, self.canvas_height))
            self.draw = ImageDraw.Draw(self.canvas)
        finally:
            self.lock.release()


    def show_image(self, image=None, alpha_overlay=None, show_direct=False):
        if show_direct:
            # Use the incoming image as the canvas and immediately render
            self.disp.show_image(image, 0, 0)
            return

        if alpha_overlay:
            if image == None:
                image = self.canvas
            image = Image.alpha_composite(image, alpha_overlay)

        if image:
            # Always write to the current canvas, rather than trying to replace it
            self.canvas.paste(image)

        self.disp.show_image(self.canvas, 0, 0)


    def show_image_pan(self, image, start_x, start_y, end_x, end_y, rate, alpha_overlay=None):
        cur_x = start_x
        cur_y = start_y
        rate_x = rate
        rate_y = rate
        if end_x - start_x < 0:
            rate_x = rate_x * -1
        if end_y - start_y < 0:
            rate_y = rate_y * -1

        while (cur_x != end_x or cur_y != end_y) and (rate_x != 0 or rate_y != 0):
            cur_x += rate_x
            if (rate_x > 0 and cur_x > end_x) or (rate_x < 0 and cur_x < end_x):
                # We've moved too far; back up and undo that last move.
                cur_x -= rate_x
                rate_x = 0

            cur_y += rate_y
            if (rate_y > 0 and cur_y > end_y) or (rate_y < 0 and cur_y < end_y):
                # We've moved too far; back up and undo that last move.
                cur_y -= rate_y
                rate_y = 0

            crop = image.crop((cur_x, cur_y, cur_x + self.canvas_width, cur_y + self.canvas_height))

            if alpha_overlay:
                crop = Image.alpha_composite(crop, alpha_overlay)

            # Always keep a copy of the current display in the canvas
            self.canvas.paste(crop)

            self.disp.show_image(crop, 0, 0)



    def display_blank_screen(self):
        self.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)
        self.show_image()


    def set_touch_bar_labels(self, labels: tuple):
        """
        Set the touch bar labels for DPI28 display.

        Args:
            labels: Tuple from DPI28 touch bar presets (e.g., TOUCH_BAR_DEFAULT, TOUCH_BAR_KEYBOARD)
        """
        if self.display_type == DISPLAY_TYPE__DPI28 and hasattr(self.disp.display, 'set_touch_bar_labels'):
            self.disp.display.set_touch_bar_labels(labels)
