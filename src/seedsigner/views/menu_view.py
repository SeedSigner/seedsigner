# Internal file class dependencies
from . import View

from seedsigner.gui.components import Fonts
from seedsigner.gui.screens import RET_CODE__BACK_BUTTON, ButtonListScreen
from seedsigner.helpers import B, Path, Buttons
from seedsigner.models import SeedStorage, Settings, Seed

# External Dependencies
import time
import re



class SeedToolsMenuView(View):
    def run(self, **kwargs):
        title = "Store a Seed"
        if self.controller.storage.num_of_saved_seeds() > 0:
            if self.controller.storage.num_of_saved_seeds() < 3:
                title = "View/Store Seeds"
            else:
                title = "View Seeds"

        selected_menu_num = ButtonListScreen(
            title=title,
            button_labels=["Temp Seed Storage",
                           "Seed Passphrase",
                           "Export xPub",
                           "Calc Last Word",
                           "New Seed w/Dice",
                           "New Seed w/Image"]
        ).display()

        return_views = [
            Path.SAVE_SEED,
            Path.PASSPHRASE_SEED,
            Path.GEN_XPUB,
            Path.GEN_LAST_WORD,
            Path.DICE_GEN_SEED,
            Path.IMAGE_GEN_SEED,
        ]

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            from . import MainMenuView
            return MainMenuView

        return return_views[selected_menu_num]




"""
    OLD CODE BELOW:
"""
class MenuView(View):

    def __init__(self) -> None:
        super().__init__()

        self.menu_lines = []
        self.selected_menu_num = 1


    ### Signing Tools Menu
    def display_signing_tools_menu(self) -> None:
        lines = ["... [ Return to Main ]", "Generate xPub", "Sign a Transaction"]
        self.draw_menu(lines, 1)
        input = 0

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            if input == B.KEY_UP:
                self.menu_up()
            elif input == B.KEY_DOWN:
                self.menu_down()
            elif input == B.KEY_PRESS:
                if self.selected_menu_num == 1:
                    return Path.MAIN_MENU
                elif self.selected_menu_num == 2:
                    return Path.GEN_XPUB
                elif self.selected_menu_num == 3:
                    return Path.SIGN_TRANSACTION
        raise Exception("Unhandled case")


    ### Settings Menu
    def display_settings_menu(self) -> int:
        lines = [
            "... [ Return to Main ]",
            f"Wallet: {Settings.get_instance().software}",
            f"Network: {Settings.get_instance().network}",
            f"QR Density: {Settings.get_instance().qr_density_name}",
            "Input / Output Tests",
            f"Persistent Settings: {Settings.get_instance().persistent_display}",
            "Camera Rotation",
            "Version Info",
            "Donate to SeedSigner",
            "Reset SeedSigner"
        ]
        input = 0

        # Draw Menu
        self.selected_menu_num = 1
        self.draw_menu(lines, 1, None, None, True)

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            if input == B.KEY_UP:
                self.menu_up()
            elif input == B.KEY_DOWN:
                self.menu_down()
            elif input == B.KEY_PRESS:
                if self.selected_menu_num == 1:
                    return Path.MAIN_MENU
                elif self.selected_menu_num == 2:
                    return Path.WALLET
                elif self.selected_menu_num == 3:
                    return Path.CURRENT_NETWORK
                elif self.selected_menu_num == 4:
                    return Path.QR_DENSITY_SETTING
                elif self.selected_menu_num == 5:
                    return Path.IO_TEST_TOOL
                elif self.selected_menu_num == 6:
                    return Path.PERSISTENT_SETTINGS
                elif self.selected_menu_num == 7:
                    return Path.CAMERA_ROTATION
                elif self.selected_menu_num == 8:
                    return Path.VERSION_INFO
                elif self.selected_menu_num == 9:
                    return Path.DONATE
                elif self.selected_menu_num == 10:
                    return Path.RESET
        raise Exception("Unhandled case")


    ### Generic Word 12 or 24 seed phrase menu
    # internal method
    def draw_12_24_word_menu(self, lines, return_txt = "... [ Return to ... ]") -> int:
        self.draw_menu(lines)

         # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            if input == B.KEY_UP:
                self.menu_up()
            elif input == B.KEY_DOWN:
                self.menu_down()
            elif input == B.KEY_PRESS:
                if self.selected_menu_num == 1:
                    return -1
                elif self.selected_menu_num == 2:
                    return Path.SEED_WORD_12
                elif self.selected_menu_num == 3:
                    return Path.SEED_WORD_24
                elif self.selected_menu_num == 4:
                    return Path.SEED_WORD_QR

    def display_12_24_word_menu(self, return_txt = "... [ Return to ... ]") -> int:
        lines = [return_txt, "Use a 12 Word Seed", "Use a 24 Word Seed"]
        return self.draw_12_24_word_menu(lines, return_txt)

    def display_qr_12_24_word_menu(self, return_txt = "... [ Return to ... ]") -> int:
        lines = [return_txt, "Enter 12 Word Seed", "Enter 24 Word Seed", "Scan a Seed QR Code"]
        return self.draw_12_24_word_menu(lines, return_txt)

    ### Select a Seed Slot to Save a Seed Menu

    def display_saved_seed_menu(self, storage, type = 1, return_sel_txt = "... [ Return to Seed Tools ]") -> int:
        lines = []
        if return_sel_txt != None:
            lines.append(return_sel_txt)

        if type == 1:
            # Show all slots used and free
            lines.extend(["Use Seed Slot #1", "Use Seed Slot #2", "Use Seed Slot #3"])
            if storage.check_slot_1():
                lines[1] = "Display Seed Slot #1" # replace
            if storage.check_slot_2():
                lines[2] = "Display Seed Slot #2" # replace
            if storage.check_slot_3():
                lines[3] = "Display Seed Slot #3" # replace
        elif type == 2:
            # Show only free slots
            if storage.check_slot_1() == False:
                lines.append("Use Seed Slot #1")
            if storage.check_slot_2() == False:
                lines.append("Use Seed Slot #2")
            if storage.check_slot_3() == False:
                lines.append("Use Seed Slot #3")
            if storage.num_of_free_slots() == 0:
                return 0
        elif type == 3:
            # Show only used slots
            if storage.check_slot_1():
                lines.append("Use Seed Slot #1")
            if storage.check_slot_2():
                lines.append("Use Seed Slot #2")
            if storage.check_slot_3():
                lines.append("Use Seed Slot #3")
        elif type == 4:
            # Show only used slots with passphrase
            if storage.check_slot_passphrase(1):
                lines.append("Seed Slot #1")
            if storage.check_slot_passphrase(2):
                lines.append("Seed Slot #2")
            if storage.check_slot_passphrase(3):
                lines.append("Seed Slot #3")

        else:
            return 0

        self.draw_menu(lines)

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            if input == B.KEY_UP:
                self.menu_up()
            elif input == B.KEY_DOWN:
                self.menu_down()
            elif input == B.KEY_PRESS:
                if lines[self.selected_menu_num-1] == return_sel_txt:
                    return 0
                else:
                    return int(re.search("#(\d+)", lines[self.selected_menu_num-1], re.IGNORECASE).group(1))
        raise Exception("Unhandled case")




