import os
import random
import time

from PIL import Image, ImageDraw

from .view import View

from seedsigner.gui.components import Fonts, GUIConstants, load_image



# TODO: Should be derived from View?
class LogoView:
    def __init__(self):
        from seedsigner.gui import Renderer
        self.renderer = Renderer.get_instance()
        self.logo = load_image("logo_black_240.png")



class OpeningSplashView(LogoView):
    def start(self):
        from seedsigner.controller import Controller
        controller = Controller.get_instance()

        # Fade in alpha
        for i in range(250, -1, -25):
            self.logo.putalpha(255 - i)
            background = Image.new("RGBA", self.logo.size, (0,0,0))
            self.renderer.disp.ShowImage(Image.alpha_composite(background, self.logo), 0, 0)

        # Display version num and hold for a few seconds
        font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.TOP_NAV_TITLE_FONT_SIZE)
        version = f"v{controller.VERSION}"
        tw, th = font.getsize(version)
        x = int((self.renderer.canvas_width - tw) / 2)
        y = int(self.renderer.canvas_height / 2) + 40

        draw = ImageDraw.Draw(self.logo)
        draw.text((x, y), version, fill=GUIConstants.ACCENT_COLOR, font=font)
        self.renderer.show_image(self.logo)
        time.sleep(3)



class ScreensaverView(LogoView):
    def __init__(self, buttons):
        super().__init__()

        self.buttons = buttons

        # Paste the logo in a bigger image that is 2x the size of the logo
        self.image = Image.new("RGB", (2 * self.logo.size[0], 2 * self.logo.size[1]), (0,0,0))
        self.image.paste(self.logo, (int(self.logo.size[0] / 2), int(self.logo.size[1] / 2)))

        self.min_coords = (0, 0)
        self.max_coords = (self.logo.size[0], self.logo.size[1])

        self.increment_x = self.rand_increment()
        self.increment_y = self.rand_increment()
        self.cur_x = int(self.logo.size[0] / 2)
        self.cur_y = int(self.logo.size[1] / 2)

        self._is_running = False
        self.last_screen = None


    @property
    def is_running(self):
        return self._is_running
    

    def rand_increment(self):
        max_increment = 10.0
        min_increment = 1.0
        increment = random.uniform(min_increment, max_increment)
        if random.uniform(-1.0, 1.0) < 0.0:
            return -1.0 * increment
        return increment


    def start(self):
        if self.is_running:
            return

        self._is_running = True

        # Store the current screen in order to restore it later
        self.last_screen = self.renderer.canvas.copy()

        screensaver_start = int(time.time() * 1000)

        # Screensaver must block any attempts to use the Renderer in another thread so it
        # never gives up the lock until it returns.
        with self.renderer.lock:
            while True:
                if self.buttons.has_any_input():
                    return self.stop()

                # Must crop the image to the exact display size
                crop = self.image.crop((
                    self.cur_x, self.cur_y,
                    self.cur_x + self.renderer.canvas_width, self.cur_y + self.renderer.canvas_height))
                self.renderer.disp.ShowImage(crop, 0, 0)

                self.cur_x += self.increment_x
                self.cur_y += self.increment_y

                # At each edge bump, calculate a new random rate of change for that axis
                if self.cur_x < self.min_coords[0]:
                    self.cur_x = self.min_coords[0]
                    self.increment_x = self.rand_increment()
                    if self.increment_x < 0.0:
                        self.increment_x *= -1.0
                elif self.cur_x > self.max_coords[0]:
                    self.cur_x = self.max_coords[0]
                    self.increment_x = self.rand_increment()
                    if self.increment_x > 0.0:
                        self.increment_x *= -1.0

                if self.cur_y < self.min_coords[1]:
                    self.cur_y = self.min_coords[1]
                    self.increment_y = self.rand_increment()
                    if self.increment_y < 0.0:
                        self.increment_y *= -1.0
                elif self.cur_y > self.max_coords[1]:
                    self.cur_y = self.max_coords[1]
                    self.increment_y = self.rand_increment()
                    if self.increment_y > 0.0:
                        self.increment_y *= -1.0


    def stop(self):
        # Restore the original screen
        self.renderer.show_image(self.last_screen)

        self._is_running = False


