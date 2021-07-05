from dataclasses import dataclass

from . import B



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
        "letter": "del",
        "font": COMPACT_KEY_FONT,
        "size": 2,
    }
    KEY_PREVIOUS_PAGE = {
        "letter": "prev"
    }
    ADDITIONAL_KEYS = {
        KEY_BACKSPACE["letter"]: KEY_BACKSPACE,
        KEY_PREVIOUS_PAGE["letter"]: KEY_PREVIOUS_PAGE,
    }

    @dataclass
    class Key:
        """
            Simple python3.x dataclass (akin to a strut) to store info about each
            individual key in the keyboard and its state. Attrs with defaults must be
            listed last.
        """
        letter: str
        screen_x: int
        screen_y: int
        keyboard: any
        size: int = 1
        is_active: bool = True
        is_selected: bool = False
        is_additional_key: bool = False

        def render_key(self):
            font = self.keyboard.font
            if self.letter in Keyboard.ADDITIONAL_KEYS:
                if Keyboard.ADDITIONAL_KEYS[self.letter]["font"] == Keyboard.COMPACT_KEY_FONT:
                    font = self.keyboard.additonal_key_compact_font

            outline_color = "#333"
            if not self.is_active:
                rect_color = self.keyboard.background_color
                font_color = "#666"  # Show the letter but render as gray
                if self.is_selected:
                    # Inactive, selected just gets highlighted outline
                    outline_color = self.keyboard.highlight_color
            elif self.is_selected:
                rect_color = self.keyboard.highlight_color  # Render solid background with the UI's hero color
                font_color = self.keyboard.background_color
            else:
                rect_color = self.keyboard.background_color
                font_color = self.keyboard.highlight_color

            self.keyboard.draw.rectangle((self.screen_x, self.screen_y, self.screen_x + self.keyboard.x_width * self.size, self.screen_y + self.keyboard.y_height), outline=outline_color, fill=rect_color)
            tw, th = self.keyboard.draw.textsize(self.letter, font=font)
            self.keyboard.draw.text((self.screen_x + int((self.keyboard.x_width * self.size - tw) / 2), self.screen_y + int((self.keyboard.y_height - th)/2)), self.letter, fill=font_color, font=font)



    def __init__(self, 
                 draw,
                 charset="1234567890abcdefghijklmnopqrstuvwxyz",
                 selected_char="a",
                 rows=4,
                 cols=10,
                 rect=(0,40, 240,240),
                 font=None,
                 additional_keys=[KEY_BACKSPACE],
                 auto_wrap=[WRAP_TOP, WRAP_BOTTOM, WRAP_LEFT, WRAP_RIGHT]):
        """
            `auto_wrap` specifies which edges the keyboard is allowed to loop back when
            navigating past the end.
        """

        # Import here to avoid circular import problems
        from seedsigner.views import View

        self.draw = draw
        self.charset = charset
        self.rows = rows
        self.cols = cols
        self.rect = rect
        if font:
            self.font = font
        else:
            self.font = View.ROBOTOCONDENSED_REGULAR_24
        self.auto_wrap = auto_wrap
        self.background_color = "black"
        self.highlight_color = View.color

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
        self.additonal_key_compact_font = View.ROBOTOCONDENSED_BOLD_18
        self.x_start = rect[0]
        self.y_start = rect[1]
        self.x_gap = 1
        self.x_width = int((rect[2] - rect[0]) / cols) - self.x_gap
        self.y_gap = 6
        self.y_height = int((rect[3] - rect[1]) / rows) - self.y_gap

        # Two-dimensional list of Key obj row data
        self.keys = []
        self.selected_key = {"x": 0, "y": 0}  # Indices in the `keys` 2D list
        cur_y = self.y_start
        for i in range(0, rows):
            cur_row = []
            cur_x = self.x_start
            for j, letter in enumerate(charset[i*cols:(i+1)*cols]):
                is_selected = False
                if letter == selected_char:
                    is_selected = True
                    self.selected_key["y"] = i
                    self.selected_key["x"] = j
                cur_row.append(self.Key(
                    letter=letter,
                    screen_x=cur_x,
                    screen_y=cur_y,
                    is_selected=is_selected,
                    keyboard=self
                ))
                cur_x += self.x_width + self.x_gap
            self.keys.append(cur_row)
            if i < rows -1:
                # increment to the next row and continue
                cur_y += self.y_height + self.y_gap
            else:
                # It's the last row; add the additional keys at the end
                for additional_key in additional_keys:
                    self.keys[-1].append(self.Key(
                        letter=additional_key["letter"],
                        screen_x=cur_x,
                        screen_y=cur_y,
                        keyboard=self,
                        size=additional_key["size"],
                        is_additional_key=True,
                    ))
                    cur_x += self.x_width + self.x_gap

        # Render the keys
        self.render_keys()

        # Render the initial highlighted character
        self.update_from_input(input=None)


    def update_active_keys(self, active_keys):
        self.active_keys = active_keys
        for i, row_keys in enumerate(self.keys):
            for j, key in enumerate(row_keys):
                if key.letter not in self.active_keys and key.letter not in Keyboard.ADDITIONAL_KEYS:
                    # Note: ADDITIONAL_KEYS are never deactivated.
                    key.is_active = False
                else:
                    key.is_active = True


    def render_keys(self, selected_letter=None):
        """
            Renders just the keys of the keyboard. Useful when you need to redraw just
            that section, as in when changing `active_keys` or swapping to alternate
            charsets (e.g. alpha to special symbols).

            Does NOT call View.DispShowImage to avoid multiple calls on the same screen.
        """
        # Start with a clear screen
        self.draw.rectangle(self.rect, outline=0, fill=0)

        for i, row_keys in enumerate(self.keys):
            for j, key in enumerate(row_keys):
                if selected_letter and key.letter == selected_letter:
                    key.is_selected = True
                    self.selected_key["y"] = i
                    self.selected_key["x"] = j
                key.render_key()


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

            Does NOT call View.DispShowImage to avoid multiple calls on the same screen.
        """
        key = self.keys[self.selected_key["y"]][self.selected_key["x"]]

        # Before we update, undo our previously self.selected_key key
        key.is_selected = False
        key.render_key()

        if input == B.KEY_RIGHT:
            self.selected_key["x"] += 1
            if self.selected_key["x"] == len(self.keys[self.selected_key["y"]]):
                if Keyboard.WRAP_RIGHT in self.auto_wrap:
                    # Loop it back to the right side
                    self.selected_key["x"] = 0
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    self.selected_key["x"] -= 1
                    return Keyboard.EXIT_RIGHT

        elif input == B.KEY_LEFT:
            self.selected_key["x"] -= 1
            if self.selected_key["x"] < 0:
                if Keyboard.WRAP_LEFT in self.auto_wrap:
                    # Loop it back to the left side
                    self.selected_key["x"] = len(self.keys[self.selected_key["y"]]) - 1
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    self.selected_key["x"] += 1
                    return Keyboard.EXIT_LEFT

        elif input == B.KEY_DOWN:
            self.selected_key["y"] += 1
            if self.selected_key["y"] == len(self.keys):
                if Keyboard.WRAP_BOTTOM in self.auto_wrap:
                    # Loop it back to the top
                    self.selected_key["y"] = 0
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    self.selected_key["y"] -= 1
                    return Keyboard.EXIT_BOTTOM

            if self.selected_key["x"] >= len(self.keys[self.selected_key["y"]]):
                if Keyboard.WRAP_BOTTOM in self.auto_wrap:
                    # This line is too short to land here
                    self.selected_key["y"] = 0
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    self.selected_key["y"] -= 1
                    return Keyboard.EXIT_BOTTOM

        elif input == B.KEY_UP:
            self.selected_key["y"] -= 1
            if self.selected_key["y"] < 0:
                if Keyboard.WRAP_TOP in self.auto_wrap:
                    # Loop it back to the bottom
                    self.selected_key["y"] = len(self.keys) - 1
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    self.selected_key["y"] += 1
                    return Keyboard.EXIT_TOP

            if self.selected_key["x"] >= len(self.keys[self.selected_key["y"]]):
                if Keyboard.WRAP_TOP in self.auto_wrap:
                    # This line is too short to land here
                    self.selected_key["y"] -= 1
                else:
                    # Undo selection change and notify controlling loop that we've left
                    #   the keyboard
                    self.selected_key["y"] += 1
                    return Keyboard.EXIT_TOP

        elif input == Keyboard.ENTER_LEFT:
            # User has returned to the keyboard along the left edge
            # Keep the last y position that was selected.
            self.selected_key["x"] = 0

        elif input == Keyboard.ENTER_RIGHT:
            # User has returned to the keyboard along the right edge
            # Keep the last y position that was selected.
            self.selected_key["x"] = len(self.keys[self.selected_key["y"]]) - 1

        elif input == Keyboard.ENTER_TOP:
            # User has returned to the keyboard along the top edge
            # Keep the last x position that was selected.
            self.selected_key["y"] = 0

        elif input == Keyboard.ENTER_BOTTOM:
            # User has returned to the keyboard along the bottom edge
            # Keep the last x position that was selected.
            self.selected_key["y"] = len(self.keys) - 1
            if self.selected_key["x"] > len(self.keys[self.selected_key["y"]]) - 1:
                # Can't enter here. Jump up a row
                self.selected_key["y"] -= 1

        # Render the newly self.selected_key letter
        key = self.keys[self.selected_key["y"]][self.selected_key["x"]]
        key.is_selected = True
        key.render_key()

        return key.letter


    def set_selected_key(self, selected_letter):
        # De-select the current selected_key
        self.keys[self.selected_key["y"]][self.selected_key["x"]].is_selected = False

        # Find the new selected_key
        for i, row_keys in enumerate(self.keys):
            for j, key in enumerate(row_keys):
                if selected_letter and key.letter == selected_letter:
                    key.is_selected = True
                    self.selected_key["y"] = i
                    self.selected_key["x"] = j
                    return
        raise Exception(f"""`selected_letter` "{selected_letter}" not found in keyboard""")


