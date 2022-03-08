

from dataclasses import dataclass
from seedsigner.gui.components import GUIConstants, TextArea

from seedsigner.gui.screens.screen import ButtonListScreen



@dataclass
class ToolsCalcFinalWordShowFinalWordScreen(ButtonListScreen):
    final_word: str = None
    mnemonic_word_length: int = 12

    def __post_init__(self):
        # Customize defaults
        self.title = "Final Word"
        self.is_bottom_list = True

        super().__post_init__()

        self.components.append(TextArea(
            text=f"{self.mnemonic_word_length}th word:",
            font_size=GUIConstants.BUTTON_FONT_SIZE,
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        ))

        self.components.append(TextArea(
            text=self.final_word,
            font_size=GUIConstants.TOP_NAV_TITLE_FONT_SIZE,
            is_text_centered=True,
            screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
        ))
