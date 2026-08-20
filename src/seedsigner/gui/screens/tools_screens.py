import hashlib
import time

from dataclasses import dataclass
from gettext import gettext as _
from typing import Any
from PIL import Image, ImageDraw
from seedsigner.gui.renderer import Renderer
from seedsigner.hardware.camera import Camera
from seedsigner.gui.components import FontAwesomeIconConstants, Fonts, GUIConstants, IconTextLine, SeedSignerIconConstants, TextArea

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, BaseScreen, ButtonListScreen, ButtonOption, KeyboardScreen
from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.gui.keyboard import Keyboard



@dataclass
class ToolsImageEntropyLivePreviewScreen(BaseScreen):
    # Set how many distinct, non-blank preview frames must be collected into the preview
    # pool before the final image can be taken.
    PREVIEW_POOL_SIZE = 50

    def __post_init__(self):
        super().__post_init__()

        self.camera = Camera.get_instance()

        # If the stream is set to 320x240, we get pillarboxed frames (black bars on the
        # sides). But passing in square dims gives us an edge-to-edge image.
        # TODO: Figure out why (camera expecting frame dims of multiples other than 16?)
        max_dimension = max(self.canvas_width, self.canvas_height)
        self.camera.start_video_stream_mode(resolution=(max_dimension, max_dimension), framerate=24, format="rgb")


    def _run(self):
        # save preview image frames to use as additional entropy below
        preview_images = []
        instructions_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_button_font_size())

        # Pre-calculate how wide the frame counter display can be.
        # TRANSLATOR_NOTE: Counts frames collected so far vs the total required (e.g. 12/50)
        max_counter_text = _("{}/{}").format(self.PREVIEW_POOL_SIZE, self.PREVIEW_POOL_SIZE)
        (left, top, right, bottom) = instructions_font.getbbox(max_counter_text)
        counter_text_width = right - left

        # The camera hands us its most recent frame on every loop pass, but the SAME frame
        # can arrive more than once. Store each image's sha256 hash so we can recognize
        # and skip the repeats. The set is intentionally never pruned. A frame identical
        # to any previously admitted frame can never be added a second time.
        preview_frame_hashes = set()

        # If the user continues holding the button that brought them into this flow, we
        # have to ensure that it doesn't trigger the ANYCLICK check below, otherwise the
        # final image capture would fire on its own the instant the preview pool fills.
        is_maybe_still_holding = True

        while True:
            if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                # Have to manually update last input time since we're not in a wait_for loop
                self.hw_inputs.update_last_input_time()
                self.words = []
                self.camera.stop_video_stream_mode()
                return RET_CODE__BACK_BUTTON

            frame: Image.Image = self.camera.read_video_stream(as_image=True)

            if frame is None:
                # Camera probably isn't ready yet
                time.sleep(0.01)
                continue

            with self.renderer.lock:
                # Account for the possibly different aspect ratio of the camera frame
                # vs the display; crop any excess.
                # TODO: This cropping may be unnecessary if the above TODO about the
                # camera resolution is solved.
                box = None
                if self.canvas_width != frame.width:
                    half_width_diff = int(abs(self.canvas_width - frame.width)/2)
                    box = (
                        half_width_diff,
                        0,
                        frame.width - half_width_diff,
                        frame.height
                    )
                elif self.canvas_height != frame.height:
                    half_height_diff = int(abs(self.canvas_height - frame.height)/2)
                    box = (
                        0,
                        half_height_diff,
                        frame.width,
                        frame.height - half_height_diff
                    )

                self.renderer.canvas.paste(frame.crop(box=box))

            # Decide whether this frame can be added to the preview pool.
            # Rule 1: the frame must not be a single flat color (e.g. an all-black frame
            # or an overexposed all-white one). getextrema() reports the lowest and
            # highest value found in each color channel; if the lowest equals the highest
            # in every channel, every pixel in the frame is identical and the frame is
            # rejected.
            frame_has_variation = False
            for lowest_value, highest_value in frame.getextrema():
                if lowest_value != highest_value:
                    frame_has_variation = True

            if frame_has_variation:
                # Rule 2: the frame must be one we have never counted before
                frame_hash = hashlib.sha256(frame.tobytes()).digest()
                if frame_hash not in preview_frame_hashes:
                    preview_frame_hashes.add(frame_hash)
                    if len(preview_images) == self.PREVIEW_POOL_SIZE:
                        # The preview pool is full. Dump the oldest and add the current
                        # frame.
                        preview_images.pop(0)
                    preview_images.append(frame)

            # Can only proceed to the final image when the preview pool is full
            if len(preview_images) == self.PREVIEW_POOL_SIZE:
                # If the ANYCLICK buttons are detected as being all released (none of
                # them cause check_for_low to return True), we can be sure that the user
                # isn't still holding down the initial button press that brought them
                # into this flow. It is then safe to arm the loop to trigger the final
                # image capture for whenever the *next* ANYCLICK button is pressed.
                if not self.hw_inputs.check_for_low(keys=HardwareButtonsConstants.KEYS__ANYCLICK):
                    # Confirmed that all ANYCLICK buttons are released. The next click
                    # can now trigger the final image capture.
                    is_maybe_still_holding = False

                elif not is_maybe_still_holding:
                    # We passed the above check; this is a fresh, explicit click. We can
                    # now capture the final image and exit this loop.

                    # Have to manually update last input time since we're not in a wait_for loop
                    self.hw_inputs.update_last_input_time()
                    self.camera.stop_video_stream_mode()

                    with self.renderer.lock:
                        self.renderer.draw.text(
                            xy=(
                                int(self.renderer.canvas_width/2),
                                self.renderer.canvas_height - GUIConstants.EDGE_PADDING
                            ),
                            text=_("Capturing image..."),
                            fill=GUIConstants.ACCENT_COLOR,
                            font=instructions_font,
                            stroke_width=4,
                            stroke_fill=GUIConstants.BACKGROUND_COLOR,
                            anchor="ms"
                        )
                        self.renderer.show_image()

                    return preview_images

            # If we're still here, it's just another preview frame loop
            with self.renderer.lock:
                if len(preview_images) == self.PREVIEW_POOL_SIZE and not is_maybe_still_holding:
                    self.renderer.draw.text(
                        xy=(
                            int(self.renderer.canvas_width/2),
                            self.renderer.canvas_height - GUIConstants.EDGE_PADDING
                        ),
                        text="< " + _("back") + "  |  " + _("click a button"),  # TODO: Render with UI elements instead of text
                        fill=GUIConstants.BODY_FONT_COLOR,
                        font=instructions_font,
                        stroke_width=4,
                        stroke_fill=GUIConstants.BACKGROUND_COLOR,
                        anchor="ms"
                    )

                else:
                    # Still collecting (or is_maybe_still_holding); report current
                    # progress on number of preview pool frames.

                    # TRANSLATOR_NOTE: Shown while the camera gathers the image frames a new seed requires
                    collecting_text = _("Collecting entropy frames")
                    self.renderer.draw.text(
                        xy=(
                            int(self.renderer.canvas_width/2),
                            self.renderer.canvas_height - GUIConstants.EDGE_PADDING - GUIConstants.BUTTON_HEIGHT - GUIConstants.COMPONENT_PADDING
                        ),
                        text=collecting_text,
                        fill=GUIConstants.BODY_FONT_COLOR,
                        font=instructions_font,
                        stroke_width=4,
                        stroke_fill=GUIConstants.BACKGROUND_COLOR,
                        anchor="ms"
                    )

                    # Render the frame counter progress bar; same visual design as the
                    # animated QR scan progress bar.
                    rectangle = Image.new('RGBA', (self.renderer.canvas_width - 2*GUIConstants.EDGE_PADDING, GUIConstants.BUTTON_HEIGHT), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(rectangle)

                    # Start with a background rounded rectangle, same dims as the buttons
                    overlay_color = (0, 0, 0, 191)  # opacity ranges from 0-255
                    draw.rounded_rectangle(
                        (
                            (0, 0),
                            (rectangle.width, rectangle.height)
                        ),
                        fill=overlay_color,
                        radius=8,
                        outline=overlay_color,
                        width=2,
                    )

                    progress_bar_thickness = 4
                    progress_bar_width = rectangle.width - 2*GUIConstants.EDGE_PADDING - counter_text_width - int(GUIConstants.EDGE_PADDING/2)
                    progress_bar_xy = (
                            (GUIConstants.EDGE_PADDING, int((rectangle.height - progress_bar_thickness) / 2)),
                            (GUIConstants.EDGE_PADDING + progress_bar_width, int(rectangle.height + progress_bar_thickness) / 2)
                        )
                    draw.rounded_rectangle(
                        progress_bar_xy,
                        fill=GUIConstants.INACTIVE_COLOR,
                        radius=8
                    )

                    if len(preview_images) > 0:
                        draw.rounded_rectangle(
                            (
                                progress_bar_xy[0],
                                (GUIConstants.EDGE_PADDING + int(len(preview_images) * progress_bar_width / self.PREVIEW_POOL_SIZE), progress_bar_xy[1][1])
                            ),
                            fill=GUIConstants.GREEN_INDICATOR_COLOR,
                            radius=8
                        )

                    # TRANSLATOR_NOTE: Counts frames collected so far vs the total required (e.g. 12/50)
                    counter_text = _("{}/{}").format(len(preview_images), self.PREVIEW_POOL_SIZE)

                    draw.text(
                        xy=(rectangle.width - GUIConstants.EDGE_PADDING, int(rectangle.height / 2)),
                        text=counter_text,
                        fill=GUIConstants.BODY_FONT_COLOR,
                        font=instructions_font,
                        anchor="rm",  # right-justified, middle
                    )

                    self.renderer.canvas.paste(rectangle, (GUIConstants.EDGE_PADDING, self.renderer.canvas_height - GUIConstants.EDGE_PADDING - rectangle.height), rectangle)

                self.renderer.show_image()



@dataclass
class ToolsImageEntropyFinalImageScreen(BaseScreen):
    final_image: Image.Image = None

    def _run(self):
        instructions_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_button_font_size())

        with self.renderer.lock:
            self.renderer.canvas.paste(self.final_image)

            # TRANSLATOR_NOTE: A prompt to the user to either accept or reshoot the image
            reshoot = _("reshoot")

            # TRANSLATOR_NOTE: A prompt to the user to either accept or reshoot the image
            accept = _("accept")
            self.renderer.draw.text(
                xy=(
                    int(self.renderer.canvas_width/2),
                    self.renderer.canvas_height - GUIConstants.EDGE_PADDING
                ),
                text=" < " + reshoot + "  |  " + accept + " > ",
                fill=GUIConstants.BODY_FONT_COLOR,
                font=instructions_font,
                stroke_width=4,
                stroke_fill=GUIConstants.BACKGROUND_COLOR,
                anchor="ms"
            )
            self.renderer.show_image()

        # The button click that triggered the final image might still be held down as this
        # screen appears. We can't let that held button auto-dismiss the final image
        # review here. Wait until every button has been released before listening for the
        # accept/reshoot decision.
        while self.hw_inputs.check_for_low(keys=[HardwareButtonsConstants.KEY_LEFT, HardwareButtonsConstants.KEY_RIGHT] + HardwareButtonsConstants.KEYS__ANYCLICK):
            time.sleep(0.01)

        # LEFT = reshoot, RIGHT / ANYCLICK = accept
        input = self.hw_inputs.wait_for([HardwareButtonsConstants.KEY_LEFT, HardwareButtonsConstants.KEY_RIGHT] + HardwareButtonsConstants.KEYS__ANYCLICK)
        if input == HardwareButtonsConstants.KEY_LEFT:
            return RET_CODE__BACK_BUTTON



@dataclass
class ToolsDiceEntropyEntryScreen(KeyboardScreen):

    def __post_init__(self):
        # TRANSLATOR_NOTE: current roll number vs total rolls (e.g. roll 7 of 50)
        self.title = _("Dice Roll {}/{}").format(1, self.return_after_n_chars)
        self.custom_additional_keys = [Keyboard.KEY_BACKSPACE]

        # Specify the keys in the keyboard
        self.rows = 3
        self.cols = 3
        self.keyboard_font_name = GUIConstants.ICON_FONT_NAME__FONT_AWESOME
        self.keyboard_font_size = 36
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
        self.title = _("Dice Roll {}/{}").format(self.cursor_position + 1, self.return_after_n_chars)
        return True



@dataclass
class ToolsCalcFinalWordFinalizePromptScreen(ButtonListScreen):
    mnemonic_length: int = None
    num_entropy_bits: int = None

    def __post_init__(self):
        # TRANSLATOR_NOTE: Build the last word in a 12 or 24 word BIP-39 mnemonic seed phrase.
        self.title = _("Build Final Word")
        self.is_bottom_list = True
        self.is_button_text_centered = True
        super().__post_init__()

        # TRANSLATOR_NOTE: Final word calc. `mnemonic_length` = 12 or 24. `num_bits` = 7 or 3 (bits of entropy in final word).
        text=_("The {mnemonic_length}th word is built from {num_bits} more entropy bits plus auto-calculated checksum.").format(mnemonic_length=self.mnemonic_length, num_bits=self.num_entropy_bits)

        self.components.append(TextArea(
            text=text,
            screen_y=self.top_nav.height + int(GUIConstants.COMPONENT_PADDING/2),
        ))



@dataclass
class ToolsCoinFlipEntryScreen(KeyboardScreen):
    def __post_init__(self):
        # Override values set by the parent class
        # TRANSLATOR_NOTE: current coin-flip number vs total flips (e.g. flip 3 of 4)
        self.title = _("Coin Flip {}/{}").format(1, self.return_after_n_chars)
        self.custom_additional_keys = [Keyboard.KEY_BACKSPACE_2]

        # Specify the keys in the keyboard
        self.rows = 1
        self.cols = 4
        self.key_height = GUIConstants.get_top_nav_title_font_size() + 2 + 2*GUIConstants.EDGE_PADDING
        self.keys_charset = "10"

        # Now initialize the parent class
        super().__post_init__()
    
        self.components.append(TextArea(
            # TRANSLATOR_NOTE: How we call the "front" side result during a coin toss.
            text=_("Heads = 1"),
            screen_y = self.keyboard.rect[3] + 4*GUIConstants.COMPONENT_PADDING,
        ))
        self.components.append(TextArea(
            # TRANSLATOR_NOTE: How we call the "back" side result during a coin toss.
            text=_("Tails = 0"),
            screen_y = self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
        ))


    def update_title(self) -> bool:
        # l10n_note already done.
        self.title = _("Coin Flip {}/{}").format(self.cursor_position + 1, self.return_after_n_chars)
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
        bit_font_size = GUIConstants.get_button_font_size(locale="default") + 2  # bit font size should not vary by locale
        font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, bit_font_size)
        (left, top, bit_display_width, bottom) = font.getbbox("0" * 11, anchor="lt")
        (left, top, checksum_x, bottom) = font.getbbox("0" * (11 - len(self.checksum_bits)), anchor="lt")
        bit_display_x = int((self.canvas_width - bit_display_width)/2)
        checksum_x += bit_display_x

        y_spacer = GUIConstants.COMPONENT_PADDING
        if GUIConstants.get_body_font_size() > GUIConstants.get_body_font_size("default"):
            y_spacer -= 1

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

        # TRANSLATOR_NOTE: The additional entropy the user supplied (e.g. coin flips)
        your_input = _('Your input: "{}"').format(selection_text)
        self.components.append(TextArea(
            text=your_input,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING - 2,  # Nudge to last line doesn't get too close to "Next" button
            height_ignores_below_baseline=True,  # Keep the next line (bits display) snugged up, regardless of text rendering below the baseline
        ))

        # ...and that entropy's associated 11 bits
        screen_y = self.components[-1].screen_y + self.components[-1].height + y_spacer
        first_bits_line = TextArea(
            text=keeper_selected_bits,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=bit_font_size,
            edge_padding=0,
            screen_x=bit_display_x,
            screen_y=screen_y,
            is_text_centered=False,
        )
        self.components.append(first_bits_line)

        # Render the least significant bits that will be replaced by the checksum in a
        # de-emphasized font color.
        if "_" in discard_selected_bits:
            screen_y += int(first_bits_line.height/2)  # center the underscores vertically like hypens
        self.components.append(TextArea(
            text=discard_selected_bits,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_color=GUIConstants.LABEL_FONT_COLOR,
            font_size=bit_font_size,
            edge_padding=0,
            screen_x=checksum_x,
            screen_y=screen_y,
            is_text_centered=False,
        ))

        # Show the checksum...
        self.components.append(TextArea(
            # TRANSLATOR_NOTE: A function of "x" to be used for detecting errors in "x"
            text=_("Checksum"),
            edge_padding=0,
            screen_y=first_bits_line.screen_y + first_bits_line.height + 2*GUIConstants.COMPONENT_PADDING,
            height_ignores_below_baseline=True,  # Keep the next line (bits display) snugged up, regardless of text rendering below the baseline
        ))

        # ...and its actual bits. Prepend spacers to keep vertical alignment
        checksum_spacer = "_" * (11 - len(self.checksum_bits))

        screen_y = self.components[-1].screen_y + self.components[-1].height + y_spacer

        # This time we de-emphasize the prepended spacers that are irrelevant
        self.components.append(TextArea(
            text=checksum_spacer,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_color=GUIConstants.LABEL_FONT_COLOR,
            font_size=bit_font_size,
            edge_padding=0,
            screen_x=bit_display_x,
            screen_y=screen_y + int(first_bits_line.height/2),  # center the underscores vertically like hypens
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
            # TRANSLATOR_NOTE: labeled presentation of the last word in a BIP-39 mnemonic seed phrase.
            text=_('Final Word: "{}"').format(self.actual_final_word),
            screen_y=self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING,
            height_ignores_below_baseline=True,  # Keep the next line (bits display) snugged up, regardless of text rendering below the baseline
        ))

        # Once again show the bits that came from the user's entropy...
        num_checksum_bits = len(self.checksum_bits)
        user_component = self.selected_final_bits[:11 - num_checksum_bits]
        screen_y = self.components[-1].screen_y + self.components[-1].height + y_spacer
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
        # Manually specify 12 vs 24 case for easier ordinal translation
        if self.mnemonic_word_length == 12:
            # TRANSLATOR_NOTE: a label for the last word of a 12-word BIP-39 mnemonic seed phrase
            self.title = _("12th Word")
        else:
            # TRANSLATOR_NOTE: a label for the last word of a 24-word BIP-39 mnemonic seed phrase
            self.title = _("24th Word")
        self.is_bottom_list = True

        super().__post_init__()

        self.components.append(TextArea(
            text=f"""\"{self.final_word}\"""",
            font_size=26,
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        ))

        self.components.append(IconTextLine(
            icon_name=SeedSignerIconConstants.FINGERPRINT,
            icon_color=GUIConstants.INFO_COLOR,
            # TRANSLATOR_NOTE: a label for the shortened Key-id of a BIP-32 master HD wallet
            label_text=_("fingerprint"),
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
        # TRANSLATOR_NOTE: a label for the tool to explore public addresses for this seed.
        self.title = _("Address Explorer")
        self.is_bottom_list = True
        super().__post_init__()

        if self.fingerprint:
            self.components.append(IconTextLine(
                icon_name=SeedSignerIconConstants.FINGERPRINT,
                icon_color=GUIConstants.INFO_COLOR,
                # TRANSLATOR_NOTE: a label for the shortened Key-id of a BIP-32 master HD wallet
                label_text=_("Fingerprint"),
                value_text=self.fingerprint,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
            ))

            if self.script_type != SettingsConstants.CUSTOM_DERIVATION:
                self.components.append(IconTextLine(
                    icon_name=SeedSignerIconConstants.DERIVATION,
                    # TRANSLATOR_NOTE: a label for the derivation-path into a BIP-32 HD wallet
                    label_text=_("Derivation"),
                    value_text=SettingsDefinition.get_settings_entry(attr_name=SettingsConstants.SETTING__SCRIPT_TYPES).get_selection_option_display_name_by_value(value=self.script_type),
                    screen_x=GUIConstants.EDGE_PADDING,
                    screen_y=self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING,
                ))
            else:
                self.components.append(IconTextLine(
                    icon_name=SeedSignerIconConstants.DERIVATION,
                    # l10n_note already exists.
                    label_text=_("Derivation"),
                    value_text=self.custom_derivation_path,
                    screen_x=GUIConstants.EDGE_PADDING,
                    screen_y=self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING,
                ))

        else:
            self.components.append(IconTextLine(
                # TRANSLATOR_NOTE: a label for a BIP-380-ish Output Descriptor
                label_text=_("Wallet descriptor"),
                value_text=self.wallet_descriptor_display_name,
                is_text_centered=True,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
            ))



@dataclass
class ToolsAddressExplorerAddressListScreen(ButtonListScreen):
    start_index: int = 0
    addresses: list[str] = None

    def __post_init__(self):
        self.button_font_name = GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME
        self.button_font_size = GUIConstants.get_button_font_size() + 4
        self.is_button_text_centered = False
        self.is_bottom_list = True

        left, top, right, bottom  = Fonts.get_font(self.button_font_name, self.button_font_size).getbbox("X")
        char_width = right - left

        last_addr_index = self.start_index + len(self.addresses) - 1
        index_digits = len(str(last_addr_index))
        
        # Calculate how many pixels we have available within each address button,
        # remembering to account for the index number that will be displayed.
        # Note: because we haven't called the parent's post_init yet, we don't have a
        # self.canvas_width set; have to use the Renderer singleton to get it.
        available_width = Renderer.get_instance().canvas_width - 2*GUIConstants.EDGE_PADDING - 2*GUIConstants.COMPONENT_PADDING - (index_digits + 1)*char_width
        displayable_chars = int(available_width / char_width) - 3  # ellipsis
        displayable_half = int(displayable_chars/2)

        self.button_data = []
        for i, address in enumerate(self.addresses):
            cur_index = i + self.start_index

            # TODO: Intentionally NOT marking these for translation, but we may need to in
            # the future.
            button_label = f"{cur_index}:{address[:displayable_half]}...{address[-1*displayable_half:]}"
            active_button_label = f"{cur_index}:{address}"

            self.button_data.append(ButtonOption(button_label, active_button_label=active_button_label))
        
        # TRANSLATOR_NOTE: Insert the number of addrs displayed per screen (e.g. "Next 10")
        button_label = _("Next {}").format(len(self.addresses))
        self.button_data.append(ButtonOption(button_label, right_icon_name=SeedSignerIconConstants.CHEVRON_RIGHT))

        super().__post_init__()
