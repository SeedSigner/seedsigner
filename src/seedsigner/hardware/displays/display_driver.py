DISPLAY_TYPE__ST7789 = "st7789"
DISPLAY_TYPE__ILI9341 = "ili9341"
DISPLAY_TYPE__ILI9486 = "ili9486"

ALL_DISPLAY_TYPES = [DISPLAY_TYPE__ST7789, DISPLAY_TYPE__ILI9341, DISPLAY_TYPE__ILI9486]


class DisplayDriver:
    def __init__(self, display_type: str = DISPLAY_TYPE__ST7789, width: int = None, height: int = None):
        if display_type not in ALL_DISPLAY_TYPES:
            raise ValueError(f"Invalid display type: {display_type}")
        self.display_type = display_type

        if self.display_type == DISPLAY_TYPE__ST7789:
            if height not in [240, 320] or width != 240:
                raise ValueError("ST7789 display only supports 240x240 or 320x240 resolutions")

            if height == 240:
                # TODO: For now the original ST7789 driver has to be used for 240x240.
                # The mpy version below renders incorrectly (almost like each row of pixels
                # is one pixel short, so the entire screen exhibits a diagonal skew).
                from seedsigner.hardware.displays.ST7789 import ST7789
                self.display = ST7789()

            elif height == 320:
                from seedsigner.hardware.displays.st7789_mpy import ST7789
                self.display = ST7789(width=width, height=height)
        
        elif self.display_type == DISPLAY_TYPE__ILI9341:
            from seedsigner.hardware.displays.ili9341 import ILI9341
            self.display = ILI9341()
            self.display.begin()
        
        elif self.display_type == DISPLAY_TYPE__ILI9486:
            # TODO: improve performance of ili9486 driver
            raise Exception("ILI9486 display not implemented yet")
    

    def __str__(self):
        return f"DisplayDriver(display_type={self.display_type}, width={self.width}, height={self.height})"


    @property
    def width(self):
        return self.display.width


    @property
    def height(self):
        return self.display.height


    def invert(self, enabled: bool = True):
        """Invert how the display interprets colors"""
        self.display.invert(enabled)


    def show_image(self, image, x_start: int = 0, y_start: int = 0):
        self.display.show_image(image, x_start, y_start)