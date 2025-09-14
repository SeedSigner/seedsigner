import time

from dataclasses import dataclass
from gettext import gettext as _
from typing import Any
from PIL.Image import Image
from seedsigner.gui.renderer import Renderer
from seedsigner.hardware.camera import Camera
from seedsigner.gui.components import FontAwesomeIconConstants, Fonts, GUIConstants, IconTextLine, SeedSignerIconConstants, TextArea

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, BaseScreen, BaseTopNavScreen, ButtonListScreen, ButtonOption, KeyboardScreen
from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition



@dataclass
class ToolsImageEntropyLivePreviewScreen(BaseScreen):
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
        max_entropy_frames = 50
        instructions_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_button_font_size())

        while True:
            if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                # Have to manually update last input time since we're not in a wait_for loop
                self.hw_inputs.update_last_input_time()
                self.words = []
                self.camera.stop_video_stream_mode()
                return RET_CODE__BACK_BUTTON

            frame: Image = self.camera.read_video_stream(as_image=True)

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

            # Check for ANYCLICK to take final entropy image
            if self.hw_inputs.check_for_low(keys=HardwareButtonsConstants.KEYS__ANYCLICK):
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
                self.renderer.show_image()

            if len(preview_images) == max_entropy_frames:
                # Keep a moving window of the last n preview frames; pop the oldest
                # before we add the currest frame.
                preview_images.pop(0)
            preview_images.append(frame)



@dataclass
class ToolsImageEntropyFinalImageScreen(BaseScreen):
    final_image: Image = None

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

        # LEFT = reshoot, RIGHT / ANYCLICK = accept
        input = self.hw_inputs.wait_for([HardwareButtonsConstants.KEY_LEFT, HardwareButtonsConstants.KEY_RIGHT] + HardwareButtonsConstants.KEYS__ANYCLICK)
        if input == HardwareButtonsConstants.KEY_LEFT:
            return RET_CODE__BACK_BUTTON



@dataclass
class ToolsDiceEntropyEntryScreen(KeyboardScreen):

    def __post_init__(self):
        # TRANSLATOR_NOTE: current roll number vs total rolls (e.g. roll 7 of 50)
        self.title = _("Dice Roll {}/{}").format(1, self.return_after_n_chars)

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
        (left, top, bit_display_width, bit_font_height) = font.getbbox("0" * 11, anchor="lt")
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
                value_text=self.wallet_descriptor_display_name,  # TODO: English text from embit (e.g. "1 / 2 multisig"); make l10 friendly
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



@dataclass
class ToolsGameEntropyMnemonicLengthScreen(ButtonListScreen):
    """
    Screen for selecting mnemonic length with game instructions.
    """
    title: str = "Entropy Snake"
    is_bottom_list: bool = True
    is_button_text_centered: bool = True
    
    def __post_init__(self):
        super().__post_init__()
        
        # Add instructions text above the buttons
        instructions_text = _("Guide the snake to eat food and generate entropy.")
        self.components.append(TextArea(
            text=instructions_text,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
            font_size=GUIConstants.BODY_FONT_SIZE["default"]
        ))


@dataclass
class ToolsGameEntropyScreen(BaseTopNavScreen):
    """
    Screen for the entropy mini-game where users move a snake around to generate entropy.
    """
    title: str = "Entropy Snake"
    target_entropy_bits: int = 128  # 128 or 256 bits
    
    def __post_init__(self):
        super().__post_init__()
        
        # Game state
        self.entropy_data = []
        self.game_grid_size = 16  # Smaller grid cells for better gameplay
        
        # Random starting positions for snake and food
        import random
        self.snake_body = [[random.randint(2, self.game_grid_size - 3), random.randint(2, self.game_grid_size - 3)]]
        
        # Random initial direction (up, right, down, or left)
        directions = [[0, -1], [1, 0], [0, 1], [-1, 0]]  # up, right, down, left
        self.snake_direction = random.choice(directions)
        
        # Initialize food positions
        self.food_count = 2
        self.food_positions = []  # Initialize empty first
        self._generate_food_positions()
        
        self.moves_count = 0
        self.last_move_time = 0
        
        self.target_moves = 400
            
        # Progress tracking
        self.progress_percent = 0.0
        
        # Set up the game area. Optimize for screen fit
        available_height = self.canvas_height - self.top_nav.height - 20  # Reserve space for progress bar
        self.grid_cell_size = min(
            self.canvas_width // (self.game_grid_size + 2),
            available_height // (self.game_grid_size + 2)
        )
        self.game_start_x = (self.canvas_width - self.game_grid_size * self.grid_cell_size) // 2
        self.game_start_y = self.top_nav.height + 8  # Minimal top spacing
        
        # Progress bar (positioned below grid with minimal spacing)
        self.progress_bar_y = self.game_start_y + self.game_grid_size * self.grid_cell_size + 2
        self.progress_bar_height = 8  # Slightly taller for better text visibility

        # Key state tracking
        self.previous_key_states = {
            HardwareButtonsConstants.KEY_UP: False,
            HardwareButtonsConstants.KEY_DOWN: False,
            HardwareButtonsConstants.KEY_LEFT: False,
            HardwareButtonsConstants.KEY_RIGHT: False
        }

    def _generate_food_positions(self):
        """Generate initial food positions that don't overlap with snake or each other"""
        import random
        for _ in range(self.food_count):
            while True:
                new_pos = [
                    random.randint(0, self.game_grid_size - 1),
                    random.randint(0, self.game_grid_size - 1)
                ]
                if self._is_valid_food_position(new_pos):
                    self.food_positions.append(new_pos)
                    break

    def _render(self):
        super()._render()
        
        # Draw game grid
        self._draw_game_grid()
        
        # Draw snake
        self._draw_snake()
        
        # Draw food
        self._draw_food()
        
        # Draw progress bar
        self._draw_progress_bar()

    def _draw_game_grid(self):
        """Draw the game grid as a simple grid of squares"""
        for row in range(self.game_grid_size):
            for col in range(self.game_grid_size):
                x = self.game_start_x + col * self.grid_cell_size
                y = self.game_start_y + row * self.grid_cell_size
                
                # Draw grid cell border
                self.renderer.draw.rectangle(
                    [x, y, x + self.grid_cell_size - 1, y + self.grid_cell_size - 1],
                    outline=GUIConstants.INACTIVE_COLOR,
                    width=1
                )

    def _draw_snake(self):
        """Draw the snake body"""
        for i, segment in enumerate(self.snake_body):
            x = self.game_start_x + segment[0] * self.grid_cell_size
            y = self.game_start_y + segment[1] * self.grid_cell_size
            
            # Head is a different color ??
            if i == 0:
                color = GUIConstants.SUCCESS_COLOR
            else:
                color = GUIConstants.SUCCESS_COLOR
            
            # Draw snake segment
            self.renderer.draw.rectangle(
                [x + 1, y + 1, x + self.grid_cell_size - 2, y + self.grid_cell_size - 2],
                fill=color
            )
    
    def _draw_food(self):
        """Draw all food items as circles"""
        for food_pos in self.food_positions:
            x = self.game_start_x + food_pos[0] * self.grid_cell_size
            y = self.game_start_y + food_pos[1] * self.grid_cell_size
        
            # Draw food as a circle
            center_x = x + self.grid_cell_size // 2
            center_y = y + self.grid_cell_size // 2
            radius = self.grid_cell_size // 3
            
            self.renderer.draw.ellipse(
                [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                fill=GUIConstants.BITCOIN_ORANGE
            )

    def _draw_progress_bar(self):
        """Draw the progress bar with integrated text"""
        bar_width = self.canvas_width - 2 * GUIConstants.EDGE_PADDING
        progress_width = int(bar_width * self.progress_percent)
        
        # Background bar
        self.renderer.draw.rectangle(
            [GUIConstants.EDGE_PADDING, self.progress_bar_y, 
             GUIConstants.EDGE_PADDING + bar_width, self.progress_bar_y + self.progress_bar_height],
            fill=GUIConstants.INACTIVE_COLOR
        )
        
        # Progress bar
        if progress_width > 0:
            self.renderer.draw.rectangle(
                [GUIConstants.EDGE_PADDING, self.progress_bar_y,
                 GUIConstants.EDGE_PADDING + progress_width, self.progress_bar_y + self.progress_bar_height],
                fill=GUIConstants.SUCCESS_COLOR
            )
        
        # Progress text overlay
        progress_text = _("Moves: {}/{}").format(self.moves_count, self.target_moves)
        text_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_SIZE["default"] - 2)
        
        # Center the text on the progress bar
        text_bbox = text_font.getbbox(progress_text)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = GUIConstants.EDGE_PADDING + (bar_width - text_width) // 2
        text_y = self.progress_bar_y + (self.progress_bar_height + text_bbox[3] - text_bbox[1]) // 2
        
        # Draw text with background for better readability
        self.renderer.draw.text(
            xy=(text_x, text_y),
            text=progress_text,
            fill=GUIConstants.BODY_FONT_COLOR,
            font=text_font
        )

    def _run(self):
        """Main game loop"""
        while True:
            # Check for back button
            if any(self.hw_inputs.check_for_low(key) for key in (
                    HardwareButtonsConstants.KEY1,
                    HardwareButtonsConstants.KEY2,
                    HardwareButtonsConstants.KEY3
                    )):
                return RET_CODE__BACK_BUTTON
            
            # Check for movement keys (detect key release to move)
            current_up = self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_UP)
            current_down = self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_DOWN)
            current_left = self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT)
            current_right = self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT)
                        
            # Move snake on key release (was pressed, now not pressed)
            if self.previous_key_states[HardwareButtonsConstants.KEY_UP] and not current_up:
                if self.snake_direction != [0, 1]:  # Don't reverse direction
                    self.snake_direction = [0, -1]
                    self._move_snake()
            elif self.previous_key_states[HardwareButtonsConstants.KEY_DOWN] and not current_down:
                if self.snake_direction != [0, -1]:  # Don't reverse direction
                    self.snake_direction = [0, 1]
                    self._move_snake()
            elif self.previous_key_states[HardwareButtonsConstants.KEY_LEFT] and not current_left:
                if self.snake_direction != [1, 0]:  # Don't reverse direction
                    self.snake_direction = [-1, 0]
                    self._move_snake()
            elif self.previous_key_states[HardwareButtonsConstants.KEY_RIGHT] and not current_right:
                if self.snake_direction != [-1, 0]:  # Don't reverse direction
                    self.snake_direction = [1, 0]
                    self._move_snake()
            
            # Update previous key states for next iteration
            self.previous_key_states[HardwareButtonsConstants.KEY_UP] = current_up
            self.previous_key_states[HardwareButtonsConstants.KEY_DOWN] = current_down
            self.previous_key_states[HardwareButtonsConstants.KEY_LEFT] = current_left
            self.previous_key_states[HardwareButtonsConstants.KEY_RIGHT] = current_right

            # Check if we have enough entropy
            if self.moves_count >= self.target_moves:
                return self._generate_final_entropy()
            
            # Small delay (1MHz)
            time.sleep(0.000001)

    def _move_snake(self):
        """Move the snake in the current direction"""
        # Get current head position
        head = self.snake_body[0].copy()
        
        # Calculate new head position
        new_head = [
            (head[0] + self.snake_direction[0]) % self.game_grid_size,
            (head[1] + self.snake_direction[1]) % self.game_grid_size
        ]
        
        # Check if snake ate food
        ate_food = new_head in self.food_positions
        
        # Add new head
        self.snake_body.insert(0, new_head)
        
        # Remove tail unless food was eaten
        if not ate_food:
            self.snake_body.pop()
        else:
            # Find which food was eaten and replace only that one
            for i, food in enumerate(self.food_positions):
                if food == new_head:
                    self._replace_food_at_index(i)
                    break
        
        # Record the move data for entropy
        current_time = time.time_ns()  # Current time in nanoseconds
        interval = current_time - self.last_move_time
        self.last_move_time = current_time
        
        self.entropy_data.append(interval)
        self.moves_count += 1
        
        # Update progress
        self.progress_percent = min(1.0, self.moves_count / self.target_moves)
        
        # Redraw
        with self.renderer.lock:
            self._render()
            self.renderer.show_image()
    
    def _is_valid_food_position(self, pos):
        """Check if a position is valid for food placement"""
        return pos not in self.snake_body and pos not in self.food_positions
    
    def _replace_food_at_index(self, food_index):
        """Replace food at specific index with new random position"""
        import random
        while True:
            new_pos = [
                random.randint(0, self.game_grid_size - 1),
                random.randint(0, self.game_grid_size - 1)
            ]
            if self._is_valid_food_position(new_pos):
                self.food_positions[food_index] = new_pos
                break

    def _generate_final_entropy(self):
        """Generate the final entropy from collected data"""
        # Convert all collected data to a byte stream
        # Each move contributes 4 bytes of entropy data: relative interaction time in ns
        # 
        # ~400 moves × 4 bytes = ~1.6KB raw data
        # 
        # The raw data is hashed with SHA-256 and truncated to target size:
        # - 128-bit: SHA-256 hash truncated to first 16 bytes
        # - 256-bit: Full SHA-256 hash (32 bytes)
        entropy_bytes = b""
        
        for move in self.entropy_data:
            # Add relative timestamp (use modulo to fit in 4 bytes)
            # Convert to relative time from start to avoid overflow
            relative_timestamp = move % (2**32)  # Ensure it fits in 4 bytes
            timestamp_bytes = relative_timestamp.to_bytes(4, byteorder='big')
            entropy_bytes += timestamp_bytes
            
        # Hash the entropy data
        import hashlib
        final_hash = hashlib.sha256(entropy_bytes).digest()
        
        # Truncate to target entropy size
        if self.target_entropy_bits == 128:
            final_entropy = final_hash[:16]  # 128 bits = 16 bytes
        else:
            final_entropy = final_hash  # 256 bits = 32 bytes
        
        # Clear entropy data from memory
        self.entropy_data.clear()
        
        return final_entropy
