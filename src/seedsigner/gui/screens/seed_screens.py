import logging
import math
import time

from dataclasses import dataclass
from gettext import gettext as _
from PIL import Image, ImageDraw, ImageFilter
from typing import List

from seedsigner.hardware.buttons import HardwareButtons, HardwareButtonsConstants
from seedsigner.helpers.qr import QR
from seedsigner.gui.components import (Button, FontAwesomeIconConstants, Fonts, FormattedAddress, IconButton,
    IconTextLine, SeedSignerIconConstants, TextArea, GUIConstants, reflow_text_into_pages)
from seedsigner.gui.keyboard import Keyboard, TextEntryDisplay
from seedsigner.gui.renderer import Renderer
from seedsigner.models.threads import BaseThread, ThreadsafeCounter

from .screen import RET_CODE__BACK_BUTTON, BaseScreen, BaseTopNavScreen, ButtonListScreen, ButtonOption, KeyboardScreen, LargeIconStatusScreen, WarningEdgesMixin

logger = logging.getLogger(__name__)



@dataclass
class SeedMnemonicEntryScreen(BaseTopNavScreen):
    initial_letters: list = None
    wordlist: list = None

    def __post_init__(self):
        super().__post_init__()

        self.possible_alphabet = "abcdefghijklmnopqrstuvwxyz"

        # Set up the keyboard params
        self.keyboard_width = 128
        text_entry_display_y = self.top_nav.height
        text_entry_display_height = 30

        self.arrow_up_is_active = False
        self.arrow_down_is_active = False

        # TODO: support other BIP39 languages/charsets
        self.keyboard = Keyboard(
            draw=self.image_draw,
            charset=self.possible_alphabet,
            rows=5,
            cols=6,
            rect=(
                GUIConstants.EDGE_PADDING,
                text_entry_display_y + text_entry_display_height + 6,
                GUIConstants.EDGE_PADDING + self.keyboard_width,
                self.canvas_height
            ),
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT]
        )

        self.text_entry_display = TextEntryDisplay(
            canvas=self.canvas,
            rect=(
                GUIConstants.EDGE_PADDING,
                text_entry_display_y,
                GUIConstants.EDGE_PADDING + self.keyboard.width,
                text_entry_display_y + text_entry_display_height
            ),
            is_centered=False,
            cur_text="".join(self.initial_letters)
        )

        self.letters = self.initial_letters

        # Initialize the current matches
        self.possible_words = []
        if len(self.letters) > 1:
            self.letters.append(" ")    # "Lock in" the last letter as if KEY_PRESS
            self.calc_possible_alphabet()
            self.keyboard.update_active_keys(active_keys=self.possible_alphabet)
            self.keyboard.set_selected_key(selected_letter=self.letters[-2])
        else:
            self.keyboard.set_selected_key(selected_letter=self.letters[-1])

        self.matches_list_x = GUIConstants.EDGE_PADDING + self.keyboard.width + GUIConstants.COMPONENT_PADDING
        self.matches_list_y = self.top_nav.height
        self.highlighted_row_y = int((self.canvas_height - GUIConstants.BUTTON_HEIGHT)/2)

        self.matches_list_highlight_button = Button(
            text="abcdefghijklmnopqrstuvwxyz",
            is_text_centered=False,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=GUIConstants.get_button_font_size() + 4,
            screen_x=self.matches_list_x,
            screen_y=self.highlighted_row_y,
            width=self.canvas_width - self.matches_list_x + GUIConstants.COMPONENT_PADDING,
            height=int(0.75*GUIConstants.BUTTON_HEIGHT),
            is_scrollable_text=False,
        )

        arrow_button_width = GUIConstants.BUTTON_HEIGHT + GUIConstants.EDGE_PADDING
        arrow_button_height = int(0.75*GUIConstants.BUTTON_HEIGHT)
        self.matches_list_up_button = IconButton(
            icon_name=FontAwesomeIconConstants.ANGLE_UP,
            icon_size=GUIConstants.ICON_INLINE_FONT_SIZE + 2,
            is_text_centered=False,
            screen_x=self.canvas_width - arrow_button_width + GUIConstants.COMPONENT_PADDING,
            screen_y=self.highlighted_row_y - 3*GUIConstants.COMPONENT_PADDING - GUIConstants.BUTTON_HEIGHT,
            width=arrow_button_width,
            height=arrow_button_height,
        )

        self.matches_list_down_button = IconButton(
            icon_name=FontAwesomeIconConstants.ANGLE_DOWN,
            icon_size=GUIConstants.ICON_INLINE_FONT_SIZE + 2,
            is_text_centered=False,
            screen_x=self.canvas_width - arrow_button_width + GUIConstants.COMPONENT_PADDING,
            screen_y=self.highlighted_row_y + GUIConstants.BUTTON_HEIGHT + 3*GUIConstants.COMPONENT_PADDING,
            width=arrow_button_width,
            height=arrow_button_height,
        )

        self.word_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, GUIConstants.get_button_font_size() + 4)
        (left, top, right, bottom) = self.word_font.getbbox("abcdefghijklmnopqrstuvwxyz", anchor="ls")
        self.word_font_height = -1 * top
        self.matches_list_row_height = self.word_font_height + GUIConstants.COMPONENT_PADDING


    def calc_possible_alphabet(self, new_letter = False):
        if (self.letters and len(self.letters) > 1 and new_letter == False) or (len(self.letters) > 0 and new_letter == True):
            search_letters = self.letters[:]
            if new_letter == False:
                search_letters.pop()
            self.calc_possible_words()
            letter_num = len(search_letters)
            possible_letters = []
            for word in self.possible_words:
                if len(word)-1 >= letter_num:
                    possible_letters.append(word[letter_num])
            # remove duplicates and keep order
            self.possible_alphabet = list(dict.fromkeys(possible_letters))[:]
        else:
            self.possible_alphabet = "abcdefghijklmnopqrstuvwxyz"
            self.possible_words = []


    def calc_possible_words(self):
        self.possible_words = [i for i in self.wordlist if i.startswith("".join(self.letters).strip())]
        self.selected_possible_words_index = 0        


    def render_possible_matches(self, highlight_word=None):
        """ Internal helper method to render the KEY 1, 2, 3 word candidates.
            (has access to all vars in the parent's context)
        """
        # Render the possible matches to a temp ImageDraw surface and paste it in
        # BUT render the currently highlighted match as a normal Button element

        if not self.possible_words:
            # Clear the right panel
            self.renderer.draw.rectangle(
                (
                    self.matches_list_x,
                    self.top_nav.height,
                    self.canvas_width,
                    self.matches_list_y
                ),
                fill=GUIConstants.BACKGROUND_COLOR
            )
            return

        img = Image.new(
            "RGB",
            (
                self.canvas_width - self.matches_list_x,
                self.canvas_height
            ),
            GUIConstants.BACKGROUND_COLOR
        )
        draw = ImageDraw.Draw(img)

        word_indent = GUIConstants.COMPONENT_PADDING

        highlighted_row = 3
        num_possible_rows = 11
        y = self.highlighted_row_y - GUIConstants.LIST_ITEM_PADDING - 3 * self.matches_list_row_height

        if not highlight_word:
            list_starting_index = self.selected_possible_words_index - highlighted_row
            for row, i in enumerate(range(list_starting_index, list_starting_index + num_possible_rows)):
                if i < 0:
                    # We're near the top of the list, not enough items to fill above the highlighted row
                    continue

                if row == highlighted_row:
                    # Leave the highlighted row to be rendered below
                    continue

                if len(self.possible_words) <= i:
                    # No more possible words to render
                    break

                if row < highlighted_row:
                    self.cur_y = self.highlighted_row_y - GUIConstants.COMPONENT_PADDING - (highlighted_row - row - 1) * self.matches_list_row_height

                elif row > highlighted_row:
                    self.cur_y = self.highlighted_row_y + self.matches_list_highlight_button.height + (row - highlighted_row) * self.matches_list_row_height

                # else draw the nth row
                draw.text(
                    (word_indent, self.cur_y),
                    self.possible_words[i],
                    fill="#ddd",
                    font=self.word_font,
                    anchor="ls",
                )

        self.canvas.paste(
            img.crop(
                (
                    0,
                    self.top_nav.height,
                    img.width,
                    img.height
                )
            ),
            (self.matches_list_x, self.matches_list_y)
        )

        # Now render the buttons over the matches list
        self.matches_list_highlight_button.text = self.possible_words[self.selected_possible_words_index]
        self.matches_list_highlight_button.is_selected = True
        self.matches_list_highlight_button.render()

        self.matches_list_up_button.render()
        self.matches_list_down_button.render()


    def _render(self):
        super()._render()
        self.keyboard.render_keys()
        self.text_entry_display.render()
        self.render_possible_matches()

        self.renderer.show_image()


    def _run(self):
        while True:
            input = self.hw_inputs.wait_for(HardwareButtonsConstants.ALL_KEYS)

            with self.renderer.lock:
                if self.is_input_in_top_nav:
                    if input == HardwareButtonsConstants.KEY_PRESS:
                        # User clicked the "back" arrow
                        return RET_CODE__BACK_BUTTON

                    elif input == HardwareButtonsConstants.KEY_UP:
                        input = Keyboard.ENTER_BOTTOM
                        self.is_input_in_top_nav = False
                        # Re-render it without the highlight
                        self.top_nav.left_button.is_selected = False
                        self.top_nav.left_button.render()

                    elif input == HardwareButtonsConstants.KEY_DOWN:
                        input = Keyboard.ENTER_TOP
                        self.is_input_in_top_nav = False
                        # Re-render it without the highlight
                        self.top_nav.left_button.is_selected = False
                        self.top_nav.left_button.render()

                    elif input in [HardwareButtonsConstants.KEY_RIGHT, HardwareButtonsConstants.KEY_LEFT]:
                        # no action in this context
                        continue

                ret_val = self.keyboard.update_from_input(input)

                if ret_val in Keyboard.EXIT_DIRECTIONS:
                    self.is_input_in_top_nav = True
                    self.top_nav.left_button.is_selected = True
                    self.top_nav.left_button.render()

                elif ret_val in Keyboard.ADDITIONAL_KEYS:
                    if input == HardwareButtonsConstants.KEY_PRESS and ret_val == Keyboard.KEY_BACKSPACE["code"]:
                        self.letters = self.letters[:-2]
                        self.letters.append(" ")

                        # Reactivate keys after deleting last letter
                        self.calc_possible_alphabet()
                        self.keyboard.update_active_keys(active_keys=self.possible_alphabet)
                        self.keyboard.render_keys()
                            
                        # Update the right-hand possible matches area
                        self.render_possible_matches()

                    elif ret_val == Keyboard.KEY_BACKSPACE["code"]:
                        # We're just hovering over DEL but haven't clicked. Show blank (" ")
                        #   in the live text entry display at the top.
                        self.letters = self.letters[:-1]
                        self.letters.append(" ")

                # Has the user made a final selection of a candidate word?
                final_selection = None
                if input == HardwareButtonsConstants.KEY1 and self.possible_words:
                    # Scroll the list up
                    self.selected_possible_words_index -= 1
                    if self.selected_possible_words_index < 0:
                        self.selected_possible_words_index = 0

                    if not self.arrow_up_is_active:
                        # Flash the up arrow as selected
                        self.arrow_up_is_active = True
                        self.matches_list_up_button.is_selected = True

                elif input == HardwareButtonsConstants.KEY2:
                    if self.possible_words:
                        final_selection = self.possible_words[self.selected_possible_words_index]

                elif input == HardwareButtonsConstants.KEY3 and self.possible_words:
                    # Scroll the list down
                    self.selected_possible_words_index += 1
                    if self.selected_possible_words_index >= len(self.possible_words):
                        self.selected_possible_words_index = len(self.possible_words) - 1

                    if not self.arrow_down_is_active:
                        # Flash the down arrow as selected
                        self.arrow_down_is_active = True
                        self.matches_list_down_button.is_selected = True

                if input is not HardwareButtonsConstants.KEY1 and self.arrow_up_is_active:
                    # Deactivate the UP arrow and redraw
                    self.arrow_up_is_active = False
                    self.matches_list_up_button.is_selected = False

                if input is not HardwareButtonsConstants.KEY3 and self.arrow_down_is_active:
                    # Deactivate the DOWN arrow and redraw
                    self.arrow_down_is_active = False
                    self.matches_list_down_button.is_selected = False

                if final_selection:
                    # Animate the selection storage, then return the word to the caller
                    self.letters = list(final_selection + " ")
                    self.render_possible_matches(highlight_word=final_selection)
                    self.text_entry_display.cur_text = ''.join(self.letters)
                    self.text_entry_display.render()
                    self.renderer.show_image()

                    return final_selection

                elif input == HardwareButtonsConstants.KEY_PRESS and ret_val in self.possible_alphabet:
                    # User has locked in the current letter
                    if self.letters[-1] != " ":
                        # We'll save that locked in letter next but for now update the
                        # live text entry display with blank (" ") so that we don't try
                        # to autocalc matches against a second copy of the letter they
                        # just selected. e.g. They KEY_PRESS on "s" to build "mus". If
                        # we advance the live block cursor AND display "s" in it, the
                        # current word would then be "muss" with no matches. If "mus"
                        # can get us to our match, we don't want it to disappear right
                        # as we KEY_PRESS.
                        self.letters.append(" ")
                    else:
                        # clicked same letter twice in a row. Because of the above, an
                        # immediate second click of the same letter would lock in "ap "
                        # (note the space) instead of "app". So we replace that trailing
                        # space with the correct repeated letter and then, as above,
                        # append a trailing blank.
                        self.letters = self.letters[:-1]
                        self.letters.append(ret_val)
                        self.letters.append(" ")

                    # Recalc and deactivate keys after advancing
                    self.calc_possible_alphabet()
                    self.keyboard.update_active_keys(active_keys=self.possible_alphabet)

                    if len(self.possible_alphabet) == 1:
                        # If there's only one possible letter left, select it
                        self.keyboard.set_selected_key(self.possible_alphabet[0])

                    self.keyboard.render_keys()

                elif input in HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN \
                        or input in (Keyboard.ENTER_TOP, Keyboard.ENTER_BOTTOM):
                    if ret_val in self.possible_alphabet:
                        # Live joystick movement; haven't locked this new letter in yet.
                        # Replace the last letter w/the currently selected one. But don't
                        # call `calc_possible_alphabet()` because we want to still be able
                        # to freely float to a different letter; only update the active
                        # keyboard keys when a selection has been locked in (KEY_PRESS) or
                        # removed ("del").
                        self.letters = self.letters[:-1]
                        self.letters.append(ret_val)
                        self.calc_possible_words()  # live update our matches as we move
                    
                    else:
                        # We've navigated to a deactivated letter
                        pass

                # Render the text entry display and cursor block
                self.text_entry_display.cur_text = ''.join(self.letters)
                self.text_entry_display.render()

                # Update the right-hand possible matches area
                self.render_possible_matches()

                # Now issue one call to send the pixels to the screen
                self.renderer.show_image()



@dataclass
class SeedFinalizeScreen(ButtonListScreen):
    fingerprint: str = None
    is_bottom_list: bool = True
    button_data: list = None

    def __post_init__(self):
        self.show_back_button = False
        self.title = _("Finalize Seed")
        super().__post_init__()

        self.fingerprint_icontl = IconTextLine(
            icon_name=SeedSignerIconConstants.FINGERPRINT,
            icon_color=GUIConstants.INFO_COLOR,
            icon_size=GUIConstants.ICON_FONT_SIZE + 12,
            label_text=_("fingerprint"),
            value_text=self.fingerprint,
            font_size=GUIConstants.get_body_font_size() + 2,
            is_text_centered=True,
            screen_y=self.top_nav.height + int((self.buttons[0].screen_y - self.top_nav.height) / 2) - 30
        )
        self.components.append(self.fingerprint_icontl)



@dataclass
class SeedOptionsScreen(ButtonListScreen):
    fingerprint: str = None
    has_passphrase: bool = False

    def __post_init__(self):
        self.top_nav_icon_name = SeedSignerIconConstants.FINGERPRINT
        self.top_nav_icon_color = GUIConstants.INFO_COLOR
        self.title = self.fingerprint
        self.is_button_text_centered = False
        self.is_bottom_list = True

        super().__post_init__()



@dataclass
class SeedBackupScreen(ButtonListScreen):
    has_passphrase: bool = False

    def __post_init__(self):
        self.title = _("Backup Seed")
        self.is_bottom_list = True
        super().__post_init__()

        if self.has_passphrase:
            self.components.append(TextArea(
                # TRANSLATOR_NOTE: Additional explainer for the two seed backup options (mnemonic phrase and SeedQR).
                text=_("Backups do not include your passphrase."),
                screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
            ))



@dataclass
class SeedWordsScreen(WarningEdgesMixin, ButtonListScreen):
    words: List[str] = None
    page_index: int = 0
    num_pages: int = 3
    is_bottom_list: bool = True
    status_color: str = GUIConstants.DIRE_WARNING_COLOR


    def __post_init__(self):
        # TRANSLATOR_NOTE: Displays the page number and total: (e.g. page 1 of 6)
        self.title = _("Seed Words: {}/{}").format(self.page_index + 1, self.num_pages)
        super().__post_init__()

        words_per_page = len(self.words)

        self.body_x = 0
        self.body_y = self.top_nav.height - int(GUIConstants.COMPONENT_PADDING / 2)
        self.body_height = self.buttons[0].screen_y - self.body_y

        # Have to supersample the whole body since it's all at the small font size
        supersampling_factor = 1
        font = Fonts.get_font(GUIConstants.get_body_font_name(), (GUIConstants.get_top_nav_title_font_size() + 2) * supersampling_factor)

        # Calc horizontal center based on longest word
        max_word_width = 0
        for word in self.words:
            (left, top, right, bottom) = font.getbbox(word, anchor="ls")
            if right > max_word_width:
                max_word_width = right

        # Measure the max digit height for the numbering boxes, from baseline
        number_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_button_font_size() * supersampling_factor)
        (left, top, right, bottom) = number_font.getbbox("24", anchor="ls")
        number_height = -1 * top
        number_width = right
        number_box_width = number_width + int(GUIConstants.COMPONENT_PADDING/2 * supersampling_factor)
        number_box_height = number_box_width

        number_box_x = int((self.canvas_width * supersampling_factor - number_box_width - GUIConstants.COMPONENT_PADDING*supersampling_factor - max_word_width))/2
        number_box_y = GUIConstants.COMPONENT_PADDING * supersampling_factor

        # Set up our temp supersampled rendering surface
        self.body_img = Image.new(
            "RGB",
            (self.canvas_width * supersampling_factor, self.body_height * supersampling_factor),
            GUIConstants.BACKGROUND_COLOR
        )
        draw = ImageDraw.Draw(self.body_img)

        for index, word in enumerate(self.words):
            draw.rounded_rectangle(
                (number_box_x, number_box_y, number_box_x + number_box_width, number_box_y + number_box_height),
                fill=GUIConstants.BUTTON_BACKGROUND_COLOR,
                radius=5 * supersampling_factor
            )
            baseline_y = number_box_y + number_box_height - int((number_box_height - number_height)/2)
            draw.text(
                (number_box_x + int(number_box_width/2), baseline_y),
                font=number_font,
                text=str(self.page_index * words_per_page + index + 1),
                fill=GUIConstants.INFO_COLOR,
                anchor="ms"  # Middle (centered), baSeline
            )

            # Now draw the word
            draw.text(
                (number_box_x + number_box_width + (GUIConstants.COMPONENT_PADDING * supersampling_factor), baseline_y),
                font=font,
                text=word,
                fill=GUIConstants.BODY_FONT_COLOR,
                anchor="ls",  # Left, baSeline
            )

            number_box_y += number_box_height + (int(1.5*GUIConstants.COMPONENT_PADDING) * supersampling_factor)

        # Resize to target and sharpen final image
        self.body_img = self.body_img.resize((self.canvas_width, self.body_height), Image.Resampling.LANCZOS)
        self.body_img = self.body_img.filter(ImageFilter.SHARPEN)
        self.paste_images.append((self.body_img, (self.body_x, self.body_y)))



@dataclass
class SeedBIP85SelectChildIndexScreen(KeyboardScreen):
    def __post_init__(self):
        self.title = _("BIP-85 Index")
        self.user_input = ""

        # Specify the keys in the keyboard
        self.rows = 3
        self.cols = 5
        self.keys_charset = "0123456789"
        self.show_save_button = True

        super().__post_init__()



@dataclass
class SeedWordsBackupTestPromptScreen(ButtonListScreen):
    def __post_init__(self):
        self.title = _("Verify Backup?")
        self.show_back_button = False
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(TextArea(
            text=_("Optionally verify that your mnemonic backup is correct."),
            screen_y=self.top_nav.height,
            is_text_centered=True,
        ))



@dataclass
class SeedExportXpubCustomDerivationScreen(KeyboardScreen):
    def __post_init__(self):
        self.title = _("Derivation Path")
        self.user_input = "m/"

        # Specify the keys in the keyboard
        self.rows = 3
        self.cols = 6
        self.keys_charset = "/'0123456789"
        self.show_save_button = True

        super().__post_init__()



@dataclass
class SeedExportXpubDetailsScreen(WarningEdgesMixin, ButtonListScreen):
    # Customize defaults
    is_bottom_list: bool = True
    fingerprint: str = None
    has_passphrase: bool = False
    derivation_path: str = "m/84'/0'/0'"
    xpub: str = "zpub6r..."

    def __post_init__(self):
        # Programmatically set up other args
        self.button_data = [ButtonOption("Export Xpub")]
        self.title = _("Xpub Details")

        # Initialize the base class
        super().__post_init__()

        # Set up the fingerprint and passphrase displays
        self.fingerprint_line = IconTextLine(
            icon_name=SeedSignerIconConstants.FINGERPRINT,
            icon_color=GUIConstants.INFO_COLOR,
            # TRANSLATOR_NOTE: Short for "BIP32 Master Fingerprint"
            label_text=_("Fingerprint"),
            value_text=self.fingerprint,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        )
        self.components.append(self.fingerprint_line)

        self.derivation_line = IconTextLine(
            icon_name=SeedSignerIconConstants.DERIVATION,
            icon_color=GUIConstants.INFO_COLOR,
            # TRANSLATOR_NOTE: Short for "Derivation Path"
            label_text=_("Derivation"),
            value_text=self.derivation_path,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=self.components[-1].screen_y + self.components[-1].height + int(1.5*GUIConstants.COMPONENT_PADDING),
        )
        self.components.append(self.derivation_line)

        self.xpub_line = IconTextLine(
            icon_name=FontAwesomeIconConstants.X,
            icon_color=GUIConstants.INFO_COLOR,
            # TRANSLATOR_NOTE: Short for "BIP32 Extended Public Key"
            label_text=_("Xpub"),
            value_text=f"{self.xpub[:18]}...",
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_size=GUIConstants.get_body_font_size() + 2,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=self.components[-1].screen_y + self.components[-1].height + int(1.5*GUIConstants.COMPONENT_PADDING),
        )
        self.components.append(self.xpub_line)



@dataclass
class SeedAddPassphraseScreen(BaseTopNavScreen):
    passphrase: str = ""

    # Only used by the screenshot generator
    initial_keyboard: str = None

    KEYBOARD__LOWERCASE_BUTTON_TEXT = "abc"
    KEYBOARD__UPPERCASE_BUTTON_TEXT = "ABC"
    KEYBOARD__DIGITS_BUTTON_TEXT = "123"
    KEYBOARD__SYMBOLS_1_BUTTON_TEXT = "!@#"
    KEYBOARD__SYMBOLS_2_BUTTON_TEXT = "*[]"


    def __post_init__(self):
        self.title = _("BIP-39 Passphrase")
        super().__post_init__()

        keys_lower = "abcdefghijklmnopqrstuvwxyz"
        keys_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        keys_number = "0123456789"

        # Present the most common/puncutation-related symbols & the most human-friendly
        #   symbols first (limited to 18 chars).
        keys_symbol_1 = """!@#$%&();:,.-+='"?"""

        # Isolate the more math-oriented or just uncommon symbols
        keys_symbol_2 = """^*[]{}_\\|<>/`~"""


        # Set up the keyboard params
        self.right_panel_buttons_width = 56

        max_cols = 9
        text_entry_display_y = self.top_nav.height
        text_entry_display_height = 30

        keyboard_start_y = text_entry_display_y + text_entry_display_height + GUIConstants.COMPONENT_PADDING
        self.keyboard_abc = Keyboard(
            draw=self.renderer.draw,
            charset=keys_lower,
            rows=4,
            cols=max_cols,
            rect=(
                GUIConstants.COMPONENT_PADDING,
                keyboard_start_y,
                self.canvas_width - GUIConstants.COMPONENT_PADDING - self.right_panel_buttons_width,
                self.canvas_height - GUIConstants.EDGE_PADDING
            ),
            additional_keys=[
                Keyboard.KEY_SPACE_5,
                Keyboard.KEY_CURSOR_LEFT,
                Keyboard.KEY_CURSOR_RIGHT,
                Keyboard.KEY_BACKSPACE
            ],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT]
        )

        self.keyboard_ABC = Keyboard(
            draw=self.renderer.draw,
            charset=keys_upper,
            rows=4,
            cols=max_cols,
            rect=(
                GUIConstants.COMPONENT_PADDING,
                keyboard_start_y,
                self.canvas_width - GUIConstants.COMPONENT_PADDING - self.right_panel_buttons_width,
                self.canvas_height - GUIConstants.EDGE_PADDING
            ),
            additional_keys=[
                Keyboard.KEY_SPACE_5,
                Keyboard.KEY_CURSOR_LEFT,
                Keyboard.KEY_CURSOR_RIGHT,
                Keyboard.KEY_BACKSPACE
            ],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        self.keyboard_digits = Keyboard(
            draw=self.renderer.draw,
            charset=keys_number,
            rows=3,
            cols=5,
            rect=(
                GUIConstants.COMPONENT_PADDING,
                keyboard_start_y,
                self.canvas_width - GUIConstants.COMPONENT_PADDING - self.right_panel_buttons_width,
                self.canvas_height - GUIConstants.EDGE_PADDING
            ),
            additional_keys=[
                Keyboard.KEY_CURSOR_LEFT,
                Keyboard.KEY_CURSOR_RIGHT,
                Keyboard.KEY_BACKSPACE
            ],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        self.keyboard_symbols_1 = Keyboard(
            draw=self.renderer.draw,
            charset=keys_symbol_1,
            rows=4,
            cols=6,
            rect=(
                GUIConstants.COMPONENT_PADDING,
                keyboard_start_y,
                self.canvas_width - GUIConstants.COMPONENT_PADDING - self.right_panel_buttons_width,
                self.canvas_height - GUIConstants.EDGE_PADDING
            ),
            additional_keys=[
                Keyboard.KEY_SPACE_2,
                Keyboard.KEY_CURSOR_LEFT,
                Keyboard.KEY_CURSOR_RIGHT,
                Keyboard.KEY_BACKSPACE
            ],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        self.keyboard_symbols_2 = Keyboard(
            draw=self.renderer.draw,
            charset=keys_symbol_2,
            rows=4,
            cols=6,
            rect=(
                GUIConstants.COMPONENT_PADDING,
                keyboard_start_y,
                self.canvas_width - GUIConstants.COMPONENT_PADDING - self.right_panel_buttons_width,
                self.canvas_height - GUIConstants.EDGE_PADDING
            ),
            additional_keys=[
                Keyboard.KEY_SPACE_2,
                Keyboard.KEY_CURSOR_LEFT,
                Keyboard.KEY_CURSOR_RIGHT,
                Keyboard.KEY_BACKSPACE
            ],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        self.text_entry_display = TextEntryDisplay(
            canvas=self.renderer.canvas,
            rect=(
                GUIConstants.EDGE_PADDING,
                text_entry_display_y,
                self.canvas_width - self.right_panel_buttons_width,
                text_entry_display_y + text_entry_display_height
            ),
            cursor_mode=TextEntryDisplay.CURSOR_MODE__BAR,
            is_centered=False,
            cur_text=''.join(self.passphrase)
        )

        # Nudge the buttons off the right edge w/padding
        hw_button_x = self.canvas_width - self.right_panel_buttons_width + GUIConstants.COMPONENT_PADDING

        # Calc center button position first
        hw_button_y = int((self.canvas_height - GUIConstants.BUTTON_HEIGHT)/2)

        self.hw_button1 = Button(
            text=self.KEYBOARD__UPPERCASE_BUTTON_TEXT,
            is_text_centered=False,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=GUIConstants.get_button_font_size() + 4,
            width=self.right_panel_buttons_width,
            screen_x=hw_button_x,
            screen_y=hw_button_y - 3*GUIConstants.COMPONENT_PADDING - GUIConstants.BUTTON_HEIGHT,
            is_scrollable_text=False,
        )

        self.hw_button2 = Button(
            text=self.KEYBOARD__DIGITS_BUTTON_TEXT,
            is_text_centered=False,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=GUIConstants.get_button_font_size() + 4,
            width=self.right_panel_buttons_width,
            screen_x=hw_button_x,
            screen_y=hw_button_y,
            is_scrollable_text=False,
        )

        self.hw_button3 = IconButton(
            icon_name=SeedSignerIconConstants.CHECK,
            icon_color=GUIConstants.SUCCESS_COLOR,
            width=self.right_panel_buttons_width,
            screen_x=hw_button_x,
            screen_y=hw_button_y + 3*GUIConstants.COMPONENT_PADDING + GUIConstants.BUTTON_HEIGHT,
            is_scrollable_text=False,
        )


    def _render(self):
        super()._render()

        # Change from the default lowercase keyboard for the screenshot generator
        if self.initial_keyboard == self.KEYBOARD__UPPERCASE_BUTTON_TEXT:
            cur_keyboard = self.keyboard_ABC
            self.hw_button1.text = self.KEYBOARD__LOWERCASE_BUTTON_TEXT

        elif self.initial_keyboard == self.KEYBOARD__DIGITS_BUTTON_TEXT:
            cur_keyboard = self.keyboard_digits
            self.hw_button2.text = self.KEYBOARD__SYMBOLS_1_BUTTON_TEXT

        elif self.initial_keyboard == self.KEYBOARD__SYMBOLS_1_BUTTON_TEXT:
            cur_keyboard = self.keyboard_symbols_1
            self.hw_button2.text = self.KEYBOARD__SYMBOLS_2_BUTTON_TEXT

        elif self.initial_keyboard == self.KEYBOARD__SYMBOLS_2_BUTTON_TEXT:
            cur_keyboard = self.keyboard_symbols_2
            self.hw_button2.text = self.KEYBOARD__DIGITS_BUTTON_TEXT
        
        else:
            cur_keyboard = self.keyboard_abc

        self.text_entry_display.render()
        self.hw_button1.render()
        self.hw_button2.render()
        self.hw_button3.render()
        cur_keyboard.render_keys()

        self.renderer.show_image()


    def _run(self):
        cursor_position = len(self.passphrase)
        cur_keyboard = self.keyboard_abc
        cur_button1_text = self.KEYBOARD__UPPERCASE_BUTTON_TEXT
        cur_button2_text = self.KEYBOARD__DIGITS_BUTTON_TEXT

        # Start the interactive update loop
        while True:
            input = self.hw_inputs.wait_for(HardwareButtonsConstants.ALL_KEYS)

            keyboard_swap = False

            with self.renderer.lock:
                # Check our two possible exit conditions
                # TODO: note the unusual return value, consider refactoring to a Response object in the future
                if input == HardwareButtonsConstants.KEY3:
                    # Save!
                    # First light up key3
                    self.hw_button3.is_selected = True
                    self.hw_button3.render()
                    self.renderer.show_image()
                    return dict(passphrase=self.passphrase)

                elif input == HardwareButtonsConstants.KEY_PRESS and self.top_nav.is_selected:
                    # Back button clicked
                    return dict(passphrase=self.passphrase, is_back_button=True)

                # Check for keyboard swaps
                if input == HardwareButtonsConstants.KEY1:
                    # First light up key1
                    self.hw_button1.is_selected = True
                    self.hw_button1.render()

                    # Return to the same button2 keyboard, if applicable
                    if cur_keyboard == self.keyboard_digits:
                        cur_button2_text = self.KEYBOARD__DIGITS_BUTTON_TEXT
                    elif cur_keyboard == self.keyboard_symbols_1:
                        cur_button2_text = self.KEYBOARD__SYMBOLS_1_BUTTON_TEXT
                    elif cur_keyboard == self.keyboard_symbols_2:
                        cur_button2_text = self.KEYBOARD__SYMBOLS_2_BUTTON_TEXT

                    if cur_button1_text == self.KEYBOARD__LOWERCASE_BUTTON_TEXT:
                        self.keyboard_abc.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                        cur_keyboard = self.keyboard_abc
                        cur_button1_text = self.KEYBOARD__UPPERCASE_BUTTON_TEXT
                    else:
                        self.keyboard_ABC.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                        cur_keyboard = self.keyboard_ABC
                        cur_button1_text = self.KEYBOARD__LOWERCASE_BUTTON_TEXT
                    cur_keyboard.render_keys()

                    # Show the changes; this loop will have two renders
                    self.renderer.show_image()

                    keyboard_swap = True
                    ret_val = None

                elif input == HardwareButtonsConstants.KEY2:
                    # First light up key2
                    self.hw_button2.is_selected = True
                    self.hw_button2.render()
                    self.renderer.show_image()

                    # And reset for next redraw
                    self.hw_button2.is_selected = False

                    # Return to the same button1 keyboard, if applicable
                    if cur_keyboard == self.keyboard_abc:
                        cur_button1_text = self.KEYBOARD__LOWERCASE_BUTTON_TEXT
                    elif cur_keyboard == self.keyboard_ABC:
                        cur_button1_text = self.KEYBOARD__UPPERCASE_BUTTON_TEXT

                    if cur_button2_text == self.KEYBOARD__DIGITS_BUTTON_TEXT:
                        self.keyboard_digits.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                        cur_keyboard = self.keyboard_digits
                        cur_keyboard.render_keys()
                        cur_button2_text = self.KEYBOARD__SYMBOLS_1_BUTTON_TEXT
                    elif cur_button2_text == self.KEYBOARD__SYMBOLS_1_BUTTON_TEXT:
                        self.keyboard_symbols_1.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                        cur_keyboard = self.keyboard_symbols_1
                        cur_keyboard.render_keys()
                        cur_button2_text = self.KEYBOARD__SYMBOLS_2_BUTTON_TEXT
                    elif cur_button2_text == self.KEYBOARD__SYMBOLS_2_BUTTON_TEXT:
                        self.keyboard_symbols_2.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                        cur_keyboard = self.keyboard_symbols_2
                        cur_keyboard.render_keys()
                        cur_button2_text = self.KEYBOARD__DIGITS_BUTTON_TEXT
                    cur_keyboard.render_keys()

                    # Show the changes; this loop will have two renders
                    self.renderer.show_image()

                    keyboard_swap = True
                    ret_val = None

                else:
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

                    ret_val = cur_keyboard.update_from_input(input)

                # Now process the result from the keyboard
                if ret_val in Keyboard.EXIT_DIRECTIONS:
                    self.top_nav.is_selected = True
                    self.top_nav.render_buttons()

                elif ret_val in Keyboard.ADDITIONAL_KEYS and input == HardwareButtonsConstants.KEY_PRESS:
                    if ret_val == Keyboard.KEY_BACKSPACE["code"]:
                        if cursor_position == 0:
                            pass
                        elif cursor_position == len(self.passphrase):
                            self.passphrase = self.passphrase[:-1]
                            cursor_position -= 1
                        else:
                            self.passphrase = self.passphrase[:cursor_position - 1] + self.passphrase[cursor_position:]
                            cursor_position -= 1

                    elif ret_val == Keyboard.KEY_CURSOR_LEFT["code"]:
                        cursor_position -= 1
                        if cursor_position < 0:
                            cursor_position = 0

                    elif ret_val == Keyboard.KEY_CURSOR_RIGHT["code"]:
                        cursor_position += 1
                        if cursor_position > len(self.passphrase):
                            cursor_position = len(self.passphrase)

                    elif ret_val == Keyboard.KEY_SPACE["code"]:
                        if cursor_position == len(self.passphrase):
                            self.passphrase += " "
                        else:
                            self.passphrase = self.passphrase[:cursor_position] + " " + self.passphrase[cursor_position:]
                        cursor_position += 1

                    # Update the text entry display and cursor
                    self.text_entry_display.render(self.passphrase, cursor_position)

                elif input == HardwareButtonsConstants.KEY_PRESS and ret_val not in Keyboard.ADDITIONAL_KEYS:
                    # User has locked in the current letter
                    if cursor_position == len(self.passphrase):
                        self.passphrase += ret_val
                    else:
                        self.passphrase = self.passphrase[:cursor_position] + ret_val + self.passphrase[cursor_position:]
                    cursor_position += 1

                    # Update the text entry display and cursor
                    self.text_entry_display.render(self.passphrase, cursor_position)

                elif input in HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN or keyboard_swap:
                    # Live joystick movement; haven't locked this new letter in yet.
                    # Leave current spot blank for now. Only update the active keyboard keys
                    # when a selection has been locked in (KEY_PRESS) or removed ("del").
                    pass
            
                if keyboard_swap:
                    # Show the hw buttons' updated text and not active state
                    self.hw_button1.text = cur_button1_text
                    self.hw_button2.text = cur_button2_text                
                    self.hw_button1.is_selected = False
                    self.hw_button2.is_selected = False
                    self.hw_button1.render()
                    self.hw_button2.render()

                self.renderer.show_image()



@dataclass
class SeedReviewPassphraseScreen(ButtonListScreen):
    fingerprint_without: str = None
    fingerprint_with: str = None
    passphrase: str = None

    def __post_init__(self):
        # Customize defaults
        self.title = _("Verify Passphrase")
        self.is_bottom_list = True

        super().__post_init__()

        self.components.append(IconTextLine(
            icon_name=SeedSignerIconConstants.FINGERPRINT,
            icon_color=GUIConstants.INFO_COLOR,
            # TRANSLATOR_NOTE: Describes the effect of applying a BIP-39 passphrase; it changes the seed's fingerprint
            label_text=_("changes fingerprint"),
            value_text=f"{self.fingerprint_without} >> {self.fingerprint_with}",
            is_text_centered=True,
            screen_y = self.buttons[0].screen_y - GUIConstants.COMPONENT_PADDING - int(GUIConstants.get_body_font_size()*2.5)
        ))

        if self.passphrase != self.passphrase.strip() or "  " in self.passphrase:
            self.passphrase = self.passphrase.replace(" ", "\u2589")
        available_height = self.components[-1].screen_y - self.top_nav.height + GUIConstants.COMPONENT_PADDING
        max_font_size = GUIConstants.get_top_nav_title_font_size() + 8
        min_font_size = GUIConstants.get_top_nav_title_font_size() - 4
        font_size = max_font_size
        max_lines = 3
        passphrase = [self.passphrase]
        found_solution = False
        for font_size in range(max_font_size, min_font_size, -2):
            if found_solution:
                break
            font = Fonts.get_font(font_name=GUIConstants.FIXED_WIDTH_FONT_NAME, size=font_size)
            left, top, right, bottom  = font.getbbox("X")
            char_width, char_height = right - left, bottom - top
            for num_lines in range(1, max_lines+1):
                # Break the passphrase into n lines
                chars_per_line = math.ceil(len(self.passphrase) / num_lines)
                passphrase = []
                for i in range(0, len(self.passphrase), chars_per_line):
                    passphrase.append(self.passphrase[i:i+chars_per_line])
                
                # See if it fits in this configuration
                if char_width * len(passphrase[0]) <= self.canvas_width - 2*GUIConstants.EDGE_PADDING:
                    # Width is good...
                    if num_lines * char_height <= available_height:
                        # And the height is good!
                        found_solution = True
                        break

        # Set up each line of text
        screen_y = self.top_nav.height + int((available_height - char_height*num_lines)/2) - GUIConstants.COMPONENT_PADDING
        for line in passphrase:
            self.components.append(TextArea(
                text=line,
                font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
                font_size=font_size,
                font_color="orange",
                is_text_centered=True,
                screen_y=screen_y,
                allow_text_overflow=True
            ))
            screen_y += char_height + 2



@dataclass
class SeedTranscribeSeedQRFormatScreen(ButtonListScreen):
    def __post_init__(self):
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(IconTextLine(
            # TRANSLATOR_NOTE: Refers to the SeedQR type: Standard or Compact
            label_text=_("Standard"),
            # TRANSLATOR_NOTE: Briefly explains the Standard SeedQR data format
            value_text=_("BIP-39 wordlist indices"),
            is_text_centered=False,
            auto_line_break=True,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        ))
        self.components.append(IconTextLine(
            # TRANSLATOR_NOTE: Refers to the SeedQR type: Standard or Compact
            label_text=_("Compact"),
            # TRANSLATOR_NOTE: Briefly explains the Compact SeedQR data format
            value_text=_("Raw entropy bits"),
            is_text_centered=False,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING,
        ))



@dataclass
class SeedTranscribeSeedQRWholeQRScreen(WarningEdgesMixin, ButtonListScreen):
    qr_data: str = None
    num_modules: int = None

    def __post_init__(self):
        self.title = _("Transcribe SeedQR")
        # TRANSLATOR_NOTE: Refers to the QR code size: 21x21, 25x25, or 29x29
        button_label = _("Begin {}x{}").format(self.num_modules, self.num_modules)
        self.button_data = [ButtonOption(button_label)]
        self.is_bottom_list = True
        self.status_color = GUIConstants.DIRE_WARNING_COLOR
        super().__post_init__()

        qr_height = self.buttons[0].screen_y - self.top_nav.height - GUIConstants.COMPONENT_PADDING
        qr_width = qr_height

        qr = QR()
        qr_image = qr.qrimage(
            data=self.qr_data,
            width=qr_width,
            height=qr_height,
            border=1,
            style=QR.STYLE__ROUNDED
        ).convert("RGBA")

        self.paste_images.append((qr_image, (int((self.canvas_width - qr_width)/2), self.top_nav.height)))



@dataclass
class SeedTranscribeSeedQRZoomedInScreen(BaseScreen):
    qr_data: str = None
    num_modules: int = None
    initial_block_x: int = 0
    initial_block_y: int = 0

    def __post_init__(self):
        super().__post_init__()

        # Render an oversized QR code that we can view up close
        self.pixels_per_block = 24

        # Border must accommodate the 3 blocks outside the center 5x5 mask plus up to
        # 1 empty block inside the 5x5 mask (29x29 has a 4-block final col/row).
        self.qr_border = 4
        if self.num_modules == 21:
            # Optimize for 21x21
            self.qr_blocks_per_zoom = 7
        else:
            self.qr_blocks_per_zoom = 5

        self.qr_width = (self.qr_border + self.num_modules + self.qr_border) * self.pixels_per_block
        self.height = self.qr_width
        qr = QR()
        self.qr_image = qr.qrimage(
            self.qr_data,
            width=self.qr_width,
            height=self.height,
            border=self.qr_border,
            style=QR.STYLE__ROUNDED
        ).convert("RGBA")

        # Render gridlines but leave the 1-block border as-is
        draw = ImageDraw.Draw(self.qr_image)
        for i in range(self.qr_border, math.floor(self.qr_width/self.pixels_per_block) - self.qr_border):
            draw.line((i * self.pixels_per_block, self.qr_border * self.pixels_per_block, i * self.pixels_per_block, self.height - self.qr_border * self.pixels_per_block), fill="#bbb")
            draw.line((self.qr_border * self.pixels_per_block, i * self.pixels_per_block, self.qr_width - self.qr_border * self.pixels_per_block, i * self.pixels_per_block), fill="#bbb")

        # Prep the semi-transparent mask overlay
        # make a blank image for the overlay, initialized to transparent
        self.block_mask = Image.new("RGBA", (self.canvas_width, self.canvas_height), (255,255,255,0))
        draw = ImageDraw.Draw(self.block_mask)

        self.mask_width = int((self.canvas_width - self.qr_blocks_per_zoom * self.pixels_per_block)/2)
        self.mask_height = int((self.canvas_height - self.qr_blocks_per_zoom * self.pixels_per_block)/2)
        mask_rgba = (0, 0, 0, 226)
        draw.rectangle((0, 0, self.canvas_width, self.mask_height), fill=mask_rgba)
        draw.rectangle((0, self.canvas_height - self.mask_height - 1, self.canvas_width, self.canvas_height), fill=mask_rgba)
        draw.rectangle((0, self.mask_height, self.mask_width, self.canvas_height - self.mask_height), fill=mask_rgba)
        draw.rectangle((self.canvas_width - self.mask_width - 1, self.mask_height, self.canvas_width, self.canvas_height - self.mask_height), fill=mask_rgba)

        # Draw a box around the cutout portion of the mask for better visibility
        draw.line((self.mask_width, self.mask_height, self.mask_width, self.canvas_height - self.mask_height), fill=GUIConstants.ACCENT_COLOR)
        draw.line((self.canvas_width - self.mask_width, self.mask_height, self.canvas_width - self.mask_width, self.canvas_height - self.mask_height), fill=GUIConstants.ACCENT_COLOR)
        draw.line((self.mask_width, self.mask_height, self.canvas_width - self.mask_width, self.mask_height), fill=GUIConstants.ACCENT_COLOR)
        draw.line((self.mask_width, self.canvas_height - self.mask_height, self.canvas_width - self.mask_width, self.canvas_height - self.mask_height), fill=GUIConstants.ACCENT_COLOR)

        msg = _("click to exit")
        font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size())
        (left, top, right, bottom) = font.getbbox(msg, anchor="ls")
        msg_height = -1 * top + GUIConstants.COMPONENT_PADDING
        msg_width = right + 2*GUIConstants.COMPONENT_PADDING
        draw.rectangle(
            (
                int((self.canvas_width - msg_width)/2),
                self.canvas_height - msg_height,
                int((self.canvas_width + msg_width)/2),
                self.canvas_height
            ),
            fill=GUIConstants.BACKGROUND_COLOR,
        )
        draw.text(
            (int(self.canvas_width/2), self.canvas_height - int(GUIConstants.COMPONENT_PADDING/2)),
            msg,
            fill=GUIConstants.BODY_FONT_COLOR,
            font=font,
            anchor="ms"  # Middle, baSeline
        )



    def draw_block_labels(self):
        # Create overlay for block labels (e.g. "D-5")
        block_labels_x = ["1", "2", "3", "4", "5", "6"]
        block_labels_y = ["A", "B", "C", "D", "E", "F"]

        block_labels = Image.new("RGBA", (self.canvas_width, self.canvas_height), (255,255,255,0))
        draw = ImageDraw.Draw(block_labels)
        draw.rectangle((self.mask_width, 0, self.canvas_width - self.mask_width, self.pixels_per_block), fill=GUIConstants.ACCENT_COLOR)
        draw.rectangle((0, self.mask_height, self.pixels_per_block, self.canvas_height - self.mask_height), fill=GUIConstants.ACCENT_COLOR)

        label_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 28)
        x_label = block_labels_x[self.cur_block_x]
        (left, top, right, bottom) = label_font.getbbox(x_label, anchor="ls")
        x_label_height = -1 * top

        draw.text(
            (int(self.canvas_width/2), self.pixels_per_block - int((self.pixels_per_block - x_label_height)/2)),
            text=x_label,
            fill=GUIConstants.BUTTON_SELECTED_FONT_COLOR,
            font=label_font,
            anchor="ms",  # Middle, baSeline
        )

        y_label = block_labels_y[self.cur_block_y]
        (left, top, right, bottom) = label_font.getbbox(y_label, anchor="ls")
        y_label_height = -1 * top
        draw.text(
            (int(self.pixels_per_block/2), int((self.canvas_height + y_label_height) / 2)),
            text=y_label,
            fill=GUIConstants.BUTTON_SELECTED_FONT_COLOR,
            font=label_font,
            anchor="ms",  # Middle, baSeline
        )

        return block_labels


    def _render(self):
        # Track our current coordinates for the upper left corner of our view
        self.cur_block_x = self.initial_block_x
        self.cur_block_y = self.initial_block_y
        self.cur_x = (self.cur_block_x * self.qr_blocks_per_zoom * self.pixels_per_block) + self.qr_border * self.pixels_per_block - self.mask_width
        self.cur_y = (self.cur_block_y * self.qr_blocks_per_zoom * self.pixels_per_block) + self.qr_border * self.pixels_per_block - self.mask_height
        self.next_x = self.cur_x
        self.next_y = self.cur_y

        block_labels = self.draw_block_labels()

        self.renderer.show_image(
            self.qr_image.crop((self.cur_x, self.cur_y, self.cur_x + self.canvas_width, self.cur_y + self.canvas_height)),
            alpha_overlay=Image.alpha_composite(self.block_mask, block_labels)
        )


    def _run(self):
        while True:
            input = self.hw_inputs.wait_for(HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN + HardwareButtonsConstants.KEYS__ANYCLICK)
            if input == HardwareButtonsConstants.KEY_RIGHT:
                self.next_x = self.cur_x + self.qr_blocks_per_zoom * self.pixels_per_block
                self.cur_block_x += 1
                if self.next_x > self.qr_width - self.canvas_width:
                    self.next_x = self.cur_x
                    self.cur_block_x -= 1
            elif input == HardwareButtonsConstants.KEY_LEFT:
                self.next_x = self.cur_x - self.qr_blocks_per_zoom * self.pixels_per_block
                self.cur_block_x -= 1
                if self.next_x < 0:
                    self.next_x = self.cur_x
                    self.cur_block_x += 1
            elif input == HardwareButtonsConstants.KEY_DOWN:
                self.next_y = self.cur_y + self.qr_blocks_per_zoom * self.pixels_per_block
                self.cur_block_y += 1
                if self.next_y > self.height - self.canvas_height:
                    self.next_y = self.cur_y
                    self.cur_block_y -= 1
            elif input == HardwareButtonsConstants.KEY_UP:
                self.next_y = self.cur_y - self.qr_blocks_per_zoom * self.pixels_per_block
                self.cur_block_y -= 1
                if self.next_y < 0:
                    self.next_y = self.cur_y
                    self.cur_block_y += 1
            elif input in HardwareButtonsConstants.KEYS__ANYCLICK:
                return

            # Create overlay for block labels (e.g. "D-5")
            block_labels = self.draw_block_labels()

            if self.cur_x != self.next_x or self.cur_y != self.next_y:
                with self.renderer.lock:
                    self.renderer.show_image_pan(
                        self.qr_image,
                        self.cur_x, self.cur_y, self.next_x, self.next_y,
                        rate=self.pixels_per_block,
                        alpha_overlay=Image.alpha_composite(self.block_mask, block_labels)
                    )
                    self.cur_x = self.next_x
                    self.cur_y = self.next_y



@dataclass
class SeedTranscribeSeedQRConfirmQRPromptScreen(ButtonListScreen):
    def __post_init__(self):
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(TextArea(
            text=_("Optionally scan your transcribed SeedQR to confirm that it reads back correctly."),
            screen_y=self.top_nav.height,
            height=self.buttons[0].screen_y - self.top_nav.height,
        ))



@dataclass
class AddressVerificationSigTypeScreen(ButtonListScreen):
    text: str = ""

    def __post_init__(self):
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(TextArea(
            text=self.text,
            screen_y=self.top_nav.height,
        ))



@dataclass
class SeedSelectSeedScreen(ButtonListScreen):
    text: str = ""

    def __post_init__(self):
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(TextArea(
            text=self.text,
            screen_y=self.top_nav.height,
        ))



@dataclass
class SeedAddressVerificationScreen(ButtonListScreen):
    """
        "Skip 10" feature increments the `ThreadsafeCounter` via its `increment(step=10)`
        method. Because it is threadsafe, the next brute force round by the
        `BruteForceAddressVerificationThread` can just check the ThreadsafeCounter's
        value and resume its work from the updated index.
    """
    address: str = None
    derivation_path: str = None
    script_type: str = None
    sig_type: str = None
    network: str = None
    is_mainnet: bool = None
    threadsafe_counter: ThreadsafeCounter = None
    verified_index: ThreadsafeCounter = None


    def __post_init__(self):
        # Customize defaults
        self.title = _("Verify Address")
        self.is_bottom_list = True
        self.show_back_button = False

        super().__post_init__()

        address_display = FormattedAddress(
            address=self.address,
            max_lines=1,
            screen_y=self.top_nav.height
        )
        self.components.append(address_display)

        text = f"{self.sig_type} - {self.script_type}"
        if not self.is_mainnet:
            text += f" ({self.network})"
        self.components.append(TextArea(
            text=text,
            font_size=GUIConstants.LABEL_FONT_SIZE,
            font_color=GUIConstants.LABEL_FONT_COLOR,
            is_text_centered=True,
            screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
        ))

        self.threads.append(SeedAddressVerificationScreen.ProgressThread(
            renderer=self.renderer,
            screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
            threadsafe_counter=self.threadsafe_counter,
            verified_index=self.verified_index,
        ))
    

    def _run_callback(self):
        # Exit the screen on success via a non-None value.
        # see: ButtonListScreen._run()
        if self.verified_index.cur_count is not None:
            # Note that the ProgressThread will have already exited on its own.

            # Return a success value (anything other than None) to end the 
            # ButtonListScreen._run() loop.
            return 1


    class ProgressThread(BaseThread):
        def __init__(self, renderer: Renderer, screen_y: int, threadsafe_counter: ThreadsafeCounter, verified_index: ThreadsafeCounter):
            self.renderer = renderer
            self.screen_y = screen_y
            self.threadsafe_counter = threadsafe_counter
            self.verified_index = verified_index
            super().__init__()
        

        def run(self):
            while self.keep_running:
                if self.verified_index.cur_count is not None:
                    # This thread will detect the success state while its parent Screen
                    # blocks in its `wait_for`. Have to trigger a hw_input override event
                    # to break the Screen._run out of the `wait_for` state. The Screen
                    # will then call its `_run_callback` and detect the success state and
                    # exit.
                    HardwareButtons.get_instance().trigger_override()

                    # Exit the loop and thereby end this thread
                    return

                textarea = TextArea(
                    # TRANSLATOR_NOTE: Inserts the nth address number (e.g. "Checking address 7")
                    text=_("Checking address {}").format(self.threadsafe_counter.cur_count),
                    font_name=GUIConstants.get_body_font_name(),
                    font_size=GUIConstants.get_body_font_size(),
                    screen_y=self.screen_y
                )

                with self.renderer.lock:
                    textarea.render()
                    self.renderer.show_image()

                time.sleep(0.1)



@dataclass
class SeedAddressVerificationSuccessScreen(LargeIconStatusScreen):
    address: str = None
    verified_index: int = None
    verified_index_is_change: bool = None


    def __post_init__(self):
        # Customize defaults
        self.title = _("Success!")
        self.status_headline = _("Address Verified")
        self.button_data = [ButtonOption("OK")]
        self.is_bottom_list = True
        self.show_back_button = False
        super().__post_init__()

        if self.verified_index_is_change:
            # TRANSLATOR_NOTE: Describes the address type (change or receive)
            address_type = _("change address")
        else:
            # TRANSLATOR_NOTE: Describes the address type (change or receive)
            address_type = _("receive address")

        self.components.append(FormattedAddress(
            screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
            address=self.address,
            max_lines=1,  # Use abbreviated format w/ellipsis
        ))

        self.components.append(TextArea(
            text=address_type,
            screen_y=self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING,
        ))

        # TRANSLATOR_NOTE: Describes the address index (e.g. "index 7")
        index_str = _("index {}").format(self.verified_index)
        self.components.append(TextArea(
            text=index_str,
            screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
        ))



@dataclass
class LoadMultisigWalletDescriptorScreen(ButtonListScreen):
    def __post_init__(self):
        self.title = _("Multisig Verification")
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(TextArea(
            text=_("Load your multisig wallet descriptor to verify your receive/self-transfer or change address."),
            screen_y=self.top_nav.height,
            height=self.buttons[0].screen_y - self.top_nav.height,
        ))



@dataclass
class MultisigWalletDescriptorScreen(ButtonListScreen):
    policy: str = None
    fingerprints: List[str] = None

    def __post_init__(self):
        self.title = _("Descriptor Loaded")
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(IconTextLine(
            # TRANSLATOR_NOTE: Label for the multisig wallet's signing policy (e.g. 2-of-3)
            label_text=_("Policy"),
            value_text=self.policy,
            font_size=20,
            screen_y=self.top_nav.height,
            is_text_centered=True,
        ))

        self.components.append(IconTextLine(
            label_text=_("Signing Keys"),
            value_text=" ".join(self.fingerprints),
            font_size=24,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            screen_y=self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING,
            is_text_centered=True,
            auto_line_break=True,
        ))



@dataclass
class SeedSignMessageConfirmMessageScreen(ButtonListScreen):
    page_num: int = None

    def __post_init__(self):
        from seedsigner.controller import Controller
        renderer = Renderer.get_instance()
        start_y = GUIConstants.TOP_NAV_HEIGHT + GUIConstants.COMPONENT_PADDING
        end_y = renderer.canvas_height - GUIConstants.EDGE_PADDING - GUIConstants.BUTTON_HEIGHT - GUIConstants.COMPONENT_PADDING
        message_height = end_y - start_y

        # TODO: Pass the full message in from the View so that this Screen doesn't need to
        # interact with the Controller here.
        self.sign_message_data = Controller.get_instance().sign_message_data
        if "paged_message" not in self.sign_message_data:
            paged = reflow_text_into_pages(
                text=self.sign_message_data["message"],
                width=renderer.canvas_width - 2*GUIConstants.EDGE_PADDING,
                height=message_height,
                allow_text_overflow=True,
            )
            self.sign_message_data["paged_message"] = paged

        if self.page_num >= len(self.sign_message_data["paged_message"]):
            raise Exception("Bug in paged_message calculation")

        if len(self.sign_message_data["paged_message"]) == 1:
            self.title = _("Review Message")
        else:
            self.title = f"""Message (pt {self.page_num + 1}/{len(self.sign_message_data["paged_message"])})"""
        self.is_bottom_list = True
        self.is_button_text_centered = True
        self.button_data = [ButtonOption("Next")]
        super().__post_init__()

        message_display = TextArea(
            text=self.sign_message_data["paged_message"][self.page_num],
            is_text_centered=False,
            allow_text_overflow=True,
            screen_y=start_y,
        )
        self.components.append(message_display)



@dataclass
class SeedSignMessageConfirmAddressScreen(ButtonListScreen):
    derivation_path: str = None
    address: str = None

    def __post_init__(self):
        self.title = _("Confirm Address")
        self.is_bottom_list = True
        self.is_button_text_centered = True
        self.button_data = [ButtonOption("Sign Message")]
        super().__post_init__()

        derivation_path_display = IconTextLine(
            icon_name=SeedSignerIconConstants.DERIVATION,
            icon_color=GUIConstants.INFO_COLOR,
            label_text=_("derivation path"),
            value_text=self.derivation_path,
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        )
        self.components.append(derivation_path_display)

        address_display = FormattedAddress(
            address=self.address,
            max_lines=3,
            screen_y=derivation_path_display.screen_y + derivation_path_display.height + 2*GUIConstants.COMPONENT_PADDING,
        )
        self.components.append(address_display)
