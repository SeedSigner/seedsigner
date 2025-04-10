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


class BaseLogoScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.logo = load_image("logo_black_240.png")
        self.load_partner_logos()

    def load_partner_logos(self):
        self.partners = ["hrf"]
        self.partner_logos = {}
        for partner in self.partners:
            logo_url = os.path.join("partners", f"{partner}_logo.png")
            self.partner_logos[partner] = load_image(logo_url)

    def get_random_partner(self) -> str:
        return self.partners[random.randrange(len(self.partners))]
    
    def animate_fade_in(self, image, offset_y=0, skip_animation=False):
        from PIL import Image
        background = Image.new("RGBA", size=image.size, color="black")
        if not skip_animation:
            for i in range(250, -1, -25):
                image.putalpha(255 - i)
                self.renderer.canvas.paste(Image.alpha_composite(background, image), (0, offset_y))
                self.renderer.show_image()
        else:
            self.renderer.canvas.paste(image, (0, offset_y))
    
    def display_version(self, version, offset_y=0):
        font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_top_nav_title_font_size())
        logo_height = 70
        version_x = int(self.renderer.canvas_width/2)
        version_y = int(self.canvas_height/2) + int(logo_height/2) + offset_y + GUIConstants.COMPONENT_PADDING
        self.renderer.draw.text(xy=(version_x, version_y), text=version, font=font, fill=GUIConstants.ACCENT_COLOR, anchor="mt")
    
    def display_partner_logo(self, partner=None, skip_animation=False):
        if not partner:
            partner = self.get_random_partner()
        partner_logo = self.partner_logos[partner]
        font = Fonts.get_font(GUIConstants.get_top_nav_title_font_name(), GUIConstants.get_body_font_size())
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
        if not skip_animation:
            self.renderer.show_image()


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


class OpeningSplashScreen(BaseLogoScreen):
    def __init__(self, is_screenshot_renderer=False, force_partner_logos=None):
        self.is_screenshot_renderer = is_screenshot_renderer
        self.force_partner_logos = force_partner_logos
        super().__init__()
    
    def _render(self):
        from seedsigner.controller import Controller
        controller = Controller.get_instance()
        self.clear_screen()

        show_partner_logos = Settings.get_instance().get_value(SettingsConstants.SETTING__PARTNER_LOGOS) == SettingsConstants.OPTION__ENABLED
        if self.force_partner_logos is not None:
            show_partner_logos = self.force_partner_logos

        logo_offset_y = -56 if show_partner_logos else 0

        self.animate_fade_in(self.logo, logo_offset_y, skip_animation=self.is_screenshot_renderer)
        version = f"v{controller.VERSION}"
        self.display_version(version, logo_offset_y)
        if not self.is_screenshot_renderer:
            self.renderer.show_image()

        if show_partner_logos:
            if not self.is_screenshot_renderer:
                time.sleep(1)
            self.display_partner_logo(skip_animation=self.is_screenshot_renderer)

        if not self.is_screenshot_renderer:
            time.sleep(2)


@dataclass
class ToolsImageEntropyLivePreviewScreen(BaseScreen):
    def __post_init__(self):
        super().__post_init__()

        self.camera = Camera.get_instance()
        self.camera.start_video_stream_mode(resolution=(self.canvas_width, self.canvas_height), framerate=24, format="rgb")

    def _run(self):
        # save preview image frames to use as additional entropy below
        preview_images = []
        max_entropy_frames = 50
        instructions_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_button_font_size())

        while True:
            if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                # Have to manually update last input time since we're not in a wait_for loop
                self.hw_inputs.update_last_input_time()
                self.camera.stop_video_stream_mode()
                return RET_CODE__BACK_BUTTON

            frame = self.camera.read_video_stream(as_image=True)

            if frame is None:
                # Camera probably isn't ready yet
                time.sleep(0.01)
                continue

            # Check for ANYCLICK to take final entropy image
            if self.hw_inputs.check_for_low(keys=HardwareButtonsConstants.KEYS__ANYCLICK):
                # Have to manually update last input time since we're not in a wait_for loop
                self.hw_inputs.update_last_input_time()
                self.camera.stop_video_stream_mode()

                with self.renderer.lock:
                    self.renderer.canvas.paste(frame)

                    self.render_bottom_instruction_text(
                        draw=self.renderer.draw,
                        text=_("Capturing image..."),
                        fill_color=GUIConstants.ACCENT_COLOR,
                        font=instructions_font
                    )
                    self.renderer.show_image()

                return preview_images

            # If we're still here, it's just another preview frame loop
            with self.renderer.lock:
                self.renderer.canvas.paste(frame)

                # Use the standardized helper method instead of manual text rendering
                instruction_text = "< " + _("back") + "  |  " + _("click a button")  # TODO: Render with UI elements instead of text
                self.render_bottom_instruction_text(
                    draw=self.renderer.draw,
                    text=instruction_text,
                    font=instructions_font
                )
                self.renderer.show_image()

            if len(preview_images) == max_entropy_frames:
                # Keep a moving window of the last n preview frames; pop the oldest
                # before we add the current frame.
                preview_images.pop(0)
            preview_images.append(frame)


class ScreensaverScreen(BaseLogoScreen):
    def __init__(self, buttons):
        from PIL import Image
        super().__init__()

        self.buttons = buttons
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

        self.last_screen = self.renderer.canvas.copy()

        screensaver_start = int(time.time() * 1000)

        with self.renderer.lock:
            try:
                while self._is_running:
                    if self.buttons.has_any_input() or self.buttons.override_ind:
                        break

                    crop = self.image.crop((
                        self.cur_x, self.cur_y,
                        self.cur_x + self.renderer.canvas_width, self.cur_y + self.renderer.canvas_height))
                    self.renderer.disp.ShowImage(crop, 0, 0)

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

            except KeyboardInterrupt as e:
                logger.info("Shutting down Screensaver")
                raise e
            finally:
                self._is_running = False
                self.renderer.show_image(self.last_screen)

    def stop(self):
        self._is_running = False
