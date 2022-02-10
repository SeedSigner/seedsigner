
from seedsigner.gui.components import FontAwesomeIconConstants
from .view import View, Destination, BackStackView, MainMenuView

from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen,
    LargeButtonScreen, WarningScreen, DireWarningScreen)
from seedsigner.models.seed import SeedConstants
from seedsigner.models.settings import Settings, SettingsConstants



class ToolsMenuView(View):
    def run(self):
        IMAGE = (" New seed", FontAwesomeIconConstants.CAMERA)
        DICE = ("New seed", FontAwesomeIconConstants.DICE)
        KEYBOARD = ("Calc 12th/24th word", FontAwesomeIconConstants.KEYBOARD)
        button_data = [IMAGE, DICE, KEYBOARD]
        screen = ButtonListScreen(
            title="Tools",
            is_button_text_centered=False,
            button_data=button_data
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == IMAGE:
            return Destination(MainMenuView)

        elif button_data[selected_menu_num] == DICE:
            return Destination(MainMenuView)

        if button_data[selected_menu_num] == KEYBOARD:
            return Destination(MainMenuView)

