import os

from dataclasses import dataclass
from PIL import Image, ImageDraw

from seedsigner.gui.renderer import Renderer
from seedsigner.gui.toast import BaseToastOverlayManagerThread
from seedsigner.views.view import View



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



@dataclass
class ScreenshotConfig:
    View_cls: View
    view_kwargs: dict = None
    screenshot_name: str = None
    toast_thread: BaseToastOverlayManagerThread = None
    run_before: callable = None
    run_after: callable = None


    def __post_init__(self):
        if not self.view_kwargs:
            self.view_kwargs = {}
        if not self.screenshot_name:
            self.screenshot_name = self.View_cls.__name__


    def run_callback_before(self):
        if self.run_before:
            self.run_before()
    

    def run_callback_after(self):
        if self.run_after:
            self.run_after()
