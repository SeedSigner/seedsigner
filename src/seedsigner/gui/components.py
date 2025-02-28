import logging
import math
import os
import pathlib
import re
import time

from dataclasses import dataclass
from decimal import Decimal
from gettext import gettext as _
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Any, List, Tuple

from seedsigner.gui.renderer import Renderer
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.models.singleton import Singleton
from seedsigner.models.threads import BaseThread

logger = logging.getLogger(__name__)



# TODO: Remove all pixel hard coding
class GUIConstants:
    EDGE_PADDING = 8
    COMPONENT_PADDING = 8
    LIST_ITEM_PADDING = 4

    BACKGROUND_COLOR = "#000000"
    INACTIVE_COLOR = "#414141"
    ACCENT_COLOR = "#FF9F0A" # Active Color
    WARNING_COLOR = "#FFD60A"
    DIRE_WARNING_COLOR = "#FF5700"
    ERROR_COLOR = "#FF1B0A"
    SUCCESS_COLOR = "#30D158"
    INFO_COLOR = "#409CFF"
    BITCOIN_ORANGE = "#FF9416"
    TESTNET_COLOR = "#00F100"
    REGTEST_COLOR = "#00CAF1"
    GREEN_INDICATOR_COLOR = "#00FF00"

    ICON_FONT_NAME__FONT_AWESOME = "Font_Awesome_6_Free-Solid-900"
    ICON_FONT_NAME__SEEDSIGNER = "seedsigner-icons"
    ICON_FONT_SIZE = 22
    ICON_INLINE_FONT_SIZE = 24
    ICON_LARGE_BUTTON_SIZE = 48
    ICON_TOAST_FONT_SIZE = 30
    ICON_PRIMARY_SCREEN_SIZE = 50

    TOP_NAV_TITLE_FONT_NAME = {
        "default": "OpenSans-SemiBold",
        # "ar": "multilanguage/NotoSansAR-Regular",
        # "he": "multilanguage/NotoSansHE-Regular",
        # "ja": "multilanguage/NotoSansJP-Regular",
        # "kr": "multilanguage/NotoSansKR-Regular",
        # "ru": "multilanguage/NotoSans-Regular",
    }
    TOP_NAV_TITLE_FONT_SIZE = {
        "default": 20,
    }
    TOP_NAV_HEIGHT = 48
    TOP_NAV_BUTTON_SIZE = 32

    BODY_FONT_NAME = {
        "default": "OpenSans-Regular",
        # "ar": "multilanguage/NotoSansAR-Regular",
        # "he": "multilanguage/NotoSansHE-Regular",
        # "ja": "multilanguage/NotoSansJP-Regular",
        # "kr": "multilanguage/NotoSansKR-Regular",
        # "ru": "multilanguage/NotoSans-Regular",
    }
    BODY_FONT_SIZE = {
        "default": 17,
        # "ar": 16,
    }
    BODY_FONT_MAX_SIZE = TOP_NAV_TITLE_FONT_SIZE["default"]
    BODY_FONT_MIN_SIZE = 15
    BODY_FONT_COLOR = "#FCFCFC"
    BODY_LINE_SPACING = COMPONENT_PADDING

    FIXED_WIDTH_FONT_NAME = "Inconsolata-Regular"
    FIXED_WIDTH_EMPHASIS_FONT_NAME = "Inconsolata-SemiBold"

    LABEL_FONT_SIZE = BODY_FONT_MIN_SIZE
    LABEL_FONT_COLOR = "#777777"

    BUTTON_FONT_NAME = {
        "default": "OpenSans-SemiBold",
        # "ar": "multilanguage/NotoSansAR-Regular",
        # "he": "multilanguage/NotoSansHE-Regular",
        # "ja": "multilanguage/NotoSansJP-Regular",
        # "kr": "multilanguage/NotoSansKR-Regular",
        # "ru": "multilanguage/NotoSans-Regular",
    }
    BUTTON_FONT_SIZE = {
        "default": 18,
        # "ar": 16,
        # "ja": 16,
    }
    BUTTON_FONT_COLOR = "#FCFCFC"
    BUTTON_BACKGROUND_COLOR = "#2C2C2C"
    BUTTON_HEIGHT = 32
    BUTTON_SELECTED_FONT_COLOR = BACKGROUND_COLOR
    
    NOTIFICATION_COLOR = "#00F100"


    @staticmethod
    def get_body_font_name():
        locale = Settings.get_instance().get_value(SettingsConstants.SETTING__LOCALE)
        if locale in GUIConstants.BODY_FONT_NAME:
            return GUIConstants.BODY_FONT_NAME[locale]
        else:
            return GUIConstants.BODY_FONT_NAME["default"]


    @staticmethod
    def get_body_font_size():
        locale = Settings.get_instance().get_value(SettingsConstants.SETTING__LOCALE)
        if locale in GUIConstants.BODY_FONT_SIZE:
            return GUIConstants.BODY_FONT_SIZE[locale]
        else:
            return GUIConstants.BODY_FONT_SIZE["default"]


    @staticmethod
    def get_top_nav_title_font_name():
        locale = Settings.get_instance().get_value(SettingsConstants.SETTING__LOCALE)
        if locale in GUIConstants.TOP_NAV_TITLE_FONT_NAME:
            return GUIConstants.TOP_NAV_TITLE_FONT_NAME[locale]
        else:
            return GUIConstants.TOP_NAV_TITLE_FONT_NAME["default"]


    @staticmethod
    def get_top_nav_title_font_size():
        locale = Settings.get_instance().get_value(SettingsConstants.SETTING__LOCALE)
        if locale in GUIConstants.TOP_NAV_TITLE_FONT_SIZE:
            return GUIConstants.TOP_NAV_TITLE_FONT_SIZE[locale]
        else:
            return GUIConstants.TOP_NAV_TITLE_FONT_SIZE["default"]


    @staticmethod
    def get_button_font_name():
        locale = Settings.get_instance().get_value(SettingsConstants.SETTING__LOCALE)
        if locale in GUIConstants.BUTTON_FONT_NAME:
            return GUIConstants.BUTTON_FONT_NAME[locale]
        else:
            return GUIConstants.BUTTON_FONT_NAME["default"]


    @staticmethod
    def get_button_font_size():
        locale = Settings.get_instance().get_value(SettingsConstants.SETTING__LOCALE)
        if locale in GUIConstants.BUTTON_FONT_SIZE:
            return GUIConstants.BUTTON_FONT_SIZE[locale]
        else:
            return GUIConstants.BUTTON_FONT_SIZE["default"]



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
    INFO = "\ue912"
    SUCCESS = "\ue913"
    WARNING = "\ue914"
    ERROR = "\ue915"

    # Informational icons
    ADDRESS = "\ue916"
    CHANGE = "\ue917"
    DERIVATION = "\ue918"
    FEE = "\ue919"
    FINGERPRINT = "\ue91a"
    PASSPHRASE = "\ue91b"

    # Misc icons
    BITCOIN = "\ue91c"
    BITCOIN_ALT = "\ue91d"
    BRIGHTNESS = "\ue91e"
    MICROSD = "\ue91f"
    QRCODE = "\ue920"
    SIGN = "\ue921"

    # Input icons
    DELETE = "\ue922"
    SPACE = "\ue923"

    # Must be updated whenever new icons are added. See usage in `Icon` class below.
    MIN_VALUE = SCAN
    MAX_VALUE = SPACE



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



def load_image(image_name: str) -> Image.Image:
    image_url = os.path.join(pathlib.Path(__file__).parent.resolve(), "..", "resources", "img", image_name)
    image = Image.open(image_url).convert("RGB")
    return image



class Fonts(Singleton):
    font_path = os.path.join(
        pathlib.Path(__file__).parent.resolve().parent.resolve(),
        "resources",
        "fonts"
    )
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
        from seedsigner.gui.renderer import Renderer
        self.renderer: Renderer = Renderer.get_instance()
        self.canvas_width = self.renderer.canvas_width
        self.canvas_height = self.renderer.canvas_height

        # Component threads will be managed in their parent's `Screen.display()`
        self.threads: list[BaseThread] = []

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
    scroll_y: int = 0
    min_text_x: int = 0  # Text can not start at x any less than this
    background_color: str = GUIConstants.BACKGROUND_COLOR
    font_name: str = None
    font_size: int = None
    font_color: str = GUIConstants.BODY_FONT_COLOR
    edge_padding: int = GUIConstants.EDGE_PADDING
    is_text_centered: bool = True
    supersampling_factor: int = 2  # 1 = disabled; 2 = default, double sample (4px square rendered for 1px)
    auto_line_break: bool = True
    allow_text_overflow: bool = False
    is_horizontal_scrolling_enabled: bool = False
    horizontal_scroll_speed: int = 40  # px per sec
    horizontal_scroll_begin_hold_secs: float = 2.0
    horizontal_scroll_end_hold_secs: float = 1.0
    height_ignores_below_baseline: bool = False  # If True, characters that render below the baseline (e.g. "pqgy") will not affect the final height calculation


    def __post_init__(self):
        if self.is_horizontal_scrolling_enabled and self.auto_line_break:
            raise Exception("TextArea: Cannot have auto_line_break and horizontal scrolling enabled at the same time")

        if self.is_horizontal_scrolling_enabled and not self.allow_text_overflow:
            self.allow_text_overflow = True
            logger.warning("TextArea: allow_text_overflow gets overridden to True when horizontal scrolling is enabled")

        if not self.font_name:
            self.font_name = GUIConstants.get_body_font_name()
        if not self.font_size:
            self.font_size = GUIConstants.get_body_font_size()

        super().__post_init__()

        if not self.width:
            self.width = self.canvas_width
        
        if self.screen_x + self.width > self.canvas_width:
            self.width = self.canvas_width - self.screen_x

        self.line_spacing = GUIConstants.BODY_LINE_SPACING

        # Calculate the actual font height from the "baseline" anchor ("_s")
        font = Fonts.get_font(self.font_name, self.font_size)

        # Note: from the baseline anchor, `top` is a negative number while `bottom`
        # conveys the height of the pixels that rendered below the baseline, if any
        # (e.g. "py" in "python").
        (left, top, full_text_width, bottom) = font.getbbox(self.text, anchor="ls")
        self.text_height_above_baseline = -1 * top
        self.text_height_below_baseline = bottom

        # Initialize the text rendering relative to the baseline
        self.text_y = self.text_height_above_baseline

        self.visible_width = self.width - max(self.edge_padding, self.min_text_x) - self.edge_padding
        if not ImageFont.core.HAVE_RAQM:
            # Fudge factor for imprecise width calcs w/out libraqm
            full_text_width = int(full_text_width * 1.05)
            self.visible_width = int(self.visible_width * 1.05)

        if self.is_horizontal_scrolling_enabled or not self.auto_line_break:
            # Guaranteed to be a single line of text, possibly wider than self.width
            self.text_lines = [{"text": self.text, "text_width": full_text_width}]
            self.text_width = full_text_width
            if self.text_width > self.visible_width:
                # We'll have to left justify the text and scroll it (if scrolling is enabled,
                # otherwise it'll just run off the right edge).
                self.is_text_centered = False
            else:
                # The text fits; horizontal scrolling isn't needed
                self.is_horizontal_scrolling_enabled = False

        else:
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

        self.text_offset_y = 0
        if self.height is None:
            # Autoscale height to text lines
            self.height = total_text_height

        else:
            if total_text_height > self.height:
                if not self.allow_text_overflow:
                    # For now, early into the l10n rollout, we can't enforce strict
                    # conformance here. Too many screens will just break if this is were
                    # to raise an exception.
                    logger.warning(f"Text cannot fit in target rect with this font/size\n\ttotal_text_height: {total_text_height} | self.height: {self.height}")
                else:
                    # Just let it render past the bottom edge
                    pass

            else:
                # Vertically center the text's starting point
                self.text_offset_y = int((self.height - total_text_height)/2)
                self.text_y += self.text_offset_y  # (relative to text rendering baseline)

        # Render to a temp img scaled up by self.supersampling_factor, then resize down
        #   with bicubic resampling.
        # Add a `resample_padding` above and below when supersampling to avoid edge
        # effects (resized text that's right up against the top/bottom gets slightly
        # dimmer at the edge otherwise).
        # if self.background_color == GUIConstants.ACCENT_COLOR and self.supersampling_factor == 1:
        #     # Don't boost supersampling factor. Text against the accent color does not
        #     # render well when supersampled.
        #     pass
        # elif self.font_size < 20 and (not self.supersampling_factor or self.supersampling_factor == 1):
        #     self.supersampling_factor = 2
        if self.font_size >= 20 and self.supersampling_factor != 1:
            self.supersampling_factor = 1
            logger.warning(f"Supersampling disabled for large font size: {self.font_size}")

        if self.height_ignores_below_baseline:
            # Even though we're ignoring the pixels below the baseline for spacing
            # purposes, we have to make sure we don't crop those pixels out during the
            # supersampling operations here.
            total_text_height += self.text_height_below_baseline

        resample_padding = 10 if self.supersampling_factor > 1 else 0

        if self.is_horizontal_scrolling_enabled:
            # Temp img will be the full width of the text
            image_width = self.text_width
        else:
            # Temp img will be the component's width, but must respect right edge padding
            image_width = self.width - self.edge_padding
        
        if self.supersampling_factor > 1:
            start = time.time()
            supersampled_font = Fonts.get_font(self.font_name, int(self.supersampling_factor * self.font_size))
            print(f"Supersampled font load time: {time.time() - start:.04}")
        else:
            supersampled_font = font

        img = Image.new(
            "RGBA",
            (
                image_width * self.supersampling_factor,
                (total_text_height + 2*resample_padding) * self.supersampling_factor
            ),
            self.background_color
            # "red"
        )
        draw = ImageDraw.Draw(img)

        cur_y = (resample_padding + self.text_height_above_baseline) * self.supersampling_factor

        if self.is_text_centered:
            # middle baseline
            anchor = "ms"
        else:
            # left baseline
            anchor = "ls"

        # Default, not-centered text will be relative to its left-justified starting point
        text_x = max([self.edge_padding, self.min_text_x])

        for line in self.text_lines:
            if self.is_text_centered:
                # We'll render with a centered anchor so we just need the midpoint
                text_x = int(self.width/2)
                if text_x - int(line["text_width"]/2) < self.min_text_x:
                    # The left edge of the centered text will protrude too far; nudge it right
                    text_x = self.min_text_x + int(line["text_width"]/2)
            
            elif self.is_horizontal_scrolling_enabled:
                # Scrolling temp img isn't relative to any positioning other than its own text
                text_x = 0

            draw.text((text_x * self.supersampling_factor, cur_y), line["text"], fill=self.font_color, font=supersampled_font, anchor=anchor)

            # Debugging: show the exact vertical extents of each line of text
            # draw.line((0, cur_y - self.text_height_above_baseline * self.supersampling_factor, image_width * self.supersampling_factor, cur_y - self.text_height_above_baseline * self.supersampling_factor), fill="blue", width=int(self.supersampling_factor))
            # draw.line((0, cur_y, image_width * self.supersampling_factor, cur_y), fill="red", width=int(self.supersampling_factor))

            cur_y += (self.text_height_above_baseline + self.line_spacing) * self.supersampling_factor

        # Crop off the top_padding and resize the result down to onscreen size
        if self.supersampling_factor > 1:
            resized = img.resize((image_width, total_text_height + 2*resample_padding), Image.LANCZOS)
            sharpened = resized.filter(ImageFilter.SHARPEN)

            img = sharpened.crop((0, resample_padding, image_width, resample_padding + total_text_height))
        
        self.rendered_text_img = img

        if not ImageFont.core.HAVE_RAQM:
            # At this point we need the visible_width to be the "actual" (yet still incorrect) width
            self.visible_width = int(self.visible_width * 0.95)

        self.horizontal_text_scroll_thread: TextArea.HorizontalTextScrollThread = None
        if self.is_horizontal_scrolling_enabled:
            self.horizontal_text_scroll_thread = TextArea.HorizontalTextScrollThread(
                rendered_text_img=self.rendered_text_img,
                screen_x=self.screen_x + self.min_text_x,
                screen_y=self.screen_y + self.text_y - self.text_height_above_baseline,
                visible_width=self.visible_width,
                horizontal_scroll_speed=self.horizontal_scroll_speed,
                begin_hold_secs=self.horizontal_scroll_begin_hold_secs,
                end_hold_secs=self.horizontal_scroll_end_hold_secs
            )


    class HorizontalTextScrollThread(BaseThread):
        """
        Note that Components in general should not try to manage the Renderer.lock; we
        leave that up to the calling Screen to manage. HOWEVER, since this renders in its
        own thread, we lose all normal timing guarantees and therefore this thread must
        manage the lock itself.
        """
        def __init__(self, rendered_text_img: Image, screen_x: int, screen_y: int, visible_width: int, horizontal_scroll_speed:int, begin_hold_secs: float, end_hold_secs: float):
            super().__init__()
            self.rendered_text_img = rendered_text_img
            self.screen_x = screen_x
            self.screen_y = screen_y
            self.visible_width = visible_width
            self.horizontal_scroll_speed = horizontal_scroll_speed
            self.begin_hold_secs = begin_hold_secs
            self.end_hold_secs = end_hold_secs

            self.scroll_y = 0
            self.scrolling_active = True
            self.horizontal_scroll_position = 0
            self.scroll_increment_sign = 1  # flip to negative to scroll text to the right

            self.renderer = Renderer.get_instance()        


        def stop_scrolling(self):
            self.scrolling_active = False


        def start_scrolling(self):
            # Reset scroll position to left edge
            self.horizontal_scroll_position = 0
            self.scroll_increment_sign = 1
            self.scrolling_active = True


        def run(self):
            """
            Subjective opinion: on a Pi Zero, scrolling at 40px/sec looks smooth but
            50px/sec creates a slight ghosting / doubling effect that impedes
            readability. 45px/sec is better but still perceptually a bit stuttery.
            """
            max_scroll = self.rendered_text_img.width - self.visible_width

            while self.keep_running:
                if not self.scrolling_active:
                    time.sleep(0.1)
                    continue

                with self.renderer.lock:
                    if not self.scrolling_active:
                        # We were stopped while waiting for the lock
                        continue

                    img = self.rendered_text_img.crop((self.horizontal_scroll_position, 0, self.horizontal_scroll_position + self.visible_width, self.rendered_text_img.height))
                    self.renderer.canvas.paste(img, (self.screen_x, self.screen_y - self.scroll_y))
                    self.renderer.show_image()

                if self.horizontal_scroll_position == 0:
                    # Pause on initial (left-justified) position...                
                    time.sleep(self.begin_hold_secs)

                    # Don't count those pause seconds
                    last_render_time = None

                    # Scroll the text left
                    self.scroll_increment_sign = 1

                elif self.horizontal_scroll_position == max_scroll:
                    # ...and slight pause at end of scroll
                    time.sleep(self.end_hold_secs)

                    # Don't count those pause seconds
                    last_render_time = None

                    # Scroll the text right
                    self.scroll_increment_sign = -1
                
                else:
                    # No need to CPU limit when running in its own thread?
                    time.sleep(0.02)
                
                next_render_time = time.time()

                if not last_render_time:
                    # First frame when pulling off either end will move 1 pixel; have to
                    # "get off zero" for the real increment calc logic to kick in.
                    scroll_position_increment = 1 * self.scroll_increment_sign
                else:
                    scroll_position_increment = int(self.horizontal_scroll_speed * (next_render_time - last_render_time) * self.scroll_increment_sign)

                if abs(scroll_position_increment) > 0:
                    self.horizontal_scroll_position += scroll_position_increment
                    self.horizontal_scroll_position = max(0, min(self.horizontal_scroll_position, max_scroll))

                    last_render_time = next_render_time
                else:
                    # Wait to accumulate more time before scrolling
                    pass


    def render(self):
        """
            Even if we need to animate for scrolling, all instances should explicitly render
            their initial state. Note that the screenshot generator currently does not render
            anything from within child threads.
        """
        # Default text and centered text already include any edge padding considerations
        # in their rendered img that we're about to paste onto the canvas.
        text_x = self.screen_x
        text_img = self.rendered_text_img
        if self.is_horizontal_scrolling_enabled:
            # Scrolling text has no edge considerations so must be placed exactly
            text_x += self.min_text_x

            # Must also account for the right edge running off our visible width
            text_img = text_img.crop((0, 0, self.visible_width, text_img.height))

        self.canvas.paste(text_img, (text_x, self.screen_y + self.text_y - self.text_height_above_baseline - self.scroll_y))


    def set_scroll_y(self, scroll_y: int):
        """ Used by ButtonListScreen """
        self.scroll_y = scroll_y
        if self.horizontal_text_scroll_thread:
            self.horizontal_text_scroll_thread.scroll_y = scroll_y



@dataclass
class ScrollableTextLine(TextArea):
    """
    Convenience class to more clearly communicate usage intention:
    * A single line of text
    * Can be centered (e.g. TopNav title)
    * Will automatically scroll if it does not fit the specified width
    """
    def __post_init__(self):
        self.auto_line_break = False
        self.is_horizontal_scrolling_enabled = True
        self.allow_text_overflow = True
        super().__post_init__()


    @property
    def needs_scroll(self) -> bool:
        return self.horizontal_text_scroll_thread is not None


    @property
    def scroll_thread(self) -> TextArea.HorizontalTextScrollThread:
        return self.horizontal_text_scroll_thread



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
            self.icon_font = Fonts.get_font(GUIConstants.ICON_FONT_NAME__FONT_AWESOME, self.icon_size)
        
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
    value_text: str = ""
    font_name: str = None
    font_size: int = None
    is_text_centered: bool = False
    auto_line_break: bool = False
    allow_text_overflow: bool = True
    screen_x: int = 0
    screen_y: int = 0

    def __post_init__(self):
        if not self.font_name:
            self.font_name = GUIConstants.get_body_font_name()
        if not self.font_size:
            self.font_size = GUIConstants.get_body_font_size()
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
                font_size=GUIConstants.get_body_font_size() - 2,
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

        # TRANSLATOR_NOTE: Testnet bitcoin
        btc_unit = _("tBtc")

        # TRANSLATOR_NOTE: Testnet sats
        sats_unit = _("tSats")
        if network == SettingsConstants.MAINNET:
            btc_unit = _("btc")
            sats_unit = _("sats")
            btc_color = GUIConstants.ACCENT_COLOR

        elif network == SettingsConstants.TESTNET:
            btc_color = GUIConstants.TESTNET_COLOR
        
        elif network == SettingsConstants.REGTEST:
            btc_color = GUIConstants.REGTEST_COLOR
        
        digit_font = Fonts.get_font(font_name=GUIConstants.get_body_font_name(), size=self.font_size)
        smaller_digit_font = Fonts.get_font(font_name=GUIConstants.get_body_font_name(), size=self.font_size - 2)
        unit_font_size = GUIConstants.get_button_font_size() + 2

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
            pipe_font = Fonts.get_font(font_name=GUIConstants.get_body_font_name(), size=self.icon_size - 4)
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
        unit_font = Fonts.get_font(font_name=GUIConstants.get_body_font_name(), size=unit_font_size)
        (left, top, unit_text_width, bottom) = unit_font.getbbox(unit_text, anchor="ls")
        unit_font_height = -1 * top

        unit_textarea = TextArea(
            image_draw=draw,
            canvas=self.paste_image,
            text=f" {unit_text}",
            font_name=GUIConstants.get_body_font_name(),
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
    """
    Buttons offer two rendering methods:

    * Reusable in-memory image (is_scrollable_text = True; default): For both active and
        inactive states, the text is rendered once (on a just-in-time basis) into an
        in-memory image that is then reused as needed during the life of the Component.

        Specifically built with l10n in mind. Will automatically add scrolling via
        ScrollableTextLine for the Button's active state when necessary; a static
        TextArea is used otherwise.

        This means that this setting is not suitable for Buttons whose
        text label needs to interactively change (e.g. the "ABC" vs "abc" soft keys in
        the passphrase entry Keyboard). 

    * Real-time text (is_scrollable_text = False): The label text's active/inactive state
        is just rendered as basic text on-the-fly, so it can support uses where the button
        label can change. Text scrolling is not supported in this mode so in general it
        should not to used with l10n content whose length might vary by language.

    """
    text: str = "Button Label"
    active_text: str = None  # Optional alt text to replace the button label when the button is selected
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
    font_name: str = None
    font_size: int = None
    font_color: str = GUIConstants.BUTTON_FONT_COLOR
    selected_font_color: str = GUIConstants.BUTTON_SELECTED_FONT_COLOR
    outline_color: str = None
    selected_outline_color: str = None
    is_text_centered: bool = True
    is_selected: bool = False
    is_scrollable_text: bool = True  # True: active state will automatically scroll if necessary, text is rendered once (not dynamic)


    def __post_init__(self):
        if not self.font_name:
            self.font_name = GUIConstants.get_button_font_name()
        
        if not self.font_size:
            self.font_size = GUIConstants.get_button_font_size()
        
        super().__post_init__()

        if not self.width:
            self.width = self.canvas_width - 2*GUIConstants.EDGE_PADDING

        if not self.height:
            self.height = GUIConstants.BUTTON_HEIGHT
        
        if not self.icon_color:
            self.icon_color = GUIConstants.BUTTON_FONT_COLOR

        self.active_button_label = None

        if self.text is not None:
            self.font = Fonts.get_font(self.font_name, self.font_size)

            # Calc true pixel height (any anchor from "baseline" will work)
            (left, top, self.text_width, bottom) = self.font.getbbox(self.text, anchor="ls")
            # print(f"left: {left} |  top: {top} | right: {self.text_width} | bottom: {bottom}")

            # Note: "top" is negative when measured from a "baseline" anchor. Intentionally
            # ignore any chars below the baseline for consistent vertical positioning
            # regardless of the Button text.
            self.text_height = -1 * top

            # Total space available just for the text (will contract later if there are icons)
            self.visible_text_width = self.width - 2*GUIConstants.COMPONENT_PADDING

            if self.text_width > self.visible_text_width and not self.is_scrollable_text:
                logger.warning("Button label \"{self.text}\" will not fit but is_scrollable_text is False")

            if self.is_text_centered and self.text_width < self.visible_text_width:
                # self.text_x = int(self.width/2)
                # self.text_anchor = "ms"  # centered horizontally, baseline

                # Calculate the centered text's starting point, but relative to the "ls"
                # anchor point.
                self.text_x = int((self.width - self.text_width)/2)
                self.text_anchor = "ls"  # left, baseline
            else:
                # Text is left-justified or has to be because it will be scrolled
                self.is_text_centered = False
                self.text_x = GUIConstants.COMPONENT_PADDING
                self.text_anchor = "ls"  # left, baseline

            if self.text_y_offset:
                self.text_y = self.text_y_offset + self.text_height
            else:
                self.text_y = self.height - int((self.height - self.text_height)/2)

        # Preload the icon and its "_selected" variant
        icon_padding = GUIConstants.COMPONENT_PADDING
        if self.icon_name:
            self.icon = Icon(icon_name=self.icon_name, icon_size=self.icon_size, icon_color=self.icon_color)
            self.icon_selected = Icon(icon_name=self.icon_name, icon_size=self.icon_size, icon_color=self.selected_icon_color)

            if self.icon_y_offset:
                self.icon_y = self.icon_y_offset
            else:
                self.icon_y = math.ceil((self.height - self.icon.height)/2)

            if self.is_icon_inline:
                self.visible_text_width -= self.icon.width + icon_padding
                if self.text_width > self.visible_text_width:
                    self.is_text_centered = False
                    self.text_x = GUIConstants.COMPONENT_PADDING

                    if not self.is_scrollable_text:
                        logger.warning("Button label \"{self.text}\" with icon inline will not fit but is_scrollable_text is False")

                if self.is_text_centered:
                    if self.text:
                        # Shift the text's center-based anchor to the right to make room
                        # self.text_x += int((self.icon.width + icon_padding) / 2)

                        # Shift the text's "ls"-based anchor to the right to make room
                        self.text_x += int((self.icon.width + icon_padding) / 2)

                        # Position the icon's left-based anchor on the left
                        self.icon_x = self.text_x - (self.icon.width + icon_padding)
                    else:
                        # TODO: Is an inline icon but w/no text even a sensible input configuration?
                        self.icon_x = math.ceil((self.width - self.icon.width)/2)

                else:
                    if self.text:
                        self.text_x += self.icon.width + icon_padding
                    self.icon_x = GUIConstants.COMPONENT_PADDING

            else:
                self.icon_x = int((self.width - self.icon.width) / 2)
                if self.text:
                    self.text_y = self.icon_y + self.icon.height + GUIConstants.COMPONENT_PADDING

        if self.right_icon_name:
            self.right_icon = Icon(icon_name=self.right_icon_name, icon_size=self.right_icon_size, icon_color=self.right_icon_color)
            self.right_icon_selected = Icon(icon_name=self.right_icon_name, icon_size=self.right_icon_size, icon_color=self.selected_icon_color)

            self.visible_text_width -= self.right_icon.width + icon_padding
            if self.text_width > self.visible_text_width:
                self.is_text_centered = False

                if not self.is_scrollable_text:
                    logger.warning("Button label \"{self.text}\" with icon inline will not fit but is_scrollable_text is False")

            self.right_icon_x = self.width - self.right_icon.width - GUIConstants.COMPONENT_PADDING

            self.right_icon_y = math.ceil((self.height - self.right_icon.height)/2)

        if self.text and self.is_scrollable_text:
            button_kwargs = dict(
                text=self.active_text if self.active_text else self.text,
                font_name=self.font_name,
                font_size=self.font_size,
                supersampling_factor=1,  # disable; not necessary at button font size. Also black text on orange supersamples poorly
                font_color=self.selected_font_color,
                background_color=self.selected_color,
                screen_x=self.screen_x,
                screen_y=self.screen_y + self.text_y_offset,
                width=self.width,
                height=self.text_height if self.icon_name and not self.is_icon_inline else self.height,
                min_text_x=self.text_x if self.icon_name and self.is_icon_inline else GUIConstants.COMPONENT_PADDING,
                is_text_centered=self.is_text_centered,
                height_ignores_below_baseline=True,  # Consistently vertically center text, ignoring chars that render below baseline (e.g. "pqyj")
                horizontal_scroll_speed=30,  #px per sec
                horizontal_scroll_begin_hold_secs=0.5,
                horizontal_scroll_end_hold_secs=0.5,
            )

            # ButtonListScreens with lots of buttons will take too long to pre-render all
            # the Buttons, so we use a just-in-time approach to create BOTH the active and
            # inactive Buttons. For simple "Done" screens, the inactive state will never be
            # rendered.
            self.active_button_label = None
            self.active_button_label_kwargs = button_kwargs.copy()

            button_kwargs["text"] = self.text
            button_kwargs["font_color"] = self.font_color
            button_kwargs["background_color"] = self.background_color
            button_kwargs["allow_text_overflow"] = True
            button_kwargs["auto_line_break"] = False
            del button_kwargs["horizontal_scroll_begin_hold_secs"]
            del button_kwargs["horizontal_scroll_end_hold_secs"]

            self.inactive_button_label = None
            self.inactive_button_label_kwargs = button_kwargs.copy()


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
            if not self.is_scrollable_text:
                # Just directly render the text for the current active/inactive state
                self.image_draw.text(
                    (self.screen_x + self.text_x, self.screen_y + self.text_y - self.scroll_y),
                    self.text,
                    fill=font_color,
                    font=self.font,
                    anchor=self.text_anchor
                )

            else:
                # Use just-in-time instatiation of pre-rendered ScrollableTextLine and TextArea
                if self.is_selected:
                    if not self.active_button_label:
                        # Just-in-time create the active button label
                        self.active_button_label = ScrollableTextLine(**self.active_button_label_kwargs)

                        if self.active_button_label.needs_scroll:
                            self.threads.append(self.active_button_label.scroll_thread)
                            self.active_button_label.scroll_thread.start()

                    self.active_button_label.set_scroll_y(self.scroll_y)
                    self.active_button_label.render()

                    if self.active_button_label.needs_scroll:
                        # Activate the scrollable text line
                        self.active_button_label.scroll_thread.start_scrolling()
                
                else:
                    if self.active_button_label and self.active_button_label.needs_scroll:
                        self.active_button_label.scroll_thread.stop_scrolling()

                    if not self.inactive_button_label:
                        # Just-in-time create the inactive button label
                        self.inactive_button_label = TextArea(**self.inactive_button_label_kwargs)

                    self.inactive_button_label.set_scroll_y(self.scroll_y)
                    self.inactive_button_label.render()

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
    is_scrollable_text: bool = False



@dataclass
class LargeIconButton(IconButton):
    """
        A button that is primarily a big icon (e.g. the Home screen buttons) w/text below
        the icon.
    """
    icon_size: int = GUIConstants.ICON_LARGE_BUTTON_SIZE
    icon_y_offset: int = GUIConstants.COMPONENT_PADDING
    is_scrollable_text: bool = True



@dataclass
class TopNav(BaseComponent):
    text: str = "Screen Title"
    width: int = None
    height: int = GUIConstants.TOP_NAV_HEIGHT
    background_color: str = GUIConstants.BACKGROUND_COLOR
    icon_name: str = None
    icon_color: str = GUIConstants.BODY_FONT_COLOR
    font_name: str = GUIConstants.get_top_nav_title_font_name()
    font_size: int = GUIConstants.get_top_nav_title_font_size()
    font_color: str = GUIConstants.BODY_FONT_COLOR
    show_back_button: bool = True
    show_power_button: bool = False
    is_selected: bool = False


    def __post_init__(self):
        if not self.font_name:
            self.font_name = GUIConstants.get_top_nav_title_font_name()
        
        if not self.font_size:
            self.font_size = GUIConstants.get_top_nav_title_font_size()
            print(f"self.font_size: {self.font_size}")

        super().__post_init__()
        if not self.width:
            self.width = self.canvas_width

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

        min_text_x = GUIConstants.EDGE_PADDING
        if self.show_back_button:
            # Don't let the title intrude on the BACK button
            min_text_x = self.left_button.screen_x + self.left_button.width + GUIConstants.COMPONENT_PADDING

        if self.icon_name:
            # TODO: Refactor IconTextLine to use ScrollableTextLine
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
            self.title = ScrollableTextLine(
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
            if self.title.needs_scroll:
                # Add the scroll thread to TopNav's self.threads so it automatically runs
                # for the life of the Component.
                self.threads.append(self.title.scroll_thread)


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
                          font_name=GUIConstants.get_body_font_name(),
                          font_size=GUIConstants.get_body_font_size(),
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
    font = Fonts.get_font(font_name=font_name, size=font_size)
    # Measure from left baseline ("ls")
    (left, top, full_text_width, bottom) = font.getbbox(text, anchor="ls")

    if not ImageFont.core.HAVE_RAQM:
        # Fudge factor for imprecise width calcs w/out libraqm
        full_text_width = int(full_text_width * 1.05)

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

            if not ImageFont.core.HAVE_RAQM:
                # Fudge factor for imprecise width calcs w/out libraqm
                line_width = int(line_width * 1.05)

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
                           font_name=GUIConstants.get_body_font_name(),
                           font_size=GUIConstants.get_body_font_size(),
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
