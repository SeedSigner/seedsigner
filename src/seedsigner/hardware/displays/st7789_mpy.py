"""
MIT License

Copyright (c) 2020-2023 Russ Hughes

Copyright (c) 2019 Ivan Belokobylskiy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

The driver is based on devbis' st7789py_mpy module from
https://github.com/devbis/st7789py_mpy.

This driver supports:

- 320x240, 240x240, 135x240 and 128x128 pixel displays
- Display rotation
- RGB and BGR color orders
- Hardware based scrolling
- Drawing text using 8 and 16 bit wide bitmap fonts with heights that are
  multiples of 8.  Included are 12 bitmap fonts derived from classic pc
  BIOS text mode fonts.
- Drawing text using converted TrueType fonts.
- Drawing converted bitmaps
- Named color constants

  - BLACK
  - BLUE
  - RED
  - GREEN
  - CYAN
  - MAGENTA
  - YELLOW
  - WHITE

"""

import array
import spidev
import RPi.GPIO as GPIO

from math import sin, cos

#
# This allows sphinx to build the docs
#

try:
    from time import sleep_ms
except ImportError:
    sleep_ms = lambda ms: None
    uint = int
    const = lambda x: x

    class micropython:
        @staticmethod
        def viper(func):
            return func

        @staticmethod
        def native(func):
            return func


#
# If you don't need to build the docs, you can remove all of the lines between
# here and the comment above except for the "from time import sleep_ms" line.
#

import struct

# ST7789 commands
_ST7789_SWRESET = b"\x01"
_ST7789_SLPIN = b"\x10"
_ST7789_SLPOUT = b"\x11"
_ST7789_NORON = b"\x13"
_ST7789_INVOFF = b"\x20"
_ST7789_INVON = b"\x21"
_ST7789_DISPOFF = b"\x28"
_ST7789_DISPON = b"\x29"
_ST7789_CASET = b"\x2a"
_ST7789_RASET = b"\x2b"
_ST7789_RAMWR = b"\x2c"
_ST7789_VSCRDEF = b"\x33"
_ST7789_COLMOD = b"\x3a"
_ST7789_MADCTL = b"\x36"
_ST7789_VSCSAD = b"\x37"
_ST7789_RAMCTL = b"\xb0"

# MADCTL bits
_ST7789_MADCTL_MY = const(0x80)
_ST7789_MADCTL_MX = const(0x40)
_ST7789_MADCTL_MV = const(0x20)
_ST7789_MADCTL_ML = const(0x10)
_ST7789_MADCTL_BGR = const(0x08)
_ST7789_MADCTL_MH = const(0x04)
_ST7789_MADCTL_RGB = const(0x00)

RGB = 0x00
BGR = 0x08

# Color modes
_COLOR_MODE_65K = const(0x50)
_COLOR_MODE_262K = const(0x60)
_COLOR_MODE_12BIT = const(0x03)
_COLOR_MODE_16BIT = const(0x05)
_COLOR_MODE_18BIT = const(0x06)
_COLOR_MODE_16M = const(0x07)

# Color definitions
BLACK = const(0x0000)
BLUE = const(0x001F)
RED = const(0xF800)
GREEN = const(0x07E0)
CYAN = const(0x07FF)
MAGENTA = const(0xF81F)
YELLOW = const(0xFFE0)
WHITE = const(0xFFFF)

_ENCODE_PIXEL = const(">H")
_ENCODE_PIXEL_SWAPPED = const("<H")
_ENCODE_POS = const(">HH")
_ENCODE_POS_16 = const("<HH")

# must be at least 128 for 8 bit wide fonts
# must be at least 256 for 16 bit wide fonts
_BUFFER_SIZE = const(256)

_BIT7 = const(0x80)
_BIT6 = const(0x40)
_BIT5 = const(0x20)
_BIT4 = const(0x10)
_BIT3 = const(0x08)
_BIT2 = const(0x04)
_BIT1 = const(0x02)
_BIT0 = const(0x01)

# fmt: off

# Rotation tables
#   (madctl, width, height, xstart, ystart, needs_swap)[rotation % 4]

_DISPLAY_240x320 = (
    (0x00, 240, 320, 0, 0, False),
    (0x60, 320, 240, 0, 0, False),
    (0xc0, 240, 320, 0, 0, False),
    (0xa0, 320, 240, 0, 0, False))

_DISPLAY_240x240 = (
    (0x00, 240, 240,  0,  0, False),
    (0x60, 240, 240,  0,  0, False),
    (0xc0, 240, 240,  0, 80, False),
    (0xa0, 240, 240, 80,  0, False))

_DISPLAY_135x240 = (
    (0x00, 135, 240, 52, 40, False),
    (0x60, 240, 135, 40, 53, False),
    (0xc0, 135, 240, 53, 40, False),
    (0xa0, 240, 135, 40, 52, False))

_DISPLAY_128x128 = (
    (0x00, 128, 128, 2, 1, False),
    (0x60, 128, 128, 1, 2, False),
    (0xc0, 128, 128, 2, 1, False),
    (0xa0, 128, 128, 1, 2, False))

# index values into rotation table
_WIDTH = const(0)
_HEIGHT = const(1)
_XSTART = const(2)
_YSTART = const(3)
_NEEDS_SWAP = const(4)

# Supported displays (physical width, physical height, rotation table)
_SUPPORTED_DISPLAYS = (
    (240, 320, _DISPLAY_240x320),
    (240, 240, _DISPLAY_240x240),
    (135, 240, _DISPLAY_135x240),
    (128, 128, _DISPLAY_128x128))

# init tuple format (b'command', b'data', delay_ms)
_ST7789_INIT_CMDS = (
    ( b'\x11', b'\x00', 120),               # Exit sleep mode
    ( b'\x13', b'\x00', 0),                 # Turn on the display
    ( b'\xb6', b'\x0a\x82', 0),             # Set display function control
    ( b'\x3a', b'\x55', 10),                # Set pixel format to 16 bits per pixel (RGB565)
    ( b'\xb2', b'\x0c\x0c\x00\x33\x33', 0), # Set porch control
    ( b'\xb7', b'\x35', 0),                 # Set gate control
    ( b'\xbb', b'\x28', 0),                 # Set VCOMS setting
    ( b'\xc0', b'\x0c', 0),                 # Set power control 1
    ( b'\xc2', b'\x01\xff', 0),             # Set power control 2
    ( b'\xc3', b'\x10', 0),                 # Set power control 3
    ( b'\xc4', b'\x20', 0),                 # Set power control 4
    ( b'\xc6', b'\x0f', 0),                 # Set VCOM control 1
    ( b'\xd0', b'\xa4\xa1', 0),             # Set power control A
                                            # Set gamma curve positive polarity
    ( b'\xe0', b'\xd0\x00\x02\x07\x0a\x28\x32\x44\x42\x06\x0e\x12\x14\x17', 0),
                                            # Set gamma curve negative polarity
    ( b'\xe1', b'\xd0\x00\x02\x07\x0a\x28\x31\x54\x47\x0e\x1c\x17\x1b\x1e', 0),
    ( b'\x21', b'\x00', 0),                 # Enable display inversion
    ( b'\x29', b'\x00', 120)                # Turn on the display
)

# fmt: on


def color565(red, green=0, blue=0):
    """
    Convert red, green and blue values (0-255) into a 16-bit 565 encoding.
    """
    if isinstance(red, (tuple, list)):
        red, green, blue = red[:3]
    return (red & 0xF8) << 8 | (green & 0xFC) << 3 | blue >> 3


class ST7789:
    """
    ST7789 driver class

    Args:
        spi (spi): spi object **Required**
        width (int): display width **Required**
        height (int): display height **Required**
        reset (pin): reset pin
        dc (pin): dc pin **Required**
        cs (pin): cs pin
        backlight(pin): backlight pin
        rotation (int):

          - 0-Portrait
          - 1-Landscape
          - 2-Inverted Portrait
          - 3-Inverted Landscape

        color_order (int):

          - RGB: Red, Green Blue, default
          - BGR: Blue, Green, Red

        custom_init (tuple): custom initialization commands

          - ((b'command', b'data', delay_ms), ...)

        custom_rotations (tuple): custom rotation definitions

          - ((width, height, xstart, ystart, madctl, needs_swap), ...)

    """

    def __init__(
        self,
        # spi,
        width,
        height,
        reset=13,
        dc=22,
        cs=None,
        backlight=18,
        rotation=1,
        color_order=BGR,
        custom_init=None,
        custom_rotations=None,
    ):

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(dc,GPIO.OUT)
        GPIO.setup(reset,GPIO.OUT)
        GPIO.setup(backlight,GPIO.OUT)

        #Initialize SPI
        spi = spidev.SpiDev(0, 0)
        spi.max_speed_hz = 40000000

        """
        Initialize display.
        """
        self.rotations = custom_rotations or self._find_rotations(width, height)
        if not self.rotations:
            supported_displays = ", ".join(
                [f"{display[0]}x{display[1]}" for display in _SUPPORTED_DISPLAYS]
            )
            raise ValueError(
                f"Unsupported {width}x{height} display. Supported displays: {supported_displays}"
            )

        if dc is None:
            raise ValueError("dc pin is required.")

        self.physical_width = self.width = width
        self.physical_height = self.height = height
        self.xstart = 0
        self.ystart = 0
        self.spi = spi
        self.reset = reset
        self.dc = dc
        self.cs = cs
        self.backlight = backlight
        self._rotation = rotation % 4
        self.color_order = color_order
        self.init_cmds = custom_init or _ST7789_INIT_CMDS
        self.hard_reset()
        # yes, twice, once is not always enough
        self.init(self.init_cmds)
        self.init(self.init_cmds)
        self.rotation(self._rotation)
        self.needs_swap = False
        self.fill(0x0)

        if backlight is not None:
            GPIO.output(backlight, GPIO.HIGH)
            # backlight.value(1)

    @staticmethod
    def _find_rotations(width, height):
        for display in _SUPPORTED_DISPLAYS:
            if display[0] == width and display[1] == height:
                return display[2]
        return None

    def init(self, commands):
        """
        Initialize display.
        """
        for command, data, delay in commands:
            self._write(command, data)
            sleep_ms(delay)

    def invert(self, enabled: bool = True):
        raise Exception("Invert not implemented")

    def show_image(self, image, x_start: int = 0, y_start: int = 0):
        """Set buffer to value of Python Imaging Library image."""
        """Write display buffer to physical display"""

        # image = image.rotate(90, expand=True)

        imwidth, imheight = image.size
        if imwidth != self.width or imheight != self.height:
            raise ValueError('Image must be same dimensions as display \
                ({0}x{1}).' .format(self.width, self.height))

        # convert 24-bit RGB-8:8:8 to gBRG-3:5:5:3; then per-pixel byteswap to 16-bit RGB-5:6:5
        arr = array.array("H", image.convert("BGR;16").tobytes())
        arr.byteswap()
        pix = arr.tobytes()

        self._set_window(x_start, y_start, self.width, self.height)
        GPIO.output(self.dc,GPIO.HIGH)
        self._write(data=pix)

    def _write(self, command=None, data=None):
        """SPI write to the device: commands and data."""
        if self.cs:
            GPIO.output(self.cs, GPIO.LOW)
        if command is not None:
            GPIO.output(self.dc, GPIO.LOW)
            self.spi.writebytes2(command)
        if data is not None:
            GPIO.output(self.dc,GPIO.HIGH)
            self.spi.writebytes2(data)
            if self.cs:
                GPIO.output(self.cs,GPIO.HIGH)

    def hard_reset(self):
        """
        Hard reset display.
        """
        if self.cs:
            GPIO.output(self.cs, GPIO.LOW)
        if self.reset:
            GPIO.output(self.reset, GPIO.HIGH)
        sleep_ms(10)
        if self.reset:
            GPIO.output(self.reset, GPIO.LOW)
        sleep_ms(10)
        if self.reset:
            GPIO.output(self.reset, GPIO.HIGH)
        sleep_ms(120)
        if self.cs:
            GPIO.output(self.cs, GPIO.HIGH)

    def soft_reset(self):
        """
        Soft reset display.
        """
        self._write(_ST7789_SWRESET)
        sleep_ms(150)

    def sleep_mode(self, value):
        """
        Enable or disable display sleep mode.

        Args:
            value (bool): if True enable sleep mode. if False disable sleep
            mode
        """
        if value:
            self._write(_ST7789_SLPIN)
        else:
            self._write(_ST7789_SLPOUT)

    def inversion_mode(self, value):
        """
        Enable or disable display inversion mode.

        Args:
            value (bool): if True enable inversion mode. if False disable
            inversion mode
        """
        if value:
            self._write(_ST7789_INVON)
        else:
            self._write(_ST7789_INVOFF)

    def rotation(self, rotation):
        """
        Set display rotation.

        Args:
            rotation (int):
                - 0-Portrait
                - 1-Landscape
                - 2-Inverted Portrait
                - 3-Inverted Landscape

            custom_rotations can have any number of rotations
        """
        rotation %= len(self.rotations)
        self._rotation = rotation
        (
            madctl,
            self.width,
            self.height,
            self.xstart,
            self.ystart,
            self.needs_swap,
        ) = self.rotations[rotation]

        if self.color_order == BGR:
            madctl |= _ST7789_MADCTL_BGR
        else:
            madctl &= ~_ST7789_MADCTL_BGR

        self._write(_ST7789_MADCTL, bytes([madctl]))

    def _set_window(self, x0, y0, x1, y1):
        """
        Set window to column and row address.

        Args:
            x0 (int): column start address
            y0 (int): row start address
            x1 (int): column end address
            y1 (int): row end address
        """
        if x0 <= x1 <= self.width and y0 <= y1 <= self.height:
            self._write(
                _ST7789_CASET,
                struct.pack(_ENCODE_POS, x0 + self.xstart, x1 + self.xstart),
            )
            self._write(
                _ST7789_RASET,
                struct.pack(_ENCODE_POS, y0 + self.ystart, y1 + self.ystart),
            )
            self._write(_ST7789_RAMWR)

    def vline(self, x, y, length, color):
        """
        Draw vertical line at the given location and color.

        Args:
            x (int): x coordinate
            Y (int): y coordinate
            length (int): length of line
            color (int): 565 encoded color
        """
        self.fill_rect(x, y, 1, length, color)

    def hline(self, x, y, length, color):
        """
        Draw horizontal line at the given location and color.

        Args:
            x (int): x coordinate
            Y (int): y coordinate
            length (int): length of line
            color (int): 565 encoded color
        """
        self.fill_rect(x, y, length, 1, color)

    def pixel(self, x, y, color):
        """
        Draw a pixel at the given location and color.

        Args:
            x (int): x coordinate
            Y (int): y coordinate
            color (int): 565 encoded color
        """
        self._set_window(x, y, x, y)
        self._write(
            None,
            struct.pack(
                _ENCODE_PIXEL_SWAPPED if self.needs_swap else _ENCODE_PIXEL, color
            ),
        )

    def blit_buffer(self, buffer, x, y, width, height):
        """
        Copy buffer to display at the given location.

        Args:
            buffer (bytes): Data to copy to display
            x (int): Top left corner x coordinate
            Y (int): Top left corner y coordinate
            width (int): Width
            height (int): Height
        """
        self._set_window(x, y, x + width - 1, y + height - 1)
        self._write(None, buffer)

    def rect(self, x, y, w, h, color):
        """
        Draw a rectangle at the given location, size and color.

        Args:
            x (int): Top left corner x coordinate
            y (int): Top left corner y coordinate
            width (int): Width in pixels
            height (int): Height in pixels
            color (int): 565 encoded color
        """
        self.hline(x, y, w, color)
        self.vline(x, y, h, color)
        self.vline(x + w - 1, y, h, color)
        self.hline(x, y + h - 1, w, color)

    def fill_rect(self, x, y, width, height, color):
        """
        Draw a rectangle at the given location, size and filled with color.

        Args:
            x (int): Top left corner x coordinate
            y (int): Top left corner y coordinate
            width (int): Width in pixels
            height (int): Height in pixels
            color (int): 565 encoded color
        """
        self._set_window(x, y, x + width - 1, y + height - 1)
        chunks, rest = divmod(width * height, _BUFFER_SIZE)
        pixel = struct.pack(
            _ENCODE_PIXEL_SWAPPED if self.needs_swap else _ENCODE_PIXEL, color
        )
        GPIO.output(self.dc,GPIO.HIGH)
        if chunks:
            data = pixel * _BUFFER_SIZE
            for _ in range(chunks):
                self._write(None, data)
        if rest:
            self._write(None, pixel * rest)

    def fill(self, color):
        """
        Fill the entire FrameBuffer with the specified color.

        Args:
            color (int): 565 encoded color
        """
        self.fill_rect(0, 0, self.width, self.height, color)

    def line(self, x0, y0, x1, y1, color):
        """
        Draw a single pixel wide line starting at x0, y0 and ending at x1, y1.

        Args:
            x0 (int): Start point x coordinate
            y0 (int): Start point y coordinate
            x1 (int): End point x coordinate
            y1 (int): End point y coordinate
            color (int): 565 encoded color
        """
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0
        dx = x1 - x0
        dy = abs(y1 - y0)
        err = dx // 2
        ystep = 1 if y0 < y1 else -1
        while x0 <= x1:
            if steep:
                self.pixel(y0, x0, color)
            else:
                self.pixel(x0, y0, color)
            err -= dy
            if err < 0:
                y0 += ystep
                err += dx
            x0 += 1

    def vscrdef(self, tfa, vsa, bfa):
        """
        Set Vertical Scrolling Definition.

        To scroll a 135x240 display these values should be 40, 240, 40.
        There are 40 lines above the display that are not shown followed by
        240 lines that are shown followed by 40 more lines that are not shown.
        You could write to these areas off display and scroll them into view by
        changing the TFA, VSA and BFA values.

        Args:
            tfa (int): Top Fixed Area
            vsa (int): Vertical Scrolling Area
            bfa (int): Bottom Fixed Area
        """
        self._write(_ST7789_VSCRDEF, struct.pack(">HHH", tfa, vsa, bfa))

    def vscsad(self, vssa):
        """
        Set Vertical Scroll Start Address of RAM.

        Defines which line in the Frame Memory will be written as the first
        line after the last line of the Top Fixed Area on the display

        Example:

            for line in range(40, 280, 1):
                tft.vscsad(line)
                utime.sleep(0.01)

        Args:
            vssa (int): Vertical Scrolling Start Address

        """
        self._write(_ST7789_VSCSAD, struct.pack(">H", vssa))

    # @micropython.viper
    # @staticmethod
    # def _pack8(glyphs, idx: uint, fg_color: uint, bg_color: uint):
    #     buffer = bytearray(128)
    #     bitmap = ptr16(buffer)
    #     glyph = ptr8(glyphs)

    #     for i in range(0, 64, 8):
    #         byte = glyph[idx]
    #         bitmap[i] = fg_color if byte & _BIT7 else bg_color
    #         bitmap[i + 1] = fg_color if byte & _BIT6 else bg_color
    #         bitmap[i + 2] = fg_color if byte & _BIT5 else bg_color
    #         bitmap[i + 3] = fg_color if byte & _BIT4 else bg_color
    #         bitmap[i + 4] = fg_color if byte & _BIT3 else bg_color
    #         bitmap[i + 5] = fg_color if byte & _BIT2 else bg_color
    #         bitmap[i + 6] = fg_color if byte & _BIT1 else bg_color
    #         bitmap[i + 7] = fg_color if byte & _BIT0 else bg_color
    #         idx += 1

    #     return buffer

    # @micropython.viper
    # @staticmethod
    # def _pack16(glyphs, idx: uint, fg_color: uint, bg_color: uint):
    #     """
    #     Pack a character into a byte array.

    #     Args:
    #         char (str): character to pack

    #     Returns:
    #         128 bytes: character bitmap in color565 format
    #     """

    #     buffer = bytearray(256)
    #     bitmap = ptr16(buffer)
    #     glyph = ptr8(glyphs)

    #     for i in range(0, 128, 16):
    #         byte = glyph[idx]

    #         bitmap[i] = fg_color if byte & _BIT7 else bg_color
    #         bitmap[i + 1] = fg_color if byte & _BIT6 else bg_color
    #         bitmap[i + 2] = fg_color if byte & _BIT5 else bg_color
    #         bitmap[i + 3] = fg_color if byte & _BIT4 else bg_color
    #         bitmap[i + 4] = fg_color if byte & _BIT3 else bg_color
    #         bitmap[i + 5] = fg_color if byte & _BIT2 else bg_color
    #         bitmap[i + 6] = fg_color if byte & _BIT1 else bg_color
    #         bitmap[i + 7] = fg_color if byte & _BIT0 else bg_color
    #         idx += 1

    #         byte = glyph[idx]
    #         bitmap[i + 8] = fg_color if byte & _BIT7 else bg_color
    #         bitmap[i + 9] = fg_color if byte & _BIT6 else bg_color
    #         bitmap[i + 10] = fg_color if byte & _BIT5 else bg_color
    #         bitmap[i + 11] = fg_color if byte & _BIT4 else bg_color
    #         bitmap[i + 12] = fg_color if byte & _BIT3 else bg_color
    #         bitmap[i + 13] = fg_color if byte & _BIT2 else bg_color
    #         bitmap[i + 14] = fg_color if byte & _BIT1 else bg_color
    #         bitmap[i + 15] = fg_color if byte & _BIT0 else bg_color
    #         idx += 1

    #     return buffer

    def _text8(self, font, text, x0, y0, fg_color=WHITE, bg_color=BLACK):
        """
        Internal method to write characters with width of 8 and
        heights of 8 or 16.

        Args:
            font (module): font module to use
            text (str): text to write
            x0 (int): column to start drawing at
            y0 (int): row to start drawing at
            color (int): 565 encoded color to use for characters
            background (int): 565 encoded color to use for background
        """

        for char in text:
            ch = ord(char)
            if (
                font.FIRST <= ch < font.LAST
                and x0 + font.WIDTH <= self.width
                and y0 + font.HEIGHT <= self.height
            ):
                if font.HEIGHT == 8:
                    passes = 1
                    size = 8
                    each = 0
                else:
                    passes = 2
                    size = 16
                    each = 8

                for line in range(passes):
                    idx = (ch - font.FIRST) * size + (each * line)
                    buffer = self._pack8(font.FONT, idx, fg_color, bg_color)
                    self.blit_buffer(buffer, x0, y0 + 8 * line, 8, 8)

                x0 += 8

    # def _text16(self, font, text, x0, y0, fg_color=WHITE, bg_color=BLACK):
    #     """
    #     Internal method to draw characters with width of 16 and heights of 16
    #     or 32.

    #     Args:
    #         font (module): font module to use
    #         text (str): text to write
    #         x0 (int): column to start drawing at
    #         y0 (int): row to start drawing at
    #         color (int): 565 encoded color to use for characters
    #         background (int): 565 encoded color to use for background
    #     """

    #     for char in text:
    #         ch = ord(char)
    #         if (
    #             font.FIRST <= ch < font.LAST
    #             and x0 + font.WIDTH <= self.width
    #             and y0 + font.HEIGHT <= self.height
    #         ):
    #             each = 16
    #             if font.HEIGHT == 16:
    #                 passes = 2
    #                 size = 32
    #             else:
    #                 passes = 4
    #                 size = 64

    #             for line in range(passes):
    #                 idx = (ch - font.FIRST) * size + (each * line)
    #                 buffer = self._pack16(font.FONT, idx, fg_color, bg_color)
    #                 self.blit_buffer(buffer, x0, y0 + 8 * line, 16, 8)
    #         x0 += 16

    def text(self, font, text, x0, y0, color=WHITE, background=BLACK):
        """
        Draw text on display in specified font and colors. 8 and 16 bit wide
        fonts are supported.

        Args:
            font (module): font module to use.
            text (str): text to write
            x0 (int): column to start drawing at
            y0 (int): row to start drawing at
            color (int): 565 encoded color to use for characters
            background (int): 565 encoded color to use for background
        """
        fg_color = color if self.needs_swap else ((color << 8) & 0xFF00) | (color >> 8)
        bg_color = (
            background
            if self.needs_swap
            else ((background << 8) & 0xFF00) | (background >> 8)
        )

        if font.WIDTH == 8:
            self._text8(font, text, x0, y0, fg_color, bg_color)
        else:
            self._text16(font, text, x0, y0, fg_color, bg_color)

    def bitmap(self, bitmap, x, y, index=0):
        """
        Draw a bitmap on display at the specified column and row

        Args:
            bitmap (bitmap_module): The module containing the bitmap to draw
            x (int): column to start drawing at
            y (int): row to start drawing at
            index (int): Optional index of bitmap to draw from multiple bitmap
                module
        """
        width = bitmap.WIDTH
        height = bitmap.HEIGHT
        to_col = x + width - 1
        to_row = y + height - 1
        if self.width <= to_col or self.height <= to_row:
            return

        bitmap_size = height * width
        buffer_len = bitmap_size * 2
        bpp = bitmap.BPP
        bs_bit = bpp * bitmap_size * index  # if index > 0 else 0
        palette = bitmap.PALETTE
        needs_swap = self.needs_swap
        buffer = bytearray(buffer_len)

        for i in range(0, buffer_len, 2):
            color_index = 0
            for _ in range(bpp):
                color_index = (color_index << 1) | (
                    (bitmap.BITMAP[bs_bit >> 3] >> (7 - (bs_bit & 7))) & 1
                )
                bs_bit += 1

            color = palette[color_index]
            if needs_swap:
                buffer[i] = color & 0xFF
                buffer[i + 1] = color >> 8
            else:
                buffer[i] = color >> 8
                buffer[i + 1] = color & 0xFF

        self._set_window(x, y, to_col, to_row)
        self._write(None, buffer)

    def pbitmap(self, bitmap, x, y, index=0):
        """
        Draw a bitmap on display at the specified column and row one row at a time

        Args:
            bitmap (bitmap_module): The module containing the bitmap to draw
            x (int): column to start drawing at
            y (int): row to start drawing at
            index (int): Optional index of bitmap to draw from multiple bitmap
                module

        """
        width = bitmap.WIDTH
        height = bitmap.HEIGHT
        bitmap_size = height * width
        bpp = bitmap.BPP
        bs_bit = bpp * bitmap_size * index  # if index > 0 else 0
        palette = bitmap.PALETTE
        needs_swap = self.needs_swap
        buffer = bytearray(bitmap.WIDTH * 2)

        for row in range(height):
            for col in range(width):
                color_index = 0
                for _ in range(bpp):
                    color_index <<= 1
                    color_index |= (
                        bitmap.BITMAP[bs_bit // 8] & 1 << (7 - (bs_bit % 8))
                    ) > 0
                    bs_bit += 1
                color = palette[color_index]
                if needs_swap:
                    buffer[col * 2] = color & 0xFF
                    buffer[col * 2 + 1] = color >> 8 & 0xFF
                else:
                    buffer[col * 2] = color >> 8 & 0xFF
                    buffer[col * 2 + 1] = color & 0xFF

            to_col = x + width - 1
            to_row = y + row
            if self.width > to_col and self.height > to_row:
                self._set_window(x, y + row, to_col, to_row)
                self._write(None, buffer)

    def write(self, font, string, x, y, fg=WHITE, bg=BLACK):
        """
        Write a string using a converted true-type font on the display starting
        at the specified column and row

        Args:
            font (font): The module containing the converted true-type font
            s (string): The string to write
            x (int): column to start writing
            y (int): row to start writing
            fg (int): foreground color, optional, defaults to WHITE
            bg (int): background color, optional, defaults to BLACK
        """
        buffer_len = font.HEIGHT * font.MAX_WIDTH * 2
        buffer = bytearray(buffer_len)
        fg_hi = fg >> 8
        fg_lo = fg & 0xFF

        bg_hi = bg >> 8
        bg_lo = bg & 0xFF

        for character in string:
            try:
                char_index = font.MAP.index(character)
                offset = char_index * font.OFFSET_WIDTH
                bs_bit = font.OFFSETS[offset]
                if font.OFFSET_WIDTH > 1:
                    bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 1]

                if font.OFFSET_WIDTH > 2:
                    bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 2]

                char_width = font.WIDTHS[char_index]
                buffer_needed = char_width * font.HEIGHT * 2

                for i in range(0, buffer_needed, 2):
                    if font.BITMAPS[bs_bit // 8] & 1 << (7 - (bs_bit % 8)) > 0:
                        buffer[i] = fg_hi
                        buffer[i + 1] = fg_lo
                    else:
                        buffer[i] = bg_hi
                        buffer[i + 1] = bg_lo

                    bs_bit += 1

                to_col = x + char_width - 1
                to_row = y + font.HEIGHT - 1
                if self.width > to_col and self.height > to_row:
                    self._set_window(x, y, to_col, to_row)
                    self._write(None, buffer[:buffer_needed])

                x += char_width

            except ValueError:
                pass

    def write_width(self, font, string):
        """
        Returns the width in pixels of the string if it was written with the
        specified font

        Args:
            font (font): The module containing the converted true-type font
            string (string): The string to measure

        Returns:
            int: The width of the string in pixels

        """
        width = 0
        for character in string:
            try:
                char_index = font.MAP.index(character)
                width += font.WIDTHS[char_index]
            except ValueError:
                pass

        return width

    @micropython.native
    def polygon(self, points, x, y, color, angle=0, center_x=0, center_y=0):
        """
        Draw a polygon on the display.

        Args:
            points (list): List of points to draw.
            x (int): X-coordinate of the polygon's position.
            y (int): Y-coordinate of the polygon's position.
            color (int): 565 encoded color.
            angle (float): Rotation angle in radians (default: 0).
            center_x (int): X-coordinate of the rotation center (default: 0).
            center_y (int): Y-coordinate of the rotation center (default: 0).

        Raises:
            ValueError: If the polygon has less than 3 points.
        """
        if len(points) < 3:
            raise ValueError("Polygon must have at least 3 points.")

        if angle:
            cos_a = cos(angle)
            sin_a = sin(angle)
            rotated = [
                (
                    x
                    + center_x
                    + int(
                        (point[0] - center_x) * cos_a - (point[1] - center_y) * sin_a
                    ),
                    y
                    + center_y
                    + int(
                        (point[0] - center_x) * sin_a + (point[1] - center_y) * cos_a
                    ),
                )
                for point in points
            ]
        else:
            rotated = [(x + int((point[0])), y + int((point[1]))) for point in points]

        for i in range(1, len(rotated)):
            self.line(
                rotated[i - 1][0],
                rotated[i - 1][1],
                rotated[i][0],
                rotated[i][1],
                color,
            )