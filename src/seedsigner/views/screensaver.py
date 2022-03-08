import os
import random
import time

from PIL import Image, ImageDraw

from . import View

from seedsigner.helpers import B, touchscreen


class LogoView(View):
    def __init__(self, disp, q):
        print("inside logo")
        # View.disp = touchscreen.touchscreen()
        # View.disp.Init()
        View.disp = disp
        dirname = os.path.dirname(__file__)
        logo_url = os.path.join(dirname, "../../", "seedsigner", "resources", "logo_black_240.png")
        self.logo = Image.open(logo_url)
        View.canvas_width = View.WIDTH
        View.canvas_height = View.HEIGHT
        View.canvas = Image.new('RGB', (View.canvas_width, View.canvas_height))
        View.draw = ImageDraw.Draw(View.canvas)
        



class OpeningSplashView(LogoView):
    def start(self):
        from seedsigner.controller import Controller
        controller = Controller.get_instance()

        # Fade in alpha
        for i in range(250, -1, -25):
            self.logo.putalpha(255 - i)
            background = Image.new("RGBA", self.logo.size, (0,0,0))
            # View.disp.ShowImage(Image.alpha_composite(background, self.logo), 0, 0)
            View.q.put((Image.alpha_composite(background, self.logo), 0, 0))

        # Display version num and hold for a few seconds
        font = View.ROBOTOCONDENSED_REGULAR_22
        version = f"v{controller.VERSION}"
        tw, th = font.getsize(version)
        x = int((View.canvas_width - tw) / 2)
        y = int(View.canvas_height / 2) + 40

        draw = ImageDraw.Draw(self.logo)
        draw.text((x, y), version, fill="orange", font=font)
        View.DispShowImage(self.logo)
        time.sleep(3)



class ScreensaverView(LogoView):
    def __init__(self, buttons, disp, q):
        super().__init__(disp, q)

        self.buttons = buttons

        # Paste the logo in a bigger image that is 2x the size of the logo
        self.image = Image.new("RGB", (2 * self.logo.size[0], 2 * self.logo.size[1]), (0,0,0))
        self.image.paste(self.logo, (int(self.logo.size[0] / 2), int(self.logo.size[1] / 2)))

        self.min_coords = (0, 0)
        self.max_coords = (self.logo.size[0], self.logo.size[1])

        max_increment = 25
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
        self.last_screen = View.canvas.copy()

        screensaver_start = int(time.time() * 1000)

        while True:
            if self.buttons.has_any_input():
                return self.stop()

            # Must crop the image to the exact display size
            crop = self.image.crop((
                self.cur_x, self.cur_y,
                self.cur_x + View.canvas_width, self.cur_y + View.canvas_height))
            View.disp.ShowImage(crop, 0, 0)

            self.cur_x += self.increment_x
            self.cur_y += self.increment_y

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
        View.DispShowImage(self.last_screen)

        self._is_running = False


