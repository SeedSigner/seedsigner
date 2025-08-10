from PIL import Image, ImageDraw
from threading import Lock

# from seedsigner.hardware.st7789_mpy import ST7789
from seedsigner.hardware.displays.display_driver import ALL_DISPLAY_TYPES, DISPLAY_TYPE__ILI9341, DISPLAY_TYPE__ILI9486, DISPLAY_TYPE__ST7789, DisplayDriver
from seedsigner.hardware.displays.ili9341 import ILI9341, ILI9341_TFTWIDTH, ILI9341_TFTHEIGHT
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.models.singleton import ConfigurableSingleton



class Renderer(ConfigurableSingleton):
    buttons = None
    canvas_width = 0
    canvas_height = 0
    canvas: Image.Image = None
    draw: ImageDraw.ImageDraw = None
    disp = None
    lock = Lock()


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

        display_config = Settings.get_instance().get_value(SettingsConstants.SETTING__DISPLAY_CONFIGURATION, default_if_none=True)
        self.display_type = display_config.split("_")[0]
        if self.display_type not in ALL_DISPLAY_TYPES:
            raise Exception(f"Invalid display type: {self.display_type}")

        width, height = display_config.split("_")[1].split("x")
        self.disp = DisplayDriver(self.display_type, width=int(width), height=int(height))

        if Settings.get_instance().get_value(SettingsConstants.SETTING__DISPLAY_COLOR_INVERTED, default_if_none=True) == SettingsConstants.OPTION__ENABLED:
            self.disp.invert()

        if self.display_type == DISPLAY_TYPE__ST7789:
            self.canvas_width = self.disp.width
            self.canvas_height = self.disp.height

        elif self.display_type in [DISPLAY_TYPE__ILI9341, DISPLAY_TYPE__ILI9486]:
            # Swap for the natively portrait-oriented displays
            self.canvas_width = self.disp.height
            self.canvas_height = self.disp.width

        self.canvas = Image.new('RGB', (self.canvas_width, self.canvas_height))
        self.draw = ImageDraw.Draw(self.canvas)

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
