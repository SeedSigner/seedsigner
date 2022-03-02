# SeedSigner file class dependencies
from . import View
from seedsigner.helpers import B, QR
from seedsigner.gui.keyboard import Keyboard, TextEntryDisplay
from seedsigner.models import EncodeQR



class SettingsToolsView(View):
    def __init__(self) -> None:
        View.__init__(self)

        self.qr = QR()
        self.donate_image = None
        self.derivation = None


    ### Donate Menu Item
    def display_donate_info_screen(self):
        self.renderer.draw_modal(["You can support", "SeedSigner by donating", "any amount of BTC", "Thank You!!!"], "", "(Press right for a QR code)")
        return True


    def display_donate_qr(self):
        self.renderer.draw_modal(["Loading..."])
        self.donate_image = self.qr.qrimage("bc1qphlyv2dde290tqdlnk8uswztnshw3x9rjurexqqhksvu7vdevhtsuw4efe")
        self.renderer.show_image(self.donate_image)
        return True



    ###
    ### Custom Derivation Path
    ###
    def draw_derivation_keyboard_entry(self, existing_derivation = "m/"):
        def render_right_panel():
            row_height = 28
            right_button_left_margin = 10
            right_button_width = 60
            font_padding_right = 2
            font_padding_top = 1
            key_x = self.renderer.canvas_width - right_button_width
            key_y = int(self.renderer.canvas_height - row_height) / 2 - 1 - 60
            font = Fonts.get_font("RobotoCondensed-Regular", 24)
            background_color = "#111"
            font_color = View.color
            button3_text = "Save"
            tw, th = font.getsize(button3_text)
            key_y = int(self.renderer.canvas_height - row_height) / 2 - 1 + 60
            self.renderer.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=View.color, fill=background_color, radius=5, width=1)
            self.renderer.draw.text((self.renderer.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button3_text, fill=font_color)
    
        # Clear the screen
        self.renderer.draw.rectangle((0,0, self.renderer.canvas_width,self.renderer.canvas_height), fill="black")
    
        self.render_previous_button()
        previous_button_is_active = False
    
        # Have to ensure that we don't carry any effects from a previous run
        # TODO: This shouldn't be a member var
        if existing_derivation:
            self.derivation = existing_derivation
        else:
            self.derivation = "m/"
    
        # Set up the keyboard params
        right_panel_buttons_width = 60
    
        # render top title banner
        font = Fonts.get_font("RobotoCondensed-Regular", 20)
        title = "Enter Derivation"
        title_top_padding = 0
        title_bottom_padding = 10
        tw, th = font.getsize(title)
        self.renderer.draw.text((int(self.renderer.canvas_width - tw) / 2, title_top_padding), text=title, font=font, fill=View.color)
        title_height = th + title_top_padding + title_bottom_padding
    
        # Render the live text entry display
        font = Fonts.get_font("RobotoCondensed-Regular", 28)
        tw, th = font.getsize("m/1234567890")  # All possible chars for max range
        text_entry_side_padding = 0
        text_entry_top_padding = 1
        text_entry_bottom_padding = 10
        text_entry_top_y = title_height + text_entry_top_padding
        text_entry_bottom_y = text_entry_top_y + 3 + th + 3
        text_entry_display = TextEntryDisplay(
            self.renderer.draw,
            rect=(text_entry_side_padding,text_entry_top_y, self.renderer.canvas_width - right_panel_buttons_width - 1, text_entry_bottom_y),
            font=font,
            font_color=View.color,
            cursor_mode=TextEntryDisplay.CURSOR_MODE__BLOCK,
            is_centered=False,
            has_outline=True,
            cur_text=''.join(self.derivation)
        )
        text_entry_display.render()
        cursor_position = len(self.derivation)
    
        keyboard_start_y = text_entry_bottom_y + text_entry_bottom_padding
        keyboard_digits = Keyboard(
            self.renderer.draw,
            charset="/'0123456789",
            rows=3,
            cols=6,
            rect=(0, keyboard_start_y, self.renderer.canvas_width - right_panel_buttons_width, self.renderer.canvas_height),
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )
        keyboard_digits.set_selected_key(selected_letter="/")
        keyboard_digits.render_keys()
        render_right_panel()
        
        text_entry_display.render(self.derivation)
        self.renderer.show_image()
    
        # Start the interactive update loop
        while True:
            input = self.buttons.wait_for(
                [B.KEY_UP, B.KEY_DOWN, B.KEY_RIGHT, B.KEY_LEFT, B.KEY_PRESS, B.KEY3],
                check_release=True,
                release_keys=[B.KEY_PRESS, B.KEY3]
            )
    
            # Check our two possible exit conditions
            if input == B.KEY3:
                # Save!
                if len(self.derivation) > 0:
                    return self.derivation.strip()
    
            elif input == B.KEY_PRESS and previous_button_is_active:
                # Prev button clicked; return empty string to signal cancel.
                return ""
    
            # Process normal input
            if input in [B.KEY_UP, B.KEY_DOWN] and previous_button_is_active:
                # We're navigating off the previous button
                previous_button_is_active = False
                self.render_previous_button(highlight=False)
    
                # Override the actual input w/an ENTER signal for the Keyboard
                if input == B.KEY_DOWN:
                    input = Keyboard.ENTER_TOP
                else:
                    input = Keyboard.ENTER_BOTTOM
            elif input in [B.KEY_LEFT, B.KEY_RIGHT] and previous_button_is_active:
                # ignore
                continue
    
            ret_val = keyboard_digits.update_from_input(input)
    
            # Now process the result from the keyboard
            if ret_val in Keyboard.EXIT_DIRECTIONS:
                self.render_previous_button(highlight=True)
                previous_button_is_active = True
    
            elif ret_val in Keyboard.ADDITIONAL_KEYS and input == B.KEY_PRESS:
                if ret_val == Keyboard.KEY_BACKSPACE["code"]:
                    if len(self.derivation) <= 2:
                        pass
                    elif cursor_position == len(self.derivation):
                        self.derivation = self.derivation[:-1]
                        cursor_position -= 1
                    else:
                        self.derivation = self.derivation[:cursor_position - 1] + self.derivation[cursor_position:]
                        cursor_position -= 1
    
            elif input == B.KEY_PRESS and ret_val not in Keyboard.ADDITIONAL_KEYS:
                # User has locked in the current letter
                if cursor_position == len(self.derivation):
                    self.derivation += ret_val
                else:
                    self.derivation = self.derivation[:cursor_position] + ret_val + self.derivation[cursor_position:]
                cursor_position += 1
    
            elif input in [B.KEY_RIGHT, B.KEY_LEFT, B.KEY_UP, B.KEY_DOWN]:
                # Live joystick movement; haven't locked this new letter in yet.
                # Leave current spot blank for now. Only update the active keyboard keys
                # when a selection has been locked in (KEY_PRESS) or removed ("del").
                pass
    
            # Render the text entry display and cursor block
            text_entry_display.render(self.derivation)
    
            self.renderer.show_image()