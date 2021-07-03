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

    KEY_BACKSPACE = "del"
    REGULAR_KEY_FONT = "regular"
    COMPACT_KEY_FONT = "compact"

    ADDITIONAL_KEYS = {
        KEY_BACKSPACE: {
            "font": COMPACT_KEY_FONT,
            "key_size": 2,
        }
    }

    def __init__(self, draw, charset="1234567890abcdefghijklmnopqrstuvwxyz", selected_char="a", rows=4, cols=10, rect=(0,40, 240,240), font=None):
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

        additional_keys = 2  # backspace
        if rows * cols < len(charset) + additional_keys:
            raise Exception(f"charset will not fit in a {rows}x{cols} layout")

        self.lines = []
        for i in range(0, rows):
            self.lines.append(list(charset[i*cols:(i+1)*cols]))
        self.lines[-1].append(Keyboard.KEY_BACKSPACE)
        print(self.lines)

        self.x_start = rect[0]
        self.y_start = rect[1]
        self.x_gap = 1
        self.x_width = int((rect[2] - rect[0]) / cols) - self.x_gap
        self.y_gap = 6
        self.y_height = int((rect[3] - rect[1]) / rows) - self.y_gap

        # Render the base keyboard
        self.draw.rectangle(self.rect, outline=0, fill=0)

        self.additonal_key_compact_font = View.ROBOTOCONDENSED_BOLD_18

        self.cur_x = self.x_start
        self.cur_y = self.y_start
        for row_num, line in enumerate(self.lines):
            self.cur_x = 0
            for letter in line:
                self._render_key(letter, is_selected=False)
                self.cur_x += self.x_width + self.x_gap
            self.cur_y += self.y_height + self.y_gap

        View.DispShowImage()

        for j, line in enumerate(self.lines):
            if selected_char in line:
                self.selected = {"x": line.index(selected_char), "y": j}

        # Render the initial highlighted character
        self.update_from_input(input=None)



    def _render_key(self, letter, is_selected=False):
        # Import here to avoid circular import problems
        from seedsigner.views import View

        font = self.font
        key_size = 1
        if letter in Keyboard.ADDITIONAL_KEYS:
            if Keyboard.ADDITIONAL_KEYS[letter]["font"] == Keyboard.COMPACT_KEY_FONT:
                font = self.additonal_key_compact_font
            key_size = Keyboard.ADDITIONAL_KEYS[letter]["key_size"]

        if is_selected:
            rect_color = View.color
            font_color = "black"
        else:
            rect_color = "black"
            font_color = View.color

        self.draw.rectangle((self.cur_x, self.cur_y, self.cur_x + self.x_width * key_size, self.cur_y + self.y_height), outline="#333", fill=rect_color)
        tw, th = self.draw.textsize(letter, font=font)
        self.draw.text((self.cur_x + int((self.x_width * key_size - tw) / 2), self.cur_y + int((self.y_height - th)/2)), letter, fill=font_color, font=font)



    def update_from_input(self, input, auto_wrap=[WRAP_TOP, WRAP_BOTTOM, WRAP_LEFT, WRAP_RIGHT], enter_from=None):
        """
            Managing code must handle its own input/update loop since other action buttons
            will be active on the same screen outside of the keyboard rect (e.g. "Ok",
            "Back", etc). Pass relevant input here to update the keyboard.

            `auto_wrap` specifies which edges the keyboard is allowed to loop back when
            navigating past the end.

            `enter_from` tells the keyboard that the external UI has caused a loop back
            navigation.
            (e.g. pressing up from a submit button below the keyboard = ENTER_BOTTOM)

            Returns the character currently highlighted or one of the EXIT_* codes if the
            user has navigated off the keyboard past an edge that is not in `auto_wrap`.
        """
        # Import here to avoid circular import problems
        from seedsigner.views import View

        letter = self.lines[self.selected["y"]][self.selected["x"]]

        # Before we update, undo our previously self.selected letter
        self._render_key(letter, is_selected=False)

        if input == B.KEY_RIGHT:
            self.selected["x"] += 1
            if self.selected["x"] == len(self.lines[self.selected["y"]]):
                if Keyboard.WRAP_RIGHT in auto_wrap:
                    # Loop it back to the right side
                    self.selected["x"] = 0
                else:
                    # Notify controlling loop that we've left the keyboard
                    return Keyboard.EXIT_RIGHT

        elif input == B.KEY_LEFT:
            self.selected["x"] -= 1
            if self.selected["x"] < 0:
                if Keyboard.WRAP_LEFT in auto_wrap:
                    # Loop it back to the left side
                    self.selected["x"] = len(self.lines[self.selected["y"]]) - 1
                else:
                    # Notify controlling loop that we've left the keyboard
                    return Keyboard.EXIT_LEFT

        elif input == B.KEY_DOWN:
            self.selected["y"] += 1
            if self.selected["y"] == len(self.lines):
                if Keyboard.WRAP_BOTTOM in auto_wrap:
                    # Loop it back to the top
                    self.selected["y"] = 0
                else:
                    # Notify controlling loop that we've left the keyboard
                    return Keyboard.EXIT_BOTTOM

            if self.selected["x"] >= len(self.lines[self.selected["y"]]):
                if Keyboard.WRAP_BOTTOM in auto_wrap:
                    # This line is too short to land here
                    self.selected["y"] = 0
                else:
                    # Notify controlling loop that we've left the keyboard
                    return Keyboard.EXIT_BOTTOM

        elif input == B.KEY_UP:
            self.selected["y"] -= 1
            if self.selected["y"] < 0:
                if Keyboard.WRAP_TOP in auto_wrap:
                    # Loop it back to the bottom
                    self.selected["y"] = len(self.lines) - 1
                else:
                    # Notify controlling loop that we've left the keyboard
                    return Keyboard.EXIT_TOP
            if self.selected["x"] >= len(self.lines[self.selected["y"]]):
                if Keyboard.WRAP_TOP in auto_wrap:
                    # This line is too short to land here
                    self.selected["y"] -= 1
                else:
                    # Notify controlling loop that we've left the keyboard
                    return Keyboard.EXIT_TOP

        # Render the newly self.selected letter
        self.cur_x = self.selected["x"] * (self.x_width + self.x_gap)
        self.cur_y = self.y_start + (self.selected["y"] * (self.y_height + self.y_gap))
        letter = self.lines[self.selected["y"]][self.selected["x"]]
        self._render_key(letter, is_selected=True)

        View.DispShowImage()

        return letter


