from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple

from seedsigner.gui.components import Fonts, GUIConstants
from seedsigner.hardware.buttons import HardwareButtonsConstants



class Keyboard:
    WRAP_TOP = "wrap_top"
    WRAP_BOTTOM = "wrap_bottom"
    WRAP_LEFT = "wrap_left"
    WRAP_RIGHT = "wrap_right"

    EXIT_TOP = "exit_top"
    EXIT_BOTTOM = "exit_bottom"
    EXIT_LEFT = "exit_left"
    EXIT_RIGHT = "exit_right"
    EXIT_DIRECTIONS = [EXIT_TOP, EXIT_BOTTOM, EXIT_LEFT, EXIT_RIGHT]

    ENTER_TOP = "enter_top"
    ENTER_BOTTOM = "enter_bottom"
    ENTER_LEFT = "enter_left"
    ENTER_RIGHT = "enter_right"

    REGULAR_KEY_FONT = "regular"
    COMPACT_KEY_FONT = "compact"

    KEY_BACKSPACE = {
        "code": "DEL",
        "letter": "del",
        "font": COMPACT_KEY_FONT,
        "size": 2,
    }
    KEY_SPACE = {
        "code": "SPACE",
        "letter": "space",
        "font": COMPACT_KEY_FONT,
        "size": 1,
    }
    KEY_SPACE_2 = {
        "code": "SPACE",
        "letter": "space",
        "font": COMPACT_KEY_FONT,
        "size": 2,
    }
    KEY_SPACE_3 = {
        "code": "SPACE",
        "letter": "space",
        "font": COMPACT_KEY_FONT,
        "size": 3,
    }
    KEY_SPACE_4 = {
        "code": "SPACE",
        "letter": "space",
        "font": COMPACT_KEY_FONT,
        "size": 4,
    }
    KEY_SPACE_5 = {
        "code": "SPACE",
        "letter": "space",
        "font": COMPACT_KEY_FONT,
        "size": 5,
    }
    KEY_CURSOR_LEFT = {
        "code": "CURSOR_LEFT",
        "letter": "<",
        "font": REGULAR_KEY_FONT,
        "size": 1,
    }
    KEY_CURSOR_RIGHT = {
        "code": "CURSOR_RIGHT",
        "letter": ">",
        "font": REGULAR_KEY_FONT,
        "size": 1,
    }
    KEY_PREVIOUS_PAGE = {
        "code": "PREV",
        "letter": "<",
        "font": REGULAR_KEY_FONT,
        "size": 1,
    }
    ADDITIONAL_KEYS = {
        KEY_SPACE["code"]: KEY_SPACE,
        KEY_BACKSPACE["code"]: KEY_BACKSPACE,
        KEY_CURSOR_LEFT["code"]: KEY_CURSOR_LEFT,
        KEY_CURSOR_RIGHT["code"]: KEY_CURSOR_RIGHT,
        KEY_PREVIOUS_PAGE["code"]: KEY_PREVIOUS_PAGE,
    }

    @dataclass
    class Key:
        """
            Simple python3.x dataclass (akin to a strut) to store info about each
            individual key in the keyboard and its state. Attrs with defaults must be
            listed last.
        """
        letter: str     # display value
        screen_x: int
        screen_y: int
        keyboard: any
        index_x: int = None
        index_y: int = None
        code: str = None  # key/code returned on press (e.g. "x" or "cursor_left")
        size: int = 1
        is_active: bool = True
        is_selected: bool = False
        is_additional_key: bool = False

        def __post_init__(self):
            if not self.code:
                self.code = self.letter

        def render_key(self):
            font = self.keyboard.font
            if self.is_additional_key:
                if Keyboard.ADDITIONAL_KEYS[self.code]["font"] == Keyboard.COMPACT_KEY_FONT:
                    font = self.keyboard.additonal_key_compact_font

            outline_color = "#333"
            if not self.is_active:
                rect_color = self.keyboard.deactivated_background_color
                font_color = "#333"  # Show the letter but render as gray
                outline_color = self.keyboard.deactivated_background_color

                if self.is_selected:
                    # Inactive, selected just gets highlighted outline
                    outline_color = self.keyboard.highlight_color
            elif self.is_selected:
                rect_color = self.keyboard.highlight_color  # Render solid background with the UI's hero color
                font_color = "black"
            else:
                if self.is_additional_key:
                    rect_color = "#000"
                    font_color = "#999"
                else:
                    rect_color = self.keyboard.background_color
                    font_color = "#e8e8e8"

            self.keyboard.draw.rounded_rectangle(
                (
                    self.screen_x,
                    self.screen_y,
                    self.screen_x + self.keyboard.key_width * self.size - 1,
                    self.screen_y + self.keyboard.key_height
                ),
                outline=outline_color,
                fill=rect_color,
                radius=4
            )

            # Fixed-width fonts will all have same height, ignoring below baseline (e.g. "Q" or "q")
            (left, top, right, bottom) = font.getbbox("X", anchor="ls")
            text_height = -1 * top
            self.keyboard.draw.text(
                (
                    self.screen_x + int(self.keyboard.key_width * self.size / 2),
                    self.screen_y + self.keyboard.key_height - int((self.keyboard.key_height - text_height)/2)
                ),
                self.letter,
                fill=font_color,
                font=font,
                anchor="ms"
            )



    def __init__(self,
                 draw: ImageDraw,
                 charset="1234567890abcdefghijklmnopqrstuvwxyz",
                 font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                 font_size=24,
                 selected_char="a",
                 rows=4,
                 cols=10,
                 rect=(0,40, 240,240),
                 additional_keys=[KEY_BACKSPACE],
                 auto_wrap=[WRAP_TOP, WRAP_BOTTOM, WRAP_LEFT, WRAP_RIGHT],
                 render_now=True,
                 highlight_color: str = GUIConstants.ACCENT_COLOR):
        """
            `auto_wrap` specifies which edges the keyboard is allowed to loop back when
            navigating past the end.
        """
        self.draw = draw
        self.charset = charset
        self.rows = rows
        self.cols = cols
        self.rect = rect
        self.font = Fonts.get_font(font_name, font_size)

        self.auto_wrap = auto_wrap
        self.background_color = GUIConstants.BUTTON_BACKGROUND_COLOR
        self.deactivated_background_color = GUIConstants.BACKGROUND_COLOR
        self.additional_key_deactivated_background_color = GUIConstants.BACKGROUND_COLOR
        self.highlight_color = highlight_color

        # Does the specified layout work?
        additional_key_spaces = 0
        for additional_key in additional_keys:
            additional_key_spaces += additional_key["size"]  # e.g. backspace takes up 2 slots
        if rows * cols < len(charset) + additional_key_spaces:
            raise Exception(f"charset will not fit in a {rows}x{cols} layout | additional_keys: {additional_keys}")

        if not selected_char:
            raise Exception("`selected_char` cannot be None")

        # Set up the rendering and state params
        self.active_keys = list(self.charset)
        self.additonal_key_compact_font = Fonts.get_font("RobotoCondensed-Bold", 18)
        self.x_start = rect[0]
        self.y_start = rect[1]
        self.x_gap = 2
        self.key_width = int((rect[2] - rect[0]) / cols) - self.x_gap
        self.width = cols * (self.key_width) + (cols - 1) * self.x_gap
        self.y_gap = 2
        self.key_height = int((rect[3] - rect[1]) / rows) - self.y_gap
        self.height = rows * (self.key_height) + (rows - 1) * self.y_gap
        self.additional_key_entered_from_x = None

        # Two-dimensional list of Key obj row data
        self.keys = []
        self.selected_key = {"x": 0, "y": 0}  # Indices in the `keys` 2D list
        cur_y = self.y_start
        for i in range(0, rows):
            cur_row = []
            cur_x = self.x_start
            cur_index_x = 0
            for letter in charset[i*cols:(i+1)*cols]:
                is_selected = False
                if letter == selected_char:
                    is_selected = True
                    self.selected_key["y"] = i
                    self.selected_key["x"] = cur_index_x
                cur_row.append(self.Key(
                    letter=letter,
                    screen_x=cur_x,
                    screen_y=cur_y,
                    index_x=cur_index_x,
                    index_y=i,
                    is_selected=is_selected,
                    keyboard=self
                ))
                cur_x += self.key_width + self.x_gap
                cur_index_x += 1
            self.keys.append(cur_row)
            if i < rows - 1:
                # increment to the next row and continue
                cur_y += self.key_height + self.y_gap
            else:
                # It's the last row; add the additional keys at the end
                for additional_key in additional_keys:
                    self.keys[-1].append(self.Key(
                        letter=additional_key["letter"],
                        code=additional_key["code"],
                        screen_x=cur_x,
                        screen_y=cur_y,
                        index_x=cur_index_x,
                        index_y=i,
                        keyboard=self,
                        size=additional_key["size"],
                        is_additional_key=True,
                    ))
                    cur_x += self.key_width * additional_key["size"] + self.x_gap
                    cur_index_x += additional_key["size"]

        if render_now:
            # Render the keys
            self.render_keys()

            # Render the initial highlighted character
            self.update_from_input(input=None)


    def update_active_keys(self, active_keys):
        self.active_keys = active_keys
        for i, row_keys in enumerate(self.keys):
            for j, key in enumerate(row_keys):
                if key.code not in self.active_keys and not key.is_additional_key:
                    # Note: ADDITIONAL_KEYS are never deactivated.
                    key.is_active = False
                else:
                    key.is_active = True


    def render_keys(self, selected_letter=None):
        """
            Renders just the keys of the keyboard. Useful when you need to redraw just
            that section, as in when changing `active_keys` or swapping to alternate
            charsets (e.g. alpha to special symbols).

            Does NOT call self.renderer.show_image to avoid multiple calls on the same screen.
        """
        # Start with a clear screen
        self.draw.rectangle(self.rect, outline=0, fill=0)

        for i, row_keys in enumerate(self.keys):
            for j, key in enumerate(row_keys):
                if selected_letter and key.code == selected_letter:
                    key.is_selected = True
                    self.selected_key["y"] = i
                    self.selected_key["x"] = j
                key.render_key()


    def get_selected_key(self):
        return self.get_key_at(self.selected_key["x"], self.selected_key["y"])


    def get_key_at(self, index_x, index_y):
        if index_y < len(self.keys) - 1:
            # Not on the bottom row
            if index_x < len(self.keys[index_y]):
                return self.keys[index_y][index_x]
            else:
                # index_x is beyond the last key in this row
                return None

        effective_index = 0
        key = None
        for cur_key in self.keys[index_y]:
            if index_x >= effective_index and index_x < effective_index + cur_key.size:
                return cur_key
            effective_index += cur_key.size

        return None


    def get_key_above(self, cur_x, cur_y):
        next_y = cur_y - 1

        while True:
            if next_y < 0:
                # We started from the top row; auto_wrap or exit.
                if Keyboard.WRAP_TOP in self.auto_wrap:
                    # Loop it back to the bottom
                    next_y = len(self.keys) - 1
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    return (cur_x, cur_y, Keyboard.EXIT_TOP)

            target_key = self.get_key_at(cur_x, next_y)
            if target_key:
                return(cur_x, next_y, None)
            else:
                # No match was found. Move up one more row.
                next_y -= 1


    def get_key_below(self, cur_x, cur_y):
        next_y = cur_y + 1

        while True:
            if next_y == len(self.keys):
                # We started from the bottom row; auto_wrap or exit.
                if Keyboard.WRAP_BOTTOM in self.auto_wrap:
                    # Loop it back to the top
                    next_y = 0
                    return (cur_x, next_y, None)
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    return (cur_x, cur_y, Keyboard.EXIT_BOTTOM)

            target_key = self.get_key_at(cur_x, next_y)
            if target_key is not None:
                return (cur_x, next_y, None)

            # No keys in this col in this row. Move down again and recheck.
            next_y += 1


    def update_from_input(self, input, enter_from=None):
        """
            Managing code must handle its own input/update loop since other action buttons
            will be active on the same screen outside of the keyboard rect (e.g. "Ok",
            "Back", etc). Pass relevant input here to update the keyboard.

            `enter_from` tells the keyboard that the external UI has caused a loop back
            navigation.
            (e.g. pressing up from a submit button below the keyboard = ENTER_BOTTOM)

            Returns the character currently highlighted or one of the EXIT_* codes if the
            user has navigated off the keyboard past an edge that is not in `auto_wrap`.

            Does NOT call self.renderer.show_image to avoid multiple calls on the same screen.
        """
        key = self.get_key_at(self.selected_key["x"], self.selected_key["y"])

        # Before we update, undo our previously self.selected_key key
        key.is_selected = False
        key.render_key()

        if input == HardwareButtonsConstants.KEY_RIGHT:
            self.selected_key["x"] = key.index_x + key.size
            new_key = self.get_key_at(self.selected_key["x"], self.selected_key["y"])
            if new_key is None:
                if Keyboard.WRAP_RIGHT in self.auto_wrap:
                    # Loop it back to the right side
                    self.selected_key["x"] = 0
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    self.selected_key["x"] -= 1
                    return Keyboard.EXIT_RIGHT

        elif input == HardwareButtonsConstants.KEY_LEFT:
            key = self.get_selected_key()
            self.selected_key["x"] = key.index_x - 1
            if self.selected_key["x"] < 0:
                if Keyboard.WRAP_LEFT in self.auto_wrap:
                    # Loop it back to the left side
                    self.selected_key["x"] = self.keys[self.selected_key["y"]][-1].index_x
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    self.selected_key["x"] += 1
                    return Keyboard.EXIT_LEFT

        elif input == HardwareButtonsConstants.KEY_DOWN:
            new_index_x, new_index_y, keyboard_exit = self.get_key_below(self.selected_key["x"], self.selected_key["y"])
            self.selected_key["x"] = new_index_x
            self.selected_key["y"] = new_index_y
            if keyboard_exit:
                return keyboard_exit

        elif input == HardwareButtonsConstants.KEY_UP:
            new_index_x, new_index_y, keyboard_exit = self.get_key_above(self.selected_key["x"], self.selected_key["y"])
            self.selected_key["x"] = new_index_x
            self.selected_key["y"] = new_index_y
            if keyboard_exit:
                return keyboard_exit

        elif input == Keyboard.ENTER_LEFT:
            # User has returned to the keyboard along the left edge
            # Keep the last y position that was selected.
            self.selected_key["x"] = 0

        elif input == Keyboard.ENTER_RIGHT:
            # User has returned to the keyboard along the right edge
            # Keep the last y position that was selected.
            self.selected_key["x"] = self.keys[self.selected_key["y"]][-1].index_x

        elif input == Keyboard.ENTER_TOP:
            # User has returned to the keyboard along the top edge
            # Keep the last x position that was selected.
            self.selected_key["y"] = 0

        elif input == Keyboard.ENTER_BOTTOM:
            # User has returned to the keyboard along the bottom edge
            # Keep the last x position that was selected.
            self.selected_key["y"] = len(self.keys) - 1
            while True:
                key = self.get_key_at(self.selected_key["x"], self.selected_key["y"])
                if key is not None:
                    break
                else:
                    # Can't enter here. Jump up a row
                    self.selected_key["y"] -= 1

        # Render the newly self.selected_key letter
        key = self.get_key_at(self.selected_key["x"], self.selected_key["y"])
        key.is_selected = True
        key.render_key()

        return key.code


    def set_selected_key(self, selected_letter):
        # De-select the current selected_key
        self.get_selected_key().is_selected = False

        # Find the new selected_key
        for i, row_keys in enumerate(self.keys):
            for j, key in enumerate(row_keys):
                if selected_letter and key.code == selected_letter:
                    key.is_selected = True
                    self.selected_key["y"] = i
                    self.selected_key["x"] = j
                    return
        raise Exception(f"""`selected_letter` "{selected_letter}" not found in keyboard""")


    def set_selected_key_indices(self, x, y):
        # De-select the current selected_key
        self.get_selected_key().is_selected = False

        if y < len(self.keys):
            self.selected_key["y"] = y
        else:
            self.selected_key["y"] = len(self.keys) - 1

        if x < len(self.keys[self.selected_key["y"]]):
            self.selected_key["x"] = x
        else:
            self.selected_key["x"] = len(self.keys[self.selected_key["y"]]) - 1

        # Select the new selected_key
        self.get_key_at(self.selected_key["x"], self.selected_key["y"]).is_selected = True



class TextEntryDisplayConstants:
    CURSOR_MODE__BAR = "bar"
    CURSOR_MODE__BLOCK = "block"



@dataclass
class TextEntryDisplay(TextEntryDisplayConstants):
    canvas: Image
    rect: Tuple[int,int,int,int]
    font_name: str = GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME
    font_size: int = 24
    accent_color: str = GUIConstants.ACCENT_COLOR
    background_color: str = GUIConstants.BUTTON_BACKGROUND_COLOR
    cursor_mode: str = TextEntryDisplayConstants.CURSOR_MODE__BLOCK
    is_centered: bool = True
    cur_text: str = " "
    text_offset = 0


    def __post_init__(self):
        self.font = Fonts.get_font(self.font_name, self.font_size)


    @property
    def width(self):
        return self.rect[2] - self.rect[0]


    @property
    def height(self):
        return self.rect[3] - self.rect[1]


    def render(self, cur_text=None, cursor_position=None):
        """ Render the live text entry display """
        if cur_text is not None:
            self.cur_text = cur_text

        # Start by rendering to a new Image that we'll composite in at the end
        image = Image.new("RGB", (self.width + 1, self.height + 1), "black")
        draw = ImageDraw.Draw(image)

        draw.rounded_rectangle((0, 0, self.width, self.height), fill=self.background_color, radius=4)

        (left, top, right, bottom) = self.font.getbbox("X", anchor="ls")  # measure from baseline
        text_height = -1 * top  # "top" is negative when measuring from baseline; ignoring below baseline

        if self.cursor_mode == TextEntryDisplay.CURSOR_MODE__BLOCK:
            cursor_block_width = 18
            cursor_block_height = 33

            # Draw n-1 of the selected letters
            (left, top, right, bottom) = self.font.getbbox(self.cur_text[:-1], anchor="ls")
            text_width = right
            if self.is_centered:
                self.text_offset = int(self.width - text_width - cursor_block_width)/2
            else:
                self.text_offset = GUIConstants.COMPONENT_PADDING
            cursor_block_offset = self.text_offset + text_width - 1
            if cursor_block_offset == 0:
                cursor_block_offset = 1

            end_pos_x = cursor_block_offset + cursor_block_width
            if end_pos_x >= self.width:
                # Shift the display left
                cursor_block_offset -= end_pos_x - self.width + 1
                self.text_offset -= end_pos_x - self.width + 1
            
            draw.text((self.text_offset, self.height - int(text_height/2)), self.cur_text[:-1], fill=GUIConstants.ACCENT_COLOR, font=self.font, anchor="ls")

            # Draw the highlighted cursor block
            cursor_color = "#666"
            draw.rectangle((cursor_block_offset, 1, cursor_block_offset + cursor_block_width, self.height - 1), fill=cursor_color)
            draw.text((cursor_block_offset + 1, self.height - int(text_height/2)), self.cur_text[-1], fill=GUIConstants.ACCENT_COLOR, font=self.font, anchor="ls")

        else:
            cursor_bar_serif_half_width = 4
            if self.is_centered:
                # self.text_offset = int(self.width - tw)/2
                raise Exception("Centered cursor bars not fully implemented")

            (left, top, right, bottom) = self.font.getbbox(cur_text if cur_text else "", anchor="ls")  # measure from baseline
            text_width = right

            end_pos_x = 3 + text_width + cursor_bar_serif_half_width + 3
            if end_pos_x < self.width:
                # The entire cur_text plus the cursor bar fits
                self.text_offset = 3 + cursor_bar_serif_half_width
                left, top, right, bottom  = self.font.getbbox(self.cur_text[:cursor_position])
                tw_left, th = right - left, bottom - top
                cursor_bar_x = self.text_offset + tw_left

            else:
                if cursor_position is None:
                    cursor_position = len(self.cur_text)

                # Is the cursor at either extreme?
                left, top, right, bottom  = self.font.getbbox(self.cur_text[:cursor_position])
                tw_left, th = right - left, bottom - top

                if self.text_offset + tw_left + cursor_bar_serif_half_width + 3 >= self.width:
                    # Cursor is at the extreme right; have to push the full tw_right off
                    #   the right edge of the display.
                    self.text_offset = self.width - (tw_left + cursor_bar_serif_half_width + 3)
                elif self.text_offset + tw_left < 3 + cursor_bar_serif_half_width:
                    # Cursor is at the extreme left; have to push the full tw_left off 
                    #   left edge of the display.
                    self.text_offset = 3 + cursor_bar_serif_half_width - tw_left

                cursor_bar_x = self.text_offset + tw_left

            draw.text(
                (
                    self.text_offset,
                    self.height - int((self.height - text_height)/2)
                ),
                self.cur_text,
                fill=self.accent_color,
                font=self.font,
                anchor="ls"
            )

            # Render as an "I" bar
            cursor_bar_color = "#ccc"
            draw.line((cursor_bar_x, 3, cursor_bar_x, self.height - 3), fill=cursor_bar_color)
            draw.line((cursor_bar_x - cursor_bar_serif_half_width, 3, cursor_bar_x + cursor_bar_serif_half_width, 3), fill=cursor_bar_color)
            draw.line((cursor_bar_x - cursor_bar_serif_half_width, self.height - 3, cursor_bar_x + cursor_bar_serif_half_width, self.height - 3), fill=cursor_bar_color)

        # Paste the display onto the main canvas
        self.canvas.paste(image, (self.rect[0], self.rect[1]))

