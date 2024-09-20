import os
from PIL import Image, ImageDraw
from seedsigner.gui.renderer import Renderer



class ScreenshotComplete(Exception):
    pass



class ScreenshotRenderer(Renderer):
    screenshot_path: str = None
    screenshot_filename: str = None

    @classmethod
    def configure_instance(cls):
        # Instantiate the one and only Renderer instance
        renderer = cls.__new__(cls)
        cls._instance = renderer

        # Hard-coding output values for now
        renderer.canvas_width = 240
        renderer.canvas_height = 240

        renderer.canvas = Image.new('RGB', (renderer.canvas_width, renderer.canvas_height))
        renderer.draw = ImageDraw.Draw(renderer.canvas)
    

    def set_screenshot_filename(self, filename:str):
        self.screenshot_filename = filename
    

    def set_screenshot_path(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
        self.screenshot_path = path


    def show_image(self, image=None, alpha_overlay=None, is_background_thread: bool = False):
        if is_background_thread:
            return

        if alpha_overlay:
            if image == None:
                image = self.canvas
            image = Image.alpha_composite(image, alpha_overlay)

        if image:
            # Always write to the current canvas, rather than trying to replace it
            self.canvas.paste(image)

        self.canvas.save(os.path.join(self.screenshot_path, self.screenshot_filename))
        raise ScreenshotComplete()

