from dataclasses import dataclass
from typing import Any
from PIL.Image import Image
from seedsigner.gui.keyboard import Keyboard, TextEntryDisplay
from seedsigner.hardware.camera import Camera
from seedsigner.gui.components import FontAwesomeIconConstants, Fonts, FormattedAddress, GUIConstants, IconTextLine, SeedSignerCustomIconConstants, TextArea

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, BaseScreen, BaseTopNavScreen, ButtonListScreen, KeyboardScreen
from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.helpers.qr import QR
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition



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
class ToolsDiceEntropyEntryScreen(KeyboardScreen):
    def __post_init__(self):
        # Override values set by the parent class
        self.title = f"Dice Roll 1/{self.return_after_n_chars}"

        # Specify the keys in the keyboard
        self.rows = 3
        self.cols = 3
        self.keyboard_font_name = GUIConstants.ICON_FONT_NAME__FONT_AWESOME
        self.keyboard_font_size = None  # Force auto-scaling to Key height
        self.keys_charset = "".join([
            FontAwesomeIconConstants.DICE_ONE,
            FontAwesomeIconConstants.DICE_TWO,
            FontAwesomeIconConstants.DICE_THREE,
            FontAwesomeIconConstants.DICE_FOUR,
            FontAwesomeIconConstants.DICE_FIVE,
            FontAwesomeIconConstants.DICE_SIX,
        ])

        # Map Key display chars to actual output values
        self.keys_to_values = {
            FontAwesomeIconConstants.DICE_ONE: "1",
            FontAwesomeIconConstants.DICE_TWO: "2",
            FontAwesomeIconConstants.DICE_THREE: "3",
            FontAwesomeIconConstants.DICE_FOUR: "4",
            FontAwesomeIconConstants.DICE_FIVE: "5",
            FontAwesomeIconConstants.DICE_SIX: "6",
        }

        # Now initialize the parent class
        super().__post_init__()
    

    def update_title(self) -> bool:
        self.title = f"Dice Roll {self.cursor_position + 1}/{self.return_after_n_chars}"
        return True



@dataclass
class ToolsCalcFinalWordFinalizePromptScreen(ButtonListScreen):
    mnemonic_length: int = None
    num_entropy_bits: int = None

    def __post_init__(self):
        self.title = "Build Final Word"
        self.is_bottom_list = True
        self.is_button_text_centered = True
        super().__post_init__()

        self.components.append(TextArea(
            text=f"The {self.mnemonic_length}th word is built from {self.num_entropy_bits} more entropy bits plus auto-calculated checksum.",
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        ))



@dataclass
class ToolsCoinFlipEntryScreen(KeyboardScreen):
    def __post_init__(self):
        # Override values set by the parent class
        self.title = f"Coin Flip 1/{self.return_after_n_chars}"

        # Specify the keys in the keyboard
        self.rows = 1
        self.cols = 4
        self.key_height = GUIConstants.TOP_NAV_TITLE_FONT_SIZE + 2 + 2*GUIConstants.EDGE_PADDING
        self.keys_charset = "10"

        # Now initialize the parent class
        super().__post_init__()
    
        self.components.append(TextArea(
            text="Heads = 1",
            screen_y = self.keyboard.rect[3] + 4*GUIConstants.COMPONENT_PADDING,
        ))
        self.components.append(TextArea(
            text="Tails = 0",
            screen_y = self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
        ))


    def update_title(self) -> bool:
        self.title = f"Coin Flip {self.cursor_position + 1}/{self.return_after_n_chars}"
        return True



@dataclass
class ToolsCalcFinalWordScreen(ButtonListScreen):
    selected_final_word: str = None
    selected_final_bits: str = None
    checksum_bits: str = None
    actual_final_word: str = None

    def __post_init__(self):
        self.is_bottom_list = True
        super().__post_init__()

        # First what's the total bit display width and where do the checksum bits start?
        bit_font_size = GUIConstants.BUTTON_FONT_SIZE + 2
        font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, bit_font_size)
        (left, top, bit_display_width, bit_font_height) = font.getbbox("0" * 11, anchor="lt")
        (left, top, checksum_x, bottom) = font.getbbox("0" * (11 - len(self.checksum_bits)), anchor="lt")
        bit_display_x = int((self.canvas_width - bit_display_width)/2)
        checksum_x += bit_display_x

        # Display the user's additional entropy input
        if self.selected_final_word:
            selection_text = self.selected_final_word
            keeper_selected_bits = self.selected_final_bits[:11 - len(self.checksum_bits)]

            # The word's least significant bits will be rendered differently to convey
            # the fact that they're being discarded.
            discard_selected_bits = self.selected_final_bits[-1*len(self.checksum_bits):]
        else:
            # User entered coin flips or all zeros
            selection_text = self.selected_final_bits
            keeper_selected_bits = self.selected_final_bits

            # We'll append spacer chars to preserve the vertical alignment (most
            # significant n bits always rendered in same column)
            discard_selected_bits = "_" * (len(self.checksum_bits))

        self.components.append(TextArea(
            text=f"""Your input: \"{selection_text}\"""",
            screen_y=self.top_nav.height,
        ))

        # ...and that entropy's associated 11 bits
        screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING
        self.components.append(TextArea(
            text=keeper_selected_bits,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=bit_font_size,
            edge_padding=0,
            screen_x=bit_display_x,
            screen_y=screen_y,
            height=bit_font_height,
            is_text_centered=False,
        ))

        # Render the least significant bits that will be replaced by the checksum in a
        # de-emphasized font color.
        self.components.append(TextArea(
            text=discard_selected_bits,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_color=GUIConstants.LABEL_FONT_COLOR,
            font_size=bit_font_size,
            edge_padding=0,
            screen_x=checksum_x,
            screen_y=screen_y,
            height=bit_font_height,
            is_text_centered=False,
        ))

        # Show the checksum..
        self.components.append(TextArea(
            text="Checksum",
            edge_padding=0,
            screen_y=self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING,
        ))

        # ...and its actual bits. Prepend spacers to keep vertical alignment
        checksum_spacer = "_" * (11 - len(self.checksum_bits))

        screen_y = self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING

        # This time we de-emphasize the prepended spacers that are irrelevant
        self.components.append(TextArea(
            text=checksum_spacer,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_color=GUIConstants.LABEL_FONT_COLOR,
            font_size=bit_font_size,
            edge_padding=0,
            screen_x=bit_display_x,
            screen_y=screen_y,
            height=bit_font_height,
            is_text_centered=False,
        ))

        # And especially highlight (orange!) the actual checksum bits
        self.components.append(TextArea(
            text=self.checksum_bits,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=bit_font_size,
            font_color=GUIConstants.ACCENT_COLOR,
            edge_padding=0,
            screen_x=checksum_x,
            screen_y=screen_y,
            is_text_centered=False,
        ))

        # And now the *actual* final word after merging the bit data
        self.components.append(TextArea(
            text=f"""Final Word: \"{self.actual_final_word}\"""",
            screen_y=self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING,
        ))

        # Once again show the bits that came from the user's entropy...
        num_checksum_bits = len(self.checksum_bits)
        user_component = self.selected_final_bits[:11 - num_checksum_bits]
        screen_y = self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING
        self.components.append(TextArea(
            text=user_component,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=bit_font_size,
            edge_padding=0,
            screen_x=bit_display_x,
            screen_y=screen_y,
            is_text_centered=False,
        ))

        # ...and append the checksum's bits, still highlighted in orange
        self.components.append(TextArea(
            text=self.checksum_bits,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_color=GUIConstants.ACCENT_COLOR,
            font_size=bit_font_size,
            edge_padding=0,
            screen_x=checksum_x,
            screen_y=screen_y,
            is_text_centered=False,
        ))



@dataclass
class ToolsCalcFinalWordDoneScreen(ButtonListScreen):
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



@dataclass
class ToolsAddressExplorerAddressTypeScreen(ButtonListScreen):
    fingerprint: str = None
    wallet_descriptor_display_name: Any = None
    script_type: str = None
    custom_derivation_path: str = None

    def __post_init__(self):
        self.title = "Address Explorer"
        self.is_bottom_list = True
        super().__post_init__()

        if self.fingerprint:
            self.components.append(IconTextLine(
                icon_name=SeedSignerCustomIconConstants.FINGERPRINT,
                icon_color="blue",
                label_text="Fingerprint",
                value_text=self.fingerprint,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
            ))

            if self.script_type != SettingsConstants.CUSTOM_DERIVATION:
                self.components.append(IconTextLine(
                    icon_name=SeedSignerCustomIconConstants.PATH,
                    label_text="Derivation",
                    value_text=SettingsDefinition.get_settings_entry(attr_name=SettingsConstants.SETTING__SCRIPT_TYPES).get_selection_option_display_name_by_value(value=self.script_type),
                    screen_x=GUIConstants.EDGE_PADDING,
                    screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
                ))
            else:
                self.components.append(IconTextLine(
                    icon_name=SeedSignerCustomIconConstants.PATH,
                    label_text="Derivation",
                    value_text=self.custom_derivation_path,
                    screen_x=GUIConstants.EDGE_PADDING,
                    screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
                ))

        else:
            self.components.append(IconTextLine(
                label_text="Wallet descriptor",
                value_text=self.wallet_descriptor_display_name,
                is_text_centered=False,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
            ))
