from dataclasses import dataclass

from seedsigner.gui.components import TextArea, GUIConstants
from seedsigner.gui.screens import ButtonListScreen


@dataclass
class RequestAddressShareAddressScreen(ButtonListScreen):
    address: str = None
    derivation_index_id: int = None

    def __post_init__(self):
        self.title = f"m/44'/148'/{self.derivation_index_id}'"
        self.is_bottom_list = True

        super().__post_init__()

        break_point = 14
        # break every 14 characters
        address_with_break = " ".join(
            [
                self.address[i : i + break_point]
                for i in range(0, len(self.address), break_point)
            ]
        )

        self.components.append(
            TextArea(
                text=address_with_break,
                font_size=GUIConstants.BODY_FONT_MAX_SIZE + 1,
                font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                screen_y=self.top_nav.height,
                is_text_centered=True,
            )
        )
