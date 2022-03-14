from dataclasses import dataclass
from typing import List
from seedsigner.gui.components import CheckboxButton, CheckedSelectionButton, GUIConstants, TextArea

from seedsigner.gui.screens.screen import ButtonListScreen
from seedsigner.models.settings import SettingsConstants


@dataclass
class SettingsEntryUpdateSelectionScreen(ButtonListScreen):
    display_name: str = None
    help_text: str = None
    checked_buttons: List[int] = None
    settings_entry_type: str = SettingsConstants.TYPE__ENABLED_DISABLED
    selected_button: int = 0

    def __post_init__(self):
        self.title = "Settings"
        self.is_bottom_list = True
        self.use_checked_selection_buttons = True
        if self.settings_entry_type == SettingsConstants.TYPE__MULTISELECT:
            self.Button_cls = CheckboxButton
        else:
            self.Button_cls = CheckedSelectionButton
        super().__post_init__()

        self.title_textarea = TextArea(
            text=self.display_name,
            font_size=GUIConstants.BODY_FONT_MAX_SIZE,
            is_text_centered=True,
            auto_line_break=False,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        self.components.append(self.title_textarea)

        if self.help_text:
            self.title_textarea = TextArea(
                text=self.help_text,
                font_color=GUIConstants.LABEL_FONT_COLOR,
                is_text_centered=True,
                screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING
            )
            self.components.append(self.title_textarea)
