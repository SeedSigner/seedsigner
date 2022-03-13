import time

from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
from threading import Thread

from .screen import BaseTopNavScreen, ButtonListScreen
from ..components import GUIConstants, Fonts, TextArea, calc_text_centering

from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.models import DecodeQR, DecodeQRStatus



@dataclass
class ScanScreen(BaseTopNavScreen):
    decoder: DecodeQR = None
    instructions_text: str = "Scan a QR code"

    def __post_init__(self):
        from seedsigner.hardware.camera import Camera

        # Customize defaults
        self.title = "Scan"

        # Initialize the base class
        super().__post_init__()

        self.camera = Camera.get_instance()
        self.camera.start_video_stream_mode(resolution=(480, 480), framerate=12, format="rgb")

        # Prep the bottom semi-transparent instruction bar
        self.instructions_background = Image.new("RGBA", (self.canvas_width, 40), color="black")
        self.instructions_background_y = self.canvas_height - self.instructions_background.height

        # Pre-calc where the instruction text goes
        self.instructions_font = Fonts.get_font(GUIConstants.BUTTON_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)

        # TODO: Add the QR code icon and adjust start_x
        (self.instructions_text_x, self.instructions_text_y) = calc_text_centering(
            font=self.instructions_font,
            text=self.instructions_text,
            is_text_centered=True,
            total_width=self.canvas_width,
            total_height=self.instructions_background.height,
            start_x=0,
            start_y=0
        )


    def _run(self):
        """
            _render() is mostly meant to be a one-time initial drawing call to set up the
            Screen. Once interaction starts, the display updates have to be managed in
            _run(). The live preview is an extra-complex case.
        """
        def live_preview():
            while True:
                frame = self.camera.read_video_stream(as_image=True)
                if frame is not None:
                    scan_text = self.instructions_text
                    if self.decoder.get_percent_complete() > 0 and self.decoder.is_psbt:
                        scan_text = str(self.decoder.get_percent_complete()) + "% Complete"

                    # TODO: Render TopNav & instructions_background w/transparency
                    # img = Image.new(mode='RGBA', size=(self.canvas_width, self.canvas_height))
                    # img.paste(frame.resize((self.canvas_width, self.canvas_height)))
                    self.renderer.show_image_with_text(frame.resize((self.canvas_width, self.canvas_height), resample=Image.NEAREST), scan_text, font=self.instructions_font, text_color="white", text_background=(0,0,0,225))
                    # self.top_nav.render()
                    # self.renderer.show_image()

                time.sleep(0.1) # turn this up or down to tune performance while decoding psbt
                if self.camera._video_stream is None:
                    break

        # putting live preview in its own thread to improve psbt decoding performance
        t = Thread(target=live_preview)
        t.start()

        while True:
            frame = self.camera.read_video_stream()
            if frame is not None:
                status = self.decoder.add_image(frame)

                if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                    self.camera.stop_video_stream_mode()
                    break
                
                # TODO: KEY_UP gives control to NavBar; use its back arrow to cancel
                if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT) or self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                    self.camera.stop_video_stream_mode()
                    break

        time.sleep(0.2) # time to let live preview thread complete to avoid race condition on display



@dataclass
class SettingsUpdatedScreen(ButtonListScreen):
    config_name: str = None
    title: str = "Settings QR"
    is_bottom_list: bool = True

    def __post_init__(self):
        # Customize defaults
        self.button_data = ["Home"]

        super().__post_init__()

        start_y = self.top_nav.height + 20
        if self.config_name:
            self.config_name_textarea = TextArea(
                text=f'"{self.config_name}"',
                is_text_centered=True,
                auto_line_break=True,
                screen_y=start_y
            )
            self.components.append(self.config_name_textarea)
            start_y = self.config_name_textarea.screen_y + 50
        
        self.components.append(TextArea(
            text="Settings imported successfully!",
            is_text_centered=True,
            auto_line_break=True,
            screen_y=start_y
        ))

