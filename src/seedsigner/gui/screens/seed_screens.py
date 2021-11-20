from enum import auto
import os
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

from .screen import ButtonListScreen, LargeButtonScreen, WarningScreenMixin
from ..components import load_icon, Fonts, TextArea, GUIConstants, IconTextLine

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
            ("Scan a PSBT", "scan_inline"),
            "Seed Tools",
            ("Advanced", "settings_inline"),
        ]

        # Initialize the base class
        super().__post_init__()

        self.title_textarea = TextArea(
            text="Fingerprint:",
            is_text_centered=True,
            auto_line_break=False,
            screen_y=self.top_nav.height + int((self.buttons[0].screen_y - self.top_nav.height) / 2) - 30
        )

        self.fingerprint_icontl = IconTextLine(
            icon_name="fingerprint",
            value_text=self.fingerprint,
            font_size=GUIConstants.BODY_FONT_SIZE + 2,
            is_text_centered=True,
            screen_x = -4,
            screen_y=self.title_textarea.screen_y + self.title_textarea.height
        )

    def _render(self):
        super()._render()

        self.title_textarea.render()
        self.fingerprint_icontl.render()

        # self.renderer.canvas.paste(self.body_content, (self.body_content_x, self.body_content_y))

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

        self.fingerprint_icontextline = IconTextLine(
            icon_name="fingerprint",
            value_text=self.fingerprint,
            is_text_centered=True,
            screen_y=self.top_nav.height
        )


    def _render(self):
        super()._render()
        self.fingerprint_icontextline.render()


@dataclass
class SeedExportXpubDetailsScreen(WarningScreenMixin, ButtonListScreen):
    # Customize defaults
    title: str = "Xpub Details"
    is_bottom_list: bool = True
    fingerprint: str = None
    has_passphrase: bool = False
    derivation_path: str = "m/84'/0'/0'"
    xpub: str = "zpub6r..."
    button_data=["Export Xpub"]

    def __post_init__(self):
        # Programmatically set up other args
        self.button_data = ["Export Xpub"]

        # Initialize the base class
        super().__post_init__()

        # Set up the fingerprint and passphrase displays
        self.fingerprint_line = IconTextLine(
            icon_name="fingerprint",
            label_text="Fingerprint",
            value_text=self.fingerprint,
            screen_x=8,
            screen_y=self.top_nav.height,
        )

        self.derivation_line = IconTextLine(
            icon_name="fingerprint",
            label_text="Derivation",
            value_text=self.derivation_path,
            screen_x=8,
            screen_y=self.fingerprint_line.screen_y + self.fingerprint_line.height + 8,
        )

        self.xpub_line = IconTextLine(
            icon_name="fingerprint",
            label_text="Xpub",
            value_text=self.xpub,
            screen_x=8,
            screen_y=self.derivation_line.screen_y + self.derivation_line.height + 8,
        )


    def _render(self):
        super()._render()

        self.fingerprint_line.render()
        self.derivation_line.render()
        self.xpub_line.render()

        self.render_warning_edges()

        # Write the screen updates
        self.renderer.show_image()