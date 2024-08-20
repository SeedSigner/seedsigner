# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
Tested with a 320x240 IPS display (https://a.co/d/2Q9wDLo)
"""
import numbers
import time
# import numpy as np
import array

from PIL import Image
from PIL import ImageDraw

import RPi.GPIO as GPIO
from spidev import SpiDev


# Constants for interacting with display registers.
ILI9341_TFTWIDTH    = 240
ILI9341_TFTHEIGHT   = 320

ILI9341_NOP         = 0x00
ILI9341_SWRESET     = 0x01
ILI9341_RDDID       = 0x04
ILI9341_RDDST       = 0x09

ILI9341_SLPIN       = 0x10
ILI9341_SLPOUT      = 0x11
ILI9341_PTLON       = 0x12
ILI9341_NORON       = 0x13

ILI9341_RDMODE      = 0x0A
ILI9341_RDMADCTL    = 0x0B
ILI9341_RDPIXFMT    = 0x0C
ILI9341_RDIMGFMT    = 0x0A
ILI9341_RDSELFDIAG  = 0x0F

ILI9341_INVOFF      = 0x20
ILI9341_INVON       = 0x21
ILI9341_GAMMASET    = 0x26
ILI9341_DISPOFF     = 0x28
ILI9341_DISPON      = 0x29

ILI9341_CASET       = 0x2A
ILI9341_PASET       = 0x2B
ILI9341_RAMWR       = 0x2C
ILI9341_RAMRD       = 0x2E

ILI9341_PTLAR       = 0x30
ILI9341_MADCTL      = 0x36
ILI9341_PIXFMT      = 0x3A

ILI9341_FRMCTR1     = 0xB1
ILI9341_FRMCTR2     = 0xB2
ILI9341_FRMCTR3     = 0xB3
ILI9341_INVCTR      = 0xB4
ILI9341_DFUNCTR     = 0xB6

ILI9341_PWCTR1      = 0xC0
ILI9341_PWCTR2      = 0xC1
ILI9341_PWCTR3      = 0xC2
ILI9341_PWCTR4      = 0xC3
ILI9341_PWCTR5      = 0xC4
ILI9341_VMCTR1      = 0xC5
ILI9341_VMCTR2      = 0xC7

ILI9341_RDID1       = 0xDA
ILI9341_RDID2       = 0xDB
ILI9341_RDID3       = 0xDC
ILI9341_RDID4       = 0xDD

ILI9341_GMCTRP1     = 0xE0
ILI9341_GMCTRN1     = 0xE1

ILI9341_PWCTR6      = 0xFC

ILI9341_BLACK       = 0x0000
ILI9341_BLUE        = 0x001F
ILI9341_RED         = 0xF800
ILI9341_GREEN       = 0x07E0
ILI9341_CYAN        = 0x07FF
ILI9341_MAGENTA     = 0xF81F
ILI9341_YELLOW      = 0xFFE0
ILI9341_WHITE       = 0xFFFF


def color565(r, g, b):
    """Convert red, green, blue components to a 16-bit 565 RGB value. Components
    should be values 0 to 255.
    """
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def image_to_data(image):
    """Generator function to convert a PIL image to 16-bit 565 RGB bytes."""
    #NumPy is much faster at doing this. NumPy code provided by:
    #Keith (https://www.blogger.com/profile/02555547344016007163)
    # pb = np.array(image.convert('RGB')).astype('uint16')
    # color = ((pb[:,:,0] & 0xF8) << 8) | ((pb[:,:,1] & 0xFC) << 3) | (pb[:,:,2] >> 3)
    # return np.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist()

    # convert 24-bit RGB-8:8:8 to gBRG-3:5:5:3; then per-pixel byteswap to 16-bit RGB-5:6:5
    arr = array.array("H", image.convert("BGR;16").tobytes())
    arr.byteswap()
    return arr.tobytes()


class ILI9341(object):
    """Representation of an ILI9341 TFT LCD."""

    def __init__(self, dc=22, rst=13, led=12, width=ILI9341_TFTWIDTH,
        height=ILI9341_TFTHEIGHT, rotation=90):
        """Create an instance of the display using SPI communication.  Must
        provide the GPIO pin number for the D/C pin and the SPI driver.  Can
        optionally provide the GPIO pin number for the reset pin as the rst
        parameter.
        """
        spi = SpiDev(0, 0)
        # spi.mode = 0b10  # [CPOL|CPHA] -> polarity 1, phase 0
        spi.max_speed_hz = 64_000_000

        self._dc = dc
        self._rst = rst
        self._spi = spi
        self.width = width
        self.height = height
        self.rotation = rotation
        self.inverted = False
        # if self._gpio is None:
        #     self._gpio = GPIO.get_platform_gpio()
        # Set DC as output.

        GPIO.setmode(GPIO.BOARD)  # Use physical pin nums, not gpio labels
        GPIO.setwarnings(False)
        GPIO.setup(self._dc, GPIO.OUT)
        GPIO.output(self._dc, GPIO.HIGH)
        GPIO.setup(led, GPIO.OUT)
        GPIO.output(led, GPIO.HIGH)
        if self._rst is not None:
            GPIO.setup(self._rst, GPIO.OUT)
            GPIO.output(self._rst, GPIO.HIGH)

        # Create an image buffer.
        self.buffer = Image.new('RGB', (width, height))

    def send(self, data, is_data=True, chunk_size=4096):
        """Write a byte or array of bytes to the display. Is_data parameter
        controls if byte should be interpreted as display data (True) or command
        data (False).  Chunk_size is an optional size of bytes to write in a
        single SPI transaction, with a default of 4096.
        """
        # Set DC low for command, high for data.
        GPIO.output(self._dc, is_data)
        # Convert scalar argument to list so either can be passed as parameter.
        if isinstance(data, numbers.Number):
            data = [data & 0xFF]
        # Write data a chunk at a time.
        # for start in range(0, len(data), chunk_size):
        #     end = min(start+chunk_size, len(data))
        #     self._spi.writebytes2(data[start:end])

        self._spi.writebytes2(data)

    def command(self, data):
        """Write a byte or array of bytes to the display as command data."""
        self.send(data, False)

    def data(self, data):
        """Write a byte or array of bytes to the display as display data."""
        self.send(data, True)

    def reset(self):
        """Reset the display, if reset pin is connected."""
        if self._rst is not None:
            GPIO.output(self._rst, GPIO.HIGH)
            time.sleep(0.005)
            GPIO.output(self._rst, GPIO.LOW)
            time.sleep(0.02)
            GPIO.output(self._rst, GPIO.HIGH)
            time.sleep(0.150)

    def _init(self):
        # Initialize the display.  Broken out as a separate function so it can
        # be overridden by other displays in the future.
        self.command(0xEF)
        self.data(0x03)
        self.data(0x80)
        self.data(0x02)
        self.command(0xCF)
        self.data(0x00)
        self.data(0XC1)
        self.data(0X30)
        self.command(0xED)
        self.data(0x64)
        self.data(0x03)
        self.data(0X12)
        self.data(0X81)
        self.command(0xE8)
        self.data(0x85)
        self.data(0x00)
        self.data(0x78)
        self.command(0xCB)
        self.data(0x39)
        self.data(0x2C)
        self.data(0x00)
        self.data(0x34)
        self.data(0x02)
        self.command(0xF7)
        self.data(0x20)
        self.command(0xEA)
        self.data(0x00)
        self.data(0x00)
        self.command(ILI9341_PWCTR1)    # Power control
        self.data(0x23)                    # VRH[5:0]
        self.command(ILI9341_PWCTR2)    # Power control
        self.data(0x10)                    # SAP[2:0];BT[3:0]
        self.command(ILI9341_VMCTR1)    # VCM control
        self.data(0x3e)
        self.data(0x28)
        self.command(ILI9341_VMCTR2)    # VCM control2
        self.data(0x86)                    # --
        self.command(ILI9341_MADCTL)    #  Memory Access Control
        self.data(0x48)
        self.command(ILI9341_PIXFMT)
        self.data(0x55)
        self.command(ILI9341_FRMCTR1)
        self.data(0x00)
        self.data(0x18)
        self.command(ILI9341_DFUNCTR)    #  Display Function Control
        self.data(0x08)
        self.data(0x82)
        self.data(0x27)
        self.command(0xF2)                #  3Gamma Function Disable
        self.data(0x00)
        self.command(ILI9341_GAMMASET)    # Gamma curve selected
        self.data(0x01)
        self.command(ILI9341_GMCTRP1)    # Set Gamma
        self.data(0x0F)
        self.data(0x31)
        self.data(0x2B)
        self.data(0x0C)
        self.data(0x0E)
        self.data(0x08)
        self.data(0x4E)
        self.data(0xF1)
        self.data(0x37)
        self.data(0x07)
        self.data(0x10)
        self.data(0x03)
        self.data(0x0E)
        self.data(0x09)
        self.data(0x00)
        self.command(ILI9341_GMCTRN1)    # Set Gamma
        self.data(0x00)
        self.data(0x0E)
        self.data(0x14)
        self.data(0x03)
        self.data(0x11)
        self.data(0x07)
        self.data(0x31)
        self.data(0xC1)
        self.data(0x48)
        self.data(0x08)
        self.data(0x0F)
        self.data(0x0C)
        self.data(0x31)
        self.data(0x36)
        self.data(0x0F)
        self.command(ILI9341_SLPOUT)    # Exit Sleep
        time.sleep(0.120)
        self.command(ILI9341_DISPON)    # Display on

    def begin(self):
        """Initialize the display.  Should be called once before other calls that
        interact with the display are called.
        """
        self.reset()
        self._init()

    def invert(self, state: bool = True):
        """Sets display inversion to the specified state. If not provided, state
        is True, which inverts the display. If state is False, the display turns
        back into normal mode."""
        if state:
            self.command(ILI9341_INVON)
        else:
            self.command(ILI9341_INVOFF)
        self.inverted = state
        return self

    def set_window(self, x0=0, y0=0, x1=None, y1=None):
        """Set the pixel address window for proceeding drawing commands. x0 and
        x1 should define the minimum and maximum x pixel bounds.  y0 and y1
        should define the minimum and maximum y pixel bound.  If no parameters
        are specified the default will be to update the entire display from 0,0
        to 239,319.
        """
        if x1 is None:
            x1 = self.width-1
        if y1 is None:
            y1 = self.height-1
        self.command(ILI9341_CASET)        # Column addr set
        self.data(x0 >> 8)
        self.data(x0)                    # XSTART
        self.data(x1 >> 8)
        self.data(x1)                    # XEND
        self.command(ILI9341_PASET)        # Row addr set
        self.data(y0 >> 8)
        self.data(y0)                    # YSTART
        self.data(y1 >> 8)
        self.data(y1)                    # YEND
        self.command(ILI9341_RAMWR)        # write to RAM

    def display(self, image=None):
        """Write the display buffer or provided image to the hardware.  If no
        image parameter is provided the display buffer will be written to the
        hardware.  If an image is provided, it should be RGB format and the
        same dimensions as the display hardware.
        """
        # By default write the internal buffer to the display.
        if image is None:
            image = self.buffer
        # Set address bounds to entire display.
        self.set_window()
        # Convert image to array of 16bit 565 RGB data bytes.
        # Unfortunate that this copy has to occur, but the SPI byte writing
        # function needs to take an array of bytes and PIL doesn't natively
        # store images in 16-bit 565 RGB format.
        pixelbytes = image_to_data(image.rotate(self.rotation, expand=True))
        # Write data to hardware.
        self.data(pixelbytes)

    def ShowImage(self, image, x, y):
        self.display(image)

    def clear(self, color=(0,0,0)):
        """Clear the image buffer to the specified RGB color (default black)."""
        width, height = self.buffer.size
        self.buffer.putdata([color]*(width*height))

    def draw(self):
        """Return a PIL ImageDraw instance for 2D drawing on the image buffer."""
        return ImageDraw.Draw(self.buffer)