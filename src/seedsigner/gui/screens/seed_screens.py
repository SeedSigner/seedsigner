import math
import time

from dataclasses import dataclass
from typing import List

from PIL import Image, ImageDraw, ImageFilter
from seedsigner.gui.renderer import Renderer
from seedsigner.helpers.qr import QR
from seedsigner.models.qr_type import QRType
from seedsigner.models.threads import BaseThread, ThreadsafeCounter

from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants

from .screen import RET_CODE__BACK_BUTTON, BaseScreen, BaseTopNavScreen, ButtonListScreen, WarningEdgesMixin
from ..components import (FontAwesomeIconConstants, Fonts, FormattedAddress,
    IconTextLine, SeedSignerCustomIconConstants, TextArea, GUIConstants,
    calc_text_centering)

from seedsigner.gui.keyboard import Keyboard, TextEntryDisplay
from seedsigner.hardware.buttons import HardwareButtonsConstants



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

        self.text_entry_display = TextEntryDisplay(
            canvas=self.canvas,
            rect=(
                GUIConstants.EDGE_PADDING,
                text_entry_display_y,
                GUIConstants.EDGE_PADDING + self.keyboard_width,
                text_entry_display_y + text_entry_display_height
            ),
            font=Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 24),
            is_centered=False,
            cur_text="".join(self.initial_letters)
        )

        self.arrow_up_is_active = False
        self.arrow_down_is_active = False

        # TODO: support other BIP39 languages/charsets
        self.keyboard = Keyboard(
            draw=self.image_draw,
            charset=self.possible_alphabet,
            font=Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 24),
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
        # Clear the right panel
        self.renderer.draw.rectangle(
            (
                GUIConstants.EDGE_PADDING + self.keyboard_width,
                self.top_nav.height,
                self.canvas_width,
                self.canvas_height
            ),
            fill=GUIConstants.BACKGROUND_COLOR
        )

        if not self.possible_words:
            return

        # word_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE+2)
        word_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE+4)

        row_height = 28
        word_indent = 4
        x = GUIConstants.EDGE_PADDING + self.keyboard_width + 4
        y = self.top_nav.height - int(row_height / 2)

        highlighted_row = 3
        num_possible_rows = 11

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
                    break

                self.renderer.draw.text(
                    (x + word_indent, y + row * row_height),
                    self.possible_words[i],
                    fill="#ddd",
                    font=word_font
                )

        # Render the SELECT outline
        fill_color = GUIConstants.ACCENT_COLOR
        font_color = GUIConstants.BUTTON_SELECTED_FONT_COLOR
        radius = 5
        self.renderer.draw.rounded_rectangle(
            (
                x,
                y + (3 * row_height),
                self.canvas_width + 2*radius,  # render off the right edge so the rounding is clipped
                y + (4 * row_height)
            ),
            outline=GUIConstants.ACCENT_COLOR,
            fill=fill_color,
            radius=5,
        )

        if self.possible_words:
            word_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE+6)
            self.renderer.draw.text(
                (x + word_indent, y + 3 * row_height),
                self.possible_words[self.selected_possible_words_index],
                fill=font_color,
                font=word_font
            )

        self.render_possible_matches_arrows()


    def render_possible_matches_arrows(self):
        # Render the up/down arrow buttons for KEY1 and KEY3
        row_height = 26
        arrow_button_width = 25
        arrow_padding = 5
        key_x = self.canvas_width - arrow_button_width
        key_y = self.top_nav.height - int(row_height / 2) + int(0.75 * row_height)
        background_color = "#111"
        arrow_color = GUIConstants.ACCENT_COLOR
        if self.arrow_up_is_active:
            background_color = GUIConstants.ACCENT_COLOR
            arrow_color = "#111"
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=GUIConstants.ACCENT_COLOR, fill=background_color, radius=5, width=1)
        self.renderer.draw.polygon(
            [(key_x + int(arrow_button_width)/2 + 1, key_y + arrow_padding),  # centered top point
            (self.canvas_width - arrow_padding + 1, key_y + row_height - arrow_padding),  # bottom right point
            (key_x + arrow_padding + 1, key_y + row_height - arrow_padding)],  # bottom left point
            fill=arrow_color
        )

        background_color = "#111"
        arrow_color = GUIConstants.ACCENT_COLOR
        if self.arrow_down_is_active:
            background_color = GUIConstants.ACCENT_COLOR
            arrow_color = "#111"
        key_y = self.top_nav.height - int(row_height / 2) + int(5.25 * row_height)
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=GUIConstants.ACCENT_COLOR, fill=background_color, radius=5, width=1)
        self.renderer.draw.polygon(
            [(key_x + int(arrow_button_width)/2 + 1, key_y + row_height - arrow_padding),  # bottom centered point
            (self.canvas_width - arrow_padding + 1, key_y + arrow_padding),  # right top point
            (key_x + arrow_padding + 1, key_y + arrow_padding)], # left top point
            fill=arrow_color
        )


    def _render(self):
        super()._render()
        self.keyboard.render_keys()
        self.text_entry_display.render()
        self.render_possible_matches()

        self.renderer.show_image()


    def _run(self):
        while True:
            input = self.hw_inputs.wait_for(
                HardwareButtonsConstants.ALL_KEYS,
                check_release=True,
                release_keys=[HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY2]
            )

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
                    self.render_possible_matches_arrows()

                # Update the right-hand possible matches area
                self.render_possible_matches()

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
                    self.render_possible_matches_arrows()

                # Update the right-hand possible matches area
                self.render_possible_matches()

            if input is not HardwareButtonsConstants.KEY1 and self.arrow_up_is_active:
                # Deactivate the arrow and redraw
                self.arrow_up_is_active = False
                self.render_possible_matches_arrows()

            if input is not HardwareButtonsConstants.KEY3 and self.arrow_down_is_active:
                # Deactivate the arrow and redraw
                self.arrow_down_is_active = False
                self.render_possible_matches_arrows()

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
                    
                # Update the right-hand possible matches area
                self.render_possible_matches()

                if len(self.possible_alphabet) == 1:
                    # If there's only one possible letter left, select it
                    self.keyboard.set_selected_key(self.possible_alphabet[0])

                self.keyboard.render_keys()

            elif input in HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN:
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

                    # Update the right-hand possible matches area
                    self.render_possible_matches()
                
                else:
                    # We've navigated to a deactivated letter
                    pass

            # Render the text entry display and cursor block
            self.text_entry_display.cur_text = ''.join(self.letters)
            self.text_entry_display.render()

            # Now issue one call to send the pixels to the screen
            self.renderer.show_image()



@dataclass
class SeedFinalizeScreen(ButtonListScreen):
    fingerprint: str = None
    title: str = "Finalize Seed"
    is_bottom_list: bool = True
    button_data: list = None

    def __post_init__(self):
        self.show_back_button = False

        super().__post_init__()

        self.fingerprint_icontl = IconTextLine(
            icon_name=SeedSignerCustomIconConstants.FINGERPRINT,
            icon_color="blue",
            icon_size=GUIConstants.ICON_FONT_SIZE + 12,
            label_text="fingerprint",
            value_text=self.fingerprint,
            font_size=GUIConstants.BODY_FONT_SIZE + 2,
            is_text_centered=True,
            screen_y=self.top_nav.height + int((self.buttons[0].screen_y - self.top_nav.height) / 2) - 30
        )
        self.components.append(self.fingerprint_icontl)



@dataclass
class SeedOptionsScreen(ButtonListScreen):
    # Customize defaults
    is_bottom_list: bool = True
    fingerprint: str = None
    has_passphrase: bool = False

    def __post_init__(self):
        self.top_nav_icon_name = SeedSignerCustomIconConstants.FINGERPRINT
        self.top_nav_icon_color = "blue"
        self.title = self.fingerprint
        self.is_button_text_centered = False
        super().__post_init__()



@dataclass
class SeedWordsScreen(WarningEdgesMixin, ButtonListScreen):
    seed: Seed = None
    page_index: int = 0
    num_pages: int = 3
    is_bottom_list: bool = True
    status_color: str = GUIConstants.DIRE_WARNING_COLOR


    def __post_init__(self):
        self.title = f"Seed Words: {self.page_index+1}/{self.num_pages}"
        super().__post_init__()

        # Can only render 4 words per screen
        words_per_page = 4
        mnemonic = self.seed.mnemonic_display_list

        # Slice the mnemonic to our current 4-word section
        self.mnemonic = mnemonic[self.page_index*words_per_page:(self.page_index + 1)*words_per_page]

        self.body_x = 0
        self.body_y = self.top_nav.height - int(GUIConstants.COMPONENT_PADDING / 2)
        self.body_height = self.buttons[0].screen_y - self.body_y

        # Have to supersample the whole body since it's all at the small font size
        supersampling_factor = 1
        font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, (GUIConstants.TOP_NAV_TITLE_FONT_SIZE + 2) * supersampling_factor)

        # Calc horizontal center based on longest word
        max_word_width = 0
        for word in self.mnemonic:
            (left, top, right, bottom) = font.getbbox(word, anchor="ls")
            if right > max_word_width:
                max_word_width = right

        # Measure the max digit height for the numbering boxes, from baseline
        number_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE * supersampling_factor)
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

        for index, word in enumerate(self.mnemonic):
            draw.rounded_rectangle(
                (number_box_x, number_box_y, number_box_x + number_box_width, number_box_y + number_box_height),
                fill="#202020",
                radius=5 * supersampling_factor
            )
            baseline_y = number_box_y + number_box_height - int((number_box_height - number_height)/2)
            draw.text(
                (number_box_x + int(number_box_width/2), baseline_y),
                font=number_font,
                text=str(self.page_index * words_per_page + index + 1),
                fill="#0084ff",
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
        self.body_img = self.body_img.resize((self.canvas_width, self.body_height), Image.LANCZOS)
        self.body_img = self.body_img.filter(ImageFilter.SHARPEN)
        self.paste_images.append((self.body_img, (self.body_x, self.body_y)))



@dataclass
class SeedExportXpubCustomDerivationScreen(BaseTopNavScreen):
    title: str = "Derivation Path"
    derivation_path: str = "m/"

    def __post_init__(self):
        super().__post_init__()

        # Set up the keyboard params
        right_panel_buttons_width = 60
        
        # Set up the live text entry display
        font = Fonts.get_font("RobotoCondensed-Regular", 28)
        tw, th = font.getsize("m/1234567890")  # All possible chars for max range
        text_entry_side_padding = 0
        text_entry_top_padding = 1
        text_entry_bottom_padding = 10
        text_entry_top_y = self.top_nav.height + text_entry_top_padding
        text_entry_bottom_y = text_entry_top_y + 3 + th + 3
        self.text_entry_display = TextEntryDisplay(
            canvas=self.renderer.canvas,
            rect=(text_entry_side_padding,text_entry_top_y, self.renderer.canvas_width - right_panel_buttons_width - GUIConstants.COMPONENT_PADDING, text_entry_bottom_y),
            font=font,
            font_color=GUIConstants.ACCENT_COLOR,
            cursor_mode=TextEntryDisplay.CURSOR_MODE__BAR,
            is_centered=False,
            has_outline=True,
            cur_text=''.join(self.derivation_path)
        )

        keyboard_start_y = text_entry_bottom_y + text_entry_bottom_padding
        self.keyboard_digits = Keyboard(
            draw=self.renderer.draw,
            charset="/'0123456789",
            rows=3,
            cols=6,
            rect=(0, keyboard_start_y, self.renderer.canvas_width - right_panel_buttons_width - GUIConstants.COMPONENT_PADDING, self.renderer.canvas_height),
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )
        self.keyboard_digits.set_selected_key(selected_letter="/")


    def _render(self):
        super()._render()

        self.keyboard_digits.render_keys()

        # Render the right button panel (only has a Key3 "Save" button)
        row_height = 28
        right_button_left_margin = 10
        right_button_width = 60
        font_padding_right = 2
        font_padding_top = 1
        key_x = self.renderer.canvas_width - right_button_width
        key_y = int(self.renderer.canvas_height - row_height) / 2 - 1 - 60
        font = Fonts.get_font("RobotoCondensed-Regular", 24)
        background_color = "#111"
        font_color = GUIConstants.ACCENT_COLOR
        button3_text = "Save"
        tw, th = font.getsize(button3_text)
        key_y = int(self.renderer.canvas_height - row_height) / 2 - 1 + 60
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=GUIConstants.ACCENT_COLOR, fill=background_color, radius=5, width=1)
        self.renderer.draw.text((self.renderer.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button3_text, fill=font_color)

        self.text_entry_display.render(self.derivation_path)
        self.renderer.show_image()
    

    def _run(self):
        cursor_position = len(self.derivation_path)

        # Start the interactive update loop
        while True:
            input = self.hw_inputs.wait_for(
                HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN + [HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY3],
                check_release=True,
                release_keys=[HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY3]
            )
    
            # Check our two possible exit conditions
            if input == HardwareButtonsConstants.KEY3:
                # Save!
                if len(self.derivation_path) > 0:
                    return self.derivation_path.strip()
    
            elif self.top_nav.is_selected and input == HardwareButtonsConstants.KEY_PRESS:
                # Prev button clicked; return empty string to signal cancel.
                return self.top_nav.selected_button
    
            # Process normal input
            if input in [HardwareButtonsConstants.KEY_UP, HardwareButtonsConstants.KEY_DOWN] and self.top_nav.is_selected:
                # We're navigating off the previous button
                self.top_nav.is_selected = False
                self.top_nav.render()
    
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
                self.top_nav.render()
    
            elif ret_val in Keyboard.ADDITIONAL_KEYS and input == HardwareButtonsConstants.KEY_PRESS:
                if ret_val == Keyboard.KEY_BACKSPACE["code"]:
                    if len(self.derivation_path) <= 2:
                        pass
                    elif cursor_position == len(self.derivation_path):
                        self.derivation_path = self.derivation_path[:-1]
                        cursor_position -= 1
                    else:
                        self.derivation_path = self.derivation_path[:cursor_position - 1] + self.derivation_path[cursor_position:]
                        cursor_position -= 1
    
            elif input == HardwareButtonsConstants.KEY_PRESS and ret_val not in Keyboard.ADDITIONAL_KEYS:
                # User has locked in the current letter
                if cursor_position == len(self.derivation_path):
                    self.derivation_path += ret_val
                else:
                    self.derivation_path = self.derivation_path[:cursor_position] + ret_val + self.derivation_path[cursor_position:]
                cursor_position += 1
    
            elif input in HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN:
                # Live joystick movement; haven't locked this new letter in yet.
                # Leave current spot blank for now. Only update the active keyboard keys
                # when a selection has been locked in (KEY_PRESS) or removed ("del").
                pass
    
            # Render the text entry display and cursor block
            self.text_entry_display.render(self.derivation_path)
    
            self.renderer.show_image()



@dataclass
class SeedExportXpubDetailsScreen(WarningEdgesMixin, ButtonListScreen):
    # Customize defaults
    title: str = "Xpub Details"
    is_bottom_list: bool = True
    fingerprint: str = None
    has_passphrase: bool = False
    derivation_path: str = "m/84'/0'/0'"
    xpub: str = "zpub6r..."
    button_data=["Export Xpub"]

    def __post_init__(self):
        # Programmatically set up other args
        self.button_data = ["Export Xpub"]

        # Initialize the base class
        super().__post_init__()

        # Set up the fingerprint and passphrase displays
        self.fingerprint_line = IconTextLine(
            icon_name=SeedSignerCustomIconConstants.FINGERPRINT,
            icon_color="blue",
            label_text="Fingerprint",
            value_text=self.fingerprint,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        )
        self.components.append(self.fingerprint_line)

        self.derivation_line = IconTextLine(
            icon_name=SeedSignerCustomIconConstants.PATH,
            label_text="Derivation",
            value_text=self.derivation_path,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=self.components[-1].screen_y + self.components[-1].height + int(1.5*GUIConstants.COMPONENT_PADDING),
        )
        self.components.append(self.derivation_line)

        self.xpub_line = IconTextLine(
            icon_name=FontAwesomeIconConstants.X,
            label_text="Xpub",
            value_text=f"{self.xpub[:18]}...",
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_size=GUIConstants.BODY_FONT_SIZE + 2,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=self.components[-1].screen_y + self.components[-1].height + int(1.5*GUIConstants.COMPONENT_PADDING),
        )
        self.components.append(self.xpub_line)



@dataclass
class SeedAddPassphraseScreen(BaseTopNavScreen):
    title: str = "Add Passphrase"
    passphrase: str = ""

    def __post_init__(self):
        super().__post_init__()

        keys_lower = "abcdefghijklmnopqrstuvwxyz"
        keys_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        keys_number = "0123456789"
        keys_symbol = "!\"#$%&'()*+,=./;:<>?@[]|-_`~"

        # Set up the keyboard params
        self.right_panel_buttons_width = 60

        font = Fonts.get_font("RobotoCondensed-Regular", 28)
        tw, th = font.getsize(keys_lower + keys_upper + keys_number + keys_symbol)      # All possible chars for max size measurements
        text_entry_side_padding = 0
        text_entry_top_padding = 1
        text_entry_bottom_padding = 10
        text_entry_top_y = self.top_nav.height + text_entry_top_padding
        text_entry_bottom_y = text_entry_top_y + 3 + th + 3
        self.text_entry_display = TextEntryDisplay(
            canvas=self.renderer.canvas,
            rect=(text_entry_side_padding,text_entry_top_y, self.canvas_width - self.right_panel_buttons_width - 1, text_entry_bottom_y),
            font=font,
            font_color=GUIConstants.ACCENT_COLOR,
            cursor_mode=TextEntryDisplay.CURSOR_MODE__BAR,
            is_centered=False,
            cur_text=''.join(self.passphrase)
        )

        keyboard_start_y = text_entry_bottom_y + text_entry_bottom_padding
        self.keyboard_abc = Keyboard(
            draw=self.renderer.draw,
            charset=keys_lower,
            rows=4,
            cols=9,
            rect=(0, keyboard_start_y, self.canvas_width - self.right_panel_buttons_width, self.canvas_height),
            additional_keys=[Keyboard.KEY_SPACE_5, Keyboard.KEY_CURSOR_LEFT, Keyboard.KEY_CURSOR_RIGHT, Keyboard.KEY_BACKSPACE],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT]
        )

        self.keyboard_ABC = Keyboard(
            draw=self.renderer.draw,
            charset=keys_upper,
            rows=4,
            cols=9,
            rect=(0, keyboard_start_y, self.canvas_width - self.right_panel_buttons_width, self.canvas_height),
            additional_keys=[Keyboard.KEY_SPACE_5, Keyboard.KEY_CURSOR_LEFT, Keyboard.KEY_CURSOR_RIGHT, Keyboard.KEY_BACKSPACE],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        self.keyboard_digits = Keyboard(
            draw=self.renderer.draw,
            charset=keys_number,
            rows=3,
            cols=5,
            rect=(0, keyboard_start_y, self.canvas_width - self.right_panel_buttons_width, self.canvas_height),
            additional_keys=[Keyboard.KEY_CURSOR_LEFT, Keyboard.KEY_CURSOR_RIGHT, Keyboard.KEY_BACKSPACE],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        self.keyboard_symbols = Keyboard(
            draw=self.renderer.draw,
            charset=keys_symbol,
            rows=4,
            cols=10,
            rect=(0, keyboard_start_y, self.canvas_width - self.right_panel_buttons_width, self.canvas_height),
            additional_keys=[Keyboard.KEY_SPACE_4, Keyboard.KEY_CURSOR_LEFT, Keyboard.KEY_CURSOR_RIGHT, Keyboard.KEY_BACKSPACE],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        self.button1_is_active = False
        self.button2_is_active = False
        self.button3_is_active = False



    def render_right_panel(self, button1_text="ABC", button2_text="123"):
        # Render the up/down arrow buttons for KEY1 and KEY3
        row_height = 28
        right_button_left_margin = 10
        right_button_width = self.right_panel_buttons_width - right_button_left_margin
        font_padding_right = 2
        font_padding_top = 1
        key_x = self.canvas_width - right_button_width
        key_y = int(self.canvas_height - row_height) / 2 - 1 - 60

        background_color = "#111"
        font_color = GUIConstants.ACCENT_COLOR
        font = Fonts.get_font("RobotoCondensed-Regular", 24)
        tw, th = font.getsize(button1_text)
        if self.button1_is_active:
            background_color = GUIConstants.ACCENT_COLOR
            font_color = "#111"
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=GUIConstants.ACCENT_COLOR, fill=background_color, radius=5, width=1)
        self.renderer.draw.text((self.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button1_text, fill=font_color)

        background_color = "#111"
        font_color = GUIConstants.ACCENT_COLOR
        tw, th = font.getsize(button2_text)
        if self.button2_is_active:
            background_color = GUIConstants.ACCENT_COLOR
            font_color = "#111"
        key_y = int(self.canvas_height - row_height) / 2 - 1
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=GUIConstants.ACCENT_COLOR, fill=background_color, radius=5, width=1)
        self.renderer.draw.text((self.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button2_text, fill=font_color)

        background_color = "#111"
        font_color = GUIConstants.ACCENT_COLOR
        button3_text = "Save"
        tw, th = font.getsize(button3_text)
        if self.button3_is_active:
            background_color = GUIConstants.ACCENT_COLOR
            font_color = "#111"
        key_y = int(self.canvas_height - row_height) / 2 - 1 + 60
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=GUIConstants.ACCENT_COLOR, fill=background_color, radius=5, width=1)
        self.renderer.draw.text((self.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button3_text, fill=font_color)


    def _render(self):
        super()._render()

        self.text_entry_display.render()
        self.render_right_panel()
        self.keyboard_abc.render_keys()

        self.renderer.show_image()


    def _run(self):
        cursor_position = len(self.passphrase)

        KEYBOARD__LOWERCASE_BUTTON_TEXT = "abc"
        KEYBOARD__UPPERCASE_BUTTON_TEXT = "ABC"
        KEYBOARD__DIGITS_BUTTON_TEXT = "123"
        KEYBOARD__SYMBOLS_BUTTON_TEXT = "!@#"
        cur_keyboard = self.keyboard_abc
        cur_button1_text = KEYBOARD__UPPERCASE_BUTTON_TEXT
        cur_button2_text = KEYBOARD__DIGITS_BUTTON_TEXT

        # Start the interactive update loop
        while True:
            input = self.hw_inputs.wait_for(
                HardwareButtonsConstants.ALL_KEYS,
                check_release=True,
                release_keys=[HardwareButtonsConstants.KEY_PRESS, HardwareButtonsConstants.KEY1, HardwareButtonsConstants.KEY2, HardwareButtonsConstants.KEY3]
            )

            keyboard_swap = False

            # Check our two possible exit conditions
            if input == HardwareButtonsConstants.KEY3:
                # Save!
                if len(self.passphrase) > 0:
                    return self.passphrase.strip()

            elif input == HardwareButtonsConstants.KEY_PRESS and self.top_nav.is_selected:
                # Back button clicked
                return self.top_nav.selected_button

            # Check for keyboard swaps
            if input == HardwareButtonsConstants.KEY1:
                # Return to the same button2 keyboard, if applicable
                if cur_keyboard == self.keyboard_digits:
                    cur_button2_text = KEYBOARD__DIGITS_BUTTON_TEXT
                elif cur_keyboard == self.keyboard_symbols:
                    cur_button2_text = KEYBOARD__SYMBOLS_BUTTON_TEXT

                if cur_button1_text == KEYBOARD__LOWERCASE_BUTTON_TEXT:
                    self.keyboard_abc.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                    cur_keyboard = self.keyboard_abc
                    cur_button1_text = KEYBOARD__UPPERCASE_BUTTON_TEXT
                    self.render_right_panel(button1_text=cur_button1_text, button2_text=cur_button2_text)
                else:
                    self.keyboard_ABC.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                    cur_keyboard = self.keyboard_ABC
                    cur_button1_text = KEYBOARD__LOWERCASE_BUTTON_TEXT
                    self.render_right_panel(button1_text=cur_button1_text, button2_text=cur_button2_text)
                cur_keyboard.render_keys()
                keyboard_swap = True
                ret_val = None

            elif input == HardwareButtonsConstants.KEY2:
                # Return to the same button1 keyboard, if applicable
                if cur_keyboard == self.keyboard_abc:
                    cur_button1_text = KEYBOARD__LOWERCASE_BUTTON_TEXT
                elif cur_keyboard == self.keyboard_ABC:
                    cur_button1_text = KEYBOARD__UPPERCASE_BUTTON_TEXT

                if cur_button2_text == KEYBOARD__DIGITS_BUTTON_TEXT:
                    self.keyboard_digits.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                    cur_keyboard = self.keyboard_digits
                    cur_keyboard.render_keys()
                    cur_button2_text = KEYBOARD__SYMBOLS_BUTTON_TEXT
                    self.render_right_panel(button1_text=cur_button1_text, button2_text=cur_button2_text)
                else:
                    self.keyboard_symbols.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                    cur_keyboard = self.keyboard_symbols
                    cur_keyboard.render_keys()
                    cur_button2_text = KEYBOARD__DIGITS_BUTTON_TEXT
                    self.render_right_panel(button1_text=cur_button1_text, button2_text=cur_button2_text)
                cur_keyboard.render_keys()
                keyboard_swap = True
                ret_val = None

            else:
                # Process normal input
                if input in [HardwareButtonsConstants.KEY_UP, HardwareButtonsConstants.KEY_DOWN] and self.top_nav.is_selected:
                    # We're navigating off the previous button
                    self.top_nav.is_selected = False
                    self.top_nav.render()

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
                self.top_nav.render()

            elif ret_val in Keyboard.ADDITIONAL_KEYS and input == HardwareButtonsConstants.KEY_PRESS:
                if ret_val == Keyboard.KEY_BACKSPACE["code"]:
                    if cursor_position == 0:
                        pass
                    elif cursor_position == len(self.passphrase):
                        self.passphrase = self.passphrase[:-1]
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

            self.renderer.show_image()



@dataclass
class SeedReviewPassphraseScreen(ButtonListScreen):
    fingerprint_without: str = None
    fingerprint_with: str = None
    passphrase: str = None

    def __post_init__(self):
        # Customize defaults
        self.title = "Verify Passphrase"
        self.is_bottom_list = True

        super().__post_init__()

        self.components.append(IconTextLine(
            icon_name=SeedSignerCustomIconConstants.FINGERPRINT,
            icon_color="blue",
            label_text="changes fingerprint",
            value_text=f"{self.fingerprint_without} >> {self.fingerprint_with}",
            is_text_centered=True,
            screen_y = self.buttons[0].screen_y - GUIConstants.COMPONENT_PADDING - int(GUIConstants.BODY_FONT_SIZE*2.5)
        ))

        available_height = self.components[-1].screen_y - self.top_nav.height + GUIConstants.COMPONENT_PADDING
        max_font_size = GUIConstants.TOP_NAV_TITLE_FONT_SIZE + 8
        min_font_size = GUIConstants.TOP_NAV_TITLE_FONT_SIZE - 4
        font_size = max_font_size
        max_lines = 3
        passphrase = [self.passphrase]
        found_solution = False
        for font_size in range(max_font_size, min_font_size, -2):
            if found_solution:
                break
            font = Fonts.get_font(font_name=GUIConstants.FIXED_WIDTH_FONT_NAME, size=font_size)
            char_width, char_height = font.getsize("X")
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
                is_text_centered=True,
                screen_y=screen_y,
            ))
            screen_y += char_height + 2



@dataclass
class SeedTranscribeSeedQRFormatScreen(ButtonListScreen):
    def __post_init__(self):
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(IconTextLine(
            label_text="Standard",
            value_text="BIP-39 wordlist indices",
            is_text_centered=False,
            auto_line_break=True,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        ))
        self.components.append(IconTextLine(
            label_text="Compact",
            value_text="Raw entropy bits",
            is_text_centered=False,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING,
        ))

        # self.components.append(TextArea(
        #     text="Learn more about the SeedQR formats at:",
        #     is_text_centered=True,
        #     screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        # ))
        # self.components.append(TextArea(
        #     text="seedsigner.com",
        #     is_text_centered=True,
        #     screen_y=self.components[-1].screen_y + self.components[-1].height,
        #     height=self.buttons[0].screen_y - (self.components[-1].screen_y + self.components[-1].height),
        # ))


@dataclass
class SeedTranscribeSeedQRWholeQRScreen(WarningEdgesMixin, ButtonListScreen):
    qr_data: str = None
    num_modules: int = None

    def __post_init__(self):
        self.title = "Transcribe SeedQR"
        self.button_data = [f"Begin {self.num_modules}x{self.num_modules}"]
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

        # self.instructions = TextArea(
        #     text="< back  |  click to begin",
        #     background_color=GUIConstants.BACKGROUND_COLOR,
        #     is_text_centered=False,
        #     screen_y=self.canvas_height - GUIConstants.BODY_FONT_SIZE - 2*GUIConstants.COMPONENT_PADDING,
        #     height=GUIConstants.BODY_FONT_SIZE + 2*GUIConstants.COMPONENT_PADDING,
        # )



@dataclass
class SeedTranscribeSeedQRZoomedInScreen(BaseScreen):
    qr_data: str = None
    num_modules: int = None

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

        msg = "click to exit"
        font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BODY_FONT_SIZE)
        (left, top, right, bottom) = font.getbbox(msg, anchor="ls")
        msg_height = -1 * top
        msg_width = right
        # draw.rectangle(
        #     (
        #         int((self.canvas_width - msg_width)/2 - GUIConstants.COMPONENT_PADDING),
        #         self.canvas_height - msg_height - GUIConstants.COMPONENT_PADDING,
        #         int((self.canvas_width + msg_width)/2 + GUIConstants.COMPONENT_PADDING),
        #         self.canvas_height
        #     ),
        #     fill=GUIConstants.BACKGROUND_COLOR,
        # )
        # draw.text(
        #     (int(self.canvas_width/2), self.canvas_height - int(GUIConstants.COMPONENT_PADDING/2)),
        #     msg,
        #     fill=GUIConstants.BODY_FONT_COLOR,
        #     font=font,
        #     anchor="ms"  # Middle, baSeline
        # )
        TextArea(
            canvas=self.block_mask,
            image_draw=draw,
            text=msg,
            background_color=GUIConstants.BACKGROUND_COLOR,
            is_text_centered=True,
            screen_y=self.canvas_height - GUIConstants.BODY_FONT_SIZE - GUIConstants.COMPONENT_PADDING,
            height=GUIConstants.BODY_FONT_SIZE + GUIConstants.COMPONENT_PADDING,
        ).render()


    def draw_block_labels(self, cur_block_x, cur_block_y):
        # Create overlay for block labels (e.g. "D-5")
        block_labels_x = ["1", "2", "3", "4", "5", "6"]
        block_labels_y = ["A", "B", "C", "D", "E", "F"]

        block_labels = Image.new("RGBA", (self.canvas_width, self.canvas_height), (255,255,255,0))
        draw = ImageDraw.Draw(block_labels)
        draw.rectangle((self.mask_width, 0, self.canvas_width - self.mask_width, self.pixels_per_block), fill=GUIConstants.ACCENT_COLOR)
        draw.rectangle((0, self.mask_height, self.pixels_per_block, self.canvas_height - self.mask_height), fill=GUIConstants.ACCENT_COLOR)

        label_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, GUIConstants.TOP_NAV_TITLE_FONT_SIZE + 8)
        x_label = block_labels_x[cur_block_x]
        (left, top, right, bottom) = label_font.getbbox(x_label, anchor="ls")
        x_label_height = -1 * top

        draw.text(
            (int(self.canvas_width/2), self.pixels_per_block - int((self.pixels_per_block - x_label_height)/2)),
            text=x_label,
            fill=GUIConstants.BUTTON_SELECTED_FONT_COLOR,
            font=label_font,
            anchor="ms",  # Middle, baSeline
        )

        y_label = block_labels_y[cur_block_y]
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


    def _run(self):
        # Track our current coordinates for the upper left corner of our view
        cur_block_x = 0
        cur_block_y = 0
        cur_x = self.qr_border * self.pixels_per_block - self.mask_width
        cur_y = self.qr_border * self.pixels_per_block - self.mask_height
        next_x = cur_x
        next_y = cur_y

        block_labels = self.draw_block_labels(0, 0)

        self.renderer.show_image(
            self.qr_image.crop((cur_x, cur_y, cur_x + self.canvas_width, cur_y + self.canvas_height)),
            alpha_overlay=Image.alpha_composite(self.block_mask, block_labels)
        )

        while True:
            input = self.hw_inputs.wait_for(HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN + [HardwareButtonsConstants.KEY_PRESS])
            if input == HardwareButtonsConstants.KEY_RIGHT:
                next_x = cur_x + self.qr_blocks_per_zoom * self.pixels_per_block
                cur_block_x += 1
                if next_x > self.qr_width - self.canvas_width:
                    next_x = cur_x
                    cur_block_x -= 1
            elif input == HardwareButtonsConstants.KEY_LEFT:
                next_x = cur_x - self.qr_blocks_per_zoom * self.pixels_per_block
                cur_block_x -= 1
                if next_x < 0:
                    next_x = cur_x
                    cur_block_x += 1
            elif input == HardwareButtonsConstants.KEY_DOWN:
                next_y = cur_y + self.qr_blocks_per_zoom * self.pixels_per_block
                cur_block_y += 1
                if next_y > self.height - self.canvas_height:
                    next_y = cur_y
                    cur_block_y -= 1
            elif input == HardwareButtonsConstants.KEY_UP:
                next_y = cur_y - self.qr_blocks_per_zoom * self.pixels_per_block
                cur_block_y -= 1
                if next_y < 0:
                    next_y = cur_y
                    cur_block_y += 1
            elif input == HardwareButtonsConstants.KEY_PRESS:
                return

            # Create overlay for block labels (e.g. "D-5")
            block_labels = self.draw_block_labels(cur_block_x, cur_block_y)

            if cur_x != next_x or cur_y != next_y:
                self.renderer.show_image_pan(
                    self.qr_image,
                    cur_x, cur_y, next_x, next_y,
                    rate=self.pixels_per_block,
                    alpha_overlay=Image.alpha_composite(self.block_mask, block_labels)
                )
                cur_x = next_x
                cur_y = next_y



@dataclass
class SeedTranscribeSeedQRConfirmQRPromptScreen(ButtonListScreen):
    def __post_init__(self):
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(TextArea(
            text="Optionally scan your transcribed SeedQR to confirm that it reads back correctly.",
            screen_y=self.top_nav.height,
            height=self.buttons[0].screen_y - self.top_nav.height,
        ))



@dataclass
class SingleSigAddressVerificationScreen(ButtonListScreen):
    """
        TODO: Reserved for Nick
        
        Not yet exposed in the UI. This was moved from the PSBT Verification flow since
        we don't need to brute force iterate the change addrs there. But this can still
        be useful for a generalized address verification process. Probably makes sense to
        have a screen before this that prompts for the index num but also give the user
        the choice to just start the brute force search.

        "Skip 10" feature not yet implemented. To do this you would simply increment the
        `ThreadsafeCounter` via its `increment(step=10)` method. Because it is
        threadsafe, the next brute force round by the
        `SingleSigAddressVerificationThread` can just check its value and resume its work
        from the updated index.
    """
    address: str = None
    threadsafe_counter: ThreadsafeCounter = None

    def __post_init__(self):
        # Customize defaults
        self.title = "Verify Change"
        self.is_bottom_list = True
        self.button_data = ["Skip 10", "Cancel"]

        super().__post_init__()

        label = TextArea(
            text="Address",
            font_size=GUIConstants.LABEL_FONT_SIZE,
            font_color=GUIConstants.LABEL_FONT_COLOR,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        self.components.append(label)

        address_display = FormattedAddress(
            address=self.address,
            max_lines=1,
            screen_y=label.screen_y + label.height
        )
        self.components.append(address_display)

        self.threads.append(SingleSigAddressVerificationScreen.ProgressThread(
            renderer=self.renderer,
            screen_y=address_display.screen_y + address_display.height + GUIConstants.COMPONENT_PADDING,
            threadsafe_counter=self.threadsafe_counter,
        ))


    class ProgressThread(BaseThread):
        def __init__(self, renderer: Renderer, screen_y: int, threadsafe_counter: ThreadsafeCounter):
            self.renderer = renderer
            self.screen_y = screen_y
            self.threadsafe_counter = threadsafe_counter
            super().__init__()
        
        def run(self):
            font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BODY_FONT_SIZE)
            tw, th = font.getsize("Checking address 001")
            while self.keep_running:
                with self.renderer.lock:
                    # Need to clear the pixels
                    # self.renderer.draw.rectangle((0, self.screen_y, self.renderer.canvas_width, self.screen_y + th), fill=GUIConstants.BACKGROUND_COLOR)

                    textarea = TextArea(
                        text=f"Checking address {self.threadsafe_counter.cur_count}",
                        font_name=GUIConstants.BODY_FONT_NAME,
                        font_size=GUIConstants.BODY_FONT_SIZE,
                        screen_y=self.screen_y
                    )
                    textarea.render()
                    # self.renderer.draw.text((int((self.renderer.canvas_width - tw)/2), self.screen_y), text=f"Checking address {self.threadsafe_counter.cur_count}", font=font, fill=GUIConstants.BODY_FONT_COLOR)
                    self.renderer.show_image()
                time.sleep(0.1)
