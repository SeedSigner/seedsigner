# External Dependencies
import time
from multiprocessing import Process, Queue
from subprocess import call

# Internal file class dependencies
from view import View
from menu_view import MenuView
from seed_tools_view import SeedToolsView
from signing_tools_view import SigningToolsView
from settings_tools_view import SettingsToolsView
from io_test_view import IOTestView
from buttons import Buttons, B
from camera_process import CameraProcess
from path import Path
from seed_storage import SeedStorage
from psbt_signer import PSBTSigner

class Controller:
    
    VERSION = "0.4.0b3"

    def __init__(self) -> None:
        controller = self

        # Input Buttons
        self.buttons = Buttons()

        # models
        self.storage = SeedStorage("main", "m/48h/0h/0h/2h")

        # Views
        self.menu_view = MenuView(controller)
        self.seed_tools_view = SeedToolsView(controller)
        self.io_test_view = IOTestView(controller)
        self.signing_tools_view = SigningToolsView(controller, self.storage)
        self.settings_tools_view = SettingsToolsView(controller)

        # Then start seperate background camera process with two queues for communication
        # CameraProcess handles connecting to camera hardware and passing back barcode data via from camera queue
        self.from_camera_queue = Queue()
        self.to_camera_queue = Queue()
        p = Process(target=CameraProcess.start, args=(self.from_camera_queue, self.to_camera_queue))
        p.start()

        return

    def start(self, debug = False) -> None:

        if debug == False:
            crash_cnt = 0

            # Handle Unexpected crashes by restarting up to 3 times
            while True:
                try:
                    self.show_main_menu()
                except Exception as error:
                    if crash_cnt >= 3:
                        break
                    else:
                        print('Caught this error: ' + repr(error)) # debug
                        self.menu_view.draw_modal(["Crashed ..."], "", "restarting")
                        time.sleep(5)

                    crash_cnt += 1

            self.menu_view.draw_modal(["Crashed ..."], "", "requires hard restart")
        else:
            self.show_main_menu()

    ### Menu
    ### Menu View handles navigation within the menu
    ### Sub Menu's like Seed Tools, Signing Tools, Settings are all in the Menu View

    def show_main_menu(self, sub_menu = 0):
        ret_val = sub_menu
        while True:
            ret_val = self.menu_view.display_main_menu(ret_val)

            if ret_val == Path.MAIN_MENU:
                ret_val = Path.MAIN_MENU
            elif ret_val == Path.GEN_LAST_WORD:
                ret_val = self.show_generate_last_word_tool()
            elif ret_val == Path.DICE_GEN_SEED:
                ret_val = self.show_create_seed_with_dice_tool()
            elif ret_val == Path.SAVE_SEED:
                ret_val = self.show_store_a_seed_tool()
            elif ret_val == Path.GEN_XPUB:
                ret_val = self.show_generate_xpub()
            elif ret_val == Path.SIGN_TRANSACTION:
                ret_val = self.show_sign_transaction()
            elif ret_val == Path.IO_TEST_TOOL:
                ret_val = self.show_io_test_tool()
            elif ret_val == Path.VERSION_INFO:
                ret_val = self.show_version_info()
            elif ret_val == Path.CURRENT_NETWORK:
                ret_val = self.show_current_network_tool()
            elif ret_val == Path.WALLET:
                ret_val = self.show_wallet_tool()
            elif ret_val == Path.DONATE:
                ret_val = self.show_donate_tool()
            elif ret_val == Path.POWER_OFF:
                ret_val = self.show_power_off()

        print("exit show_main_menu")
        return # should never return/exit

    ### Power Off

    def show_power_off(self):

        r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Power Off?")
        if r == 1: #Yes
            self.menu_view.display_power_off_screen()
            call("sudo shutdown --poweroff now", shell=True)
            time.sleep(10)
        else: # No
            return Path.MAIN_MENU

    ###
    ### Seed Tools Controller Naviation/Launcher
    ###

    ### Generate Last Word 12 / 24 Menu

    def show_generate_last_word_tool(self) -> int:
        seed_phrase = []
        ret_val = 0

        while True:
            # display menu to select 12 or 24 word seed for last word
            ret_val = self.menu_view.display_12_24_word_menu("... [ Return to Seed Tools ]")
            if ret_val == Path.SEED_WORD_12:
                seed_phrase = self.seed_tools_view.display_gather_words_screen(11)
            elif ret_val == Path.SEED_WORD_24:
                seed_phrase = self.seed_tools_view.display_gather_words_screen(23)
            else:
                return Path.SEED_TOOLS_SUB_MENU

            if len(seed_phrase) > 0:
                completed_seed_phrase = self.seed_tools_view.display_last_word(seed_phrase)
                break

        # Ask to save seed
        if self.storage.slot_avaliable():
            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Save Seed?")
            if r == 1: #Yes
                slot_num = self.menu_view.display_saved_seed_menu(self.storage,2,None)
                if slot_num in (1,2,3):
                    self.storage.save_seed_phrase(completed_seed_phrase, slot_num)
                    self.menu_view.draw_modal(["Seed Valid", "Saved to Slot #" + str(slot_num)], "", "Right to Continue")
                    input = self.buttons.wait_for([B.KEY_RIGHT])

        return Path.MAIN_MENU

    ### Create a Seed w/ Dice Screen

    def show_create_seed_with_dice_tool(self) -> int:
        seed_phrase = []
        ret_val = True

        while True:
            seed_phrase = self.seed_tools_view.display_generate_seed_from_dice()
            if len(seed_phrase) > 0:
                break
            else:
                return Path.SEED_TOOLS_SUB_MENU

        # display seed phrase (24 words)
        while True:
            ret_val = self.seed_tools_view.display_seed_phrase(seed_phrase, "Right to Continue")
            if ret_val == True:
                break

        # Ask to save seed
        if self.storage.slot_avaliable():
            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Save Seed?")
            if r == 1: #Yes
                slot_num = self.menu_view.display_saved_seed_menu(self.storage,2,None)
                if slot_num in (1,2,3):
                    self.storage.save_seed_phrase(seed_phrase, slot_num)
                    self.menu_view.draw_modal(["Seed Valid", "Saved to Slot #" + str(slot_num)], "", "Right to Continue")
                    input = self.buttons.wait_for([B.KEY_RIGHT])

        return Path.MAIN_MENU

    ### Store a seed (temp) Menu

    def show_store_a_seed_tool(self):
        seed_phrase = []
        ret_val = 0
        ret_val = self.menu_view.display_saved_seed_menu(self.storage, 1, "... [ Return to Seed Tools ]")
        if ret_val == 0:
            return Path.SEED_TOOLS_SUB_MENU

        slot_num = ret_val

        if self.storage.check_slot(slot_num) == True:
            # show seed phrase
            # display seed phrase (24 words)
            while True:
                r = self.seed_tools_view.display_seed_phrase(self.storage.get_seed_phrase(abs(slot_num)), "Right to Continue")
                if r == True:
                    break
            return Path.MAIN_MENU
        else:
            # display menu to select 12 or 24 word seed for last word
            ret_val = self.menu_view.display_12_24_word_menu("... [ Return to Seed Tools ]")
            if ret_val == Path.SEED_WORD_12:
                seed_phrase = self.seed_tools_view.display_gather_words_screen(12)
            elif ret_val == Path.SEED_WORD_24:
                seed_phrase = self.seed_tools_view.display_gather_words_screen(24)
            else:
                return Path.SEED_TOOLS_SUB_MENU

        if len(seed_phrase) == 0:
            return Path.SEED_TOOLS_SUB_MENU

        self.menu_view.draw_modal(["Validating ..."])
        is_valid = self.storage.check_if_seed_valid(seed_phrase)
        if is_valid:
            self.storage.save_seed_phrase(seed_phrase, slot_num)
            self.menu_view.draw_modal(["Seed Valid", "Saved to Slot #" + str(slot_num)], "", "Right to Continue")
            input = self.buttons.wait_for([B.KEY_RIGHT])
        else:
            self.menu_view.draw_modal(["Seed Invalid", "check seed phrase", "and try again"], "", "Right to Continue")
            input = self.buttons.wait_for([B.KEY_RIGHT])

        return Path.MAIN_MENU


    ###
    ### Signing Tools Navigation/Launcher
    ###

    ### Generate XPUB

    def show_generate_xpub(self):
        seed_phrase = []

        # If there is a saved seed, ask to use saved seed
        if self.storage.num_of_saved_seeds() > 0:
            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Use Save Seed?")
            if r == 1: #Yes
                slot_num = self.menu_view.display_saved_seed_menu(self.storage,3,None)
                if slot_num not in (1,2,3):
                    return Path.SIGNING_TOOLS_SUB_MENU
                seed_phrase = self.storage.get_seed_phrase(slot_num)

        if len(seed_phrase) == 0:
            # gather seed phrase
            # display menu to select 12 or 24 word seed for last word
            ret_val = self.menu_view.display_12_24_word_menu("... [ Return to Sign Tools ]")
            if ret_val == Path.SEED_WORD_12:
                seed_phrase = self.seed_tools_view.display_gather_words_screen(12)
            elif ret_val == Path.SEED_WORD_24:
                seed_phrase = self.seed_tools_view.display_gather_words_screen(24)
            else:
                return Path.SIGNING_TOOLS_SUB_MENU

            if len(seed_phrase) == 0:
                return Path.SIGNING_TOOLS_SUB_MENU

            # check if seed phrase is valid
            self.menu_view.draw_modal(["Validating ..."])
            is_valid = self.storage.check_if_seed_valid(seed_phrase)
            if is_valid == False:
                self.menu_view.draw_modal(["Seed Invalid", "check seed phrase", "and try again"], "", "Right to Continue")
                input = self.buttons.wait_for([B.KEY_RIGHT])
                return Path.MAIN_MENU

        # display seed phrase
        while True:
            r = self.seed_tools_view.display_seed_phrase(seed_phrase, "Right to See QR")
            if r == True:
                break

        self.signing_tools_view.display_xpub_qr(seed_phrase)
        time.sleep(1)
        input = self.buttons.wait_for([B.KEY_RIGHT])
        return Path.MAIN_MENU

    ### Sign Transactions

    def show_sign_transaction(self):
        seed_phrase = []

        # If there is a saved seed, ask to use saved seed
        if self.storage.num_of_saved_seeds() > 0:
            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Use Save Seed?")
            if r == 1: #Yes
                slot_num = self.menu_view.display_saved_seed_menu(self.storage,3,None)
                if slot_num == 0:
                    return Path.SIGNING_TOOLS_SUB_MENU
                seed_phrase = self.storage.get_seed_phrase(slot_num)

        if len(seed_phrase) == 0:
            # gather seed phrase
            # display menu to select 12 or 24 word seed for last word
            ret_val = self.menu_view.display_12_24_word_menu("... [ Return to Sign Tools ]")
            if ret_val == Path.SEED_WORD_12:
                seed_phrase = self.seed_tools_view.display_gather_words_screen(12)
            elif ret_val == Path.SEED_WORD_24:
                seed_phrase = self.seed_tools_view.display_gather_words_screen(24)
            else:
                return Path.SIGNING_TOOLS_SUB_MENU

            if len(seed_phrase) == 0:
                return Path.SIGNING_TOOLS_SUB_MENU

            # check if seed phrase is valid
            self.menu_view.draw_modal(["Validating ..."])
            is_valid = self.storage.check_if_seed_valid(seed_phrase)
            if is_valid == False:
                self.menu_view.draw_modal(["Seed Invalid", "check seed phrase", "and try again"], "", "Right to Continue")
                input = self.buttons.wait_for([B.KEY_RIGHT])
                return Path.MAIN_MENU

        # display seed phrase
        while True:
            r = self.seed_tools_view.display_seed_phrase(seed_phrase, "Right to Scan QR")
            if r == True:
                break
            else:
                return Path.SIGNING_TOOLS_SUB_MENU

        # Scan PSBT Animated QR using Camera
        self.menu_view.draw_modal(["Loading..."])
        signer = PSBTSigner(seed_phrase, self)
        raw_pbst = signer.scan_animated_psbt_qr()
        print("raw_pbst: " + raw_pbst)
        if raw_pbst == "nodata":
            return Path.SIGNING_TOOLS_SUB_MENU
        if raw_pbst == "invalid":
            self.menu_view.draw_modal(["QR Format Unexpected"], "", "RIGHT to EXIT")
            input = self.buttons.wait_for([B.KEY_RIGHT])
            return Path.SIGNING_TOOLS_SUB_MENU
        self.menu_view.draw_modal(["Parsing PSBT ..."])
        signer.parse_psbt(raw_pbst)

        # show transaction information before sign
        self.signing_tools_view.display_transaction_information(signer)
        input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT], False)
        if input == B.KEY_LEFT:
            return Path.SIGNING_TOOLS_SUB_MENU

        # Sign PSBT
        self.menu_view.draw_modal(["PSBT Signing ..."])
        (status, signed_pbst) = signer.sign_transaction()

        # Display Animated QR Code
        self.signing_tools_view.display_signed_psbt_animated_qr(signed_pbst)

        # Return to Main Menu
        return Path.MAIN_MENU


    ###
    ### Settings Tools Navigation/Launcher
    ###

    #### Show IO Test

    def show_io_test_tool(self):
        ret_val = True

        ret_val = self.io_test_view.display_io_test_screen()

        if ret_val == True:
            return Path.MAIN_MENU

    ### Show Current Network

    def show_current_network_tool(self):
        r = self.settings_tools_view.display_current_network()
        if r == "main":
            self.storage.set_network("main")
            self.storage.set_hardened_derivation("m/48h/0h/0h/2h")
        elif r == "test":
            self.storage.set_network("test")
            self.storage.set_hardened_derivation("m/48h/1h/0h/2h")

        return Path.SETTINGS_SUB_MENU

    ### Show Wallet Selection Tool

    def show_wallet_tool(self):
        r = self.settings_tools_view.display_wallet_selection()
        if r == "Specter Desktop":
            pass

        return Path.SETTINGS_SUB_MENU

    ### Show Version Info

    def show_version_info(self):
        self.settings_tools_view.display_version_info()
        input = self.buttons.wait_for([B.KEY_LEFT, B.KEY_RIGHT])
        if input == B.KEY_LEFT:
            return Path.SETTINGS_SUB_MENU
        elif input == B.KEY_RIGHT:
            return Path.MAIN_MENU

    ### Show Donate Screen and QR

    def show_donate_tool(self):
        self.settings_tools_view.display_donate_info_screen()

        input = self.buttons.wait_for([B.KEY_LEFT, B.KEY_RIGHT])
        if input == B.KEY_LEFT:
            return Path.SETTINGS_SUB_MENU
        elif input == B.KEY_RIGHT:
            self.settings_tools_view.display_donate_qr()
            time.sleep(1)
            input = self.buttons.wait_for([B.KEY_RIGHT])
            return Path.MAIN_MENU

