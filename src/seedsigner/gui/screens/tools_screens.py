from dataclasses import dataclass
from PIL.Image import Image
from seedsigner.gui.keyboard import Keyboard, TextEntryDisplay
from seedsigner.hardware.camera import Camera
from seedsigner.gui.components import FontAwesomeIconConstants, Fonts, GUIConstants, IconTextLine, SeedSignerCustomIconConstants, TextArea

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, BaseScreen, BaseTopNavScreen, ButtonListScreen
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
        instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)

        while True:
            frame = self.camera.read_video_stream(as_image=True)
            if frame is not None:
                self.renderer.canvas.paste(frame)

                self.renderer.draw.text(
                    xy=(
                        int(self.renderer.canvas_width/2),
                        self.renderer.canvas_height - GUIConstants.EDGE_PADDING
                    ),
                    text="< back  |  click joystick",
                    fill=GUIConstants.BODY_FONT_COLOR,
                    font=instructions_font,
                    stroke_width=4,
                    stroke_fill=GUIConstants.BACKGROUND_COLOR,
                    anchor="ms"
                )
                self.renderer.show_image()

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

                self.renderer.canvas.paste(frame)

                self.renderer.draw.text(
                    xy=(
                        int(self.renderer.canvas_width/2),
                        self.renderer.canvas_height - GUIConstants.EDGE_PADDING
                    ),
                    text="Capturing image...",
                    fill=GUIConstants.ACCENT_COLOR,
                    font=instructions_font,
                    stroke_width=4,
                    stroke_fill=GUIConstants.BACKGROUND_COLOR,
                    anchor="ms"
                )
                self.renderer.show_image()

                return preview_images



@dataclass
class ToolsImageEntropyFinalImageScreen(BaseScreen):
    final_image: Image = None

    def _run(self):
        instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)

        self.renderer.canvas.paste(self.final_image)
        self.renderer.draw.text(
            xy=(
                int(self.renderer.canvas_width/2),
                self.renderer.canvas_height - GUIConstants.EDGE_PADDING
            ),
            text=" < reshoot  |  accept > ",
            fill=GUIConstants.BODY_FONT_COLOR,
            font=instructions_font,
            stroke_width=4,
            stroke_fill=GUIConstants.BACKGROUND_COLOR,
            anchor="ms"
        )
        self.renderer.show_image()

        input = self.hw_inputs.wait_for([HardwareButtonsConstants.KEY_LEFT, HardwareButtonsConstants.KEY_RIGHT])
        if input == HardwareButtonsConstants.KEY_LEFT:
            return RET_CODE__BACK_BUTTON



@dataclass
class ToolsDiceEntropyEntryScreen(BaseTopNavScreen):
    total_rolls: int = None


    def __post_init__(self):
        self.title = f"Dice Roll 1/{self.total_rolls}"
        super().__post_init__()

        self.dice_rolls = ""

        # Set up the keyboard params
        keyboard_width = self.canvas_width - 2*GUIConstants.EDGE_PADDING
        text_entry_display_y = self.top_nav.height
        text_entry_display_height = 30

        keyboard_start_y = text_entry_display_y + text_entry_display_height + GUIConstants.COMPONENT_PADDING
        rows = 3
        button_height = int((self.canvas_height - GUIConstants.EDGE_PADDING - text_entry_display_y - text_entry_display_height - GUIConstants.COMPONENT_PADDING - (rows - 1) * 2) / rows)
        self.keyboard_digits = Keyboard(
            draw=self.renderer.draw,
            charset="".join([
                FontAwesomeIconConstants.DICE_ONE,
                FontAwesomeIconConstants.DICE_TWO,
                FontAwesomeIconConstants.DICE_THREE,
                FontAwesomeIconConstants.DICE_FOUR,
                FontAwesomeIconConstants.DICE_FIVE,
                FontAwesomeIconConstants.DICE_SIX,
            ]),
            font_name=GUIConstants.ICON_FONT_NAME__FONT_AWESOME,
            font_size=button_height - GUIConstants.COMPONENT_PADDING,
            rows=rows,
            cols=3,
            rect=(
                GUIConstants.EDGE_PADDING,
                keyboard_start_y,
                GUIConstants.EDGE_PADDING + keyboard_width,
                keyboard_start_y + rows * button_height + (rows - 1) * 2
            ),
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )
        self.keyboard_digits.set_selected_key(selected_letter=FontAwesomeIconConstants.DICE_ONE)

        self.text_entry_display = TextEntryDisplay(
            canvas=self.renderer.canvas,
            rect=(
                GUIConstants.EDGE_PADDING,
                text_entry_display_y,
                self.canvas_width - GUIConstants.EDGE_PADDING,
                text_entry_display_y + text_entry_display_height
            ),
            cursor_mode=TextEntryDisplay.CURSOR_MODE__BAR,
            is_centered=False,
        )


    def _render(self):
        super()._render()

        self.keyboard_digits.render_keys()
        self.text_entry_display.render()

        self.renderer.show_image()
    

    def _run(self):
        cursor_position = len(self.dice_rolls)

        # Start the interactive update loop
        while True:
            input = self.hw_inputs.wait_for(
                HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN + [HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY3],
                check_release=True,
                release_keys=[HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY3]
            )
    
            # Check possible exit condition    
            if self.top_nav.is_selected and input == HardwareButtonsConstants.KEY_PRESS:
                return RET_CODE__BACK_BUTTON
    
            # Process normal input
            if input in [HardwareButtonsConstants.KEY_UP, HardwareButtonsConstants.KEY_DOWN] and self.top_nav.is_selected:
                # We're navigating off the previous button
                self.top_nav.is_selected = False
                self.top_nav.render_buttons()
    
                # Override the actual input w/an ENTER signal for the Keyboard
                if input == HardwareButtonsConstants.KEY_DOWN:
                    input = Keyboard.ENTER_TOP
                else:
                    input = Keyboard.ENTER_BOTTOM
            elif input in [HardwareButtonsConstants.KEY_LEFT, HardwareButtonsConstants.KEY_RIGHT] and self.top_nav.is_selected:
                # ignore
                continue
    
            ret_val = self.keyboard_digits.update_from_input(input)
    
            # Now process the result from the keyboard
            if ret_val in Keyboard.EXIT_DIRECTIONS:
                self.top_nav.is_selected = True
                self.top_nav.render_buttons()
    
            elif ret_val in Keyboard.ADDITIONAL_KEYS and input == HardwareButtonsConstants.KEY_PRESS:
                if ret_val == Keyboard.KEY_BACKSPACE["code"]:
                    if len(self.dice_rolls) > 0:
                        self.dice_rolls = self.dice_rolls[:-1]
                        cursor_position -= 1
    
            elif input == HardwareButtonsConstants.KEY_PRESS and ret_val not in Keyboard.ADDITIONAL_KEYS:
                # User has locked in the current letter
                if ret_val == FontAwesomeIconConstants.DICE_ONE:
                    ret_val = "1"
                elif ret_val == FontAwesomeIconConstants.DICE_TWO:
                    ret_val = "2"
                elif ret_val == FontAwesomeIconConstants.DICE_THREE:
                    ret_val = "3"
                elif ret_val == FontAwesomeIconConstants.DICE_FOUR:
                    ret_val = "4"
                elif ret_val == FontAwesomeIconConstants.DICE_FIVE:
                    ret_val = "5"
                elif ret_val == FontAwesomeIconConstants.DICE_SIX:
                    ret_val = "6"
                self.dice_rolls += ret_val
                cursor_position += 1

                if cursor_position == self.total_rolls:
                    return self.dice_rolls

                # Render a new TextArea over the TopNav title bar
                TextArea(
                    text=f"Dice Roll {cursor_position + 1}/{self.total_rolls}",
                    font_name=GUIConstants.TOP_NAV_TITLE_FONT_NAME,
                    font_size=GUIConstants.TOP_NAV_TITLE_FONT_SIZE,
                    height=self.top_nav.height,
                ).render()
                self.top_nav.render_buttons()
    
            elif input in HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN:
                # Live joystick movement; haven't locked this new letter in yet.
                # Leave current spot blank for now. Only update the active keyboard keys
                # when a selection has been locked in (KEY_PRESS) or removed ("del").
                pass
    
            # Render the text entry display and cursor block
            self.text_entry_display.render(self.dice_rolls)
    
            self.renderer.show_image()



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
