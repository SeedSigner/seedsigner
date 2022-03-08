from seedsigner.gui.components import FontAwesomeIconConstants
from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen)
from seedsigner.gui.screens.tools_screens import ToolsCalcFinalWordShowFinalWordScreen
from seedsigner.views.seed_views import SeedDiscardView, SeedFinalizeView, SeedMnemonicEntryView

from .view import NotYetImplementedView, View, Destination, BackStackView, MainMenuView



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
            return Destination(NotYetImplementedView)

        elif button_data[selected_menu_num] == DICE:
            return Destination(NotYetImplementedView)

        if button_data[selected_menu_num] == KEYBOARD:
            return Destination(ToolsCalcFinalWordNumWordsView)



class ToolsCalcFinalWordNumWordsView(View):
    def run(self):
        TWELVE = "12 words"
        TWENTY_FOUR = "24 words"
        
        button_data = [TWELVE, TWENTY_FOUR]
        selected_menu_num = ButtonListScreen(
            title="Mnemonic Length",
            is_bottom_list=True,
            is_button_text_centered=True,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == TWELVE:
            self.controller.storage.init_pending_mnemonic(12)
            return Destination(SeedMnemonicEntryView, view_args={"is_calc_final_word": True})

        elif button_data[selected_menu_num] == TWENTY_FOUR:
            self.controller.storage.init_pending_mnemonic(24)
            return Destination(SeedMnemonicEntryView, view_args={"is_calc_final_word": True})



class ToolsCalcFinalWordShowFinalWordView(View):
    def run(self):
        mnemonic = self.controller.storage.pending_mnemonic
        mnemonic_word_length = len(mnemonic)
        final_word = mnemonic[-1]

        LOAD = "Load seed"
        DISCARD = ("Discard", None, None, "red")
        button_data = [LOAD, DISCARD]

        selected_menu_num = ToolsCalcFinalWordShowFinalWordScreen(
            final_word=final_word,
            mnemonic_word_length=mnemonic_word_length,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        self.controller.storage.convert_pending_mnemonic_to_pending_seed()

        if button_data[selected_menu_num] == LOAD:
            return Destination(SeedFinalizeView)
        
        elif button_data[selected_menu_num] == DISCARD:
            return Destination(SeedDiscardView)
