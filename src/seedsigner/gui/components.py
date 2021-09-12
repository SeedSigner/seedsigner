import os
import pathlib

from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont



# TODO: Remove all pixel hard coding
EDGE_PADDING = 4
COMPONENT_PADDING = 8


# DEBUGGING
def load_font(font_name, size):
    font_path = os.path.join(pathlib.Path(__file__).parent.resolve(), "..", "resources", "fonts")
    return ImageFont.truetype(os.path.join(font_path, font_name), size)



class Fonts:
    font_path = os.path.join(pathlib.Path(__file__).parent.resolve(), "..", "resources", "fonts")
    ASSISTANT_REGULAR_16 = ImageFont.truetype(os.path.join(font_path, "Assistant-Regular.ttf"), 16)
    ASSISTANT_REGULAR_18 = ImageFont.truetype(os.path.join(font_path, "Assistant-Regular.ttf"), 18)
    ASSISTANT_REGULAR_20 = ImageFont.truetype(os.path.join(font_path, "Assistant-Regular.ttf"), 20)
    ASSISTANT_REGULAR_22 = ImageFont.truetype(os.path.join(font_path, "Assistant-Regular.ttf"), 22)
    ASSISTANT_REGULAR_24 = ImageFont.truetype(os.path.join(font_path, "Assistant-Regular.ttf"), 24)
    ASSISTANT_REGULAR_26 = ImageFont.truetype(os.path.join(font_path, "Assistant-Regular.ttf"), 26)
    ASSISTANT_REGULAR = [
        ASSISTANT_REGULAR_26,
        ASSISTANT_REGULAR_24,
        ASSISTANT_REGULAR_22,
        ASSISTANT_REGULAR_20,
        ASSISTANT_REGULAR_18,
        ASSISTANT_REGULAR_16,
    ]

    ASSISTANT_BOLD_16 = ImageFont.truetype(os.path.join(font_path, "Assistant-Bold.ttf"), 16)
    ASSISTANT_BOLD_18 = ImageFont.truetype(os.path.join(font_path, "Assistant-Bold.ttf"), 18)
    ASSISTANT_BOLD_20 = ImageFont.truetype(os.path.join(font_path, "Assistant-Bold.ttf"), 20)
    ASSISTANT_BOLD_22 = ImageFont.truetype(os.path.join(font_path, "Assistant-Bold.ttf"), 22)
    ASSISTANT_BOLD_24 = ImageFont.truetype(os.path.join(font_path, "Assistant-Bold.ttf"), 24)
    ASSISTANT_BOLD_26 = ImageFont.truetype(os.path.join(font_path, "Assistant-Bold.ttf"), 26)
    ASSISTANT_BOLD = [
        ASSISTANT_BOLD_26,
        ASSISTANT_BOLD_24,
        ASSISTANT_BOLD_22,
        ASSISTANT_BOLD_20,
        ASSISTANT_BOLD_18,
        ASSISTANT_BOLD_16,
    ]

    OPENSANS_SEMIBOLD_16 = ImageFont.truetype(os.path.join(font_path, "OpenSans-SemiBold.ttf"), 16)
    OPENSANS_SEMIBOLD_18 = ImageFont.truetype(os.path.join(font_path, "OpenSans-SemiBold.ttf"), 18)
    OPENSANS_SEMIBOLD_20 = ImageFont.truetype(os.path.join(font_path, "OpenSans-SemiBold.ttf"), 20)
    OPENSANS_SEMIBOLD_22 = ImageFont.truetype(os.path.join(font_path, "OpenSans-SemiBold.ttf"), 22)
    OPENSANS_SEMIBOLD_24 = ImageFont.truetype(os.path.join(font_path, "OpenSans-SemiBold.ttf"), 24)
    OPENSANS_SEMIBOLD_26 = ImageFont.truetype(os.path.join(font_path, "OpenSans-SemiBold.ttf"), 26)


    BODY_TEXT = ASSISTANT_REGULAR_18
    PAGE_TITLE = ASSISTANT_REGULAR_26
    PAGE_TITLE_SMALLER = ASSISTANT_REGULAR_20
    PAGE_TITLE_SMALLEST = ASSISTANT_REGULAR_18
    BUTTON = OPENSANS_SEMIBOLD_24


    ROBOTOCONDENSED_BOLD_16 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 16)
    ROBOTOCONDENSED_BOLD_18 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 18)
    ROBOTOCONDENSED_BOLD_20 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 20)
    ROBOTOCONDENSED_BOLD_22 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 20)
    ROBOTOCONDENSED_BOLD_24 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 22)
    ROBOTOCONDENSED_BOLD_25 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 25)
    ROBOTOCONDENSED_BOLD_26 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 26)
    ROBOTOCONDENSED_BOLD_28 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 28)
    ROBOTOCONDENSED_LIGHT_16 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Light.ttf"), 16)
    ROBOTOCONDENSED_LIGHT_24 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Light.ttf"), 24)
    ROBOTOCONDENSED_REGULAR_16 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 16)
    ROBOTOCONDENSED_REGULAR_20 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 20)
    ROBOTOCONDENSED_REGULAR_18 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 18)
    ROBOTOCONDENSED_REGULAR_22 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 22)
    ROBOTOCONDENSED_REGULAR_24 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 24)
    ROBOTOCONDENSED_REGULAR_26 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 26)
    ROBOTOCONDENSED_REGULAR_28 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 28)


@dataclass
class Button:
    # TODO: Rename the seedsigner.helpers.Buttons class (to Inputs?)
    """
        Attrs with defaults must be listed last.
    """
    text: str     # display value
    screen_x: int
    screen_y: int
    width: int
    height: int
    draw: ImageDraw
    background_color: str = "#333"
    selected_color: str = "orange"
    font: ImageFont = None
    font_color: str = "white"
    selected_font_color: str = "black"
    is_text_centered: bool = True
    is_selected: bool = False


    def __post_init__(self):
        if not self.font:
            self.font = Fonts.BUTTON

        self.text_width, self.text_height = self.font.getsize(self.text)
        if self.is_text_centered:
            self.text_x = self.screen_x + int((self.width - self.text_width) / 2)
        else:
            self.text_x = self.screen_x + COMPONENT_PADDING
        self.text_y = self.screen_y + int((self.height - self.text_height) / 2)


    def render(self):
        if self.is_selected:
            background_color = self.selected_color
            font_color = self.selected_font_color
        else:
            background_color = self.background_color
            font_color = self.font_color

        self.draw.rounded_rectangle((self.screen_x, self.screen_y, self.screen_x + self.width, self.screen_y + self.height), fill=background_color, radius=COMPONENT_PADDING)
        self.draw.text((self.text_x, self.text_y), self.text, fill=font_color, font=self.font)



@dataclass
class TopNav:
    text: str
    width: int
    height: int
    draw: ImageDraw
    background_color: str = "black"
    font: ImageFont = None
    font_color: str = "white"


    def __post_init__(self):
        button_width = int(self.width * 2.0 / 15.0)     # 32px on 240x240 screen
        self.back_button = Button(
            text="<",
            screen_x=EDGE_PADDING,
            screen_y=EDGE_PADDING,
            width=button_width,
            height=button_width,
            draw=self.draw
        )
        self.context_button = Button(
            text="?",
            screen_x=self.width - button_width - EDGE_PADDING,
            screen_y=EDGE_PADDING,
            width=button_width,
            height=button_width,
            draw=self.draw
        )

        if not self.font:
            # Pre-calc how much room the title bar text will take up. Use the biggest font
            #   that will fit.
            max_font_width = self.width - (2 * self.back_button.width) - (4 * EDGE_PADDING)
            for font in Fonts.ASSISTANT_BOLD:
                self.text_width, self.text_height = font.getsize(self.text)
                if self.text_width < max_font_width:
                    self.font = font
                    self.text_x = int((self.width - self.text_width) / 2)
                    self.text_y = int((self.height - self.text_height) / 2)
                    break

        else:
            # TESTING
            self.text_width, self.text_height = self.font.getsize(self.text)
            self.text_x = int((self.width - self.text_width) / 2)
            self.text_y = int((self.height - self.text_height) / 2)
            # End TESTING



    def update_from_input(self, input, enter_from=None):
        pass


    def render(self):
        self.draw.rectangle((0, 0, self.width, self.height), fill=self.background_color)
        self.back_button.render()
        self.context_button.render()
        # self.right_button.render()
        self.draw.text((self.text_x, self.text_y), self.text, fill=self.font_color, font=self.font)



