"""
DPI28 - Framebuffer display driver for Waveshare 2.8" DPI LCD.

Display specs:
- 480x640 resolution (portrait)
- DPI interface (uses GPIO, not SPI)
- Directly writes to /dev/fb0 framebuffer
- 32-bit BGRA format (requires RGB→BGR swap)

Layout:
- Top 480x480: UI area (240x240 scaled 2x)
- Bottom 480x160: Touch bar (KEY1, KEY2, KEY3)

Based on mutatrum's fast-pillow-fb approach:
https://github.com/mutatrum/fast-pillow-fb

"""

import logging
import os
import mmap
import fcntl
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Linux console mode constants for hiding tty text on framebuffer
KD_TEXT = 0x00
KD_GRAPHICS = 0x01
KDSETMODE = 0x4B3A

# Try to import numpy for faster conversion (~7 fps vs ~1 fps pure Python)
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.info("numpy not available, using slow Python conversion")

# Cython disabled - pyximport hangs on Pi Zero
HAS_CYTHON = False

# Icon constants from SeedSigner icon fonts (language-agnostic)
class TouchBarIcons:
    # From seedsigner-icons.otf
    CHEVRON_UP = "\ue90b"
    CHEVRON_DOWN = "\ue908"
    CHEVRON_LEFT = "\ue909"
    CHECK = "\ue905"
    DELETE = "\ue922"
    BACK = "\ue904"
    # From FontAwesome
    KEYBOARD = "\uf11c"


class DPI28:
    """
    Framebuffer display driver for Waveshare 2.8" DPI LCD.

    Accepts 240x240 images (SeedSigner native), scales to 480x480,
    and adds a 160px touch bar at the bottom.
    
    Uses mmap for fast framebuffer writes and handles RGB→BGR conversion
    required by the Raspberry Pi framebuffer.
    """

    # Native UI size (what SeedSigner renders)
    NATIVE_WIDTH = 240
    NATIVE_HEIGHT = 240

    # Physical display size
    DISPLAY_WIDTH = 480
    DISPLAY_HEIGHT = 640

    # Scaled UI area
    UI_WIDTH = 480
    UI_HEIGHT = 480

    # Touch bar
    TOUCH_BAR_HEIGHT = 160

    # Touch bar label presets: (icons_tuple, colors_tuple, font_types_tuple)
    _UP = TouchBarIcons.CHEVRON_UP
    _DOWN = TouchBarIcons.CHEVRON_DOWN
    _BACK = TouchBarIcons.BACK
    _SELECT = TouchBarIcons.CHECK
    _DEL = TouchBarIcons.DELETE
    _WORD = TouchBarIcons.KEYBOARD

    TOUCH_BAR_DEFAULT = ((_UP, _SELECT, _DOWN), ('#ff9416', '#ff9416', '#ff9416'), ('seedsigner', 'seedsigner', 'seedsigner'))
    TOUCH_BAR_UP_DISABLED = ((_UP, _SELECT, _DOWN), ('#444444', '#ff9416', '#ff9416'), ('seedsigner', 'seedsigner', 'seedsigner'))
    TOUCH_BAR_DOWN_DISABLED = ((_UP, _SELECT, _DOWN), ('#ff9416', '#ff9416', '#444444'), ('seedsigner', 'seedsigner', 'seedsigner'))
    TOUCH_BAR_SELECT_ONLY = (('', _SELECT, ''), ('#1a1a1a', '#ff9416', '#1a1a1a'), ('seedsigner', 'seedsigner', 'seedsigner'))
    TOUCH_BAR_KEYBOARD = ((_DEL, _WORD, _DOWN), ('#444444', '#444444', '#ff9416'), ('seedsigner', 'fontawesome', 'seedsigner'))
    TOUCH_BAR_KEYBOARD_DOWN_DISABLED = ((_DEL, _WORD, _DOWN), ('#444444', '#444444', '#444444'), ('seedsigner', 'fontawesome', 'seedsigner'))
    TOUCH_BAR_KEYBOARD_WORD_ACTIVE = ((_DEL, _WORD, _DOWN), ('#444444', '#ff9416', '#ff9416'), ('seedsigner', 'fontawesome', 'seedsigner'))
    TOUCH_BAR_KEYBOARD_DEL_ACTIVE = ((_DEL, _WORD, _DOWN), ('#ff9416', '#444444', '#ff9416'), ('seedsigner', 'fontawesome', 'seedsigner'))
    TOUCH_BAR_KEYBOARD_BOTH_ACTIVE = ((_DEL, _WORD, _DOWN), ('#ff9416', '#ff9416', '#ff9416'), ('seedsigner', 'fontawesome', 'seedsigner'))
    TOUCH_BAR_KEYBOARD_BOTH_ACTIVE_DOWN_DISABLED = ((_DEL, _WORD, _DOWN), ('#ff9416', '#ff9416', '#444444'), ('seedsigner', 'fontawesome', 'seedsigner'))
    TOUCH_BAR_HIDDEN = (('', '', ''), ('#1a1a1a', '#1a1a1a', '#1a1a1a'), ('seedsigner', 'seedsigner', 'seedsigner'))
    TOUCH_BAR_BACK = ((_BACK, '', ''), ('#ff9416', '#1a1a1a', '#1a1a1a'), ('seedsigner', 'seedsigner', 'seedsigner'))
    TOUCH_BAR_QR_BRIGHTNESS = ((_UP, _SELECT, _DOWN), ('#ff9416', '#ff9416', '#ff9416'), ('seedsigner', 'seedsigner', 'seedsigner'))

    def __init__(self, device_no: int = 0):
        """
        Initialize the framebuffer display.

        Args:
            device_no: Framebuffer device number (0 for /dev/fb0)
        """
        # Report 240x240 to SeedSigner (native rendering size)
        self.width = self.NATIVE_WIDTH
        self.height = self.NATIVE_HEIGHT

        self.device_no = device_no
        self.fb_path = f"/dev/fb{device_no}"
        self.config_dir = f"/sys/class/graphics/fb{device_no}/"
        
        self.fb = None
        self.fb_file = None
        self.fb_size = None
        self.bits_per_pixel = None
        self.stride = None
        self.length = None
        self.tty_fd = None  # For console mode control

        # Current touch bar labels
        self._current_labels = self.TOUCH_BAR_DEFAULT

        # Cache touch bars for different label sets
        self._touch_bar_cache = {}
        self._touch_bar = self._get_touch_bar(self.TOUCH_BAR_DEFAULT)

        # Initialize framebuffer
        self._init_framebuffer()

    def _read_config(self, filename: str) -> list:
        """Read framebuffer config from sysfs"""
        try:
            with open(filename, "r") as fp:
                content = fp.readline()
                tokens = content.strip().split(",")
                return [int(t) for t in tokens if t]
        except Exception as e:
            logger.warning(f"Could not read {filename}: {e}")
            return []

    def _init_framebuffer(self):
        """Initialize framebuffer with mmap for fast access"""
        try:
            # Read framebuffer configuration
            size_config = self._read_config(self.config_dir + "virtual_size")
            if len(size_config) >= 2:
                self.fb_size = (size_config[0], size_config[1])
            else:
                # Fallback to expected size
                self.fb_size = (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT)
            
            bpp_config = self._read_config(self.config_dir + "bits_per_pixel")
            self.bits_per_pixel = bpp_config[0] if bpp_config else 32
            
            stride_config = self._read_config(self.config_dir + "stride")
            self.stride = stride_config[0] if stride_config else (self.bits_per_pixel // 8 * self.fb_size[0])
            
            # Calculate buffer length
            self.length = self.fb_size[0] * self.fb_size[1] * (self.bits_per_pixel // 8)
            
            logger.info(f"Framebuffer: {self.fb_path}")
            logger.info(f"Size: {self.fb_size}, BPP: {self.bits_per_pixel}, Stride: {self.stride}")
            logger.info(f"Using: {'Cython' if HAS_CYTHON else 'numpy' if HAS_NUMPY else 'Python'} conversion")
            
            # Open and mmap the framebuffer
            self.fb_file = open(self.fb_path, "r+b")
            self.fb = mmap.mmap(self.fb_file.fileno(), length=self.length, access=mmap.ACCESS_WRITE)

            # Switch console to graphics mode to hide tty text (login prompt, etc.)
            self._hide_console_text()

        except Exception as e:
            logger.error(f"Could not initialize framebuffer: {e}")
            self.close()
            self.fb = None

    def _hide_console_text(self):
        """
        Switch the console to graphics mode to hide tty text on the framebuffer.

        This prevents the Linux login prompt and other console text from appearing
        over the SeedSigner graphics. Uses KDSETMODE ioctl to switch tty0 to KD_GRAPHICS mode.
        """
        try:
            self.tty_fd = os.open("/dev/tty0", os.O_RDWR)
            fcntl.ioctl(self.tty_fd, KDSETMODE, KD_GRAPHICS)
            logger.info("Console switched to graphics mode")
        except (OSError, IOError) as e:
            logger.warning(f"Could not switch console to graphics mode: {e}")
            if self.tty_fd is not None:
                try:
                    os.close(self.tty_fd)
                except Exception:
                    pass
                self.tty_fd = None

    def _restore_console_text(self):
        """Restore console to text mode (called on cleanup)."""
        if self.tty_fd is not None:
            try:
                fcntl.ioctl(self.tty_fd, KDSETMODE, KD_TEXT)
                os.close(self.tty_fd)
                logger.info("Console restored to text mode")
            except (OSError, IOError) as e:
                logger.warning(f"Could not restore console mode: {e}")
            self.tty_fd = None

    def _get_touch_bar(self, labels: tuple) -> Image.Image:
        """Get touch bar from cache or create new one"""
        if labels not in self._touch_bar_cache:
            self._touch_bar_cache[labels] = self._create_touch_bar(labels)
        return self._touch_bar_cache[labels]

    def set_touch_bar_labels(self, labels: tuple):
        """
        Set the touch bar labels.

        Args:
            labels: Tuple of 3 strings for (KEY1, KEY2, KEY3)
                    Use TOUCH_BAR_DEFAULT or TOUCH_BAR_KEYBOARD presets
        """
        if labels != self._current_labels:
            self._current_labels = labels
            self._touch_bar = self._get_touch_bar(labels)

    def _get_font_path(self, font_type: str) -> str:
        """Get the path to the icon font file"""
        this_dir = os.path.dirname(os.path.abspath(__file__))
        resources_dir = os.path.join(this_dir, '..', 'resources', 'fonts')

        if font_type == 'seedsigner':
            return os.path.join(resources_dir, 'seedsigner-icons.otf')
        elif font_type == 'fontawesome':
            return os.path.join(resources_dir, 'Font_Awesome_6_Free-Solid-900.otf')
        else:
            return None

    def _create_touch_bar(self, preset: tuple = None) -> Image.Image:
        """Create the touch bar with icons and colors"""
        if preset is None:
            preset = self.TOUCH_BAR_DEFAULT

        icons, colors, font_types = preset

        bar = Image.new('RGB', (self.UI_WIDTH, self.TOUCH_BAR_HEIGHT), '#1a1a1a')
        draw = ImageDraw.Draw(bar)

        btn_width = self.UI_WIDTH // 3
        btn_height = 100
        btn_y = (self.TOUCH_BAR_HEIGHT - btn_height) // 2

        icon_fonts = {}

        for i, (icon, color, font_type) in enumerate(zip(icons, colors, font_types)):
            x = i * btn_width
            draw.rounded_rectangle(
                [x + 10, btn_y, x + btn_width - 10, btn_y + btn_height],
                radius=15,
                fill=color
            )

            if not icon:
                continue

            icon_color = 'black' if color == '#ff9416' else 'white'

            if font_type not in icon_fonts:
                font_path = self._get_font_path(font_type)
                try:
                    icon_fonts[font_type] = ImageFont.truetype(font_path, 40)
                except Exception:
                    icon_fonts[font_type] = ImageFont.load_default()

            font = icon_fonts[font_type]

            bbox = draw.textbbox((0, 0), icon, font=font)
            icon_w = bbox[2] - bbox[0]
            icon_h = bbox[3] - bbox[1]
            icon_x = x + (btn_width - icon_w) // 2
            icon_y = btn_y + (btn_height - icon_h) // 2
            draw.text((icon_x, icon_y), icon, fill=icon_color, font=font)

        return bar

    def show_image(self, image: Image.Image, x: int = 0, y: int = 0):
        """
        Display a PIL Image on the screen.

        Accepts 240x240 image, scales to 480x480, adds touch bar.

        Args:
            image: PIL Image (240x240) to display
            x: X offset (ignored for now)
            y: Y offset (ignored for now)
        """
        if not self.fb:
            return

        # Scale 240x240 -> 480x480 using nearest neighbor (sharp pixels)
        scaled = image.resize((self.UI_WIDTH, self.UI_HEIGHT), Image.NEAREST)

        # Create full display image
        display = Image.new('RGB', (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT))
        display.paste(scaled, (0, 0))
        display.paste(self._touch_bar, (0, self.UI_HEIGHT))

        # Write to framebuffer
        self._write_to_fb(display)

    def _write_to_fb(self, image: Image.Image):
        """
        Write image to framebuffer with RGB→BGR conversion.
        
        Uses fastest available method:
        1. Cython (~17 fps)
        2. Numpy (~7 fps)
        3. Pure Python (~1 fps)
        """
        if not self.fb:
            return

        if image.mode != 'RGB':
            image = image.convert('RGB')

        if self.bits_per_pixel == 32:
            self._write_32bit(image)
        elif self.bits_per_pixel == 16:
            self._write_16bit(image)
        else:
            logger.error(f"Unsupported bits_per_pixel: {self.bits_per_pixel}")

    def _write_32bit(self, image: Image.Image):
        """Write 32-bit BGRA to framebuffer"""
        if HAS_CYTHON:
            # Fastest: Cython (~17 fps)
            rgb_data = image.tobytes()
            num_pixels = image.width * image.height
            RGBtoBGR.rgbtobgr(rgb_data, self.fb, num_pixels)
        elif HAS_NUMPY:
            # Fast: Numpy (~7 fps)
            # Convert PIL to numpy array
            arr = np.array(image)
            # Swap R and B channels: RGB -> BGR
            bgr = arr[:, :, ::-1]
            # Add alpha channel (BGRA)
            bgra = np.dstack((bgr, np.full((image.height, image.width), 255, dtype=np.uint8)))
            # Write to framebuffer
            self.fb.seek(0)
            self.fb.write(bgra.tobytes())
        else:
            # Slow: Pure Python (~1 fps)
            self._write_32bit_python(image)

    def _write_32bit_python(self, image: Image.Image):
        """Fallback pure Python 32-bit write (slow!)"""
        pixels = image.load()
        bgra_data = bytearray(self.length)
        
        idx = 0
        for row in range(image.height):
            for col in range(image.width):
                r, g, b = pixels[col, row]
                # BGRA format (swap R and B)
                bgra_data[idx] = b
                bgra_data[idx + 1] = g
                bgra_data[idx + 2] = r
                bgra_data[idx + 3] = 255  # Alpha
                idx += 4
        
        self.fb.seek(0)
        self.fb.write(bgra_data)

    def _write_16bit(self, image: Image.Image):
        """Write 16-bit RGB565 to framebuffer (if needed)"""
        if HAS_NUMPY:
            arr = np.array(image)
            r = (arr[:, :, 0] >> 3).astype(np.uint16)
            g = (arr[:, :, 1] >> 2).astype(np.uint16)
            b = (arr[:, :, 2] >> 3).astype(np.uint16)
            rgb565 = (r << 11) | (g << 5) | b
            self.fb.seek(0)
            self.fb.write(rgb565.tobytes())
        else:
            self._write_16bit_python(image)

    def _write_16bit_python(self, image: Image.Image):
        """Fallback pure Python 16-bit write (slow!)"""
        pixels = image.load()
        rgb565_data = bytearray(image.width * image.height * 2)

        idx = 0
        for row in range(image.height):
            for col in range(image.width):
                r, g, b = pixels[col, row]
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                rgb565_data[idx] = rgb565 & 0xFF
                rgb565_data[idx + 1] = (rgb565 >> 8) & 0xFF
                idx += 2

        self.fb.seek(0)
        self.fb.write(rgb565_data)

    def clear(self):
        """Clear the display to black"""
        if not self.fb:
            return

        try:
            self.fb.seek(0)
            self.fb.write(bytearray(self.length))
        except Exception as e:
            logger.error(f"Clear error: {e}")

    def close(self):
        """Close the framebuffer device and restore console mode"""
        self._restore_console_text()
        if self.fb:
            self.fb.close()
            self.fb = None
        if self.fb_file:
            self.fb_file.close()
            self.fb_file = None

    def __del__(self):
        self.close()
