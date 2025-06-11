from periphery import GPIO, SPI
import time
import array



class ST7789(object):
    """class for ST7789  240*240 1.3inch OLED displays."""

    def __init__(self):
        self.width = 240
        self.height = 240

        # Initialize DC RST pin using BCM numbering
        self._dc = GPIO("/dev/gpiochip0", 25, "out")
        self._rst = GPIO("/dev/gpiochip0", 27, "out")
        self._bl = GPIO("/dev/gpiochip0", 24, "out")
        self._bl.write(True)

        # Initialize SPI
        self._spi = SPI("/dev/spidev0.0", 0, 40000000)  # mode 0, 40MHz
        self.init()


    """    Write register address and data     """
    def command(self, cmd):
        """Write register address"""
        self._dc.write(False)
        self._spi.transfer([cmd])

    def data(self, val):
        """Write data"""
        self._dc.write(True)
        self._spi.transfer([val])

    def init(self):
        """Initialize dispaly"""    
        self.reset()

        self.command(0x36)
        self.data(0x70)                 #self.data(0x00)

        self.command(0x3A) 
        self.data(0x05)

        self.command(0xB2)
        self.data(0x0C)
        self.data(0x0C)
        self.data(0x00)
        self.data(0x33)
        self.data(0x33)

        self.command(0xB7)
        self.data(0x35) 

        self.command(0xBB)
        self.data(0x19)

        self.command(0xC0)
        self.data(0x2C)

        self.command(0xC2)
        self.data(0x01)

        self.command(0xC3)
        self.data(0x12)   

        self.command(0xC4)
        self.data(0x20)

        self.command(0xC6)
        self.data(0x0F) 

        self.command(0xD0)
        self.data(0xA4)
        self.data(0xA1)

        self.command(0xE0)
        self.data(0xD0)
        self.data(0x04)
        self.data(0x0D)
        self.data(0x11)
        self.data(0x13)
        self.data(0x2B)
        self.data(0x3F)
        self.data(0x54)
        self.data(0x4C)
        self.data(0x18)
        self.data(0x0D)
        self.data(0x0B)
        self.data(0x1F)
        self.data(0x23)

        self.command(0xE1)
        self.data(0xD0)
        self.data(0x04)
        self.data(0x0C)
        self.data(0x11)
        self.data(0x13)
        self.data(0x2C)
        self.data(0x3F)
        self.data(0x44)
        self.data(0x51)
        self.data(0x2F)
        self.data(0x1F)
        self.data(0x1F)
        self.data(0x20)
        self.data(0x23)
        
        self.command(0x21)  # inversion ON; 0x20 = inversion OFF

        self.command(0x11)

        self.command(0x29)

    def reset(self):
        """Reset the display"""
        self._rst.write(True)
        time.sleep(0.01)
        self._rst.write(False)
        time.sleep(0.01)
        self._rst.write(True)
        time.sleep(0.01)
        
    def SetWindows(self, Xstart, Ystart, Xend, Yend):
        #set the X coordinates
        self.command(0x2A)
        self.data(0x00)               #Set the horizontal starting point to the high octet
        self.data(Xstart & 0xff)      #Set the horizontal starting point to the low octet
        self.data(0x00)               #Set the horizontal end to the high octet
        self.data((Xend - 1) & 0xff) #Set the horizontal end to the low octet 
        
        #set the Y coordinates
        self.command(0x2B)
        self.data(0x00)
        self.data((Ystart & 0xff))
        self.data(0x00)
        self.data((Yend - 1) & 0xff )

        self.command(0x2C)    
    
    def show_image(self,Image,Xstart,Ystart):
        """Set buffer to value of Python Imaging Library image."""
        """Write display buffer to physical display"""
        imwidth, imheight = Image.size
        if imwidth != self.width or imheight != self.height:
            raise ValueError('Image must be same dimensions as display \
                ({0}x{1}).' .format(self.width, self.height))
        # convert 24-bit RGB-8:8:8 to gBRG-3:5:5:3; then per-pixel byteswap to 16-bit RGB-5:6:5
        arr = array.array("H", Image.convert("BGR;16").tobytes())
        arr.byteswap()
        pix = arr.tobytes()
        self.SetWindows ( 0, 0, self.width, self.height)
        self._dc.write(True)
        self._spi.transfer(pix)
        
    def clear(self):
        """Clear contents of image buffer"""
        _buffer = [0xff]*(self.width * self.height * 2)
        self.SetWindows ( 0, 0, self.width, self.height)
        self._dc.write(True)
        self._spi.transfer(_buffer)

    def invert(self, enabled: bool = True):
        """Invert how the display interprets colors"""
        self.command(0x21 if enabled else 0x20)

    def __del__(self):
        """Cleanup when object is destroyed"""
        self._dc.close()
        self._rst.close()
        self._bl.close()
        self._spi.close()