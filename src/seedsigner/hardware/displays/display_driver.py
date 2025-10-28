from dataclasses import dataclass


DISPLAY_TYPE__ST7789 = "st7789"
DISPLAY_TYPE__ILI9341 = "ili9341"
DISPLAY_TYPE__ILI9486 = "ili9486"

ALL_DISPLAY_TYPES = [DISPLAY_TYPE__ST7789, DISPLAY_TYPE__ILI9341, DISPLAY_TYPE__ILI9486]

    

@dataclass
class BaseDisplayDriver:
    _width: int
    _height: int

    def __str__(self):
        return f"DisplayDriver(display_type={getattr(self, 'display_type', None)}, width={self.width}, height={self.height})"


    @property
    def width(self):
        return self._width


    @property
    def height(self):
        return self._height


    def invert(self, enabled: bool = True):
        """
        Invert how the display interprets colors.
        Implementation in child classes is optional.
        """
        pass


    def show_image(self, image, x_start: int = 0, y_start: int = 0):
        """
        The main rendering call to the display driver.
        Must be implemented in child classes.
        """
        raise Exception("show_image() must be implemented in child classes")


    def cleanup(self):
        """
        Cleanup resources used by the display driver.
        Implementation in child classes is optional.
        """
        pass


    class GammaCurveSettingNotSupported(Exception):
        pass


    class InvalidGammaCurveValue(Exception):
        pass


    @property
    def available_gamma_curves(self) -> list[tuple[str, str]]:
        """
        Return the list of available gamma curves for the display.

        Tuple consists of: (human-readable name, settings value)
        """
        return []
    

    @property
    def default_gamma_curve(self) -> str | None:
        """
        Return the default gamma curve Settings value for the display, or None if not applicable.
        """
        return None


    def set_gamma_curve(self, curve: str) -> None | GammaCurveSettingNotSupported | InvalidGammaCurveValue:
        """
        Select the gamma curve for the display. Expects the Settings value.
        """
        raise BaseDisplayDriver.GammaCurveSettingNotSupported()



class DisplayDriverFactory:
    """
    Manages all logic related to instantiating display drivers based on type and resolution.

    Imports for specific display drivers are done within this class to avoid circular imports.
    """

    @classmethod
    def instantiate_display_driver(cls, display_type: str = DISPLAY_TYPE__ST7789, width: int = None, height: int = None, gamma_curve: str = None) -> BaseDisplayDriver:
        if display_type not in ALL_DISPLAY_TYPES:
            raise ValueError(f"Invalid display type: {display_type}")

        if display_type == DISPLAY_TYPE__ST7789:
            if width not in [240, 320] or height != 240:
                raise ValueError("ST7789 display only supports 240x240 or 320x240 resolutions")

            if width == 240:
                # TODO: For now the original ST7789 driver has to be used for 240x240.
                # The mpy version below renders incorrectly (almost like each row of pixels
                # is one pixel short, so the entire screen exhibits a diagonal skew).
                from seedsigner.hardware.displays.ST7789 import ST7789 as original_ST7789
                return original_ST7789(_width=width, _height=height, initial_gamma_curve=gamma_curve)

            elif width == 320:
                from seedsigner.hardware.displays.st7789_mpy import ST7789 as mpy_ST7789
                # Have to swap width and height; screen is natively 240x320
                return mpy_ST7789(_width=height, _height=width, initial_gamma_curve=gamma_curve)

        elif display_type == DISPLAY_TYPE__ILI9341:
            from seedsigner.hardware.displays.ili9341 import ILI9341
            display = ILI9341(_width=width, _height=height)
            display.begin()
            return display
        
        elif display_type == DISPLAY_TYPE__ILI9486:
            # TODO: improve performance of ili9486 driver
            raise Exception("ILI9486 display not implemented yet")
