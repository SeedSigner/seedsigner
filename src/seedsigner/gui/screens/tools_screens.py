import time

from dataclasses import dataclass
from PIL.Image import Image
from seedsigner.hardware.camera import Camera
from seedsigner.gui.components import Fonts, GUIConstants, IconTextLine, SeedSignerCustomIconConstants, TextArea

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, BaseScreen, ButtonListScreen
from seedsigner.hardware.buttons import HardwareButtonsConstants



@dataclass
class ToolsImageEntropyLivePreviewScreen(BaseScreen):
    def __post_init__(self):
        # Customize defaults
        self.title = "Initializing Camera..."

        # Initialize the base class
        super().__post_init__()

        self.camera = Camera.get_instance()
        self.camera.start_video_stream_mode(resolution=(240, 240), framerate=24, format="rgb")


    def _run(self):
        # save preview image frames to use as additional entropy below
        preview_images = []
        max_entropy_frames = 50

        while True:
            frame = self.camera.read_video_stream(as_image=True)
            if frame is not None:
                self.renderer.show_image_with_text(frame, "click joystick", text_color=GUIConstants.BODY_FONT_COLOR, text_background=(0,0,0,225))
                if len(preview_images) < max_entropy_frames:
                    preview_images.append(frame)

            if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                # Have to manually update last input time since we're not in a wait_for loop
                self.hw_inputs.update_last_input_time()
                self.words = []
                self.camera.stop_video_stream_mode()
                return RET_CODE__BACK_BUTTON

            elif self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_PRESS):
                # Have to manually update last input time since we're not in a wait_for loop
                self.hw_inputs.update_last_input_time()
                self.camera.stop_video_stream_mode()
                return preview_images


@dataclass
class ToolsImageEntropyFinalImageScreen(BaseScreen):
    final_image: Image = None

    def _run(self):
        self.renderer.show_image_with_text(
            self.final_image,
            text=" < reshoot  |  accept > ",
            font=Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BODY_FONT_SIZE),
            text_color=GUIConstants.BODY_FONT_COLOR,
            text_background=(0,0,0,225)
        )

        input = self.hw_inputs.wait_for([HardwareButtonsConstants.KEY_LEFT, HardwareButtonsConstants.KEY_RIGHT])
        if input == HardwareButtonsConstants.KEY_LEFT:
            return RET_CODE__BACK_BUTTON



@dataclass
class ToolsCalcFinalWordShowFinalWordScreen(ButtonListScreen):
    final_word: str = None
    mnemonic_word_length: int = 12
    fingerprint: str = None

    def __post_init__(self):
        # Customize defaults
        self.title = f"{self.mnemonic_word_length}th Word"
        self.is_bottom_list = True

        super().__post_init__()

        self.components.append(TextArea(
            text=f"""\"{self.final_word}\"""",
            font_size=GUIConstants.TOP_NAV_TITLE_FONT_SIZE + 6,
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        ))

        self.components.append(IconTextLine(
            icon_name=SeedSignerCustomIconConstants.FINGERPRINT,
            icon_color="blue",
            label_text="fingerprint",
            value_text=self.fingerprint,
            is_text_centered=True,
            screen_y=self.components[-1].screen_y + self.components[-1].height + 3*GUIConstants.COMPONENT_PADDING,
        ))
