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

from PIL import Image, ImageDraw, ImageFont


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

    # Touch bar label presets: (labels_tuple, colors_tuple)
    # Colors: grey=#444444, orange=#ff9416
    TOUCH_BAR_DEFAULT = (('▲', 'SELECT', '▼'), ('#444444', '#ff9416', '#444444'))
    TOUCH_BAR_SELECT_ONLY = (('', 'SELECT', ''), ('#1a1a1a', '#ff9416', '#1a1a1a'))  # Only SELECT visible
    TOUCH_BAR_KEYBOARD = (('BACK', 'SELECT', 'DEL'), ('#444444', '#444444', '#444444'))  # SELECT and DEL inactive (grey)
    TOUCH_BAR_KEYBOARD_SELECT_ACTIVE = (('BACK', 'SELECT', 'DEL'), ('#444444', '#ff9416', '#444444'))  # SELECT active, DEL grey
    TOUCH_BAR_KEYBOARD_DEL_ACTIVE = (('BACK', 'SELECT', 'DEL'), ('#444444', '#444444', '#ff9416'))  # DEL active, SELECT grey
    TOUCH_BAR_KEYBOARD_BOTH_ACTIVE = (('BACK', 'SELECT', 'DEL'), ('#444444', '#ff9416', '#ff9416'))  # Both active (orange)
    TOUCH_BAR_HIDDEN = (('', '', ''), ('#1a1a1a', '#1a1a1a', '#1a1a1a'))  # All buttons hidden

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

    def _create_touch_bar(self, preset: tuple = None) -> Image.Image:
        """Create the touch bar with custom labels and colors"""
        if preset is None:
            preset = self.TOUCH_BAR_DEFAULT

        labels, colors = preset

        bar = Image.new('RGB', (self.UI_WIDTH, self.TOUCH_BAR_HEIGHT), '#1a1a1a')
        draw = ImageDraw.Draw(bar)

        # Button dimensions
        btn_width = self.UI_WIDTH // 3
        btn_height = 100
        btn_y = (self.TOUCH_BAR_HEIGHT - btn_height) // 2

        for i, (label, color) in enumerate(zip(labels, colors)):
            x = i * btn_width
            # Draw button background
            draw.rounded_rectangle(
                [x + 10, btn_y, x + btn_width - 10, btn_y + btn_height],
                radius=15,
                fill=color
            )
            # Draw label
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), label, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_x = x + (btn_width - text_w) // 2
            text_y = btn_y + (btn_height - text_h) // 2
            draw.text((text_x, text_y), label, fill='white', font=font)

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
