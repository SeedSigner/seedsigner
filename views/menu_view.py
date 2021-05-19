# Internal file class dependencies
from view import View
from buttons import B
from path import Path
from seed_storage import SeedStorage

# External Dependencies
import time
import re

class MenuView(View):

    def __init__(self, controller) -> None:
        View.__init__(self, controller)

        self.menu_lines = []
        self.selected_menu_num = 1

    ###
    ### Main Navigation
    ###

    ### Main Menu

    def display_main_menu(self, sub_menu = None) -> int:
        ret_val = 0
        input = 0
        lines = ["Seed Tools", "Signing Tools", "Settings", "Power OFF Device"]

        if sub_menu == Path.SEED_TOOLS_SUB_MENU:
            return self.display_seed_tools_menu()
        elif sub_menu == Path.SIGNING_TOOLS_SUB_MENU:
            return self.display_signing_tools_menu()
        elif sub_menu == Path.SETTINGS_SUB_MENU:
            return self.display_settings_menu()
        else:
            self.draw_menu(lines, 1)

        # Wait for Button Input (specifically menu selection/press)
        while True:
            if ret_val == 0:
                input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS])
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
                    ret_val = self.display_signing_tools_menu()
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
        lines = ["... [ Return to Main ]", "Generate Word 12 / 24", "Create a Seed w/ Dice", "Store a Seed (temp)"]
        self.draw_menu(lines, 1)
        input = 0

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS])
            if input == B.KEY_UP:
                self.menu_up()
            elif input == B.KEY_DOWN:
                self.menu_down()
            elif input == B.KEY_PRESS:
                if self.selected_menu_num == 1:
                    return Path.MAIN_MENU
                elif self.selected_menu_num == 2:
                    return Path.GEN_LAST_WORD
                elif self.selected_menu_num == 3:
                    return Path.DICE_GEN_SEED
                elif self.selected_menu_num == 4:
                    return Path.SAVE_SEED

    ### Signing Tools Menu

    def display_signing_tools_menu(self) -> None:
        lines = ["... [ Return to Main ]", "Generate XPUB", "Sign a Transaction"]
        self.draw_menu(lines, 1)
        input = 0

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS])
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

    ### Settings Menu

    def display_settings_menu(self) -> int:
        lines = ["... [ Return to Main ]", "Input / Output Tests", "Current Network: <network>", "Wallet: <wallet>", "Version Info", "Donate to SeedSigner"]
        input = 0
        
        lines[2] = lines[2].replace("<network>", self.controller.storage.get_network())
        lines[3] = lines[3].replace("<wallet>", "Specter Desktop")

        # Draw Menu
        self.draw_menu(lines, 1)

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS])
            if input == B.KEY_UP:
                self.menu_up()
            elif input == B.KEY_DOWN:
                self.menu_down()
            elif input == B.KEY_PRESS:
                if self.selected_menu_num == 1:
                    return Path.MAIN_MENU
                elif self.selected_menu_num == 2:
                    return Path.IO_TEST_TOOL
                elif self.selected_menu_num == 3:
                    return Path.CURRENT_NETWORK
                elif self.selected_menu_num == 4:
                    return Path.WALLET
                elif self.selected_menu_num == 5:
                    return Path.VERSION_INFO
                elif self.selected_menu_num == 6:
                    return Path.DONATE

    ### Generic Single Menu Selection (returns 1,2,3,4,5,6 ...)

    def display_generic_selection_menu(self, lines = [], title = None, bottom = None) -> int:
        self.draw_menu(lines, 1, title, bottom)

        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS])
            if input == B.KEY_UP:
                self.menu_up(title, bottom)
            elif input == B.KEY_DOWN:
                self.menu_down(title, bottom)
            elif input == B.KEY_PRESS:
                return self.selected_menu_num

    ### Generic Word 12 or 24 seed phrase menu

    def display_12_24_word_menu(self, return_txt = "... [ Return to ... ]") -> int:
        lines = [return_txt, "Use a 12 word seed", "Use a 24 word seed"]
        self.draw_menu(lines)

         # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS])
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
        else:
            return 0

        self.draw_menu(lines)

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS])
            if input == B.KEY_UP:
                self.menu_up()
            elif input == B.KEY_DOWN:
                self.menu_down()
            elif input == B.KEY_PRESS:
                if lines[self.selected_menu_num-1] == return_sel_txt:
                    return 0
                else:
                    return int(re.search("#(\d+)", lines[self.selected_menu_num-1], re.IGNORECASE).group(1))

    ###
    ### Generic Reusable Menu Methods/Functions
    ###

    ### Generic Draw Menu Method

    def draw_menu(self, lines, selected_menu_num = 1, title = None, bottom = None) -> None:
        if title == None:
            t = "SeedSigner  v" + self.controller.VERSION
        else:
            t = title

        if bottom == None:
            b = "Press Control Stick to Select"
        else:
            b = bottom

        if lines != self.menu_lines or selected_menu_num != self.selected_menu_num:
            #Menu has changed, redraw

            View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
            tw, th = View.draw.textsize(t, font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 2), t, fill="ORANGE", font=View.IMPACT22)

            num_of_lines = len(lines)

            if selected_menu_num <= 4:
                if num_of_lines >= 1:
                    self.draw_menu_text(15, 45 , lines[0], (True if selected_menu_num == 1 else False))
                if num_of_lines >= 2:
                    self.draw_menu_text(15, 80 , lines[1], (True if selected_menu_num == 2 else False))
                if num_of_lines >= 3:
                    self.draw_menu_text(15, 115, lines[2], (True if selected_menu_num == 3 else False))
                if num_of_lines >= 4:
                    self.draw_menu_text(15, 150, lines[3], (True if selected_menu_num == 4 else False))
            elif selected_menu_num >= 5 and selected_menu_num <= 8:
                if num_of_lines >= 5:
                    self.draw_menu_text(15, 45 , lines[4], (True if selected_menu_num == 5 else False))
                if num_of_lines >= 6:
                    self.draw_menu_text(15, 80 , lines[5], (True if selected_menu_num == 6 else False))
                if num_of_lines >= 7:
                    self.draw_menu_text(15, 115, lines[6], (True if selected_menu_num == 7 else False))
                if num_of_lines >= 8:
                    self.draw_menu_text(15, 150, lines[7], (True if selected_menu_num == 8 else False))
            elif selected_menu_num >= 9 and selected_menu_num <= 12:
                if num_of_lines >= 9:
                    self.draw_menu_text(15, 45 , lines[8], (True if selected_menu_num == 9 else False))
                if num_of_lines >= 10:
                    self.draw_menu_text(15, 80 , lines[9], (True if selected_menu_num == 10 else False))
                if num_of_lines >= 11:
                    self.draw_menu_text(15, 115, lines[10], (True if selected_menu_num == 11 else False))
                if num_of_lines >= 12:
                    self.draw_menu_text(15, 150, lines[11], (True if selected_menu_num == 12 else False))

            tw, th = View.draw.textsize(b, font=View.IMPACT18)
            View.draw.text(((240 - tw) / 2, 210), b, fill="ORANGE", font=View.IMPACT18)
            View.DispShowImage()

            # saved update menu lines and selection
            self.menu_lines = lines
            self.selected_menu_num = selected_menu_num

        return

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
            View.draw.rectangle((5, y-5, 235, y+30), outline=0, fill="ORANGE")
            View.draw.text((x, y) , line, fill="BLACK", font=View.IMPACT20)
        else:
            View.draw.text((x, y) , line, fill="ORANGE", font=View.IMPACT20)

        return
