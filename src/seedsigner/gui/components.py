import logging
import math
import os
import pathlib
import re
from time import time

from dataclasses import dataclass
from decimal import Decimal
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Tuple

from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.models.singleton import Singleton

logger = logging.getLogger(__name__)


# TODO: Remove all pixel hard coding
class GUIConstants:
    EDGE_PADDING = 8
    COMPONENT_PADDING = 8
    LIST_ITEM_PADDING = 4

    BACKGROUND_COLOR = "black"
    WARNING_COLOR = "#FFD60A"
    DIRE_WARNING_COLOR = "#FF453A"
    SUCCESS_COLOR = "#30D158"
    INFO_COLOR = "#0084FF"
    ACCENT_COLOR = "#FF9F0A"
    BITCOIN_ORANGE = "#FF9416"
    TESTNET_COLOR = "#00F100"
    REGTEST_COLOR = "#00CAF1"
    GREEN_INDICATOR_COLOR = "#00FF00"
    INACTIVE_COLOR = "#414141"

    ICON_FONT_NAME__FONT_AWESOME = "Font_Awesome_6_Free-Solid-900"
    ICON_FONT_NAME__SEEDSIGNER = "seedsigner-icons"
    ICON_FONT_SIZE = 22
    ICON_INLINE_FONT_SIZE = 24
    ICON_LARGE_BUTTON_SIZE = 48
    ICON_TOAST_FONT_SIZE = 30
    ICON_PRIMARY_SCREEN_SIZE = 50

    TOP_NAV_TITLE_FONT_NAME = "OpenSans-SemiBold"
    TOP_NAV_TITLE_FONT_SIZE = 20
    TOP_NAV_HEIGHT = 48
    TOP_NAV_BUTTON_SIZE = 32

    BODY_FONT_NAME = "OpenSans-Regular"
    BODY_FONT_SIZE = 17
    BODY_FONT_MAX_SIZE = TOP_NAV_TITLE_FONT_SIZE
    BODY_FONT_MIN_SIZE = 15
    BODY_FONT_COLOR = "#FCFCFC"
    BODY_LINE_SPACING = COMPONENT_PADDING

    FIXED_WIDTH_FONT_NAME = "Inconsolata-Regular"
    FIXED_WIDTH_EMPHASIS_FONT_NAME = "Inconsolata-SemiBold"

    LABEL_FONT_SIZE = BODY_FONT_MIN_SIZE
    LABEL_FONT_COLOR = "#777777"

    BUTTON_FONT_NAME = "OpenSans-SemiBold"
    BUTTON_FONT_SIZE = 18
    BUTTON_FONT_COLOR = "#FCFCFC"
    BUTTON_BACKGROUND_COLOR = "#2C2C2C"
    BUTTON_HEIGHT = 32
    BUTTON_SELECTED_FONT_COLOR = BACKGROUND_COLOR
    
    NOTIFICATION_COLOR = "#00F100"



class FontAwesomeIconConstants:
    ANGLE_DOWN = "\uf107"
    ANGLE_LEFT = "\uf104"
    ANGLE_RIGHT = "\uf105"
    ANGLE_UP = "\uf106"
    CAMERA = "\uf030"
    CHEVRON_UP = "\uf077"
    CHEVRON_DOWN = "\uf078"
    CIRCLE = "\uf111"
    CIRCLE_CHEVRON_RIGHT = "\uf138"
    DICE = "\uf522"
    DICE_ONE = "\uf525"
    DICE_TWO = "\uf528"
    DICE_THREE = "\uf527"
    DICE_FOUR = "\uf524"
    DICE_FIVE = "\uf523"
    DICE_SIX = "\uf526"
    KEYBOARD = "\uf11c"
    LOCK = "\uf023"
    MAP = "\uf279"
    PAPER_PLANE = "\uf1d8"
    PEN = "\uf304"
    SQUARE_CARET_DOWN = "\uf150"
    SQUARE_CARET_LEFT = "\uf191"
    SQUARE_CARET_RIGHT = "\uf152"
    SQUARE_CARET_UP = "\uf151"
    UNLOCK = "\uf09c"
    X = "\u0058"


class SeedSignerIconConstants:
    # Menu icons
    SCAN = "\ue900"
    SEEDS = "\ue901"
    SETTINGS = "\ue902"
    TOOLS = "\ue903"

    # Utility icons
    BACK = "\ue904"
    CHECK = "\ue905"
    CHECKBOX = "\ue906"
    CHECKBOX_SELECTED = "\ue907"
    CHEVRON_DOWN = "\ue908"
    CHEVRON_LEFT = "\ue909"
    CHEVRON_RIGHT = "\ue90a"
    CHEVRON_UP = "\ue90b"
    CLOSE = "\ue90c"
    PAGE_DOWN = "\ue90d"
    PAGE_UP = "\ue90e"
    PLUS = "\ue90f"
    POWER = "\ue910"
    RESTART = "\ue911"

    # Messaging icons
    ERROR = "\ue912"
    SUCCESS = "\ue913"
    WARNING = "\ue914"

    # Informational icons
    ADDRESS = "\ue915"
    CHANGE = "\ue916"
    DERIVATION = "\ue917"
    FEE = "\ue918"
    FINGERPRINT = "\ue919"
    PASSPHRASE = "\ue91a"

    # Misc icons
    BITCOIN = "\ue91b"
    BITCOIN_ALT = "\ue91c"
    BRIGHTNESS = "\ue91d"
    MICROSD = "\ue91e"
    QRCODE = "\ue91f"

    MIN_VALUE = SCAN
    MAX_VALUE = QRCODE



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



def load_image(image_name: str) -> Image.Image:
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
        
        if font_name in [GUIConstants.ICON_FONT_NAME__FONT_AWESOME, GUIConstants.ICON_FONT_NAME__SEEDSIGNER]:
            file_extension = "otf"
        
        if size not in cls.fonts[font_name]:
            try:
                cls.fonts[font_name][size] = ImageFont.truetype(os.path.join(cls.font_path, f"{font_name}.{file_extension}"), size)
            except OSError as e:
                if "cannot open resource" in str(e):
                    raise Exception(f"Font {font_name}.{file_extension} not found: {repr(e)}")
                else:
                    raise e

        return cls.fonts[font_name][size]



class TextDoesNotFitException(Exception):
    pass



@dataclass
class BaseComponent:
    image_draw: ImageDraw.ImageDraw = None
    canvas: Image.Image = None

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
    min_text_x: int = 0  # Text can not start at x any less than this
    background_color: str = GUIConstants.BACKGROUND_COLOR
    font_name: str = GUIConstants.BODY_FONT_NAME
    font_size: int = GUIConstants.BODY_FONT_SIZE
    font_color: str = GUIConstants.BODY_FONT_COLOR
    edge_padding: int = GUIConstants.EDGE_PADDING
    is_text_centered: bool = True
    supersampling_factor: int = 1
    auto_line_break: bool = True
    allow_text_overflow: bool = False
    height_ignores_below_baseline: bool = False  # If True, characters that render below the baseline (e.g. "pqgy") will not affect the final height calculation


    def __post_init__(self):
        super().__post_init__()

        if not self.width:
            self.width = self.canvas_width
        
        if self.screen_x + self.width > self.canvas_width:
            self.width = self.canvas_width - self.screen_x

        self.line_spacing = GUIConstants.BODY_LINE_SPACING

        # We have to figure out if and where to make line breaks in the text so that it
        #   fits in its bounding rect (plus accounting for edge padding) using its given
        #   font.
        # Do initial calcs without worrying about supersampling.
        self.text_lines = reflow_text_for_width(
            text=self.text,
            width=self.width - 2*self.edge_padding,
            font_name=self.font_name,
            font_size=self.font_size,
            allow_text_overflow=self.allow_text_overflow,
        )

        # Calculate the actual font height from the "baseline" anchor ("_s")
        font = Fonts.get_font(self.font_name, self.font_size)

        # Note: from the baseline anchor, `top` is a negative number while `bottom`
        # conveys the height of the pixels that rendered below the baseline, if any
        # (e.g. "py" in "python").
        (left, top, right, bottom) = font.getbbox(self.text, anchor="ls")
        self.text_height_above_baseline = -1 * top
        self.text_height_below_baseline = bottom

        # Initialize the text rendering relative to the baseline
        self.text_y = self.text_height_above_baseline

        # Other components, like IconTextLine will need to know how wide the actual
        # rendered text will be, separate from the TextArea's defined overall `width`.
        self.text_width = max(line["text_width"] for line in self.text_lines)

        # Calculate the actual height
        if len(self.text_lines) == 1:
            total_text_height = self.text_height_above_baseline
            if not self.height_ignores_below_baseline:
                total_text_height += self.text_height_below_baseline
        else:
            # Multiply for the number of lines plus the spacer
            total_text_height = self.text_height_above_baseline * len(self.text_lines) + self.line_spacing * (len(self.text_lines) - 1)

            if not self.height_ignores_below_baseline and re.findall(f"[gjpqy]", self.text_lines[-1]["text"]):
                # Last line has at least one char that dips below baseline
                total_text_height += self.text_height_below_baseline

        if self.height is None:
            # Autoscale height to text lines
            self.height = total_text_height

        else:
            if total_text_height > self.height:
                if not self.allow_text_overflow:
                    raise TextDoesNotFitException(f"Text cannot fit in target rect with this font/size\n\ttotal_text_height: {total_text_height} | self.height: {self.height}")
                else:
                    # Just let it render off the edge, but preserve the top portion
                    pass

            else:
                # Vertically center the text's starting point
                self.text_y += int(self.height - total_text_height)/2


    def render(self):
        # Render to a temp img scaled up by self.supersampling_factor, then resize down
        #   with bicubic resampling.
        # Add a `resample_padding` above and below when supersampling to avoid edge
        # effects (resized text that's right up against the top/bottom gets slightly
        # dimmer at the edge otherwise).
        if self.font_size < 20 and (not self.supersampling_factor or self.supersampling_factor == 1):
            self.supersampling_factor = 2

        actual_text_height = self.height
        if self.height_ignores_below_baseline:
            # Even though we're ignoring the pixels below the baseline for spacing
            # purposes, we have to make sure we don't crop those pixels out during the
            # supersampling operations here.
            actual_text_height += self.text_height_below_baseline

        resample_padding = 10 if self.supersampling_factor > 1.0 else 0
        img = Image.new(
            "RGBA",
            (
                self.width * self.supersampling_factor,
                (actual_text_height + 2*resample_padding) * self.supersampling_factor
            ),
            self.background_color
        )
        draw = ImageDraw.Draw(img)

        cur_y = (self.text_y + resample_padding) * self.supersampling_factor
        supersampled_font = Fonts.get_font(self.font_name, int(self.supersampling_factor * self.font_size))

        if self.is_text_centered:
            anchor = "ms"
        else:
            anchor = "ls"

        # Position where we'll render each line of text
        text_x = self.edge_padding

        for line in self.text_lines:
            if self.is_text_centered:
                # We'll render with a centered anchor so we just need the midpoint
                text_x = int(self.width/2)
                if text_x - int(line["text_width"]/2) < self.min_text_x:
                    # The left edge of the centered text will protrude too far; nudge it right
                    text_x = self.min_text_x + int(line["text_width"]/2)

            draw.text((text_x * self.supersampling_factor, cur_y), line["text"], fill=self.font_color, font=supersampled_font, anchor=anchor)

            # Debugging: show the exact vertical extents of each line of text
            # draw.line((0, cur_y - self.text_height_above_baseline * self.supersampling_factor, self.width * self.supersampling_factor, cur_y - self.text_height_above_baseline * self.supersampling_factor), fill="red", width=int(self.supersampling_factor))
            # draw.line((0, cur_y, self.width * self.supersampling_factor, cur_y), fill="red", width=int(self.supersampling_factor))

            cur_y += (self.text_height_above_baseline + self.line_spacing) * self.supersampling_factor

        # Crop off the top_padding and resize the result down to onscreen size
        if self.supersampling_factor > 1.0:
            resized = img.resize((self.width, actual_text_height + 2*resample_padding), Image.LANCZOS)
            sharpened = resized.filter(ImageFilter.SHARPEN)

            # Crop args are actually (left, top, WIDTH, HEIGHT)
            img = sharpened.crop((0, resample_padding, self.width, actual_text_height + resample_padding))
        self.canvas.paste(img, (self.screen_x, self.screen_y))



@dataclass
class Icon(BaseComponent):
    screen_x: int = 0
    screen_y: int = 0
    icon_name: str = SeedSignerIconConstants.BITCOIN_ALT
    icon_size: int = GUIConstants.ICON_FONT_SIZE
    icon_color: str = GUIConstants.BODY_FONT_COLOR

    def __post_init__(self):
        super().__post_init__()

        if SeedSignerIconConstants.MIN_VALUE <= self.icon_name and self.icon_name <= SeedSignerIconConstants.MAX_VALUE:
            self.icon_font = Fonts.get_font(GUIConstants.ICON_FONT_NAME__SEEDSIGNER, self.icon_size, file_extension="otf")
        else:
            self.icon_font = Fonts.get_font(GUIConstants.ICON_FONT_NAME__FONT_AWESOME, self.icon_size, file_extension="otf")
        
        # Set width/height based on exact pixels that are rendered
        (left, top, self.width, bottom) = self.icon_font.getbbox(self.icon_name, anchor="ls")
        self.height = -1 * top


    def render(self):
        self.image_draw.text(
            (self.screen_x, self.screen_y + self.height),
            text=self.icon_name,
            font=self.icon_font,
            fill=self.icon_color,
            anchor="ls",
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
    allow_text_overflow: bool = False
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
                font_color=GUIConstants.LABEL_FONT_COLOR,
                edge_padding=0,
                is_text_centered=self.is_text_centered if not self.icon_name else False,
                auto_line_break=False,
                screen_x=text_screen_x,
                screen_y=self.screen_y,
                allow_text_overflow=False,
            )
        else:
            self.label_textarea = None        
        
        value_textarea_screen_y = self.screen_y
        if self.label_text:
            label_padding_y = int(GUIConstants.COMPONENT_PADDING / 2)
            value_textarea_screen_y += self.label_textarea.height + label_padding_y

        self.value_textarea = TextArea(
            image_draw=self.image_draw,
            canvas=self.canvas,
            height=self.height,
            text=self.value_text,
            font_name=self.font_name,
            font_size=self.font_size,
            edge_padding=0,
            is_text_centered=self.is_text_centered if not self.icon_name else False,
            auto_line_break=self.auto_line_break,
            allow_text_overflow=self.allow_text_overflow,
            screen_x=text_screen_x,
            screen_y=value_textarea_screen_y,
        )

        if self.label_text:
            if not self.height:
                self.height = self.label_textarea.height + label_padding_y + self.value_textarea.height
            max_textarea_width = max(self.label_textarea.text_width, self.value_textarea.text_width)
        else:
            if not self.height:
                self.height = self.value_textarea.height
            max_textarea_width = self.value_textarea.text_width
        
        # Now we can update the icon's y position
        if self.icon_name:
            icon_y = self.screen_y + int((self.height - self.icon.height)/2)
            self.icon.screen_y = icon_y

            self.height = max(self.icon.height, self.height)
        
        if self.is_text_centered and self.icon_name:
            total_width = max_textarea_width + self.icon.width + self.icon_horizontal_spacer
            self.icon.screen_x = self.screen_x + int((self.canvas_width - self.screen_x - total_width) / 2)
            if self.label_text:
                self.label_textarea.screen_x = self.icon.screen_x + self.icon.width + self.icon_horizontal_spacer
            self.value_textarea.screen_x = self.icon.screen_x + self.icon.width + self.icon_horizontal_spacer

        self.width = self.canvas_width


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

        single sig native segwit: 42 chars (44 for regtest)
        nested single sig:        34 chars (35 for regtest)

        multisig native segwit:   64 chars (66 for regtest)
        multisig nested segwit:   34 chars (35 for regtest?)
 
        single sig taproot:       62 chars

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
        left, top, right, bottom  = self.font.getbbox("Q")
        char_width, char_height = right - left, bottom - top

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
                cur_y += char_height + GUIConstants.BODY_LINE_SPACING
        
        self.height = cur_y
    

    def render(self):
        for p in self.text_params:
            self.image_draw.text((p[0][0], p[0][1] + self.screen_y), text=p[1], fill=p[2], font=p[3])



@dataclass
class BtcAmount(BaseComponent):
    """
        Display btc value based on the SETTING__BTC_DENOMINATION Setting:
        * btc: "B" icon + 8-decimal amount + "btc" (can truncate zero decimals to .0 or .09)
        * sats: "B" icon + comma-separated amount + "sats"
        * threshold: btc display at or above 0.01 btc; otherwise sats
        * btcsatshybrd: "B" icon + 2-decimal amount + "|" + up to 6-digit, comma-separated sats + "sats"
    """
    total_sats: int = None
    icon_size: int = 34
    font_size: int = 24
    screen_x: int = 0
    screen_y: int = None


    def __post_init__(self):
        super().__post_init__()
        self.sub_components: List[BaseComponent] = []
        self.paste_image: Image.Image = None
        self.paste_coords = None
        denomination = Settings.get_instance().get_value(SettingsConstants.SETTING__BTC_DENOMINATION)
        network = Settings.get_instance().get_value(SettingsConstants.SETTING__NETWORK)

        btc_unit = "tBtc"
        sats_unit = "tSats"
        if network == SettingsConstants.MAINNET:
            btc_unit = "btc"
            sats_unit = "sats"
            btc_color = GUIConstants.ACCENT_COLOR

        elif network == SettingsConstants.TESTNET:
            btc_color = GUIConstants.TESTNET_COLOR
        
        elif network == SettingsConstants.REGTEST:
            btc_color = GUIConstants.REGTEST_COLOR
        
        digit_font = Fonts.get_font(font_name=GUIConstants.BODY_FONT_NAME, size=self.font_size)
        smaller_digit_font = Fonts.get_font(font_name=GUIConstants.BODY_FONT_NAME, size=self.font_size - 2)
        unit_font_size = GUIConstants.BUTTON_FONT_SIZE + 2

        # Render to a temp surface
        self.paste_image = Image.new(mode="RGB", size=(self.canvas_width, self.icon_size), color=GUIConstants.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(self.paste_image)

        # Render the circular Bitcoin icon
        btc_icon = Icon(
            image_draw=draw,
            canvas=self.paste_image,
            icon_name=SeedSignerIconConstants.BITCOIN_ALT,
            icon_color=btc_color,
            icon_size=self.icon_size,
            screen_x=0,
            screen_y=0,
        )
        btc_icon.render()
        cur_x = btc_icon.width + int(GUIConstants.COMPONENT_PADDING/4)

        if denomination == SettingsConstants.BTC_DENOMINATION__BTC or \
            (denomination == SettingsConstants.BTC_DENOMINATION__THRESHOLD and self.total_sats >= 1e6) or \
                (denomination == SettingsConstants.BTC_DENOMINATION__BTCSATSHYBRID and self.total_sats >= 1e6 and str(self.total_sats)[-6:] == "0" * 6) or \
                    self.total_sats > 1e10:
            decimal_btc = Decimal(self.total_sats / 1e8).quantize(Decimal("0.12345678"))
            if str(self.total_sats)[-8:] == "0" * 8:
                # Only whole btc units being displayed; truncate to a single decimal place
                decimal_btc = decimal_btc.quantize(Decimal("0.1"))

            elif str(self.total_sats)[-6:] == "0" * 6:
                # Bottom six digits are all zeroes; trucate to two decimal places
                decimal_btc = decimal_btc.quantize(Decimal("0.12"))
            
            btc_text = f"{decimal_btc:,}"

            if len(btc_text) >= 12:
                # This is a large btc value that won't fit; omit sats
                btc_text = btc_text.split(".")[0] + "." + btc_text.split(".")[-1][:2] + "..."

            # Draw the btc side
            font = digit_font
            # if self.total_sats > 1e9:
            #     font = smaller_digit_font

            (left, top, text_width, bottom) = font.getbbox(btc_text, anchor="ls")
            text_height = -1 * top + bottom
            text_y = self.paste_image.height - int((self.paste_image.height - text_height)/2)

            draw.text(
                xy=(
                    cur_x,
                    text_y
                ),
                font=font,
                text=btc_text,
                fill=GUIConstants.BODY_FONT_COLOR,
                anchor="ls",
            )
            cur_x += text_width

            unit_text = btc_unit
        
        elif denomination == SettingsConstants.BTC_DENOMINATION__SATS or \
            (denomination == SettingsConstants.BTC_DENOMINATION__THRESHOLD and self.total_sats < 1e6) or \
                (denomination == SettingsConstants.BTC_DENOMINATION__BTCSATSHYBRID and self.total_sats < 1e6):
            # Draw the sats side
            sats_text = f"{self.total_sats:,}"

            font = digit_font
            if self.total_sats > 1e9:
                font = smaller_digit_font
            (left, top, text_width, bottom) = font.getbbox(sats_text, anchor="ls")
            text_height = -1 * top + bottom
            text_y = self.paste_image.height - int((self.paste_image.height - text_height)/2)
            draw.text(
                xy=(
                    cur_x,
                    text_y
                ),
                font=font,
                text=sats_text,
                fill=GUIConstants.BODY_FONT_COLOR,
                anchor="ls",
            )
            cur_x += text_width

            unit_text = sats_unit
        
        elif denomination == SettingsConstants.BTC_DENOMINATION__BTCSATSHYBRID:
            decimal_btc = Decimal(self.total_sats / 1e8).quantize(Decimal("0.12345678"))
            decimal_btc = Decimal(str(decimal_btc)[:-6])
            btc_text = f"{decimal_btc:,}"
            sats_text = f"{self.total_sats:,}"[-7:]
            while sats_text[0] == "0":
                sats_text = sats_text[1:]

            btc_icon = Icon(
                image_draw=draw,
                canvas=self.paste_image,
                icon_name=SeedSignerIconConstants.BITCOIN_ALT,
                icon_color=btc_color,
                icon_size=self.icon_size,
                screen_x=0,
                screen_y=0,
            )
            btc_icon.render()
            cur_x = btc_icon.width + int(GUIConstants.COMPONENT_PADDING/4)

            (left, top, text_width, bottom) = smaller_digit_font.getbbox(btc_text, anchor="ls")
            text_height = -1 * top + bottom
            text_y = self.paste_image.height - int((self.paste_image.height - text_height)/2)
            
            draw.text(
                xy=(
                    cur_x,
                    text_y
                ),
                font=smaller_digit_font,
                text=btc_text,
                fill=GUIConstants.BODY_FONT_COLOR,
                anchor="ls",
            )
            cur_x += text_width - int(GUIConstants.COMPONENT_PADDING/2)

            # Draw the pipe separator
            pipe_font = Fonts.get_font(font_name=GUIConstants.BODY_FONT_NAME, size=self.icon_size - 4)
            (left, top, text_width, bottom) = pipe_font.getbbox("|", anchor="ls")
            draw.text(
                xy=(
                    cur_x,
                    text_y
                ),
                font=pipe_font,
                text="|",
                fill=btc_color,
                anchor="ls",
            )
            cur_x += text_width - int(GUIConstants.COMPONENT_PADDING/2)

            # Draw the sats side
            (left, top, text_width, bottom) = smaller_digit_font.getbbox(sats_text, anchor="ls")
            draw.text(
                xy=(
                    cur_x,
                    text_y
                ),
                font=smaller_digit_font,
                text=sats_text,
                fill=GUIConstants.BODY_FONT_COLOR,
                anchor="ls",
            )
            cur_x += text_width

            unit_text = sats_unit

        # Draw the unit
        unit_font = Fonts.get_font(font_name=GUIConstants.BODY_FONT_NAME, size=unit_font_size)
        (left, top, unit_text_width, bottom) = unit_font.getbbox(unit_text, anchor="ls")
        unit_font_height = -1 * top

        unit_textarea = TextArea(
            image_draw=draw,
            canvas=self.paste_image,
            text=f" {unit_text}",
            font_name=GUIConstants.BODY_FONT_NAME,
            font_size=unit_font_size,
            font_color=GUIConstants.BODY_FONT_COLOR,
            supersampling_factor=2,
            is_text_centered=False,
            edge_padding=0,
            screen_x=cur_x,
            screen_y=text_y - unit_font_height,
        )
        unit_textarea.render()

        final_x = cur_x + GUIConstants.COMPONENT_PADDING + unit_text_width

        self.paste_image = self.paste_image.crop((0, 0, final_x, self.paste_image.height))
        self.paste_coords = (
            int((self.canvas_width - final_x)/2),
            self.screen_y
        )

        self.width = self.canvas_width
        self.height = self.paste_image.height


    def render(self):
        self.canvas.paste(self.paste_image, self.paste_coords)



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
    right_icon_name: str = None    # Optional icon rendered right-justified
    right_icon_size: int = GUIConstants.ICON_INLINE_FONT_SIZE
    right_icon_color: str = GUIConstants.BUTTON_FONT_COLOR
    text_y_offset: int = 0
    background_color: str = GUIConstants.BUTTON_BACKGROUND_COLOR
    selected_color: str = GUIConstants.ACCENT_COLOR
    font_name: str = GUIConstants.BUTTON_FONT_NAME
    font_size: int = GUIConstants.BUTTON_FONT_SIZE
    font_color: str = GUIConstants.BUTTON_FONT_COLOR
    selected_font_color: str = GUIConstants.BUTTON_SELECTED_FONT_COLOR
    outline_color: str = None
    selected_outline_color: str = None
    is_text_centered: bool = True
    is_selected: bool = False


    def __post_init__(self):
        super().__post_init__()

        if not self.width:
            self.width = self.canvas_width - 2*GUIConstants.EDGE_PADDING

        if not self.height:
            self.height = GUIConstants.BUTTON_HEIGHT
        
        if not self.icon_color:
            self.icon_color = GUIConstants.BUTTON_FONT_COLOR

        self.font = Fonts.get_font(self.font_name, self.font_size)

        if self.text is not None:
            if self.is_text_centered:
                self.text_x = int(self.width/2)
                self.text_anchor = "ms"  # centered horizontally, baseline
            else:
                self.text_x = GUIConstants.COMPONENT_PADDING
                self.text_anchor = "ls"  # left, baseline
            
            # Calc true pixel height (any anchor from "baseline" will work)
            (left, top, self.text_width, bottom) = self.font.getbbox(self.text, anchor="ls")
            # print(f"left: {left} |  top: {top} | right: {self.text_width} | bottom: {bottom}")

            # Note: "top" is negative when measured from a "baseline" anchor. Intentionally
            # ignore any chars below the baseline for consistent vertical positioning
            # regardless of the Button text.
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
                self.icon_y = math.ceil((self.height - self.icon.height)/2)

        if self.right_icon_name:
            self.right_icon = Icon(icon_name=self.right_icon_name, icon_size=self.right_icon_size, icon_color=self.right_icon_color)
            self.right_icon_selected = Icon(icon_name=self.right_icon_name, icon_size=self.right_icon_size, icon_color=self.selected_icon_color)

            self.right_icon_x = self.width - self.right_icon.width - GUIConstants.COMPONENT_PADDING

            self.right_icon_y = math.ceil((self.height - self.right_icon.height)/2)


    def render(self):
        if self.is_selected:
            background_color = self.selected_color
            font_color = self.selected_font_color
            outline_color = self.selected_outline_color
        else:
            background_color = self.background_color
            font_color = self.font_color
            outline_color = self.outline_color

        self.image_draw.rounded_rectangle(
            (
                self.screen_x,
                self.screen_y - self.scroll_y,
                self.screen_x + self.width,
                self.screen_y + self.height - self.scroll_y
            ),
            fill=background_color,
            radius=8,
            outline=outline_color,
            width=2,
        )

        if self.text is not None:
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

        if self.right_icon_name:
            icon = self.right_icon
            if self.is_selected:
                icon = self.right_icon_selected
            icon.screen_y = self.screen_y + self.right_icon_y - self.scroll_y
            icon.screen_x = self.screen_x + self.right_icon_x
            icon.render()



@dataclass
class CheckedSelectionButton(Button):
    is_checked: bool = False

    def __post_init__(self):
        self.is_text_centered = False
        self.icon_name = SeedSignerIconConstants.CHECK
        self.icon_color = GUIConstants.SUCCESS_COLOR
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
            self.icon_name = SeedSignerIconConstants.CHECKBOX_SELECTED
            self.icon_color = GUIConstants.SUCCESS_COLOR
        else:
            self.icon_name = SeedSignerIconConstants.CHECKBOX
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
    is_text_centered: bool = True



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
    font_color: str = GUIConstants.BODY_FONT_COLOR
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
                icon_name=SeedSignerIconConstants.BACK,
                icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=GUIConstants.EDGE_PADDING - 1,  # Text can't perfectly vertically center relative to the button; shifting it down 1px looks better.
                width=GUIConstants.TOP_NAV_BUTTON_SIZE,
                height=GUIConstants.TOP_NAV_BUTTON_SIZE,
            )

        if self.show_power_button:
            self.right_button = IconButton(
                icon_name=SeedSignerIconConstants.POWER,
                icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
                screen_x=self.width - GUIConstants.TOP_NAV_BUTTON_SIZE - GUIConstants.EDGE_PADDING,
                screen_y=GUIConstants.EDGE_PADDING,
                width=GUIConstants.TOP_NAV_BUTTON_SIZE,
                height=GUIConstants.TOP_NAV_BUTTON_SIZE,
            )

        min_text_x = 0
        if self.show_back_button:
            # Don't let the title intrude on the BACK button
            min_text_x = self.left_button.screen_x + self.left_button.width + GUIConstants.COMPONENT_PADDING

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
                min_text_x=min_text_x,
                width=self.width,
                height=self.height,
                text=self.text,
                is_text_centered=True,
                font_name=self.font_name,
                font_size=self.font_size,
                height_ignores_below_baseline=True,  # Consistently vertically center text, ignoring chars that render below baseline (e.g. "pqyj")
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
        self.render_buttons()
    

    def render_buttons(self):
        if self.show_back_button:
            self.left_button.is_selected = self.is_selected
            self.left_button.render()
        if self.show_power_button:
            self.right_button.is_selected = self.is_selected
            self.right_button.render()



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



def reflow_text_for_width(text: str,
                          width: int,
                          font_name=GUIConstants.BODY_FONT_NAME,
                          font_size=GUIConstants.BODY_FONT_SIZE,
                          allow_text_overflow: bool=False) -> list[dict]:
    """
    Reflows text to fit within `width` by breaking long lines up.

    Returns a List with each reflowed line of text as its own entry.

    Note: It is up to the calling code to handle any height considerations for the 
    resulting lines of text.
    """
    # We have to figure out if and where to make line breaks in the text so that it
    #   fits in its bounding rect (plus accounting for edge padding) using its given
    #   font.
    start = time()
    font = Fonts.get_font(font_name=font_name, size=font_size)
    # Measure from left baseline ("ls")
    (left, top, full_text_width, bottom) = font.getbbox(text, anchor="ls")

    # Stores each line of text and its rendering starting x-coord
    text_lines = []
    def _add_text_line(text, text_width):
        text_lines.append({"text": text, "text_width": text_width})

    if "\n" not in text and full_text_width < width:
        # The whole text fits on one line
        _add_text_line(text, full_text_width)        

    else:
        # Have to calc how to break text into multiple lines
        def _binary_len_search(min_index, max_index):
            # Try the middle of the range
            index = math.ceil((max_index + min_index) / 2)
            if index == 0:
                # Handle edge case where there's only one word in the last line
                index = 1

            # Measure rendered width from "left" anchor (anchor="l_")
            (left, top, right, bottom) = font.getbbox(" ".join(words[0:index]), anchor="ls")
            line_width = right - left

            if line_width >= width:
                # Candidate line is still too long. Restrict search range down.
                if min_index + 1 == index:
                    if index == 1:
                        # It's just one long, unbreakable word. There's no good
                        # solution here. Just accept it as is and let it render off
                        # the edges.
                        return (index, line_width)
                    else:
                        # There's still room to back down the min_index in the next
                        # round.
                        index -= 1
                return _binary_len_search(min_index=min_index, max_index=index)
            elif index == max_index:
                # We have converged
                return (index, line_width)
            else:
                # Candidate line is possibly shorter than necessary.
                return _binary_len_search(min_index=index, max_index=max_index)

        if len(text.split()) == 1 and not allow_text_overflow:
            # No whitespace chars to split on!
            raise TextDoesNotFitException("Text cannot fit in target rect with this font+size")

        # Now we're ready to go line-by-line into our line break binary search!
        for line in text.split("\n"):
            words = line.split()
            if not words:
                # It's a blank line
                _add_text_line("", 0)
            else:
                while words:
                    (index, tw) = _binary_len_search(0, len(words))
                    _add_text_line(" ".join(words[0:index]), tw)
                    words = words[index:]

    return text_lines



def reflow_text_into_pages(text: str,
                           width: int,
                           height: int,
                           font_name=GUIConstants.BODY_FONT_NAME,
                           font_size=GUIConstants.BODY_FONT_SIZE,
                           line_spacer: int = GUIConstants.BODY_LINE_SPACING,
                           allow_text_overflow: bool=False) -> list[str]:
    """
    Invokes `reflow_text_for_width` above to convert long text into width-limited
    individual text lines and then calculates how many lines will fit on a "page" and
    groups the output accordingly.

    Returns a list of strings where each string is a page's worth of line-breaked text.
    """
    reflowed_lines_dicts = reflow_text_for_width(text=text,
                                           width=width,
                                           font_name=font_name,
                                           font_size=font_size,
                                           allow_text_overflow=allow_text_overflow)

    lines = []
    for line_dict in reflowed_lines_dicts:
        lines.append(line_dict["text"])
        logging.info(f"""{line_dict["text_width"]:3}: {line_dict["text"]}""")

    font = Fonts.get_font(font_name=font_name, size=font_size)
    # Measure the font's height above baseline and how for below it certain characters
    # (e.g. lowercase "g") can render.
    (left, top, right, bottom) = font.getbbox("Agjpqy", anchor="ls")
    font_height_above_baseline = -1 * top
    font_height_below_baseline = bottom

    # I'm sure there's a smarter way to do this...
    lines_per_page = 0
    for i in range(1, height):
        if height > font_height_above_baseline * i + line_spacer * (i-1) + font_height_below_baseline:
            lines_per_page = i
        else:
            break

    pages = []
    for i in range(0, len(lines), lines_per_page):
        pages.append("\n".join(lines[i:i+lines_per_page]))
    
    return pages
