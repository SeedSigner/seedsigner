from typing import List, Tuple

from .view import View, Destination, BackStackView, MainMenuView

from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen)
from seedsigner.models.seed import SeedConstants
from seedsigner.models.settings import Settings, SettingsConstants


class BaseSettingsSelectionView(View):
    title: str
    category: str
    key: str
    options: List[Tuple[str,str]]

    def run(self):
        button_data = []
        for option in self.options:
            button_data.append(option[0])

        screen = ButtonListScreen(
            title=self.title,
            is_button_text_centered=False,
            button_data=button_data
        )
        selected_menu_num = screen.display()

        if selected_menu_num != RET_CODE__BACK_BUTTON:
            self.settings.set_value(category=self.category,
                                    key=self.key,
                                    value=self.options[selected_menu_num][1])

        return Destination(BackStackView)



class SettingsMenuView(View):
    def run(self):
        menu_items = [
            ("Persistent Settings", PersistentSettingsSettingView),
            ("Xpub Export", XpubExportSettingView),
            ("Another Setting", None),
            ("Foo Setting", None),
            ("Bar Setting", None),
            ("Sudoku Mode", None),
            ("Donate", None),
        ]

        screen = ButtonListScreen(
            title="Settings",
            is_button_text_centered=False,
            button_data=[item[0] for item in menu_items],
        )
        selected_menu_num = screen.display()

        if selected_menu_num < len(menu_items):
            return Destination(menu_items[selected_menu_num][1])

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class PersistentSettingsSettingView(BaseSettingsSelectionView):
    title:str = "Persistent Settings"
    category: str = "system"
    key: str = "persistent_settings"
    options = [("Enable", SettingsConstants.OPTION__ENABLED),
               ("Disable", SettingsConstants.OPTION__DISABLED)]



class XpubExportSettingView(BaseSettingsSelectionView):
    title:str = "Xpub Export"
    category: str = "features"
    key: str = "xpub_export"
    options = [("Enable", SettingsConstants.OPTION__ENABLED),
               ("Disable", SettingsConstants.OPTION__DISABLED)]
