from dataclasses import dataclass

from lumensigner.gui.components import TextArea, GUIConstants
from lumensigner.gui.screens import ButtonListScreen


@dataclass
class SignHashShowAddressScreen(ButtonListScreen):
    address: str = None

    def __post_init__(self):
        self.title = "Sign with"
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


@dataclass
class SignHashShowHashScreen(ButtonListScreen):
    hash: str = None

    def __post_init__(self):
        self.title = "Hash"
        self.is_bottom_list = True

        super().__post_init__()

        break_point = 16
        # break every 16 characters
        hash_with_break = " ".join(
            [
                self.hash[i : i + break_point]
                for i in range(0, len(self.hash), break_point)
            ]
        )

        self.components.append(
            TextArea(
                text=hash_with_break,
                font_size=GUIConstants.BODY_FONT_MAX_SIZE + 1,
                font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                screen_y=self.top_nav.height,
                is_text_centered=True,
            )
        )
