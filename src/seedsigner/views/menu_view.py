# Internal file class dependencies
from . import View
from seedsigner.helpers import B, Path
from seedsigner.models import SeedStorage, Settings

# External Dependencies
import time
import re


class MenuView(View):

    def __init__(self) -> None:
        View.__init__(self)

        self.menu_lines = []
        self.selected_menu_num = 1

    ###
    ### Main Navigation
    ###

    ### Main Menu

    def display_main_menu(self, sub_menu = None) -> int:
        ret_val = 0
        input = 0
        lines = ["Seed Tools", "Scan QR", "Settings", "Power Off"]

        if sub_menu == Path.SEED_TOOLS_SUB_MENU:
            return self.display_seed_tools_menu()
        elif sub_menu == Path.SIGNING_TOOLS_SUB_MENU:
            return Path.SIGN_TRANSACTION
        elif sub_menu == Path.SETTINGS_SUB_MENU:
            return self.display_settings_menu()
        else:
            self.draw_menu(lines, 1)

        # Wait for Button Input (specifically menu selection/press)
        while True:
            if ret_val == 0:
                input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            else:
                return ret_val
            if input == B.KEY_UP:
                self.menu_up()
            elif input == B.KEY_DOWN:
                self.menu_down()
            elif input == B.KEY_PRESS:
                if self.selected_menu_num == 1:
                    ret_val = self.display_seed_tools_menu()
                elif self.selected_menu_num == 2:
                    ret_val = Path.SIGN_TRANSACTION
                elif self.selected_menu_num == 3:
                    ret_val = self.display_settings_menu()
                elif self.selected_menu_num == 4:
                    ret_val = Path.POWER_OFF

                if ret_val != Path.MAIN_MENU: # When no main menu, return to controller
                    return ret_val
                else:
                    self.draw_menu(lines)

    ### Seed Tools Menu

    def display_seed_tools_menu(self) -> int:
        seed_storage_line = "Store a Seed (temp)"
        if self.controller.storage.num_of_saved_seeds() > 0:
            if self.controller.storage.num_of_saved_seeds() < 3:
                seed_storage_line = "View/Store Seeds (temp)"
            else:
                seed_storage_line = "View Seeds (temp)"

        lines = ["... [ Return to Main ]", "Temp Seed Storage", "Seed Passphrase", "xPub from Seed", "Calculate Last Word", "Generate Seed with Dice", "Generate Seed with Image"]
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
                    return Path.SAVE_SEED
                elif self.selected_menu_num == 3:
                    return Path.PASSPHRASE_SEED
                elif self.selected_menu_num == 4:
                    return Path.GEN_XPUB
                elif self.selected_menu_num == 5:
                    return Path.GEN_LAST_WORD
                elif self.selected_menu_num == 6:
                    return Path.DICE_GEN_SEED
                elif self.selected_menu_num == 7:
                    return Path.IMAGE_GEN_SEED

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
        lines = ["... [ Return to Main ]", "Wallet: <wallet>", "Script Policy: <policy>", "Network: <network>", "QR Density: <density>", "Input / Output Tests", "Persistent Settings: <persistent>", "Version Info", "Donate to SeedSigner", "Reset SeedSigner"]
        input = 0
        
        lines[1] = lines[1].replace("<wallet>", Settings.get_instance().software)
        lines[2] = lines[2].replace("<policy>", Settings.get_instance().policy_name)
        lines[3] = lines[3].replace("<network>", Settings.get_instance().network)
        lines[4] = lines[4].replace("<density>", Settings.get_instance().qr_density_name)
        lines[6] = lines[6].replace("<persistent>", Settings.get_instance().persistent_display)

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
                    return Path.WALLET_POLICY
                elif self.selected_menu_num == 4:
                    return Path.CURRENT_NETWORK
                elif self.selected_menu_num == 5:
                    return Path.QR_DENSITY_SETTING
                elif self.selected_menu_num == 6:
                    return Path.IO_TEST_TOOL
                elif self.selected_menu_num == 7:
                    return Path.PERSISTENT_SETTINGS
                elif self.selected_menu_num == 8:
                    return Path.VERSION_INFO
                elif self.selected_menu_num == 9:
                    return Path.DONATE
                elif self.selected_menu_num == 10:
                    return Path.RESET
        raise Exception("Unhandled case")

    ### Generic Single Menu Selection (returns 1,2,3,4,5,6 ...)

    def display_generic_selection_menu(self, lines = [], title = None, bottom = None) -> int:
        self.selected_menu_num = 1
        self.draw_menu(lines, 1, title, bottom, True)

        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            if input == B.KEY_UP:
                self.menu_up(title, bottom)
            elif input == B.KEY_DOWN:
                self.menu_down(title, bottom)
            elif input == B.KEY_PRESS:
                return self.selected_menu_num
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

    ###
    ### Generic Reusable Menu Methods/Functions
    ###

    ### Generic Draw Menu Method
    # TODO: Optimize updates by just redrawing the no-longer highlighted line and the newly highlighted line
    def draw_menu(self, lines, selected_menu_num = 1, title = None, bottom = None, force_redraw = False) -> None:
        if title == None:
            t = "SeedSigner  v" + self.controller.VERSION
        else:
            t = title

        if bottom == None and len(lines) <= 5:
            b = "Press Control Stick to Select"
        elif bottom == None:
            if len(lines) >= 6 and len(lines) <= 10:
                if selected_menu_num <= 5:
                    b = "Page 1 of 2"
                elif selected_menu_num >= 6 and selected_menu_num <= 10:
                    b = "Page 2 of 2"
            elif len(lines) >= 11 and len(lines) <= 15:
                if selected_menu_num <= 5:
                    b = "Page 1 of 3"
                elif selected_menu_num >= 6 and selected_menu_num <= 10:
                    b = "Page 2 of 3"
                elif selected_menu_num >= 11 and selected_menu_num <= 15:
                    b = "Page 3 of 3"
            else:
                b = "Press Control Stick to Select"
        else:
            b = bottom

        if lines != self.menu_lines or selected_menu_num != self.selected_menu_num or force_redraw == True:
            #Menu has changed, redraw

            View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
            tw, th = View.draw.textsize(t, font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 2), t, fill=View.color, font=View.IMPACT22)

            num_of_lines = len(lines)

            if selected_menu_num <= 5:
                if num_of_lines >= 1:
                    self.draw_menu_text(15, 43 , lines[0], (True if selected_menu_num == 1 else False))
                if num_of_lines >= 2:
                    self.draw_menu_text(15, 76 , lines[1], (True if selected_menu_num == 2 else False))
                if num_of_lines >= 3:
                    self.draw_menu_text(15, 109, lines[2], (True if selected_menu_num == 3 else False))
                if num_of_lines >= 4:
                    self.draw_menu_text(15, 142, lines[3], (True if selected_menu_num == 4 else False))
                if num_of_lines >= 5:
                    self.draw_menu_text(15, 175, lines[4], (True if selected_menu_num == 5 else False))
            elif selected_menu_num >= 6 and selected_menu_num <= 10:
                if num_of_lines >= 6:
                    self.draw_menu_text(15, 43 , lines[5], (True if selected_menu_num == 6 else False))
                if num_of_lines >= 7:
                    self.draw_menu_text(15, 76 , lines[6], (True if selected_menu_num == 7 else False))
                if num_of_lines >= 8:
                    self.draw_menu_text(15, 109, lines[7], (True if selected_menu_num == 8 else False))
                if num_of_lines >= 9:
                    self.draw_menu_text(15, 142, lines[8], (True if selected_menu_num == 9 else False))
                if num_of_lines >= 10:
                    self.draw_menu_text(15, 175, lines[9], (True if selected_menu_num == 10 else False))
            elif selected_menu_num >= 11 and selected_menu_num <= 15:
                if num_of_lines >= 11:
                    self.draw_menu_text(15, 43 , lines[10], (True if selected_menu_num == 11 else False))
                if num_of_lines >= 12:
                    self.draw_menu_text(15, 76 , lines[11], (True if selected_menu_num == 12 else False))
                if num_of_lines >= 13:
                    self.draw_menu_text(15, 109, lines[12], (True if selected_menu_num == 13 else False))
                if num_of_lines >= 14:
                    self.draw_menu_text(15, 142, lines[13], (True if selected_menu_num == 14 else False))
                if num_of_lines >= 15:
                    self.draw_menu_text(15, 175, lines[14], (True if selected_menu_num == 15 else False))

            tw, th = View.draw.textsize(b, font=View.IMPACT18)
            View.draw.text(((240 - tw) / 2, 210), b, fill=View.color, font=View.IMPACT18)
            View.DispShowImage()

            # saved update menu lines and selection
            self.menu_lines = lines
            self.selected_menu_num = selected_menu_num


    ### Generic Menu Navigation

    def menu_up(self, title = None, bottom = None):
        if self.selected_menu_num <= 1:
            self.draw_menu(self.menu_lines, len(self.menu_lines), title, bottom)
        else:
            self.draw_menu(self.menu_lines, self.selected_menu_num - 1, title, bottom)

    def menu_down(self, title = None, bottom = None):
        if self.selected_menu_num >= len(self.menu_lines):
            self.draw_menu(self.menu_lines, 1, title, bottom)
        else:
            self.draw_menu(self.menu_lines, self.selected_menu_num + 1, title, bottom)

    ### Internal View Method to Display a Line in a Menu Screen

    def draw_menu_text(self, x, y, line, selected) -> None:
        if selected == True:
            View.draw.rectangle((5, y-3, 235, y+28), outline=0, fill=View.color)
            View.draw.text((x, y) , line, fill="BLACK", font=View.IMPACT20)
        else:
            View.draw.text((x, y) , line, fill=View.color, font=View.IMPACT20)

        return
