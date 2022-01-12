import time

from dataclasses import dataclass

from seedsigner.models.seed import Seed
from seedsigner.views.menu_view import MenuView

from .screen import BaseScreen, BaseTopNavScreen, ButtonListScreen, WarningScreenMixin
from ..components import Fonts, TextArea, GUIConstants, IconTextLine, calc_text_centering

from seedsigner.gui.keyboard import Keyboard, TextEntryDisplay
from seedsigner.helpers import B
from seedsigner.models.encode_qr import EncodeQR



@dataclass
class SeedValidScreen(ButtonListScreen):
    fingerprint: str = None
    title: str = "Seed Valid"
    is_bottom_list: bool = True
    button_data: list = None

    def __post_init__(self):
        super().__post_init__()

        self.title_textarea = TextArea(
            text="Fingerprint:",
            is_text_centered=True,
            auto_line_break=False,
            screen_y=self.top_nav.height + int((self.buttons[0].screen_y - self.top_nav.height) / 2) - 30
        )

        self.fingerprint_icontl = IconTextLine(
            icon_name="fingerprint",
            value_text=self.fingerprint,
            font_size=GUIConstants.BODY_FONT_SIZE + 2,
            is_text_centered=True,
            screen_x = -4,
            screen_y=self.title_textarea.screen_y + self.title_textarea.height
        )

    def _render(self):
        super()._render()

        self.title_textarea.render()
        self.fingerprint_icontl.render()

        # Write the screen updates
        self.renderer.show_image()



@dataclass
class SeedOptionsScreen(ButtonListScreen):
    # Customize defaults
    title: str = "Seed Options"
    is_bottom_list: bool = True
    fingerprint: str = None
    has_passphrase: bool = False

    def __post_init__(self):
        super().__post_init__()

        self.fingerprint_icontextline = IconTextLine(
            icon_name="fingerprint",
            value_text=self.fingerprint,
            is_text_centered=True,
            screen_y=self.top_nav.height
        )


    def _render(self):
        super()._render()
        self.fingerprint_icontextline.render()


@dataclass
class SeedWordsScreen(ButtonListScreen):
    title: str = "Seed Words"
    seed: Seed = None
    is_first_page: bool = True
    is_bottom_list: bool = True

    def __post_init__(self):
        super().__post_init__()

        # Set up how to render the 12 words on this screen
        mnemonic = self.seed.mnemonic_display_list
        if len(mnemonic) == 12 or self.is_first_page:
            self.mnemonic = mnemonic[:12]
        else:
            self.mnemonic = mnemonic[12:]

    def _render(self):
        super()._render()

        font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, 16)

        # Calc vertical placement for the numbers
        (number_x, number_y) = calc_text_centering(
            font=font,
            text="1234567890",
            is_text_centered=True,
            box_width=20,
            box_height=20
        )
        number_box_x = GUIConstants.EDGE_PADDING
        number_box_y = self.top_nav.height
        number_box_width = 20
        number_box_height = 20
        for index, word in enumerate(self.mnemonic):
            if index == 6:
                # Start of the second column of words
                number_box_x = int(self.canvas_width / 2) + 4
                number_box_y = self.top_nav.height

            self.renderer.draw.rounded_rectangle(
                (number_box_x, number_box_y, number_box_x + number_box_width, number_box_y + number_box_height),
                fill="#202020",
                radius=5
            )
            number_str = str(index + 1)
            tw, th = font.getsize(number_str)
            self.renderer.draw.text(
                (number_box_x + int((number_box_width - tw) / 2), number_box_y + number_y),
                font=font,
                text=number_str,
                fill="#0084ff"
            )

            # Now draw the word
            self.renderer.draw.text(
                (number_box_x + number_box_width + 4, number_box_y + number_y),
                font=font,
                text=word,
                fill=GUIConstants.BODY_FONT_COLOR
            )

            number_box_y += number_box_height + 4
        self.renderer.show_image()


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
            font_color="orange",
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
        font_color = "orange"
        button3_text = "Save"
        tw, th = font.getsize(button3_text)
        key_y = int(self.renderer.canvas_height - row_height) / 2 - 1 + 60
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline="orange", fill=background_color, radius=5, width=1)
        self.renderer.draw.text((self.renderer.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button3_text, fill=font_color)

        self.text_entry_display.render(self.derivation_path)
        self.renderer.show_image()
    

    def _run(self):
        cursor_position = len(self.derivation_path)

        # Start the interactive update loop
        while True:
            input = self.hw_inputs.wait_for(
                [B.KEY_UP, B.KEY_DOWN, B.KEY_RIGHT, B.KEY_LEFT, B.KEY_PRESS, B.KEY3],
                check_release=True,
                release_keys=[B.KEY_PRESS, B.KEY3]
            )
    
            # Check our two possible exit conditions
            if input == B.KEY3:
                # Save!
                if len(self.derivation_path) > 0:
                    return self.derivation_path.strip()
    
            elif self.top_nav.is_selected and input == B.KEY_PRESS:
                # Prev button clicked; return empty string to signal cancel.
                return self.top_nav.selected_button
    
            # Process normal input
            if input in [B.KEY_UP, B.KEY_DOWN] and self.top_nav.is_selected:
                # We're navigating off the previous button
                self.top_nav.is_selected = False
                self.top_nav.render()
    
                # Override the actual input w/an ENTER signal for the Keyboard
                if input == B.KEY_DOWN:
                    input = Keyboard.ENTER_TOP
                else:
                    input = Keyboard.ENTER_BOTTOM
            elif input in [B.KEY_LEFT, B.KEY_RIGHT] and self.top_nav.is_selected:
                # ignore
                continue
    
            ret_val = self.keyboard_digits.update_from_input(input)
    
            # Now process the result from the keyboard
            if ret_val in Keyboard.EXIT_DIRECTIONS:
                self.top_nav.is_selected = True
                self.top_nav.render()
    
            elif ret_val in Keyboard.ADDITIONAL_KEYS and input == B.KEY_PRESS:
                if ret_val == Keyboard.KEY_BACKSPACE["code"]:
                    if len(self.derivation_path) <= 2:
                        pass
                    elif cursor_position == len(self.derivation_path):
                        self.derivation_path = self.derivation_path[:-1]
                        cursor_position -= 1
                    else:
                        self.derivation_path = self.derivation_path[:cursor_position - 1] + self.derivation_path[cursor_position:]
                        cursor_position -= 1
    
            elif input == B.KEY_PRESS and ret_val not in Keyboard.ADDITIONAL_KEYS:
                # User has locked in the current letter
                if cursor_position == len(self.derivation_path):
                    self.derivation_path += ret_val
                else:
                    self.derivation_path = self.derivation_path[:cursor_position] + ret_val + self.derivation_path[cursor_position:]
                cursor_position += 1
    
            elif input in [B.KEY_RIGHT, B.KEY_LEFT, B.KEY_UP, B.KEY_DOWN]:
                # Live joystick movement; haven't locked this new letter in yet.
                # Leave current spot blank for now. Only update the active keyboard keys
                # when a selection has been locked in (KEY_PRESS) or removed ("del").
                pass
    
            # Render the text entry display and cursor block
            self.text_entry_display.render(self.derivation_path)
    
            self.renderer.show_image()



@dataclass
class SeedExportXpubDetailsScreen(WarningScreenMixin, ButtonListScreen):
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
            icon_name="fingerprint",
            label_text="Fingerprint",
            value_text=self.fingerprint,
            screen_x=8,
            screen_y=self.top_nav.height,
        )

        self.derivation_line = IconTextLine(
            icon_name="fingerprint",
            label_text="Derivation",
            value_text=self.derivation_path,
            screen_x=8,
            screen_y=self.fingerprint_line.screen_y + self.fingerprint_line.height + 8,
        )

        self.xpub_line = IconTextLine(
            icon_name="fingerprint",
            label_text="Xpub",
            value_text=self.xpub,
            screen_x=8,
            screen_y=self.derivation_line.screen_y + self.derivation_line.height + 8,
        )


    def _render(self):
        super()._render()

        self.fingerprint_line.render()
        self.derivation_line.render()
        self.xpub_line.render()

        self.render_warning_edges()

        # Write the screen updates
        self.renderer.show_image()



@dataclass
class SeedExportXpubQRDisplayScreen(BaseScreen):
    qr_encoder: EncodeQR = None

    def __post_init__(self):
        # Initialize the base class
        super().__post_init__()


    def _run(self):
        while self.qr_encoder.totalParts() > 1:
            image = self.qr_encoder.nextPartImage(240,240,2)
            self.renderer.show_image(image)
            time.sleep(0.1)
            if self.hw_inputs.check_for_low(B.KEY_RIGHT):
                break

        if self.qr_encoder.totalParts() == 1:
            image = self.qr_encoder.nextPartImage(240,240,1)
            self.renderer.show_image(image)
            self.hw_inputs.wait_for([B.KEY_RIGHT])

        # TODO: handle left as BACK



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
            font_color="orange",
            cursor_mode=TextEntryDisplay.CURSOR_MODE__BAR,
            is_centered=False,
            has_outline=True,
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
        font_color = "orange"
        font = Fonts.get_font("RobotoCondensed-Regular", 24)
        tw, th = font.getsize(button1_text)
        if self.button1_is_active:
            background_color = "orange"
            font_color = "#111"
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline="orange", fill=background_color, radius=5, width=1)
        self.renderer.draw.text((self.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button1_text, fill=font_color)

        background_color = "#111"
        font_color = "orange"
        tw, th = font.getsize(button2_text)
        if self.button2_is_active:
            background_color = "orange"
            font_color = "#111"
        key_y = int(self.canvas_height - row_height) / 2 - 1
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline="orange", fill=background_color, radius=5, width=1)
        self.renderer.draw.text((self.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button2_text, fill=font_color)

        background_color = "#111"
        font_color = "orange"
        button3_text = "Save"
        tw, th = font.getsize(button3_text)
        if self.button3_is_active:
            background_color = "orange"
            font_color = "#111"
        key_y = int(self.canvas_height - row_height) / 2 - 1 + 60
        self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline="orange", fill=background_color, radius=5, width=1)
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
                [B.KEY_UP, B.KEY_DOWN, B.KEY_RIGHT, B.KEY_LEFT, B.KEY_PRESS, B.KEY1, B.KEY2, B.KEY3],
                check_release=True,
                release_keys=[B.KEY_PRESS, B.KEY1, B.KEY2, B.KEY3]
            )

            keyboard_swap = False

            # Check our two possible exit conditions
            if input == B.KEY3:
                # Save!
                if len(self.passphrase) > 0:
                    return self.passphrase.strip()

            elif input == B.KEY_PRESS and self.top_nav.is_selected:
                # Back button clicked
                return self.top_nav.selected_button

            # Check for keyboard swaps
            if input == B.KEY1:
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

            elif input == B.KEY2:
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
                if input in [B.KEY_UP, B.KEY_DOWN] and self.top_nav.is_selected:
                    # We're navigating off the previous button
                    self.top_nav.is_selected = False
                    self.top_nav.render()

                    # Override the actual input w/an ENTER signal for the Keyboard
                    if input == B.KEY_DOWN:
                        input = Keyboard.ENTER_TOP
                    else:
                        input = Keyboard.ENTER_BOTTOM
                elif input in [B.KEY_LEFT, B.KEY_RIGHT] and self.top_nav.is_selected:
                    # ignore
                    continue

                ret_val = cur_keyboard.update_from_input(input)

            # Now process the result from the keyboard
            if ret_val in Keyboard.EXIT_DIRECTIONS:
                self.top_nav.is_selected = True
                self.top_nav.render()

            elif ret_val in Keyboard.ADDITIONAL_KEYS and input == B.KEY_PRESS:
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

            elif input == B.KEY_PRESS and ret_val not in Keyboard.ADDITIONAL_KEYS:
                # User has locked in the current letter
                if cursor_position == len(self.passphrase):
                    self.passphrase += ret_val
                else:
                    self.passphrase = self.passphrase[:cursor_position] + ret_val + self.passphrase[cursor_position:]
                cursor_position += 1

                # Update the text entry display and cursor
                self.text_entry_display.render(self.passphrase, cursor_position)

            elif input in [B.KEY_RIGHT, B.KEY_LEFT, B.KEY_UP, B.KEY_DOWN] or keyboard_swap:
                # Live joystick movement; haven't locked this new letter in yet.
                # Leave current spot blank for now. Only update the active keyboard keys
                # when a selection has been locked in (KEY_PRESS) or removed ("del").
                pass

            self.renderer.show_image()
