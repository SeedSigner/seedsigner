import time

from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
from typing import List

from .screen import BaseTopNavScreen, ButtonListScreen
from ..components import GUIConstants, Fonts, IconTextLine, TextArea, calc_text_centering

from seedsigner.helpers import B
from seedsigner.models import DecodeQR, DecodeQRStatus, psbt_parser



@dataclass
class PSBTOverviewScreen(ButtonListScreen):
    title: str = "Review PSBT"
    is_bottom_list: bool = True
    spend_amount: int = 0
    change_amount: int = 0
    fee_amount: int = 0
    num_inputs: int = 0
    num_receive_addrs: int = 0
    policy_sigs_m: int = 0
    policy_sigs_n: int = 0
    

    def __post_init__(self):
        # Customize defaults
        self.button_data = ["Next"]

        super().__post_init__()

        self.icon_text_lines: List[IconTextLine] = []

        self.spend_label = TextArea(
            text="spend:",
            screen_y=self.top_nav.height - GUIConstants.COMPONENT_PADDING,
            font_size=GUIConstants.LABEL_FONT_SIZE,
            font_color=GUIConstants.LABEL_FONT_COLOR,
            is_text_centered=True,
            auto_line_break=False,
        )

        font_size = GUIConstants.BODY_FONT_SIZE

        icon_text_lines_y = self.spend_label.screen_y + self.spend_label.height
        self.icon_text_lines.append(IconTextLine(
            icon_name="btc_logo_30x30",
            is_text_centered=True,
            value_text=f"{self.spend_amount:,} sats",
            font_size=24,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=icon_text_lines_y,
        ))

        icon_text_lines_y += self.icon_text_lines[-1].height + 2*GUIConstants.COMPONENT_PADDING
        self.icon_text_lines.append(IconTextLine(
            icon_name="btc_logo_bw",
            value_text=f"Fee: {self.fee_amount:,} sats",
            font_size=font_size,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=icon_text_lines_y,
        ))

        icon_text_lines_y += font_size + GUIConstants.COMPONENT_PADDING
        self.icon_text_lines.append(IconTextLine(
            icon_name="btc_logo_bw",
            value_text=f"Change: {self.change_amount:,} sats",
            font_size=font_size,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=icon_text_lines_y,
        ))

        icon_text_lines_y += font_size + GUIConstants.COMPONENT_PADDING
        self.icon_text_lines.append(IconTextLine(
            icon_name="fingerprint",
            value_text=f"""{self.num_inputs} input{"s" if self.num_inputs > 1 else ""} -> {self.num_receive_addrs} recipient{"s" if self.num_receive_addrs > 1 else ""}""",
            font_size=font_size,
            screen_x=GUIConstants.COMPONENT_PADDING,
            screen_y=icon_text_lines_y,
        ))


    def _render(self):
        super()._render()

        self.spend_label.render()
        for icon_text_line in self.icon_text_lines:
            icon_text_line.render()

        # Write the screen updates
        self.renderer.show_image()
