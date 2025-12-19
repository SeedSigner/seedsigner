"""
DPI28 - Framebuffer display driver for Waveshare 2.8" DPI LCD.

Display specs:
- 480x640 resolution (portrait)
- DPI interface (uses GPIO, not SPI)
- Directly writes to /dev/fb0 framebuffer

Layout:
- Top 480x480: UI area (240x240 scaled 2x)
- Bottom 480x160: Touch bar (KEY1, KEY2, KEY3)

On PC/Emulator: This module is replaced by EmulatedDPI28 in run_emulator.py
"""

import os
from PIL import Image, ImageDraw, ImageFont


# Icon constants from SeedSigner icon fonts (language-agnostic)
class TouchBarIcons:
    # From seedsigner-icons.otf
    CHEVRON_UP = "\ue90b"
    CHEVRON_DOWN = "\ue908"
    CHECK = "\ue905"
    DELETE = "\ue922"
    # From FontAwesome
    KEYBOARD = "\uf11c"


class DPI28:
    """
    Framebuffer display driver for Waveshare 2.8" DPI LCD.

    Accepts 240x240 images (SeedSigner native), scales to 480x480,
    and adds a 160px touch bar at the bottom.
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
    # Colors: grey=#444444, orange=#ff9416
    # Font types: 'seedsigner' for seedsigner-icons.otf, 'fontawesome' for FontAwesome
    # Icons are language-agnostic (no translation needed)
    _UP = TouchBarIcons.CHEVRON_UP
    _DOWN = TouchBarIcons.CHEVRON_DOWN
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

    def __init__(self, fb_device: str = "/dev/fb0"):
        """
        Initialize the framebuffer display.

        Args:
            fb_device: Path to framebuffer device
        """
        # Report 240x240 to SeedSigner (native rendering size)
        self.width = self.NATIVE_WIDTH
        self.height = self.NATIVE_HEIGHT

        self.fb_device = fb_device
        self.fb = None

        # Current touch bar labels
        self._current_labels = self.TOUCH_BAR_DEFAULT

        # Cache touch bars for different label sets
        self._touch_bar_cache = {}
        self._touch_bar = self._get_touch_bar(self.TOUCH_BAR_DEFAULT)

        try:
            self.fb = open(fb_device, 'r+b')
        except Exception as e:
            print(f"[DPI28] Could not open {fb_device}: {e}")

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
        # Find the resources/fonts directory relative to this file
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

        # Button dimensions
        btn_width = self.UI_WIDTH // 3
        btn_height = 100
        btn_y = (self.TOUCH_BAR_HEIGHT - btn_height) // 2

        # Cache fonts
        icon_fonts = {}

        for i, (icon, color, font_type) in enumerate(zip(icons, colors, font_types)):
            x = i * btn_width
            # Draw button background
            draw.rounded_rectangle(
                [x + 10, btn_y, x + btn_width - 10, btn_y + btn_height],
                radius=15,
                fill=color
            )

            if not icon:
                continue

            # Draw icon - use black on orange buttons, white on grey
            icon_color = 'black' if color == '#ff9416' else 'white'

            # Get font for this icon
            if font_type not in icon_fonts:
                font_path = self._get_font_path(font_type)
                try:
                    icon_fonts[font_type] = ImageFont.truetype(font_path, 40)
                except:
                    # Fallback to default font
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
        """Write image to framebuffer in RGB565 format"""
        if not self.fb:
            return

        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Convert RGB888 to RGB565
        pixels = image.load()
        rgb565_data = bytearray(image.width * image.height * 2)

        idx = 0
        for row in range(image.height):
            for col in range(image.width):
                r, g, b = pixels[col, row]
                # RGB565: RRRRRGGGGGGBBBBB
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                rgb565_data[idx] = rgb565 & 0xFF
                rgb565_data[idx + 1] = (rgb565 >> 8) & 0xFF
                idx += 2

        try:
            self.fb.seek(0)
            self.fb.write(rgb565_data)
            self.fb.flush()
        except Exception as e:
            print(f"[DPI28] Write error: {e}")

    def clear(self):
        """Clear the display to black"""
        if not self.fb:
            return

        black = bytearray(self.width * self.height * 2)
        try:
            self.fb.seek(0)
            self.fb.write(black)
            self.fb.flush()
        except Exception as e:
            print(f"[DPI28] Clear error: {e}")

    def close(self):
        """Close the framebuffer device"""
        if self.fb:
            self.fb.close()
            self.fb = None

    def __del__(self):
        self.close()
