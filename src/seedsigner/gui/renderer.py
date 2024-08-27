from PIL import Image, ImageDraw
from threading import Lock

from seedsigner.hardware.ST7789 import ST7789
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

        # Eventually we'll be able to plug in other display controllers
        renderer.disp = ST7789()
        renderer.canvas_width = renderer.disp.width
        renderer.canvas_height = renderer.disp.height

        renderer.canvas = Image.new('RGB', (renderer.canvas_width, renderer.canvas_height))
        renderer.draw = ImageDraw.Draw(renderer.canvas)


    def show_image(self, image=None, alpha_overlay=None, show_direct=False):
        if show_direct:
            # Use the incoming image as the canvas and immediately render
            self.disp.ShowImage(image, 0, 0)
            return

        if alpha_overlay:
            if image == None:
                image = self.canvas
            image = Image.alpha_composite(image, alpha_overlay)

        if image:
            # Always write to the current canvas, rather than trying to replace it
            self.canvas.paste(image)

        self.disp.ShowImage(self.canvas, 0, 0)


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

            self.disp.ShowImage(crop, 0, 0)



    def display_blank_screen(self):
        self.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)
        self.show_image()
