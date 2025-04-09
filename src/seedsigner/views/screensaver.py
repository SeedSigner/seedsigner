import logging
import os
import random
import time

from dataclasses import dataclass
from gettext import gettext as _

from seedsigner.gui.components import Fonts, GUIConstants, load_image
from seedsigner.gui.screens.screen import BaseScreen
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views.view import View

logger = logging.getLogger(__name__)



# TODO: This early code is now outdated vis-a-vis Screen vs View distinctions
class LogoScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.logo = load_image("logo_black_240.png")

        self.partners = [
            "hrf",
        ]

        self.partner_logos: dict = {}
        for partner in self.partners:
            logo_url = os.path.join("partners", f"{partner}_logo.png")
            self.partner_logos[partner] = load_image(logo_url)


    def _run(self):
        pass


    def get_random_partner(self) -> str:
        return self.partners[random.randrange(len(self.partners))]



@dataclass
class OpeningSplashView(View):
    is_screenshot_renderer: bool = False
    force_partner_logos: bool|None = None

    def run(self):
        self.run_screen(
            OpeningSplashScreen,
            is_screenshot_renderer=self.is_screenshot_renderer,
            force_partner_logos=self.force_partner_logos
        )



class OpeningSplashScreen(LogoScreen):
    def __init__(self, is_screenshot_renderer=False, force_partner_logos=None):
        self.is_screenshot_renderer = is_screenshot_renderer
        self.force_partner_logos = force_partner_logos
        super().__init__()


    def _render(self):
        from PIL import Image
        from seedsigner.controller import Controller
        controller = Controller.get_instance()

        # TODO: Fix for the screenshot generator. When generating screenshots for
        # multiple locales, there is a button still in the canvas from the previous
        # screenshot, even though the Renderer has been reconfigured and re-
        # instantiated. This is a hack to clear the screen for now.
        self.clear_screen()

        show_partner_logos = Settings.get_instance().get_value(SettingsConstants.SETTING__PARTNER_LOGOS) == SettingsConstants.OPTION__ENABLED
        if self.force_partner_logos is not None:
            show_partner_logos = self.force_partner_logos

        if show_partner_logos:
            logo_offset_y = -56
        else:
            logo_offset_y = 0

        background = Image.new("RGBA", size=self.logo.size, color="black")
        if not self.is_screenshot_renderer:
            # Fade in alpha
            for i in range(250, -1, -25):
                self.logo.putalpha(255 - i)
                self.renderer.canvas.paste(Image.alpha_composite(background, self.logo), (0, logo_offset_y))
                self.renderer.show_image()
        else:
            # Skip animation for the screenshot generator
            self.renderer.canvas.paste(self.logo, (0, logo_offset_y))

        # Display version num below SeedSigner logo
        font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_top_nav_title_font_size())
        version = f"v{controller.VERSION}"

        # The logo png is 240x240, but the actual logo is 70px tall, vertically centered
        logo_height = 70
        version_x = int(self.renderer.canvas_width/2)
        version_y = int(self.canvas_height/2) + int(logo_height/2) + logo_offset_y + GUIConstants.COMPONENT_PADDING
        self.renderer.draw.text(xy=(version_x, version_y), text=version, font=font, fill=GUIConstants.ACCENT_COLOR, anchor="mt")

        if not self.is_screenshot_renderer:
            self.renderer.show_image()

        if show_partner_logos:
            if not self.is_screenshot_renderer:
                # Hold on the version num for a moment
                time.sleep(1)

            # Set up the partner logo
            partner_logo: Image.Image = self.partner_logos[self.get_random_partner()]
            font = Fonts.get_font(GUIConstants.get_top_nav_title_font_name(), GUIConstants.get_body_font_size())
            # TRANSLATOR_NOTE: This is on the opening splash screen, displayed above the HRF logo
            sponsor_text = _("With support from:")
            (left, top, tw, th) = font.getbbox(sponsor_text, anchor="lt")

            x = int((self.renderer.canvas_width) / 2)
            y = self.canvas_height - GUIConstants.COMPONENT_PADDING - partner_logo.height - int(GUIConstants.COMPONENT_PADDING/2) - th
            self.renderer.draw.text(xy=(x, y), text=sponsor_text, font=font, fill="#ccc", anchor="mt")
            self.renderer.canvas.paste(
                partner_logo,
                (
                    int((self.renderer.canvas_width - partner_logo.width) / 2),
                    y + th + int(GUIConstants.COMPONENT_PADDING/2)
                )
            )

            self.renderer.show_image()

        if not self.is_screenshot_renderer:
            # Hold on the splash screen for a moment
            time.sleep(2)



class ScreensaverScreen(LogoScreen):
    def __init__(self, buttons):
        from PIL import Image
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
            try:
                while self._is_running:
                    if self.buttons.has_any_input() or self.buttons.override_ind:
                        break

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

            except KeyboardInterrupt as e:
                # Exit triggered; close gracefully
                logger.info("Shutting down Screensaver")

                # Have to let the interrupt bubble up to exit the main app
                raise e

            finally:
                self._is_running = False

                # Restore the original screen
                self.renderer.show_image(self.last_screen)



    def stop(self):
        self._is_running = False


