
from .view import View, Destination, BackStackView, MainMenuView

from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen,
    LargeButtonScreen, WarningScreen, DireWarningScreen)
from seedsigner.models.seed import SeedConstants
from seedsigner.models.settings import Settings, SettingsConstants



class ToolsMenuView(View):
    def run(self):
        screen = ButtonListScreen(
            title="Tools",
            is_button_text_centered=False,
            button_data=[
                "New seed from camera",
                "New seed from dice",
                "Calculate 12th/24th word",
            ]
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            return Destination(MainMenuView)

        if selected_menu_num == 1:
            return Destination(MainMenuView)

        if selected_menu_num == 2:
            return Destination(MainMenuView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

