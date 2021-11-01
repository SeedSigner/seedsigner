import time

from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
from threading import Thread

from .base import BaseTopNavScreen
from ..components import GUIConstants, Fonts, calc_text_centering

from seedsigner.helpers import B
from seedsigner.models import DecodeQR, DecodeQRStatus



@dataclass
class ScanScreen(BaseTopNavScreen):
    decoder: DecodeQR = None

    def __post_init__(self):
        from seedsigner.camera import Camera

        # Customize defaults
        title = "Scan"

        # Initialize the base class
        super().__post_init__()

        self.camera = Camera.get_instance()
        self.camera.start_video_stream_mode(resolution=(480, 480), framerate=12, format="rgb")

        # Prep the bottom semi-transparent instruction bar
        self.instructions_background = Image.new("RGBA", (self.canvas_width, 40), color="black")
        self.instructions_background_y = self.canvas_height - self.instructions_background.height

        # Pre-calc where the instruction text goes
        self.instructions_text = "Scan a Seed or PSBT"
        self.instructions_font = Fonts.get_font(GUIConstants.BUTTON_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)

        # TODO: Add the QR code icon and adjust start_x
        (self.instructions_text_x, self.instructions_text_y) = calc_text_centering(
            font=self.instructions_font,
            text=self.instructions_text,
            is_text_centered=True,
            box_width=self.canvas_width,
            box_height=self.instructions_background.height,
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
                    if self.decoder.getPercentComplete() > 0 and self.decoder.isPSBT():
                        scan_text = str(self.decoder.getPercentComplete()) + "% Complete"

                    # TODO: Render TopNav & instructions_background w/transparency
                    self.renderer.show_image_with_text(frame.resize((240,240)), scan_text, font=self.instructions_font, text_color="white", text_background=(0,0,0,225))

                time.sleep(0.1) # turn this up or down to tune performance while decoding psbt
                if self.camera._video_stream is None:
                    break

        # putting live preview in its own thread to improve psbt decoding performance
        t = Thread(target=live_preview)
        t.start()

        while True:
            frame = self.camera.read_video_stream()
            if frame is not None:
                status = self.decoder.addImage(frame)

                if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                    self.camera.stop_video_stream_mode()
                    break
                
                # TODO: KEY_UP gives control to NavBar; use its back arrow to cancel
                if self.hw_inputs.check_for_low(B.KEY_RIGHT) or self.hw_inputs.check_for_low(B.KEY_LEFT):
                    self.camera.stop_video_stream_mode()
                    break

        time.sleep(0.2) # time to let live preview thread complete to avoid race condition on display