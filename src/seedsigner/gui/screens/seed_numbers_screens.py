from dataclasses import dataclass
from gettext import gettext as _

from PIL import Image, ImageDraw

from seedsigner.gui.components import (
    Fonts,
    GUIConstants,
    IconButton,
    SeedSignerIconConstants,
)
from seedsigner.gui.keyboard import Keyboard
from seedsigner.gui.screens.screen import (
    BaseTopNavScreen,
    ButtonListScreen,
    RET_CODE__BACK_BUTTON,
    WarningEdgesMixin,
)
from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.helpers.index_bits import (
    BIT_COUNT,
    BIT_WEIGHTS,
    bits_to_index,
    format_index1,
    index_to_bits,
    is_valid_index1,
)
from seedsigner.models.seed import Seed


BIT_BOX = 14
BIT_GAP = 3
BIT_BORDER = 3
BIT_GROUP_EXTRA = 8
BIT_LABEL_SIZE = 20
NUMBER_FONT_SIZE = 20
NUMBER_PAD_X = 6
NUMBER_PAD_Y = 6
NUMBER_BITS_GAP = 16


def _bit_label_font():
    return Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, BIT_LABEL_SIZE)


def _word_font():
    return Fonts.get_font(
        GUIConstants.get_top_nav_title_font_name(),
        GUIConstants.get_top_nav_title_font_size() + 2,
    )


def _number_font():
    return Fonts.get_font(
        GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
        NUMBER_FONT_SIZE
    )


def _bit_row_width():
    return (
        BIT_COUNT * BIT_BOX
        + (BIT_COUNT - 1) * BIT_GAP
        + ((BIT_COUNT - 1) // 4) * BIT_GROUP_EXTRA
    )


def _bit_x(x0, i):
    return x0 + i * (BIT_BOX + BIT_GAP) + (i // 4) * BIT_GROUP_EXTRA


def _bit_color(on, focused=False):
    if focused:
        return GUIConstants.ACCENT_COLOR
    if on:
        return GUIConstants.BODY_FONT_COLOR
    return GUIConstants.LABEL_FONT_COLOR


def _bit_label_height(font):
    left, top, right, bottom = font.getbbox("2048")
    return (right - left) + 2


def _number_text(index1):
    return format_index1(index1 or 0)


def _number_badge_size(font, text):
    left, top, right, bottom = font.getbbox(text, anchor="ls")
    return (right - left) + NUMBER_PAD_X * 2, -top + NUMBER_PAD_Y * 2


def _draw_number_word_row(draw, canvas_width, y, index1, word, valid):
    font = _number_font()
    text = _number_text(index1)
    box_w, box_h = _number_badge_size(font, text)
    word_font = _word_font()
    wl, wt, wr, wb = word_font.getbbox(word if word else " ", anchor="ls")
    x0 = (canvas_width - (box_w + GUIConstants.COMPONENT_PADDING + (wr - wl))) // 2
    draw.rounded_rectangle(
        (x0, y, x0 + box_w, y + box_h),
        radius=4,
        fill=GUIConstants.BUTTON_BACKGROUND_COLOR,
    )
    draw.text(
        (x0 + box_w // 2, y + box_h // 2),
        text,
        fill=GUIConstants.INFO_COLOR if valid else GUIConstants.LABEL_FONT_COLOR,
        font=font,
        anchor="mm",
    )
    draw.text(
        (x0 + box_w + GUIConstants.COMPONENT_PADDING, y + box_h // 2),
        word if word else "",
        fill=GUIConstants.BODY_FONT_COLOR if valid else GUIConstants.LABEL_FONT_COLOR,
        font=word_font,
        anchor="lm",
    )
    return box_h




def _paste_rotated_label(target, text, font, fill, cx, top_y):
    left, top, right, bottom = font.getbbox(text)
    tw, th = right - left, bottom - top
    img = Image.new("RGBA", (tw + 2, th + 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((1 - left, 1 - top), text, font=font, fill=fill)
    rot = img.rotate(90, expand=True)
    target.paste(rot, (cx - rot.width // 2, top_y), rot)
    return rot.height


def _draw_bit_row(draw, target, canvas_width, y, bits, focused_index=None, label_font=None):
    x0 = (canvas_width - _bit_row_width()) // 2
    for i, on in enumerate(bits):
        x = _bit_x(x0, i)
        focused = focused_index is not None and i == focused_index
        color = _bit_color(on, focused)
        draw.ellipse(
            (x, y, x + BIT_BOX, y + BIT_BOX),
            outline=color,
            fill=GUIConstants.BODY_FONT_COLOR if on else GUIConstants.BACKGROUND_COLOR,
            width=BIT_BORDER,
        )
        if label_font:
            _paste_rotated_label(
                target,
                str(BIT_WEIGHTS[i]),
                label_font,
                color,
                x + BIT_BOX // 2,
                y + BIT_BOX + NUMBER_BITS_GAP,
            )
    return y + BIT_BOX


@dataclass
class SeedNumbersEntryScreen(BaseTopNavScreen):
    """Enter one mnemonic word as a 1–2048 index (numbers or 12-bit row)."""

    mode: str = "binary"  # "binary" | "numbers"
    wordlist: list = None
    initial_word: str = None

    def __post_init__(self):
        super().__post_init__()
        if self.wordlist is None:
            self.wordlist = Seed.get_wordlist()

        self.bits = [False] * BIT_COUNT
        self.bit_index = 0
        self.digits = ""

        right_panel_buttons_width = 60
        self.save_button = IconButton(
            icon_name=SeedSignerIconConstants.CHECK,
            icon_color=GUIConstants.SUCCESS_COLOR,
            width=right_panel_buttons_width,
            screen_x=self.canvas_width - right_panel_buttons_width + GUIConstants.COMPONENT_PADDING,
            screen_y=(
                int(self.canvas_height - GUIConstants.BUTTON_HEIGHT) / 2 + 60
                if self.mode == "numbers"
                else self.canvas_height - GUIConstants.EDGE_PADDING - GUIConstants.BUTTON_HEIGHT
            ),
        )
        self.components.append(self.save_button)

        self.keyboard = None
        if self.mode == "numbers":
            keyboard_width = self.canvas_width - (
                GUIConstants.EDGE_PADDING
                + GUIConstants.COMPONENT_PADDING
                + right_panel_buttons_width
                - GUIConstants.COMPONENT_PADDING
            )
            kb_top = 118
            self.keyboard = Keyboard(
                draw=self.renderer.draw,
                charset="0123456789",
                rows=3,
                cols=5,
                rect=(
                    GUIConstants.EDGE_PADDING,
                    kb_top,
                    GUIConstants.EDGE_PADDING + keyboard_width,
                    self.canvas_height - GUIConstants.EDGE_PADDING,
                ),
                additional_keys=[Keyboard.KEY_BACKSPACE_5],
                auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
                render_now=False,
            )
            self.keyboard.set_selected_key(selected_letter="1")
        if self.initial_word and self.initial_word in self.wordlist:
            index1 = self.wordlist.index(self.initial_word) + 1
            self.digits = str(index1)
            self.bits = index_to_bits(index1)

    def _current_index(self) -> int:
        if self.mode == "numbers":
            if not self.digits:
                return 0
            try:
                return int(self.digits)
            except ValueError:
                return 0
        return bits_to_index(self.bits)

    def _sync_from_index(self, index1: int):
        if is_valid_index1(index1):
            self.bits = index_to_bits(index1)
        else:
            self.bits = [False] * BIT_COUNT

    def _set_top_nav_selected(self, selected: bool):
        self.top_nav.is_selected = selected
        self.is_input_in_top_nav = selected
        self.top_nav.render_buttons()

    def _render(self):
        super()._render()
        draw = self.renderer.draw
        index1 = self._current_index()
        valid = is_valid_index1(index1)
        word = self.wordlist[index1 - 1] if valid else ""

        if self.mode == "binary":
            label_font = _bit_label_font()
            badge_h = _number_badge_size(_number_font(), _number_text(index1))[1]
            label_h = _bit_label_height(label_font)
            total_h = badge_h + NUMBER_BITS_GAP + BIT_BOX + NUMBER_BITS_GAP + label_h
            available_top = self.top_nav.height
            save_reserve = GUIConstants.BUTTON_HEIGHT + GUIConstants.EDGE_PADDING
            available_h = self.canvas_height - available_top - save_reserve
            y_word = available_top + (available_h - total_h) // 2
            y_bits = y_word + badge_h + NUMBER_BITS_GAP
            _draw_number_word_row(draw, self.canvas_width, y_word, index1, word, valid)
            focused = None if self.top_nav.is_selected else self.bit_index
            _draw_bit_row(
                draw,
                self.renderer.canvas,
                self.canvas_width,
                y_bits,
                self.bits,
                focused_index=focused,
                label_font=label_font,
            )
        else:
            y_word = self.top_nav.height + 6
            badge_h = _draw_number_word_row(
                draw, self.canvas_width, y_word, index1, word, valid
            )
            _draw_bit_row(
                draw,
                self.renderer.canvas,
                self.canvas_width,
                y_word + badge_h + 9,
                self.bits,
            )

        if self.keyboard:
            self.keyboard.render_keys()
        self.save_button.render()
        self.renderer.show_image()

    def _commit_word(self):
        index1 = self._current_index()
        if not is_valid_index1(index1):
            return None
        return self.wordlist[index1 - 1]

    def _run(self):
        while True:
            input = self.hw_inputs.wait_for(HardwareButtonsConstants.ALL_KEYS)

            with self.renderer.lock:
                if input == HardwareButtonsConstants.KEY3:
                    word = self._commit_word()
                    if word:
                        self.save_button.is_selected = True
                        self.save_button.render()
                        self.renderer.show_image()
                        return word
                    continue

                if self.top_nav.is_selected:
                    if input == HardwareButtonsConstants.KEY_PRESS:
                        return RET_CODE__BACK_BUTTON
                    if input in [
                        HardwareButtonsConstants.KEY_LEFT,
                        HardwareButtonsConstants.KEY_RIGHT,
                    ]:
                        continue
                    if input not in [
                        HardwareButtonsConstants.KEY_UP,
                        HardwareButtonsConstants.KEY_DOWN,
                    ]:
                        continue

                    self._set_top_nav_selected(False)
                    if self.mode == "binary":
                        self._render()
                        continue
                    if input == HardwareButtonsConstants.KEY_DOWN:
                        input = Keyboard.ENTER_TOP
                    else:
                        input = Keyboard.ENTER_BOTTOM

                if self.mode == "binary":
                    if input in [
                        HardwareButtonsConstants.KEY_UP,
                        HardwareButtonsConstants.KEY_DOWN,
                    ]:
                        self._set_top_nav_selected(True)
                    elif input == HardwareButtonsConstants.KEY_LEFT:
                        self.bit_index = (self.bit_index + BIT_COUNT - 1) % BIT_COUNT
                    elif input == HardwareButtonsConstants.KEY_RIGHT:
                        self.bit_index = (self.bit_index + 1) % BIT_COUNT
                    elif input == HardwareButtonsConstants.KEY_PRESS:
                        self.bits[self.bit_index] = not self.bits[self.bit_index]
                    self._render()
                    continue

                ret_val = self.keyboard.update_from_input(input)

                if ret_val in Keyboard.EXIT_DIRECTIONS:
                    self._set_top_nav_selected(True)
                    self._render()
                    continue

                if input == HardwareButtonsConstants.KEY_PRESS:
                    if ret_val == Keyboard.KEY_BACKSPACE["code"]:
                        self.digits = self.digits[:-1]
                    elif ret_val in "0123456789":
                        if ret_val == "0" and not self.digits:
                            pass
                        elif len(self.digits) < 4:
                            self.digits += ret_val
                    self._sync_from_index(self._current_index())

                self._render()


@dataclass
class SeedNumbersBackupScreen(WarningEdgesMixin, ButtonListScreen):
    word_num: int = 1
    word: str = ""
    index1: int = 1
    is_bottom_list: bool = True
    status_color: str = GUIConstants.DIRE_WARNING_COLOR

    def __post_init__(self):
        super().__post_init__()

        label_font = _bit_label_font()
        label_h = _bit_label_height(label_font)
        badge_h = _number_badge_size(_number_font(), _number_text(self.index1))[1]

        body_y = self.top_nav.height
        body_h = self.buttons[0].screen_y - body_y
        body_img = Image.new("RGB", (self.canvas_width, body_h), GUIConstants.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(body_img)

        total_h = badge_h + NUMBER_BITS_GAP + BIT_BOX + NUMBER_BITS_GAP + label_h
        y_word = max((body_h - total_h) // 2, 0)
        _draw_number_word_row(draw, self.canvas_width, y_word, self.index1, self.word, True)
        _draw_bit_row(
            draw,
            body_img,
            self.canvas_width,
            y_word + badge_h + NUMBER_BITS_GAP,
            index_to_bits(self.index1),
            label_font=label_font,
        )

        self.paste_images.append((body_img, (0, body_y)))


@dataclass
class SeedNumbersBackupTestScreen(BaseTopNavScreen):
    """Four quiz choices: number plus its 12 bit circles."""

    options: list = None  # ["0274", ...]

    def __post_init__(self):
        self.show_back_button = False
        super().__post_init__()
        self.selected_button = 0
        self.number_font = _number_font()

    def _button_rects(self):
        n = len(self.options)
        gap = GUIConstants.LIST_ITEM_PADDING
        top = self.top_nav.height
        height = (self.canvas_height - top - 2 - (n - 1) * gap) // n
        rects = []
        y = top
        for _ in self.options:
            rects.append((
                GUIConstants.EDGE_PADDING,
                y,
                self.canvas_width - GUIConstants.EDGE_PADDING,
                y + height,
            ))
            y += height + gap
        return rects

    def _render(self):
        super()._render()
        draw = self.renderer.draw
        for i, (label, rect) in enumerate(zip(self.options, self._button_rects())):
            x1, y1, x2, y2 = rect
            selected = i == self.selected_button
            button_fill = GUIConstants.ACCENT_COLOR if selected else GUIConstants.BUTTON_BACKGROUND_COLOR
            draw.rounded_rectangle(rect, radius=4, fill=button_fill)

            index_color = GUIConstants.BUTTON_SELECTED_FONT_COLOR if selected else GUIConstants.BUTTON_FONT_COLOR
            on_color = GUIConstants.BUTTON_SELECTED_FONT_COLOR if selected else GUIConstants.BUTTON_FONT_COLOR
            off_color = GUIConstants.BUTTON_SELECTED_FONT_COLOR if selected else GUIConstants.LABEL_FONT_COLOR

            left, top, right, bottom = self.number_font.getbbox(label, anchor="ls")
            text_above = -top
            text_below = bottom
            box = 11
            gap = 2
            extra = 6
            border = 2
            between = 6
            button_h = y2 - y1
            content_h = text_above + text_below + between + box
            pad = max((button_h - content_h) // 2, 0)
            y_text = y1 + pad + text_above
            y_bits = y_text + text_below + between

            draw.text((self.canvas_width // 2, y_text), label, fill=index_color, font=self.number_font, anchor="ms")

            bits = index_to_bits(int(label.lstrip("#")))
            total = BIT_COUNT * box + (BIT_COUNT - 1) * gap + ((BIT_COUNT - 1) // 4) * extra
            x0 = (self.canvas_width - total) // 2
            for bit_i, on in enumerate(bits):
                x = x0 + bit_i * (box + gap) + (bit_i // 4) * extra
                draw.ellipse(
                    (x, y_bits, x + box, y_bits + box),
                    outline=on_color if on else off_color,
                    fill=on_color if on else button_fill,
                    width=border,
                )

        self.renderer.show_image()

    def _run(self):
        while True:
            input = self.hw_inputs.wait_for(
                [
                    HardwareButtonsConstants.KEY_UP,
                    HardwareButtonsConstants.KEY_DOWN,
                ] + HardwareButtonsConstants.KEYS__ANYCLICK
            )

            with self.renderer.lock:
                if input == HardwareButtonsConstants.KEY_UP:
                    self.selected_button = max(0, self.selected_button - 1)
                elif input == HardwareButtonsConstants.KEY_DOWN:
                    self.selected_button = min(len(self.options) - 1, self.selected_button + 1)
                elif input in HardwareButtonsConstants.KEYS__ANYCLICK:
                    return self.selected_button
                self._render()
