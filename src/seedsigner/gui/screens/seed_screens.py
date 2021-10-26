import os
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

from .base import ButtonListScreen, LargeButtonScreen
from ..components import load_icon, Fonts, TextArea, GUIConstants

from seedsigner.helpers import B
from seedsigner.models.seed import SeedConstants



@dataclass
class SeedValidScreen(ButtonListScreen):
    fingerprint: str = None
    title: str = "Seed Valid"
    is_bottom_list: bool = True

    def __post_init__(self):
        # Customize defaults
        self.button_data = [
            # ("Scan PSBT or Seed", "scan_inline"),
            "Home",
            ("Advanced", "settings_inline"),
        ]

        # Initialize the base class
        super().__post_init__()

        # TODO: Create a reusable Component that can display multi-line text w/an icon?
        """
            lines=[
                (None, "Fingerprint:"),
                "fingerprint", self.fingerprint,
            ]
            is_text_centered=True,

        """

        # Render each line on a separate Image that can be pasted onto the right place
        body_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BODY_FONT_MAX_SIZE)
        line_1_text = "Fingerprint:"
        line_2_text = self.fingerprint
        line_1_width, line_1_height = body_font.getsize(line_1_text)
        line_2_width, line_2_height = body_font.getsize(line_2_text)

        fingerprint_icon = load_icon("fingerprint")
        line_2_x = fingerprint_icon.width + int(GUIConstants.COMPONENT_PADDING / 2)
        line_2_y = line_1_height + int(GUIConstants.BODY_FONT_MAX_SIZE * GUIConstants.BODY_LINE_SPACING)

        body_content_width = max([
            line_1_width,
            line_2_x + line_2_width
        ])
        body_content_height = line_2_y + line_2_height

        self.body_content = Image.new('RGB', (body_content_width, body_content_height))
        body_content_draw = ImageDraw.Draw(self.body_content)
        body_content_draw.text((int((body_content_width - line_1_width) / 2), 0), line_1_text, fill=GUIConstants.BODY_FONT_COLOR, font=body_font)
        body_content_draw.text((line_2_x, line_2_y), line_2_text, fill=GUIConstants.BODY_FONT_COLOR, font=body_font)
        self.body_content.paste(fingerprint_icon, (0, line_2_y))

        self.body_content_x = int((self.canvas_width - body_content_width) / 2)
        self.body_content_y = self.top_nav.height + int((self.canvas_height - self.top_nav.height - self.buttons[0].screen_y) / 2)


    def _render(self):
        super()._render()

        # self.renderer.canvas.paste(self.fingerprint_icon, (self.fingerprint_icon_x, self.fingerprint_icon_y))
        self.renderer.canvas.paste(self.body_content, (self.body_content_x, self.body_content_y))

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
        # Programmatically set up other args
        self.button_data = [
            "View Seed Words",
            "Export Xpub",
            "Export Seed as QR",
        ]

        # Initialize the base class
        super().__post_init__()

        # TODO: Set up the fingerprint and passphrase displays

