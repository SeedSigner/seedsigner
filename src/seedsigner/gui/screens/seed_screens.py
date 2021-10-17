import os
from dataclasses import dataclass
from PIL import Image

from .base import ButtonListScreen
from ..components import TextArea, BODY_LINE_SPACING

from seedsigner.helpers import B



@dataclass
class SeedValidScreen(ButtonListScreen):
    fingerprint: str = None

    def __post_init__(self):
        # Customize defaults
        self.title = "Seed Valid"
        self.is_bottom_list = True
        self.button_labels = [
            # ("Scan PSBT or Seed", "scan_inline"),
            "Home",
            ("Advanced", "settings_inline"),
        ]

        # Initialize the base class
        super().__post_init__()

        dirname = os.path.dirname(__file__)
        icon_url = os.path.join(dirname, "..", "..", "..", "seedsigner", "resources", "icons", "fingerprint.png")
        self.fingerprint_icon = Image.open(icon_url).convert("RGBA")

        self.text_line_1 = TextArea(
            text="Fingerprint:",
            width=self.canvas_width
        )
        self.text_line_2 = TextArea(
            text=self.fingerprint,
            width=self.canvas_width
        )

        # Position the TextAreas
        total_text_height = self.text_line_1.height + int(self.text_line_1.height * BODY_LINE_SPACING) + self.text_line_2.height
        main_area_height = self.buttons[0].screen_y - self.top_nav.height
        self.text_line_1.screen_y = self.top_nav.height + int((main_area_height - total_text_height) / 2)
        self.text_line_2.screen_y = self.text_line_1.screen_y + int(self.text_line_1.height * (1.0 + BODY_LINE_SPACING))

        # Have to shift line 2 over to accomodate the fingerprint icon
        self.text_line_2.screen_x += int((self.fingerprint_icon.width) / 2)

        self.fingerprint_icon_x = int((self.canvas_width - (self.fingerprint_icon.width + 4 + self.text_line_2.text_width)) / 2)
        self.fingerprint_icon_y = self.text_line_2.screen_y


    def _render(self):
        super()._render()

        self.text_line_1.render()
        self.text_line_2.render()
        self.renderer.canvas.paste(self.fingerprint_icon, (self.fingerprint_icon_x, self.fingerprint_icon_y))

        # Write the screen updates
        self.renderer.show_image()

