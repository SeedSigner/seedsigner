import math
import os
import pathlib

from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Tuple

from seedsigner.models import Singleton


# TODO: Remove all pixel hard coding
class GUIConstants:
    EDGE_PADDING = 8
    COMPONENT_PADDING = 8
    LIST_ITEM_PADDING = 4

    BACKGROUND_COLOR = "black"
    WARNING_COLOR = "#FFD60A"
    DIRE_WARNING_COLOR = "red"
    SUCCESS_COLOR = "#00dd00"
    BITCOIN_ORANGE = "#ff9416"
    ACCENT_COLOR = "orange"

    ICON_FONT_NAME__FONT_AWESOME = "Font_Awesome_6_Free-Solid-900"
    ICON_FONT_NAME__SEEDSIGNER = "seedsigner-glyphs"
    ICON_FONT_SIZE = 22
    ICON_INLINE_FONT_SIZE = 24
    ICON_LARGE_BUTTON_SIZE = 36
    ICON_PRIMARY_SCREEN_SIZE = 44

    TOP_NAV_TITLE_FONT_NAME = "OpenSans-SemiBold"
    TOP_NAV_TITLE_FONT_SIZE = 20
    TOP_NAV_HEIGHT = 48
    TOP_NAV_BUTTON_SIZE = 32

    BODY_FONT_NAME = "OpenSans-Regular"
    BODY_FONT_SIZE = 17
    BODY_FONT_MAX_SIZE = TOP_NAV_TITLE_FONT_SIZE
    BODY_FONT_MIN_SIZE = 15
    BODY_FONT_COLOR = "#f8f8f8"
    BODY_LINE_SPACING = COMPONENT_PADDING

    FIXED_WIDTH_FONT_NAME = "Inconsolata-Regular"
    FIXED_WIDTH_EMPHASIS_FONT_NAME = "Inconsolata-SemiBold"

    LABEL_FONT_SIZE = BODY_FONT_MIN_SIZE
    LABEL_FONT_COLOR = "#777"

    BUTTON_FONT_NAME = "OpenSans-SemiBold"
    BUTTON_FONT_SIZE = 18
    BUTTON_FONT_COLOR = "#e8e8e8"
    BUTTON_BACKGROUND_COLOR = "#2c2c2c"
    BUTTON_HEIGHT = 32
    BUTTON_SELECTED_FONT_COLOR = "black"



class FontAwesomeIconConstants:
    CAMERA = "\uf030"
    SOLID_CIRCLE_CHECK = "\uf058"
    CIRCLE = "\uf111"
    CIRCLE_CHEVRON_RIGHT = "\uf138"
    DICE = "\uf522"
    GEAR = "\uf013"
    KEY = "\uf084"
    KEYBOARD = "\uf11c"
    LOCK = "\uf023"
    MAP = "\uf279"
    PAPER_PLANE = "\uf1d8"
    PEN = "\uf304"
    PLUS = "+"
    POWER_OFF = "\uf011"
    ROTATE_RIGHT = "\uf2f9"
    SCREWDRIVER_WRENCH = "\uf7d9"
    SQUARE = "\uf0c8"
    SQUARE_CHECK = "\uf14a"
    TRIANGLE_EXCLAMATION = "\uf071"
    UNLOCK = "\uf09c"
    QRCODE = "\uf029"
    X = "\u0058"



class SeedSignerCustomIconConstants:
    LARGE_CHEVRON_LEFT = "\ue900"
    SMALL_CHEVRON_RIGHT = "\ue901"
    PAGE_DOWN = "\ue902"
    PAGE_UP = "\ue903"
    CIRCLE_X = "\ue904"
    CIRCLE_EXCLAMATION = "\ue905"
    CIRCLE_CHECK = "\ue906"
    FINGERPRINT = "\ue907"
    PATH = "\ue908"
    BITCOIN_LOGO = "\ue909"
    BITCOIN_LOGO_2 = "\ue90a"

    MIN_VALUE = LARGE_CHEVRON_LEFT
    MAX_VALUE = BITCOIN_LOGO_2



def calc_text_centering(font: ImageFont,
                        text: str,
                        is_text_centered: bool,
                        total_width: int,
                        total_height: int,
                        start_x: int = 0,
                        start_y: int = 0) -> Tuple[int, int]:
    # see: https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html#text-anchors

    # Gap between the starting coordinate and the first marking.
    offset_x, offset_y = font.getoffset(text)

    # Bounding box of the actual pixels rendered.
    (box_left, box_top, box_right, box_bottom) = font.getbbox(text, anchor='lt')

    # Ascender/descender are oversized ranges baked into the font.
    ascent, descent = font.getmetrics()

    # print(f"""----- "{text}" / {font.getname()} -----""")
    # print(f"offset_x: {offset_x} | offset_y: {offset_y})")
    # print(f"box_left: {box_left} |  box_top: {box_top} | box_right: {box_right} | box_bottom: {box_bottom}")
    # print(f"ascent: {ascent} | descent: {descent})")

    if is_text_centered:
        text_x = int((total_width - (box_right - offset_x)) / 2) - offset_x
    else:
        text_x = GUIConstants.COMPONENT_PADDING

    text_y = int((total_height - (ascent - offset_y)) / 2) - offset_y

    return (start_x + text_x, start_y + text_y)



def load_icon(icon_name: str, load_selected_variant: bool = False):
    icon_url = os.path.join(pathlib.Path(__file__).parent.resolve(), "..", "resources", "icons", icon_name)
    icon = Image.open(icon_url + ".png").convert("RGB")
    if not load_selected_variant:
        return icon
    else:
        icon_selected = Image.open(icon_url + "_selected.png").convert("RGB")
        return (icon, icon_selected)


def load_image(image_name: str):
    image_url = os.path.join(pathlib.Path(__file__).parent.resolve(), "..", "resources", "img", image_name)
    image = Image.open(image_url).convert("RGB")
    return image



class Fonts(Singleton):
    font_path = os.path.join(pathlib.Path(__file__).parent.resolve(), "..", "resources", "fonts")
    fonts = {}

    @classmethod
    def get_font(cls, font_name, size, file_extension: str = "ttf") -> ImageFont.FreeTypeFont:
        # Cache already-loaded fonts
        if font_name not in cls.fonts:
            cls.fonts[font_name] = {}
        
        if size not in cls.fonts[font_name]:
            try:
                cls.fonts[font_name][size] = ImageFont.truetype(os.path.join(cls.font_path, f"{font_name}.{file_extension}"), size)
            except OSError as e:
                if "cannot open resource" in str(e):
                    raise Exception(f"Font {font_name}.ttf not found: {repr(e)}")
                else:
                    raise e

        return cls.fonts[font_name][size]



class TextDoesNotFitException(Exception):
    pass



@dataclass
class BaseComponent:
    image_draw: ImageDraw = None
    canvas: Image = None

    def __post_init__(self):
        from seedsigner.gui import Renderer
        self.renderer: Renderer = Renderer.get_instance()
        self.canvas_width = self.renderer.canvas_width
        self.canvas_height = self.renderer.canvas_height

        if not self.image_draw:
            self.set_image_draw(self.renderer.draw)

        if not self.canvas:
            self.set_canvas(self.renderer.canvas)


    def set_image_draw(self, image_draw: ImageDraw):
        self.image_draw = image_draw

    def set_canvas(self, canvas: Image):
        self.canvas = canvas


    def render(self):
        raise Exception("render() not implemented in the child class!")



@dataclass
class TextArea(BaseComponent):
    """
        Not to be confused with an html <textarea>! This is a rect-delimited text
        display box that could be the main body content of a screen or a sub-zone
        of text within a more complicated page.

        Auto-calcs line breaks based on input text and font (somewhat naive; only
        breaks on spaces. Future enhancement could break on hyphens, too).

        Raises an Exception if the text won't fit in the given rect.

        Attrs with defaults must be listed last.
    """
    text: str = "My text content"
    width: int = None       # TODO: Implement autosize width?
    height: int = None      # None = special case: autosize to min height
    screen_x: int = 0
    screen_y: int = 0
    min_text_x: int = None
    background_color: str = "black"
    font_name: str = GUIConstants.BODY_FONT_NAME
    font_size: int = GUIConstants.BODY_FONT_SIZE
    font_color: str = GUIConstants.BODY_FONT_COLOR
    edge_padding: int = GUIConstants.EDGE_PADDING
    is_text_centered: bool = True
    supersampling_factor: int = 1
    auto_line_break: bool = True


    def __post_init__(self):
        super().__post_init__()

        if not self.width:
            self.width = self.canvas_width

        if self.font_size < 18 and (not self.supersampling_factor or self.supersampling_factor == 1):
            self.supersampling_factor = 2

        self.font = Fonts.get_font(self.font_name, int(self.supersampling_factor * self.font_size))
        self.supersampled_width = self.supersampling_factor * self.width
        if self.height is None:
            self.supersampled_height = None
        else:
            self.supersampled_height = self.supersampling_factor * self.height
        self.line_spacing = GUIConstants.BODY_LINE_SPACING

        # We have to figure out if and where to make line breaks in the text so that it
        #   fits in its bounding rect (plus accounting for edge padding) using its given
        #   font.
        # Measure from left baseline ("ls")
        (left, top, full_text_width, bottom) = self.font.getbbox(self.text, anchor="ls")
        self.text_height = -1 * top
        self.bbox_height = self.text_height + bottom

        # Stores each line of text and its rendering starting x-coord
        self.text_lines = []
        self.text_width = 0
        def _add_text_line(text, width):
            if self.is_text_centered:
                text_x = int((self.supersampled_width - width) / 2)
            else:
                text_x = self.supersampling_factor * self.edge_padding
            if self.min_text_x is not None and text_x < self.min_text_x:
                text_x = self.min_text_x
            self.text_lines.append({"text": text, "text_x": text_x})

            if width > self.text_width:
                self.text_width = width

        if not self.auto_line_break or full_text_width < self.supersampled_width - (2 * self.edge_padding * self.supersampling_factor):
            # The whole text fits on one line
            _add_text_line(self.text, full_text_width)

            if self.height is None:
                self.text_y = self.text_height
                self.supersampled_height = self.bbox_height
                self.height = int(self.bbox_height / self.supersampling_factor)
            else:
                # Vertical starting point calc is easy in this case
                self.text_y = self.text_height + int((self.supersampled_height - self.text_height)/2)
            
            self.text_width = full_text_width

        else:
            # Have to calc how to break text into multiple lines
            def _binary_len_search(min_index, max_index):
                # Try the middle of the range
                index = math.ceil((max_index + min_index) / 2)
                if index == 0:
                    # Handle edge case where there's only one word in the last line
                    index = 1

                tw, th = self.font.getsize(" ".join(words[0:index]))

                if tw > self.supersampled_width - (2 * self.edge_padding * self.supersampling_factor):
                    # Candidate line is still too long. Restrict search range down.
                    if min_index + 1 == index:
                        # There's no room left to search
                        index -= 1
                    return _binary_len_search(min_index, index)
                elif index == max_index:
                    # We have converged
                    return (index, tw)
                else:
                    # Candidate line is possibly shorter than necessary.
                    return _binary_len_search(index, max_index)
            
            if len(self.text.split()) == 1:
                # No whitespace chars to split on!
                raise TextDoesNotFitException("Text cannot fit in target rect with this font/size")

            for line in self.text.split("\n"):
                words = line.split()
                if not words:
                    # It's a blank line
                    _add_text_line("", 0)
                else:
                    while words:
                        (index, tw) = _binary_len_search(0, len(words))
                        _add_text_line(" ".join(words[0:index]), tw)
                        words = words[index:]

            # TODO: Don't render blank lines as full height
            total_text_height = self.bbox_height * len(self.text_lines) + self.line_spacing * (len(self.text_lines) - 1)
            if self.height is None:
                # Autoscale height to text lines
                self.supersampled_height = total_text_height
                self.height = int(self.supersampled_height / self.supersampling_factor)
                self.text_y = self.text_height

            else:
                if total_text_height > self.height * self.supersampling_factor + 2*GUIConstants.COMPONENT_PADDING * self.supersampling_factor:
                    raise TextDoesNotFitException("Text cannot fit in target rect with this font/size")

                # Vertically center the multiline text's starting point
                self.supersampled_height = self.height * self.supersampling_factor
                self.text_y = self.text_height + int((self.supersampled_height - total_text_height)/2)

        # Make sure the width/height that get referenced outside this obj are
        #   specified and restored to their normal scaling factor.
        self.width = int(self.text_width / self.supersampling_factor)
        self.text_height = int(self.text_height / self.supersampling_factor)


    def render(self):
        # Render to a temp img scaled up by self.supersampling_factor, then resize down
        #   with bicubic resampling.
        # TODO: Store resulting super-sampled image as a member var in __post_init__ and 
        # just re-paste it here.
        img = Image.new("RGB", (self.supersampled_width, self.supersampled_height), self.background_color)
        draw = ImageDraw.Draw(img)
        cur_y = self.text_y

        # print(f"self.bbox_height: {self.bbox_height}")
        for line in self.text_lines:
            draw.text((line["text_x"], cur_y), line["text"], fill=self.font_color, font=self.font, anchor="ls")
            cur_y += self.bbox_height + self.line_spacing

        resized = img.resize((int(self.supersampled_width / self.supersampling_factor), self.height), Image.LANCZOS)
        resized = resized.filter(ImageFilter.SHARPEN)
        self.canvas.paste(resized, (self.screen_x, self.screen_y))



@dataclass
class Icon(BaseComponent):
    screen_x: int = 0
    screen_y: int = 0
    icon_name: str = SeedSignerCustomIconConstants.BITCOIN_LOGO
    icon_size: int = GUIConstants.ICON_FONT_SIZE
    icon_color: str = GUIConstants.BODY_FONT_COLOR

    def __post_init__(self):
        super().__post_init__()

        if SeedSignerCustomIconConstants.MIN_VALUE <= self.icon_name and self.icon_name <= SeedSignerCustomIconConstants.MAX_VALUE:
            self.icon_font = Fonts.get_font(GUIConstants.ICON_FONT_NAME__SEEDSIGNER, self.icon_size, file_extension="otf")
        else:
            self.icon_font = Fonts.get_font(GUIConstants.ICON_FONT_NAME__FONT_AWESOME, self.icon_size, file_extension="otf")
        
        # Set width/height based on exact pixels that are rendered
        (left, top, self.width, self.height) = self.icon_font.getbbox(self.icon_name, anchor="lt")


    def render(self):
        self.image_draw.text(
            (self.screen_x, self.screen_y),
            text=self.icon_name,
            font=self.icon_font,
            fill=self.icon_color,
            anchor="lt",  # left, top anchor to avoid "ascender" gap space
        )



@dataclass
class IconTextLine(BaseComponent):
    """
        Renders an icon next to a label/value pairing. Icon is optional as is label.
    """
    height: int = None
    icon_name: str = None
    icon_size: int = GUIConstants.ICON_FONT_SIZE
    icon_color: str = GUIConstants.BODY_FONT_COLOR
    label_text: str = None
    value_text: str = "73c5da0a"
    font_name: str = GUIConstants.BODY_FONT_NAME
    font_size: int = GUIConstants.BODY_FONT_SIZE
    is_text_centered: bool = False
    auto_line_break: bool = False
    screen_x: int = 0
    screen_y: int = 0

    def __post_init__(self):
        super().__post_init__()

        if self.height is not None and self.label_text:
            raise Exception("Can't currently support vertical auto-centering and label text")

        if self.icon_name:
            self.icon = Icon(
                image_draw=self.image_draw,
                canvas=self.canvas,
                screen_x=self.screen_x,
                screen_y=0,    # We'll update this later below
                icon_name=self.icon_name,
                icon_size=self.icon_size,
                icon_color=self.icon_color
            )

            self.icon_horizontal_spacer = int(GUIConstants.COMPONENT_PADDING/2)

            text_screen_x = self.screen_x + self.icon.width + self.icon_horizontal_spacer
        else:
            text_screen_x = self.screen_x

        if self.label_text:
            self.label_textarea = TextArea(
                image_draw=self.image_draw,
                canvas=self.canvas,
                text=self.label_text,
                font_size=GUIConstants.BODY_FONT_SIZE - 2,
                font_color="#666",
                edge_padding=0,
                is_text_centered=False,
                auto_line_break=False,
                screen_x=text_screen_x,
                screen_y=self.screen_y,
            )
        else:
            self.label_textarea = None        
        
        value_textarea_screen_y = self.screen_y
        if self.label_text:
            label_padding_y = GUIConstants.COMPONENT_PADDING
            value_textarea_screen_y += self.label_textarea.text_height + label_padding_y

        self.value_textarea = TextArea(
            image_draw=self.image_draw,
            canvas=self.canvas,
            height=self.height,
            text=self.value_text,
            font_name=self.font_name,
            font_size=self.font_size,
            edge_padding=0,
            is_text_centered=False,
            auto_line_break=self.auto_line_break,
            screen_x=text_screen_x,
            screen_y=value_textarea_screen_y,
        )

        if self.label_text:
            if not self.height:
                self.height = self.label_textarea.height + label_padding_y + self.value_textarea.height
            max_textarea_width = max(self.label_textarea.width, self.value_textarea.width)
        else:
            if not self.height:
                self.height = self.value_textarea.height
            max_textarea_width = self.value_textarea.width
        
        # Now we can update the icon's y position
        if self.icon_name:
            icon_y = self.screen_y + int((self.height - self.icon.height)/2)
            self.icon.screen_y = icon_y
        
        if self.is_text_centered:
            if self.icon_name:
                total_width = max_textarea_width + self.icon.width + self.icon_horizontal_spacer
                self.icon.screen_x = self.screen_x + int((self.canvas_width - self.screen_x - total_width) / 2)
                if self.label_text:
                    self.label_textarea.screen_x = self.icon.screen_x + self.icon.width + self.icon_horizontal_spacer
                self.value_textarea.screen_x = self.icon.screen_x + self.icon.width + self.icon_horizontal_spacer
            else:
                if self.label_text:
                    self.label_textarea.screen_x = self.screen_x + int((self.canvas_width - self.screen_x - max_textarea_width + (max_textarea_width - self.label_textarea.width))/2)
                self.value_textarea.screen_x = self.screen_x + int((self.canvas_width - self.screen_x - max_textarea_width + (max_textarea_width - self.value_textarea.width))/2)


    def render(self):
        if self.label_textarea:
            self.label_textarea.render()
        self.value_textarea.render()

        if self.icon_name:
            self.icon.render()



@dataclass
class FormattedAddress(BaseComponent):
    """
        Display a Bitcoin address in a "{first 7} {middle} {last 7}" formatted view with
        a possible/likely line break in the middle and using a fixed-width font:

        bc1q567 abcdefg1234567abcdefg
        1234567abcdefg1234567 1234567

        single sig taproot:       62 chars
        multisig native segwit:   62 chars
        multisig nested segwit:   34 chars
        single sig native segwit: 42 chars

        * max_lines: forces truncation on long addresses to fit
    """
    width: int = 0
    screen_x: int = 0
    screen_y: int = 0
    address: str = None
    max_lines: int = None
    font_name: str = GUIConstants.FIXED_WIDTH_FONT_NAME
    font_size: int = 24
    font_accent_color: str = GUIConstants.ACCENT_COLOR
    font_base_color: str = GUIConstants.LABEL_FONT_COLOR

    def __post_init__(self):
        super().__post_init__()
        if self.width == 0:
            self.width = self.renderer.canvas_width
        
        self.font = Fonts.get_font(self.font_name, self.font_size)
        self.accent_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, self.font_size)

        # Fixed width font means we only have to measure one max-height character
        char_width, char_height = self.font.getsize("Q")

        n = 7
        display_str = f"{self.address[:n]} {self.address[n:-1*n]} {self.address[-1*n:]}"
        self.text_params = []
        cur_y = 0

        if self.max_lines == 1:
            addr_lines_x = int((self.width - char_width*(2*n + 3))/2)
            # Can only show first/last n truncated
            self.text_params.append((
                (addr_lines_x, cur_y),
                display_str.split()[0],
                self.font_accent_color,
                self.accent_font
            ))
            self.text_params.append((
                (
                    addr_lines_x + char_width*n,
                    cur_y
                ),
                "...",
                self.font_base_color,
                self.font
            ))
            self.text_params.append((
                (
                    addr_lines_x + char_width*(n + 3),
                    cur_y
                ),
                display_str.split()[2],
                self.font_accent_color,
                self.accent_font
            ))
            cur_y += char_height

        else:
            max_chars_per_line = math.floor(self.width / char_width)
            num_lines = math.ceil(len(display_str)/max_chars_per_line)
            
            # Recalc chars per line to even out all x lines to the same width
            max_chars_per_line  = math.ceil(len(display_str) / num_lines)

            remaining_display_str = display_str
            addr_lines_x = self.screen_x + int((self.width - char_width*max_chars_per_line) / 2)
            for i in range(0, num_lines):
                cur_str = remaining_display_str[:max_chars_per_line]
                if i == 0:
                    # Split cur_str into two sections to highlight first_n
                    self.text_params.append((
                        (addr_lines_x, cur_y),
                        cur_str.split()[0],
                        self.font_accent_color,
                        self.accent_font
                    ))
                    self.text_params.append((
                        (
                            addr_lines_x + char_width*(n+1),
                            cur_y
                        ),
                        cur_str.split()[1],
                        self.font_base_color,
                        self.font
                    ))

                elif i == num_lines - 1:
                    # Split cur_str into two sections to highlight last_n
                    self.text_params.append((
                        (
                            addr_lines_x,
                            cur_y
                        ),
                        cur_str.split()[0],
                        self.font_base_color,
                        self.font
                    ))
                    self.text_params.append((
                        (
                            addr_lines_x + char_width*(len(cur_str) - (n)),
                            cur_y
                        ),
                        cur_str.split()[1],
                        self.font_accent_color,
                        self.accent_font
                    ))

                elif self.max_lines and i == self.max_lines - 1:
                    # We can't fit the whole address. Have to truncate here and highlight the
                    # last_n.
                    self.text_params.append((
                        (
                            addr_lines_x,
                            cur_y
                        ),
                        cur_str[:-1*n - 3] + "...",
                        self.font_base_color,
                        self.font
                    ))
                    self.text_params.append((
                        (
                            addr_lines_x + char_width*(len(cur_str) - (n)),
                            cur_y
                        ),
                        self.address[-1*n:],
                        self.font_accent_color,
                        self.accent_font
                    ))
                    cur_y += char_height
                    break

                else:
                    # This is a middle line with no highlighted section
                    self.text_params.append((
                        (
                            addr_lines_x,
                            cur_y
                        ),
                        cur_str,
                        self.font_base_color,
                        self.font
                    ))

                remaining_display_str = remaining_display_str[max_chars_per_line:]
                cur_y += char_height
        
        self.height = cur_y
    

    def render(self):
        for p in self.text_params:
            self.image_draw.text((p[0][0], p[0][1] + self.screen_y), text=p[1], fill=p[2], font=p[3])



@dataclass
class Button(BaseComponent):
    # TODO: Rename the seedsigner.helpers.Buttons class (to Inputs?) to reduce confusion
    # with this GUI component.
    """
        Attrs with defaults must be listed last.
    """
    text: str = "Button Label"
    screen_x: int = 0
    screen_y: int = 0
    scroll_y: int = 0
    width: int = None
    height: int = None
    icon_name: str = None   # Optional icon to accompany the text
    icon_size: int = GUIConstants.ICON_INLINE_FONT_SIZE
    icon_color: str = GUIConstants.BUTTON_FONT_COLOR
    selected_icon_color: str = "black"
    icon_y_offset: int = 0
    is_icon_inline: bool = True    # True = render next to text; False = render centered above text
    text_y_offset: int = 0
    background_color: str = GUIConstants.BUTTON_BACKGROUND_COLOR
    selected_color: str = GUIConstants.ACCENT_COLOR
    font_name: str = GUIConstants.BUTTON_FONT_NAME
    font_size: int = GUIConstants.BUTTON_FONT_SIZE
    font_color: str = GUIConstants.BUTTON_FONT_COLOR
    selected_font_color: str = GUIConstants.BUTTON_SELECTED_FONT_COLOR
    is_text_centered: bool = True
    is_selected: bool = False


    def __post_init__(self):
        super().__post_init__()

        if not self.width:
            self.width = self.canvas_width

        if not self.height:
            self.height = GUIConstants.BUTTON_HEIGHT
        
        if not self.icon_color:
            self.icon_color = GUIConstants.BUTTON_FONT_COLOR

        self.font = Fonts.get_font(self.font_name, self.font_size)

        if self.text:
            if self.is_text_centered:
                self.text_x = int(self.width/2)
                self.text_anchor = "ms"  # centered horizontally, baseline
            else:
                self.text_x = GUIConstants.COMPONENT_PADDING
                self.text_anchor = "ls"  # left, baseline
            
            # Calc true pixel height (any anchor from "baseline" will work)
            (left, top, self.text_width, bottom) = self.font.getbbox(self.text, anchor="ls")
            # print(f"left: {left} |  top: {top} | right: {self.text_width} | bottom: {bottom}")

            # Note: "top" is negative when measured from a "baseline" anchor
            self.text_height = -1 * top

            # TODO: Only apply screen_y at render
            if self.text_y_offset:
                self.text_y = self.text_y_offset + self.text_height
            else:
                self.text_y = self.height - int((self.height - self.text_height)/2)

        # Preload the icon and its "_selected" variant
        if self.icon_name:
            icon_padding = GUIConstants.COMPONENT_PADDING
            self.icon = Icon(icon_name=self.icon_name, icon_size=self.icon_size, icon_color=self.icon_color)
            self.icon_selected = Icon(icon_name=self.icon_name, icon_size=self.icon_size, icon_color=self.selected_icon_color)

            if self.is_icon_inline:
                # TODO: Only apply screen_* at render
                if self.is_text_centered:
                    # Shift the text's centering
                    if self.text:
                        self.text_x += int((self.icon.width + icon_padding) / 2)
                        self.icon_x = self.text_x - int(self.text_width/2) - (self.icon.width + icon_padding)
                    else:
                        self.icon_x = math.ceil((self.width - self.icon.width)/2)

                else:
                    if self.text:
                        self.text_x += self.icon.width + icon_padding
                    self.icon_x = GUIConstants.COMPONENT_PADDING

            else:
                self.icon_x = int((self.width - self.icon.width) / 2)

            if self.icon_y_offset:
                self.icon_y = self.icon_y_offset
            else:
                # print(f"self.icon_name: {self.icon_name} | self.height: {self.height} | self.icon.height: {self.icon.height}")
                # print(f"\t\tself.width: {self.width} | self.icon.width: {self.icon.width}")
                self.icon_y = math.ceil((self.height - self.icon.height)/2)

            self.icon.screen_x = self.icon_x
            self.icon_selected.screen_x = self.icon_x


    def render(self):
        if self.is_selected:
            background_color = self.selected_color
            font_color = self.selected_font_color
        else:
            background_color = self.background_color
            font_color = self.font_color

        self.image_draw.rounded_rectangle((self.screen_x, self.screen_y - self.scroll_y, self.screen_x + self.width, self.screen_y + self.height - self.scroll_y), fill=background_color, radius=8)

        if self.text:
            self.image_draw.text(
                (self.screen_x + self.text_x, self.screen_y + self.text_y - self.scroll_y),
                self.text,
                fill=font_color,
                font=self.font,
                anchor=self.text_anchor
            )

        if self.icon_name:
            icon = self.icon
            if self.is_selected:
                icon = self.icon_selected
            icon.screen_y = self.screen_y + self.icon_y - self.scroll_y
            icon.screen_x = self.screen_x + self.icon_x
            icon.render()


@dataclass
class CheckedSelectionButton(Button):
    is_checked: bool = False

    def __post_init__(self):
        self.is_text_centered = False
        self.icon_name = FontAwesomeIconConstants.SOLID_CIRCLE_CHECK
        self.icon_color = "#00dd00"
        super().__post_init__()

        if not self.is_checked:
            # Remove the checkmark icon but leave the text_x spacing as-is
            self.icon_name = None
            self.icon = None
            self.icon_selected = None



@dataclass
class CheckboxButton(Button):
    is_checked: bool = False

    def __post_init__(self):
        self.is_text_centered = False
        if self.is_checked:
            self.icon_name = FontAwesomeIconConstants.SQUARE_CHECK
            self.icon_color = "#00dd00"
        else:
            self.icon_name = FontAwesomeIconConstants.SQUARE
            self.icon_color = GUIConstants.BODY_FONT_COLOR
        super().__post_init__()



@dataclass
class IconButton(Button):
    """
        A button that is just an icon (e.g. the BACK arrow)
    """
    icon_size: int = GUIConstants.ICON_INLINE_FONT_SIZE
    text: str = None
    is_icon_inline: bool = False



@dataclass
class LargeIconButton(IconButton):
    """
        A button that is primarily a big icon (e.g. the Home screen buttons) w/text below
        the icon.
    """
    icon_size: int = GUIConstants.ICON_LARGE_BUTTON_SIZE
    icon_y_offset: int = GUIConstants.COMPONENT_PADDING



@dataclass
class TopNav(BaseComponent):
    text: str = "Screen Title"
    width: int = None
    height: int = GUIConstants.TOP_NAV_HEIGHT
    background_color: str = GUIConstants.BACKGROUND_COLOR
    icon_name: str = None
    icon_color: str = GUIConstants.BODY_FONT_COLOR
    font_name: str = GUIConstants.TOP_NAV_TITLE_FONT_NAME
    font_size: int = GUIConstants.TOP_NAV_TITLE_FONT_SIZE
    font_color: str = "#fcfcfc"
    show_back_button: bool = True
    show_power_button: bool = False
    is_selected: bool = False


    def __post_init__(self):
        super().__post_init__()
        if not self.width:
            self.width = self.canvas_width

        self.font = Fonts.get_font(self.font_name, self.font_size)

        if self.show_back_button:
            self.left_button = IconButton(
                icon_name=SeedSignerCustomIconConstants.LARGE_CHEVRON_LEFT,
                icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=GUIConstants.EDGE_PADDING,
                width=GUIConstants.TOP_NAV_BUTTON_SIZE,
                height=GUIConstants.TOP_NAV_BUTTON_SIZE,
            )

        if self.show_power_button:
            self.right_button = IconButton(
                icon_name=FontAwesomeIconConstants.POWER_OFF,
                icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
                screen_x=self.width - GUIConstants.TOP_NAV_BUTTON_SIZE - GUIConstants.EDGE_PADDING,
                screen_y=GUIConstants.EDGE_PADDING,
                width=GUIConstants.TOP_NAV_BUTTON_SIZE,
                height=GUIConstants.TOP_NAV_BUTTON_SIZE,
            )

        min_x = 0
        if self.show_back_button:
            # Don't let the title intrude on the BACK button
            min_x = self.left_button.screen_x + self.left_button.width + GUIConstants.COMPONENT_PADDING

        if self.icon_name:
            self.title = IconTextLine(
                screen_x=0,
                screen_y=0,
                height=self.height,
                icon_name=self.icon_name,
                icon_color=self.icon_color,
                icon_size=GUIConstants.ICON_FONT_SIZE + 4,
                value_text=self.text,
                is_text_centered=True,
                font_name=self.font_name,
                font_size=self.font_size,
            )
        else:
            self.title = TextArea(
                screen_x=0,
                screen_y=0,
                min_text_x=min_x,
                height=self.height,
                text=self.text,
                is_text_centered=True,
                font_name=self.font_name,
                font_size=self.font_size,
            )


    @property
    def selected_button(self):
        from .screens import RET_CODE__BACK_BUTTON, RET_CODE__POWER_BUTTON
        if not self.is_selected:
            return None
        if self.show_back_button:
            return RET_CODE__BACK_BUTTON
        if self.show_power_button:
            return RET_CODE__POWER_BUTTON


    def render(self):
        self.title.render()
        if self.show_back_button:
            self.left_button.is_selected = self.is_selected
            self.left_button.render()
        if self.show_power_button:
            self.right_button.is_selected = self.is_selected
            self.right_button.render()

        # self.image_draw.text(
        #     (self.text_x, self.text_y),
        #     self.text,
        #     font=self.font,
        #     fill=self.font_color,
        #     stroke_width=1,
        #     stroke_fill=GUIConstants.BACKGROUND_COLOR,
        # )



def linear_interp(a, b, t):
    return (
        int((1.0 - t)*a[0] + t*b[0]),
        int((1.0 - t)*a[1] + t*b[1])
    )



def calc_bezier_curve(p1: Tuple[int,int], p2: Tuple[int,int], p3: Tuple[int,int], segments: int) -> List[Tuple[Tuple[int,int], Tuple[int,int]]]:
    """
        Calculates the points of a bezier curve between points p1 and p3 with p2 as a
        control point influencing the amount of curve deflection.

        Bezier curve calcs start with two trivial linear interpolations of each line
        segment:
        L1 = p1 to p2 = (1 - t)*p1 + t*p2
        L2 = p2 to p3 = (1 - t)*p2 + t*p3

        And then interpolate over the two line segments
        Q1 = (1 - t)*L1(t) + t*L2(t)
    """
    t_step = 1.0 / segments

    points = [p1]
    for i in range(1, segments + 1):
        t = t_step * i
        if i == segments:
            points.append(p3)
            break
        l1_t = linear_interp(p1, p2, t)
        l2_t = linear_interp(p2, p3, t)
        q1 = linear_interp(l1_t, l2_t, t)
        points.append(q1)
    
    return points

