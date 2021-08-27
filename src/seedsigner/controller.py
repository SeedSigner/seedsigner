# External Dependencies
import time
from multiprocessing import Process, Queue
from subprocess import call
import os, sys
from embit import bip39, bip32
from embit.networks import NETWORKS
from binascii import hexlify
from threading import Thread

# Internal file class dependencies
from .views import (View, MenuView, SeedToolsView,SigningToolsView, 
    SettingsToolsView, IOTestView)
from .helpers import Buttons, B, Path, Singleton
from .models import (SeedStorage, Settings, DecodeQR, DecodeQRStatus,
    EncodeQRDensity, EncodeQR, PSBTParser, QRType)

class Controller(Singleton):
    """
        The Controller is a globally available singleton that maintains SeedSigner state.

        It only makes sense to ever have a single Controller instance so it is
        implemented here as a singleton. One departure from the typical singleton pattern
        is the addition of a `configure_instance()` call to pass run-time settings into
        the Controller.

        Any code that needs to interact with the one and only Controller can just run:
        ```
        from seedsigner.controller import Controller
        controller = Controller.get_instance()
        ```
        Note: In many/most cases you'll need to do the Controller import within a method
        rather than at the top in order avoid circular imports.
    """
    VERSION = "0.4.4"


    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only Controller
        if cls._instance:
            return cls._instance
        else:
            raise Exception("Must call Controller.configure_instance(config) first")


    @classmethod
    def configure_instance(cls, config=None):
        # Must be called before the first get_instance() call
        if cls._instance:
            raise Exception("Instance already configured")

        # Instantiate the one and only Controller instance
        controller = cls.__new__(cls)
        cls._instance = controller

        # Input Buttons
        controller.buttons = Buttons()

        # models
        controller.storage = SeedStorage()
        Settings.configure_instance(config)
        controller.settings = Settings.get_instance()

        # settings
        controller.DEBUG = controller.settings.debug
        controller.color = controller.settings.text_color

        # Views
        controller.menu_view = MenuView()
        controller.seed_tools_view = SeedToolsView()
        controller.io_test_view = IOTestView()
        controller.signing_tools_view = SigningToolsView(controller.storage)
        controller.settings_tools_view = SettingsToolsView()

    @property
    def camera(self):
        from .camera import Camera
        return Camera.get_instance()


    def start(self) -> None:
        if self.DEBUG:
            # Let Exceptions halt execution
            try:
                self.show_main_menu()
            finally:
                # Clear the screen when exiting
                self.menu_view.display_blank_screen()

        else:
            # Handle Unexpected crashes by restarting up to 3 times
            crash_cnt = 0
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
            elif ret_val == Path.IMAGE_GEN_SEED:
                ret_val = self.show_create_seed_with_image_tool()
            elif ret_val == Path.SAVE_SEED:
                ret_val = self.show_store_a_seed_tool()
            elif ret_val == Path.PASSPHRASE_SEED:
                ret_val = self.show_add_remove_passphrase_tool()
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
            elif ret_val == Path.QR_DENSITY_SETTING:
                ret_val = self.show_qr_density_tool()
            elif ret_val == Path.WALLET_POLICY:
                ret_val = self.show_wallet_policy_tool()
            elif ret_val == Path.PERSISTENT_SETTINGS:
                ret_val = self.show_persistent_settings_tool()
            elif ret_val == Path.DONATE:
                ret_val = self.show_donate_tool()
            elif ret_val == Path.RESET:
                ret_val = self.show_reset_tool()
            elif ret_val == Path.POWER_OFF:
                ret_val = self.show_power_off()

        raise Exception("Unhandled case")

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
                seed_phrase = self.seed_tools_view.display_manual_seed_entry(11)
            elif ret_val == Path.SEED_WORD_24:
                seed_phrase = self.seed_tools_view.display_manual_seed_entry(23)
            else:
                return Path.SEED_TOOLS_SUB_MENU

            if len(seed_phrase) > 0:
                completed_seed_phrase = self.seed_tools_view.display_last_word(seed_phrase)
                break

        # display seed phrase
        while True:
            ret_val = self.seed_tools_view.display_seed_phrase(completed_seed_phrase, show_qr_option=True)
            if ret_val == True:
                break
            else:
                # no-op; can't back out of the seed phrase view
                pass

        # Ask to save seed
        if self.storage.slot_avaliable():
            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Save Seed?")
            if r == 1: #Yes
                slot_num = self.menu_view.display_saved_seed_menu(self.storage,2,None)
                if slot_num in (1,2,3):
                    self.storage.save_seed_phrase(completed_seed_phrase, slot_num)
                    self.menu_view.draw_modal(["Seed Valid", "Saved to Slot #" + str(slot_num)], "", "Right to Main Menu")
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
            ret_val = self.seed_tools_view.display_seed_phrase(seed_phrase, show_qr_option=True)
            if ret_val == True:
                break
            else:
                # no-op; can't back out of the seed phrase view
                pass

        # Ask to save seed
        if self.storage.slot_avaliable():
            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Save Seed?")
            if r == 1: #Yes
                slot_num = self.menu_view.display_saved_seed_menu(self.storage,2,None)
                if slot_num in (1,2,3):
                    self.storage.save_seed_phrase(seed_phrase, slot_num)
                    self.menu_view.draw_modal(["Seed Valid", "Saved to Slot #" + str(slot_num)], "", "Right to Main Menu")
                    input = self.buttons.wait_for([B.KEY_RIGHT])

        return Path.MAIN_MENU

    def show_create_seed_with_image_tool(self) -> int:
        seed_phrase = []
        ret_val = True

        while True:
            (reshoot, seed_phrase) = self.seed_tools_view.seed_phrase_from_camera_image()
            if reshoot:
                # Relaunch into another image capture cycle
                continue

            if len(seed_phrase) > 0:
                break
            else:
                return Path.SEED_TOOLS_SUB_MENU

        # display seed phrase (24 words)
        while True:
            ret_val = self.seed_tools_view.display_seed_phrase(seed_phrase, show_qr_option=True)
            if ret_val == True:
                break
            else:
                # Start over
                return self.show_create_seed_with_image_tool()

        # Ask to save seed
        if self.storage.slot_avaliable():
            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Save Seed?")
            if r == 1: #Yes
                slot_num = self.menu_view.display_saved_seed_menu(self.storage,2,None)
                if slot_num in (1,2,3):
                    self.storage.save_seed_phrase(seed_phrase, slot_num)
                    self.menu_view.draw_modal(["Seed Valid", "Saved to Slot #" + str(slot_num)], "", "Right to Main Menu")
                    input = self.buttons.wait_for([B.KEY_RIGHT])

        return Path.MAIN_MENU
    ### Store a seed (temp) Menu

    def show_store_a_seed_tool(self):
        seed_phrase = []
        ret_val = 0
        display_saved_seed = False
        ret_val = self.menu_view.display_saved_seed_menu(self.storage, 1, "... [ Return to Seed Tools ]")
        if ret_val == 0:
            return Path.SEED_TOOLS_SUB_MENU

        slot_num = ret_val

        if self.storage.check_slot(slot_num) == True:
            display_saved_seed = True
            # show seed phrase
            # display seed phrase (24 words)
            while True:
                r = self.seed_tools_view.display_seed_phrase(self.storage.get_seed_phrase(abs(slot_num)), self.storage.get_passphrase(abs(slot_num)), show_qr_option=True)
                if r == True:
                    break
                else:
                    # no-op; can't back out of the seed phrase view
                    pass
            return Path.SEED_TOOLS_SUB_MENU
        else:
            # display menu to select 12 or 24 word seed for last word
            ret_val = self.menu_view.display_qr_12_24_word_menu("... [ Return to Seed Tools ]")
            if ret_val == Path.SEED_WORD_12:
                seed_phrase = self.seed_tools_view.display_manual_seed_entry(12)
            elif ret_val == Path.SEED_WORD_24:
                seed_phrase = self.seed_tools_view.display_manual_seed_entry(24)
            elif ret_val == Path.SEED_WORD_QR:
                seed_phrase = self.seed_tools_view.read_seed_phrase_qr()
            else:
                return Path.SEED_TOOLS_SUB_MENU

        if len(seed_phrase) == 0:
            return Path.SEED_TOOLS_SUB_MENU

        if ret_val == Path.SEED_WORD_QR and len(seed_phrase) > 0:
            show_qr_option = False
        else:
            show_qr_option = True

        self.menu_view.draw_modal(["Validating ..."])
        is_valid = self.storage.check_if_seed_valid(seed_phrase)
        if is_valid == False:
            # Exit if not valid with message
            self.menu_view.draw_modal(["Seed Invalid", "check seed phrase", "and try again", ""], "", "Right to Continue")
            input = self.buttons.wait_for([B.KEY_RIGHT])
            return Path.SEED_TOOLS_SUB_MENU
        else:
            self.menu_view.draw_modal(["Valid Seed!"], "", "Right to Continue")
            input = self.buttons.wait_for([B.KEY_RIGHT])

        while display_saved_seed == False:
            r = self.seed_tools_view.display_seed_phrase(seed_phrase, show_qr_option=show_qr_option )
            if r == True:
                break
            else:
                # no-op; can't back out of the seed phrase view
                pass

        if is_valid:
            self.storage.save_seed_phrase(seed_phrase, slot_num)
            self.menu_view.draw_modal(["", "Saved to Slot #" + str(slot_num)], "", "Right to Exit")
            input = self.buttons.wait_for([B.KEY_RIGHT])

        return Path.SEED_TOOLS_SUB_MENU

    ### Add a PassPhrase Menu

    def show_add_remove_passphrase_tool(self):
        ret_val = 0
        r = 0

        if self.storage.num_of_saved_seeds() == 0:
            self.menu_view.draw_modal(["Store a seed phrase", "prior to adding", "a passphrase"], "Error", "Right to Continue")
            self.buttons.wait_for([B.KEY_RIGHT])
            return Path.SEED_TOOLS_SUB_MENU

        if self.storage.num_of_saved_seeds() > 0:
            if self.storage.num_of_saved_seeds() == 1:
                ret_val = self.storage.get_first_seed_slot()
            else:
                ret_val = self.menu_view.display_saved_seed_menu(self.storage, 3, None)
                if ret_val == 0:
                    return Path.SEED_TOOLS_SUB_MENU
            # continue after top level if to capture and store passphrase
            
        slot_num = ret_val

        if self.storage.check_slot_passphrase(slot_num) == True:
            # only display menu to remove/update if there is a passphrase to remove
            r = self.menu_view.display_generic_selection_menu(["... [ Return to Seed Tools ]", "Change Passphrase", "Remove Passphrase"], "Passphrase Action")
            if r == 3:
                # Remove Passphrase Workflow
                self.storage.delete_passphrase(slot_num)
                self.menu_view.draw_modal(["Passphrase Deleted", "from Slot #" + str(slot_num)], "", "Right to Continue")
                self.buttons.wait_for([B.KEY_RIGHT])

                return Path.SEED_TOOLS_SUB_MENU
            elif r == 1:
                return Path.SEED_TOOLS_SUB_MENU
            # continue if updating passphrase

        # display a tool to pick letters/numbers to make a passphrase
        passphrase = self.seed_tools_view.draw_passphrase_keyboard_entry(existing_passphrase=self.storage.get_passphrase(slot_num))
        if len(passphrase) == 0:
            return Path.SEED_TOOLS_SUB_MENU

        self.storage.save_passphrase(passphrase, slot_num)
        if r in (0,1):
            self.menu_view.draw_modal(["Passphrase Added", passphrase, "Added to Slot #" + str(slot_num)], "", "Right to Continue")
        elif r == 2:
            self.menu_view.draw_modal(["Passphrase Updated", passphrase, "Added to Slot #" + str(slot_num)], "", "Right to Continue")
        self.buttons.wait_for([B.KEY_RIGHT])

        return Path.SEED_TOOLS_SUB_MENU

    ###
    ### Signing Tools Navigation/Launcher
    ###

    ### Generate XPUB

    def show_generate_xpub(self):
        seed_phrase = []
        passphrase = ""

        # If there is a saved seed, ask to use saved seed
        if self.storage.num_of_saved_seeds() > 0:
            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Use Saved Seed?")
            if r == 1: #Yes
                slot_num = self.menu_view.display_saved_seed_menu(self.storage,3,None)
                if slot_num not in (1,2,3):
                    return Path.SEED_TOOLS_SUB_MENU
                seed_phrase = self.storage.get_seed_phrase(slot_num)
                passphrase = self.storage.get_passphrase(slot_num)

        if len(seed_phrase) == 0:
            # gather seed phrase
            # display menu to select 12 or 24 word seed for last word
            ret_val = self.menu_view.display_qr_12_24_word_menu("... [ Return to Sign Tools ]")
            if ret_val == Path.SEED_WORD_12:
                seed_phrase = self.seed_tools_view.display_manual_seed_entry(12)
            elif ret_val == Path.SEED_WORD_24:
                seed_phrase = self.seed_tools_view.display_manual_seed_entry(24)
            elif ret_val == Path.SEED_WORD_QR:
                seed_phrase = self.seed_tools_view.read_seed_phrase_qr()
            else:
                return Path.SEED_TOOLS_SUB_MENU

            if len(seed_phrase) == 0:
                return Path.SEED_TOOLS_SUB_MENU

            # check if seed phrase is valid
            self.menu_view.draw_modal(["Validating ..."])
            is_valid = self.storage.check_if_seed_valid(seed_phrase)
            if is_valid == False:
                self.menu_view.draw_modal(["Seed Invalid", "check seed phrase", "and try again"], "", "Right to Continue")
                input = self.buttons.wait_for([B.KEY_RIGHT])
                return Path.MAIN_MENU

            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Add Seed Passphrase?")
            if r == 1:
                # display a tool to pick letters/numbers to make a passphrase
                passphrase = self.seed_tools_view.draw_passphrase_keyboard_entry()
                if len(passphrase) == 0 or passphrase == "-1":
                    passphrase = ""
                    self.menu_view.draw_modal(["No passphrase added", "to seed words"], "", "Left to Exit, Right to Continue")
                    input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT])
                    if input == B.KEY_LEFT:
                        return Path.MAIN_MENU
                else:
                    self.menu_view.draw_modal(["Optional passphrase", "added to seed words", passphrase], "", "Right to Continue")
                    self.buttons.wait_for([B.KEY_RIGHT])

        # display seed phrase
        while True:
            r = self.seed_tools_view.display_seed_phrase(seed_phrase, passphrase, "Right to Continue")
            if r == True:
                break
            else:
                # Cancel
                return Path.SEED_TOOLS_SUB_MENU

        self.signing_tools_view.draw_modal(["Loading xPub Info ..."])

        seed = bip39.mnemonic_to_seed((" ".join(seed_phrase)).strip(), passphrase)
        root = bip32.HDKey.from_seed(seed, version=NETWORKS[self.settings.network]["xprv"])
        fingerprint = hexlify(root.child(0).fingerprint).decode('utf-8')
        bip48_xprv = root.derive(self.settings.derivation)
        bip48_xpub = bip48_xprv.to_public()
        if self.settings.script_policy == "PKWPKH":
            xpub = bip48_xpub.to_base58(NETWORKS[self.settings.network]["zpub"])
        else:
            xpub = bip48_xpub.to_base58(NETWORKS[self.settings.network]["Zpub"])

        self.signing_tools_view.display_xpub_info(fingerprint, self.settings.derivation, xpub)
        self.buttons.wait_for([B.KEY_RIGHT])

        if self.settings.software == "Prompt":
            lines = ["Specter Desktop", "Blue Wallet", "Sparrow"]
            r = self.menu_view.display_generic_selection_menu(lines, "Which Wallet?")
            qr_xpub_type = Settings.getXPubType(lines[r-1])
        else:
            qr_xpub_type = self.settings.qr_xpub_type

        self.signing_tools_view.draw_modal(["Generating xPub QR ..."])
        e = EncodeQR(seed_phrase=seed_phrase, passphrase=passphrase, derivation=self.settings.derivation, network=self.settings.network, policy=self.settings.script_policy, qr_type=qr_xpub_type, qr_density=self.settings.qr_density)

        while e.totalParts() > 1:
            image = e.nextPartImage(240,240,2)
            View.DispShowImage(image)
            time.sleep(0.1)
            if self.buttons.check_for_low(B.KEY_RIGHT):
                    break

        if e.totalParts() == 1:
            image = e.nextPartImage(240,240,1)
            View.DispShowImage(image)
            self.buttons.wait_for([B.KEY_RIGHT])

        return Path.MAIN_MENU

    ### Sign Transactions

    def show_sign_transaction(self):
        seed_phrase = []
        passphrase = ""
        used_saved_seed = False

        # reusable qr scan function
        def scan_qr(scan_text="Scan QR"):
            # Scan QR using Camera
            self.menu_view.draw_modal(["Initializing Camera"])
            self.camera.start_video_stream_mode(resolution=(480, 480), framerate=12, format="rgb")
            decoder = DecodeQR()

            def live_preview(camera, decoder, scan_text):
                while True:
                    frame = self.camera.read_video_stream(as_image=True)
                    if frame is not None:
                        if decoder.getPercentComplete() > 0 and decoder.isPSBT():
                            scan_text = str(decoder.getPercentComplete()) + "% Complete"
                        View.DispShowImageWithText(frame.resize((240,240)), scan_text, font=View.IMPACT22, text_color=View.color, text_background=(0,0,0,225))
                    time.sleep(0.1) # turn this up or down to tune performace while decoding psbt
                    if camera._video_stream is None:
                        break

            # putting live preview in it's own thread to improve psbt decoding performance
            t = Thread(target=live_preview, args=(self.camera, decoder, scan_text,))
            t.start()

            while True:
                frame = self.camera.read_video_stream()
                if frame is not None:
                    status = decoder.addImage(frame)

                    if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                        self.camera.stop_video_stream_mode()
                        break
                    
                    if self.buttons.check_for_low(B.KEY_RIGHT) or self.buttons.check_for_low(B.KEY_LEFT):
                        self.camera.stop_video_stream_mode()
                        break

            time.sleep(0.2) # time to let live preview thread complete to avoid race condition on display

            return decoder

        # first QR scan
        decoder = scan_qr()

        if decoder.isComplete() and decoder.isPSBT():
            # first QR is PSBT
            self.menu_view.draw_modal(["Validating PSBT"])
            psbt = decoder.getPSBT()

            self.menu_view.draw_modal(["PSBT Valid!", "Enter", "seed phrase", "to sign this tx"], "", "Right to Continue")
            input = self.buttons.wait_for([B.KEY_RIGHT])

        elif decoder.isComplete() and decoder.isSeed():
            # first QR is Seed
            self.menu_view.draw_modal(["Validating Seed"])
            seed_phrase = decoder.getSeedPhrase()
            is_valid = self.storage.check_if_seed_valid(seed_phrase)
            if is_valid == False:
                # Exit if not valid with message
                self.menu_view.draw_modal(["Seed Invalid", "check seed phrase", "and try again", ""], "", "Right to Continue")
                input = self.buttons.wait_for([B.KEY_RIGHT])
                return Path.MAIN_MENU
            else:
                self.menu_view.draw_modal(["Valid Seed!"], "", "Right to Continue")
                input = self.buttons.wait_for([B.KEY_RIGHT])

            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Add Seed Passphrase?")
            if r == 1:
                # display a tool to pick letters/numbers to make a passphrase
                passphrase = self.seed_tools_view.draw_passphrase_keyboard_entry()
                if len(passphrase) == 0 or passphrase == "-1":
                    passphrase = ""
                    self.menu_view.draw_modal(["No passphrase added", "to seed words"], "", "Left to Exit, Right to Continue")
                    input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT])
                    if input == B.KEY_LEFT:
                        return Path.MAIN_MENU
                else:
                    self.menu_view.draw_modal(["Optional passphrase", "added to seed words"], "", "Right to Continue")
                    self.buttons.wait_for([B.KEY_RIGHT])

            # Ask to save seed
            if self.storage.slot_avaliable():
                r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Save Seed?")
                if r == 1: #Yes
                    slot_num = self.menu_view.display_saved_seed_menu(self.storage,2,None)
                    if slot_num in (1,2,3):
                        self.storage.save_seed_phrase(seed_phrase, slot_num)
                        self.storage.save_passphrase(passphrase, slot_num)
                        self.menu_view.draw_modal(["Seed Valid", "Saved to Slot #" + str(slot_num)], "", "Right to Continue")
                        input = self.buttons.wait_for([B.KEY_RIGHT])

            # display seed phrase
            while True:
                r = self.seed_tools_view.display_seed_phrase(seed_phrase, passphrase, "Right to Continue")
                if r == True:
                    break
                else:
                    # Cancel
                    return Path.MAIN_MENU

            # second QR scan need PSBT now
            decoder = scan_qr("Scan PSBT QR")

            if decoder.isComplete() and decoder.isPSBT():
                # second QR must be a PSBT
                self.menu_view.draw_modal(["Validating PSBT"])
                psbt = decoder.getPSBT()
            elif ( decoder.isComplete() and not decoder.isPSBT() ) or decoder.isInvalid():
                self.menu_view.draw_modal(["Not a valid PSBT QR"], "", "Right to Exit")
                input = self.buttons.wait_for([B.KEY_RIGHT])
                return Path.MAIN_MENU
            else:
                return Path.MAIN_MENU

        elif ( decoder.isComplete() and not decoder.isPSBT() ) or decoder.isInvalid():
            self.menu_view.draw_modal(["Not a valid PSBT QR"], "", "Right to Exit")
            input = self.buttons.wait_for([B.KEY_RIGHT])
            return Path.MAIN_MENU
        else:
            return Path.MAIN_MENU


        if len(seed_phrase) == 0:

            # If there is a saved seed, ask to use saved seed
            if self.storage.num_of_saved_seeds() > 0:
                r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Use Save Seed?")
                if r == 1: #Yes
                    slot_num = self.menu_view.display_saved_seed_menu(self.storage,3,None)
                    if slot_num == 0:
                        return Path.MAIN_MENU
                    seed_phrase = self.storage.get_seed_phrase(slot_num)
                    passphrase = self.storage.get_passphrase(slot_num)
                    used_saved_seed = True

            if len(seed_phrase) == 0:
                # gather seed phrase
                # display menu to select 12 or 24 word seed for last word
                ret_val = self.menu_view.display_qr_12_24_word_menu("... [ Return to Main Menu ]")
                if ret_val == Path.SEED_WORD_12:
                    seed_phrase = self.seed_tools_view.display_manual_seed_entry(12)
                elif ret_val == Path.SEED_WORD_24:
                    seed_phrase = self.seed_tools_view.display_manual_seed_entry(24)
                elif ret_val == Path.SEED_WORD_QR:
                    seed_phrase = self.seed_tools_view.read_seed_phrase_qr()
                else:
                    return Path.MAIN_MENU

                if len(seed_phrase) == 0:
                    return Path.MAIN_MENU

            # check if seed phrase is valid
            self.menu_view.draw_modal(["Validating Seed ..."])
            is_valid = self.storage.check_if_seed_valid(seed_phrase)
            if is_valid == False:
                self.menu_view.draw_modal(["Seed Invalid", "check seed phrase", "and try again"], "", "Right to Continue")
                input = self.buttons.wait_for([B.KEY_RIGHT])
                return Path.MAIN_MENU

            if len(passphrase) == 0:
                r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Add Seed Passphrase?")
                if r == 1:
                    # display a tool to pick letters/numbers to make a passphrase
                    passphrase = self.seed_tools_view.draw_passphrase_keyboard_entry()
                    if len(passphrase) == 0 or passphrase == "-1":
                        passphrase = ""
                        self.menu_view.draw_modal(["No passphrase added", "to seed words"], "", "Left to Exit, Right to Continue")
                        input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT])
                        if input == B.KEY_LEFT:
                            return Path.MAIN_MENU
                    else:
                        self.menu_view.draw_modal(["Optional passphrase", "added to seed words", passphrase], "", "Right to Continue")
                        self.buttons.wait_for([B.KEY_RIGHT])

            # display seed phrase
            while True:
                r = self.seed_tools_view.display_seed_phrase(seed_phrase, passphrase, "Right to Continue")
                if r == True:
                    break
                else:
                    # Cancel
                    return Path.MAIN_MENU
                    
            # Ask to save seed
            if self.storage.slot_avaliable() and used_saved_seed == False:
                r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Save Seed?")
                if r == 1: #Yes
                    slot_num = self.menu_view.display_saved_seed_menu(self.storage,2,None)
                    if slot_num in (1,2,3):
                        self.storage.save_seed_phrase(seed_phrase, slot_num)
                        self.storage.save_passphrase(passphrase, slot_num)
                        self.menu_view.draw_modal(["Seed Valid", "Saved to Slot #" + str(slot_num)], "", "Right to Continue")
                        input = self.buttons.wait_for([B.KEY_RIGHT])

        # show transaction information before sign
        self.menu_view.draw_modal(["Parsing PSBT"])
        p = PSBTParser(psbt,seed_phrase,passphrase,self.settings.network)
        self.signing_tools_view.display_transaction_information(p)
        input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT], False)
        if input == B.KEY_LEFT:
            return Path.MAIN_MENU

        # Sign PSBT
        self.menu_view.draw_modal(["PSBT Signing ..."])
        sig_cnt = PSBTParser.sigCount(psbt)
        psbt.sign_with(p.root)
        trimmed_psbt = PSBTParser.trim(psbt)

        if sig_cnt == PSBTParser.sigCount(trimmed_psbt):
            self.menu_view.draw_modal(["Signing failed", "left to exit", "or right to continue", "to display PSBT QR"], "", "")
            input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT], False)
            if input == B.KEY_LEFT:
                return Path.MAIN_MENU

        # Display Animated QR Code
        self.menu_view.draw_modal(["Generating PSBT QR ..."])
        e = EncodeQR(psbt=trimmed_psbt, qr_type=self.settings.qr_psbt_type, qr_density=self.settings.qr_density)
        while True:
            image = e.nextPartImage(240,240,1)
            View.DispShowImage(image)
            time.sleep(0.05)
            if self.buttons.check_for_low(B.KEY_RIGHT):
                    break

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
            return Path.SETTINGS_SUB_MENU

    ### Show Current Network

    def show_current_network_tool(self):
        r = self.settings_tools_view.display_current_network()
        if r is not None:
            self.settings.network = r

        return Path.SETTINGS_SUB_MENU

    ### Show Wallet Selection Tool

    def show_wallet_tool(self):
        r = self.settings_tools_view.display_wallet_selection()
        if r is not None:
            self.settings.software = r

        return Path.SETTINGS_SUB_MENU

    ### Show QR Density Tool

    def show_qr_density_tool(self):
        r = self.settings_tools_view.display_qr_density_selection()
        if r in (EncodeQRDensity.LOW, EncodeQRDensity.MEDIUM, EncodeQRDensity.HIGH):
            self.settings.qr_density = r

        return Path.SETTINGS_SUB_MENU

    ### Show Wallet Policy Tool

    def show_wallet_policy_tool(self):
        r = self.settings_tools_view.display_wallet_policy_selection()
        if r is not None:
            self.settings.script_policy = r

        return Path.SETTINGS_SUB_MENU

    ### Show Version Info

    def show_version_info(self):
        self.settings_tools_view.display_version_info()
        input = self.buttons.wait_for([B.KEY_LEFT, B.KEY_RIGHT])
        if input == B.KEY_LEFT:
            return Path.SETTINGS_SUB_MENU
        elif input == B.KEY_RIGHT:
            return Path.SETTINGS_SUB_MENU

    ### Show Persistent Settings Screen

    def show_persistent_settings_tool(self):
        r = self.settings_tools_view.display_persistent_settings()
        if r is not None:
            if r == True:
                self.menu_view.draw_modal(["Persistent settings", "keeps settings saved", "across reboot.", "Seeds are never saved"], "Warning", "Right to Continue")
                input = self.buttons.wait_for([B.KEY_LEFT, B.KEY_RIGHT])
                if input == B.KEY_RIGHT:
                    self.settings.persistent = r
            else:
                self.menu_view.draw_modal(["This will restore", "the default", "settings.", ""], "Warning", "Right to Continue")
                input = self.buttons.wait_for([B.KEY_LEFT, B.KEY_RIGHT])
                if input == B.KEY_RIGHT:
                    self.settings.persistent = r

        return Path.SETTINGS_SUB_MENU

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

    def show_reset_tool(self):
        self.menu_view.draw_modal(["This will restore", "default settings and", "restart the app", ""], "Warning", "Right to Continue")
        input = self.buttons.wait_for([B.KEY_LEFT, B.KEY_RIGHT])
        if input == B.KEY_RIGHT:
            r = self.menu_view.display_generic_selection_menu(["Yes", "No"], "Reset SeedSigner?")
            if r == 1: #Yes
                self.menu_view.display_blank_screen()
                self.settings.restoreDefault()
                time.sleep(0.1) # give time to write to disk

                return_code = os.system("sudo systemctl is-active --quiet seedsigner.service")

                if return_code == 0:
                    # systemd service is running
                    call("sudo systemctl restart seedsigner.service", shell=True)
                    time.sleep(2)
                else:
                    # systemd service is not running, restart script internally
                    os.execv(sys.executable, ['python3'] + sys.argv)

            else: # No
                return Path.MAIN_MENU

        return Path.MAIN_MENU

