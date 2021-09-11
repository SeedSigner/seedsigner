import os
import time
from PIL import Image, ImageDraw
from . import View



class OpeningSplashView(View):

    def __init__(self):
        logo_url = os.path.join("seedsigner", "resources", "logo_black_240.png")
        self.logo = Image.open(logo_url)


    def start(self):
        from seedsigner.controller import Controller
        controller = Controller.get_instance()

        # Fade in alpha
        for i in range(250, -1, -25):
            self.logo.putalpha(255 - i)
            background = Image.new("RGBA", self.logo.size, (0,0,0))
            View.disp.ShowImage(Image.alpha_composite(background, self.logo), 0, 0)

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



class ScreensaverView(OpeningSplashView):
    def start(self):
        pass


    def stop(self):
        pass