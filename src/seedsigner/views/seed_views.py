import logging
import embit
import random
import time

from binascii import hexlify
from embit import bip39
from embit.descriptor import Descriptor
from embit.networks import NETWORKS
from typing import List

from seedsigner.controller import Controller
from seedsigner.gui.components import FontAwesomeIconConstants, SeedSignerIconConstants
from seedsigner.helpers import embit_utils
from  seedsigner.gui.screens import seed_screens
from seedsigner.gui.screens.screen import (LargeIconStatusScreen, QRDisplayScreen, RET_CODE__BACK_BUTTON, ButtonListScreen,
    WarningScreen, DireWarningScreen)
from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.encode_qr import CompactSeedQrEncoder, GenericStaticQrEncoder, SeedQrEncoder, SpecterXPubQrEncoder, StaticXpubQrEncoder, UrXpubQrEncoder
from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import InvalidSeedException, Seed
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.settings_definition import SettingsDefinition
from seedsigner.models.threads import BaseThread, ThreadsafeCounter
from seedsigner.views.view import NotYetImplementedView, OptionDisabledView, View, Destination, BackStackView, MainMenuView

logger = logging.getLogger(__name__)


class SeedsMenuView(View):
    LOAD = "Load a seed"

    def __init__(self):
        super().__init__()
        self.seeds = []
        for seed in self.controller.storage.seeds:
            self.seeds.append({
                "fingerprint": seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK))
            })


    def run(self):
        if not self.seeds:
            # Nothing to do here unless we have a seed loaded
            return Destination(LoadSeedView, clear_history=True)

        button_data = []
        for seed in self.seeds:
            button_data.append((seed["fingerprint"], SeedSignerIconConstants.FINGERPRINT))
        button_data.append("Load a seed")

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="In-Memory Seeds",
            is_button_text_centered=False,
            button_data=button_data
        )

        if len(self.seeds) > 0 and selected_menu_num < len(self.seeds):
            return Destination(SeedOptionsView, view_args={"seed_num": selected_menu_num})

        elif selected_menu_num == len(self.seeds):
            return Destination(LoadSeedView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedSelectSeedView(View):
    """
    Reusable seed selection UI. Prompts the user to select amongst the already-loaded
    seeds OR to load a seed.

    * `flow`: indicates which user flow is in progress during seed selection (e.g.
                verify single sig addr or sign message).
    """
    SCAN_SEED = ("Scan a seed", SeedSignerIconConstants.QRCODE)
    TYPE_12WORD = ("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
    TYPE_24WORD = ("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)
    TYPE_ELECTRUM = ("Enter Electrum seed", FontAwesomeIconConstants.KEYBOARD)


    def __init__(self, flow: str = Controller.FLOW__VERIFY_SINGLESIG_ADDR):
        super().__init__()
        self.flow = flow


    def run(self):
        seeds = self.controller.storage.seeds

        if self.flow == Controller.FLOW__VERIFY_SINGLESIG_ADDR:
            title = "Verify Address"
            if not seeds:
                text = "Load the seed to verify"
            else: 
                text = "Select seed to verify"

        elif self.flow == Controller.FLOW__SIGN_MESSAGE:
            title = "Sign Message"
            if not seeds:
                text = "Load the seed to sign with"
            else:
                text = "Select seed to sign with"

        else:
            raise Exception(f"Unsupported `flow` specified: {self.flow}")

        button_data = []
        for seed in seeds:
            button_str = seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK))
            
            if seed.passphrase is not None:
                # TODO: Include lock icon on right side of button
                pass
            button_data.append((button_str, SeedSignerIconConstants.FINGERPRINT, "blue"))
        
        button_data.append(self.SCAN_SEED)
        button_data.append(self.TYPE_12WORD)
        button_data.append(self.TYPE_24WORD)

        if self.settings.get_value(SettingsConstants.SETTING__ELECTRUM_SEEDS) == SettingsConstants.OPTION__ENABLED:
            button_data.append(self.TYPE_ELECTRUM)

        selected_menu_num = self.run_screen(
            seed_screens.SeedSelectSeedScreen,
            title=title,
            text=text,
            is_button_text_centered=False,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        if len(seeds) > 0 and selected_menu_num < len(seeds):
            # User selected one of the n seeds
            view_args = dict(seed_num=selected_menu_num)
            if self.flow == Controller.FLOW__VERIFY_SINGLESIG_ADDR:
                return Destination(SeedAddressVerificationView, view_args=view_args)

            elif self.flow == Controller.FLOW__SIGN_MESSAGE:
                self.controller.sign_message_data["seed_num"] = selected_menu_num
                return Destination(SeedSignMessageConfirmMessageView)

        self.controller.resume_main_flow = self.flow

        if button_data[selected_menu_num] == self.SCAN_SEED:
            from seedsigner.views.scan_views import ScanView
            return Destination(ScanView)

        elif button_data[selected_menu_num] in [self.TYPE_12WORD, self.TYPE_24WORD]:
            from seedsigner.views.seed_views import SeedMnemonicEntryView
            if button_data[selected_menu_num] == self.TYPE_12WORD:
                self.controller.storage.init_pending_mnemonic(num_words=12)
            else:
                self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == self.TYPE_ELECTRUM:
            return Destination(SeedElectrumMnemonicStartView)



"""****************************************************************************
    Loading seeds, passphrases, etc
****************************************************************************"""
class LoadSeedView(View):
    SEED_QR = (" Scan a SeedQR", SeedSignerIconConstants.QRCODE)
    TYPE_12WORD = ("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
    TYPE_24WORD = ("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)
    TYPE_ELECTRUM = ("Enter Electrum seed", FontAwesomeIconConstants.KEYBOARD)
    CREATE = (" Create a seed", SeedSignerIconConstants.PLUS)

    def run(self):
        button_data = [
            self.SEED_QR,
            self.TYPE_12WORD,
            self.TYPE_24WORD,
        ]

        if self.settings.get_value(SettingsConstants.SETTING__ELECTRUM_SEEDS) == SettingsConstants.OPTION__ENABLED:
            button_data.append(self.TYPE_ELECTRUM)
        
        button_data.append(self.CREATE)

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="Load A Seed",
            is_button_text_centered=False,
            button_data=button_data
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        if button_data[selected_menu_num] == self.SEED_QR:
            from .scan_views import ScanSeedQRView
            return Destination(ScanSeedQRView)
        
        elif button_data[selected_menu_num] == self.TYPE_12WORD:
            self.controller.storage.init_pending_mnemonic(num_words=12)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == self.TYPE_24WORD:
            self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == self.TYPE_ELECTRUM:
            return Destination(SeedElectrumMnemonicStartView)

        elif button_data[selected_menu_num] == self.CREATE:
            from .tools_views import ToolsMenuView
            return Destination(ToolsMenuView)



class SeedMnemonicEntryView(View):
    def __init__(self, cur_word_index: int = 0, is_calc_final_word: bool=False):
        super().__init__()
        self.cur_word_index = cur_word_index
        self.cur_word = self.controller.storage.get_pending_mnemonic_word(cur_word_index)
        self.is_calc_final_word = is_calc_final_word


    def run(self):
        ret = self.run_screen(
            seed_screens.SeedMnemonicEntryScreen,
            title=f"Seed Word #{self.cur_word_index + 1}",  # Human-readable 1-indexing!
            initial_letters=list(self.cur_word) if self.cur_word else ["a"],
            wordlist=Seed.get_wordlist(wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)),
        )

        if ret == RET_CODE__BACK_BUTTON:
            if self.cur_word_index > 0:
                return Destination(BackStackView)
            else:
                self.controller.storage.discard_pending_mnemonic()
                return Destination(MainMenuView)
        
        # ret will be our new mnemonic word
        self.controller.storage.update_pending_mnemonic(ret, self.cur_word_index)

        if self.is_calc_final_word and self.cur_word_index == self.controller.storage.pending_mnemonic_length - 2:
            # Time to calculate the last word. User must decide how they want to specify
            # the last bits of entropy for the final word.
            from seedsigner.views.tools_views import ToolsCalcFinalWordFinalizePromptView
            return Destination(ToolsCalcFinalWordFinalizePromptView)

        if self.is_calc_final_word and self.cur_word_index == self.controller.storage.pending_mnemonic_length - 1:
            # Time to calculate the last word. User must either select a final word to
            # contribute entropy to the checksum word OR we assume 0 ("abandon").
            from seedsigner.views.tools_views import ToolsCalcFinalWordShowFinalWordView
            return Destination(ToolsCalcFinalWordShowFinalWordView)

        if self.cur_word_index < self.controller.storage.pending_mnemonic_length - 1:
            return Destination(
                SeedMnemonicEntryView,
                view_args={
                    "cur_word_index": self.cur_word_index + 1,
                    "is_calc_final_word": self.is_calc_final_word
                }
            )
        else:
            # Attempt to finalize the mnemonic
            try:
                self.controller.storage.convert_pending_mnemonic_to_pending_seed()
            except InvalidSeedException:
                return Destination(SeedMnemonicInvalidView)

            return Destination(SeedFinalizeView)



class SeedMnemonicInvalidView(View):
    EDIT = "Review & Edit"
    DISCARD = ("Discard", None, None, "red")

    def __init__(self):
        super().__init__()
        self.mnemonic: List[str] = self.controller.storage.pending_mnemonic


    def run(self):
        button_data = [self.EDIT, self.DISCARD]
        selected_menu_num = self.run_screen(
            WarningScreen,
            title="Invalid Mnemonic!",
            status_headline=None,
            text="Checksum failure; not a valid seed phrase.",
            show_back_button=False,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.EDIT:
            return Destination(SeedMnemonicEntryView, view_args={"cur_word_index": 0})

        elif button_data[selected_menu_num] == self.DISCARD:
            self.controller.storage.discard_pending_mnemonic()
            return Destination(MainMenuView)



class SeedFinalizeView(View):
    FINALIZE = "Done"

    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()
        self.fingerprint = self.seed.get_fingerprint(network=self.settings.get_value(SettingsConstants.SETTING__NETWORK))


    def run(self):
        button_data = [self.FINALIZE]
        passphrase_button = self.seed.passphrase_label
        if self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE) != SettingsConstants.OPTION__DISABLED:
            button_data.append(passphrase_button)

        selected_menu_num = self.run_screen(
            seed_screens.SeedFinalizeScreen,
            fingerprint=self.fingerprint,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.FINALIZE:
            seed_num = self.controller.storage.finalize_pending_seed()
            return Destination(SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True)

        elif button_data[selected_menu_num] == passphrase_button:
            return Destination(SeedAddPassphraseView)



class SeedAddPassphraseView(View):
    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()


    def run(self):
        passphrase_title=self.seed.passphrase_label
        ret_dict = self.run_screen(seed_screens.SeedAddPassphraseScreen, passphrase=self.seed.passphrase, title=passphrase_title)

        # The new passphrase will be the return value; it might be empty.
        self.seed.set_passphrase(ret_dict["passphrase"])

        if "is_back_button" in ret_dict:
            if len(self.seed.passphrase) > 0:
                return Destination(SeedAddPassphraseExitDialogView)
            else:
                return Destination(BackStackView)
            
        elif len(self.seed.passphrase) > 0:
            return Destination(SeedReviewPassphraseView)
        
        else:
            return Destination(SeedFinalizeView)



class SeedAddPassphraseExitDialogView(View):
    EDIT = "Edit passphrase"
    DISCARD = ("Discard passphrase", None, None, "red")

    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()


    def run(self):
        button_data = [self.EDIT, self.DISCARD]
        
        selected_menu_num = self.run_screen(
            WarningScreen,
            title="Discard passphrase?",
            status_headline=None,
            text="Your current passphrase entry will be erased",
            show_back_button=False,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.EDIT:
            return Destination(SeedAddPassphraseView)

        elif button_data[selected_menu_num] == self.DISCARD:
            self.seed.set_passphrase("")
            return Destination(SeedFinalizeView)
        


class SeedReviewPassphraseView(View):
    """
        Display the completed passphrase back to the user.
    """
    EDIT = "Edit passphrase"
    DONE = "Done"

    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()


    def run(self):
        # Get the before/after fingerprints
        network = self.settings.get_value(SettingsConstants.SETTING__NETWORK)
        passphrase = self.seed.passphrase
        fingerprint_with = self.seed.get_fingerprint(network=network)
        self.seed.set_passphrase("")
        fingerprint_without = self.seed.get_fingerprint(network=network)
        self.seed.set_passphrase(passphrase)
        
        button_data = [self.EDIT, self.DONE]

        # Because we have an explicit "Edit" button, we disable "BACK" to keep the
        # routing options sane.
        selected_menu_num = self.run_screen(
            seed_screens.SeedReviewPassphraseScreen,
            fingerprint_without=fingerprint_without,
            fingerprint_with=fingerprint_with,
            passphrase=self.seed.passphrase,
            button_data=button_data,
            show_back_button=False,
        )

        if button_data[selected_menu_num] == self.EDIT:
            return Destination(SeedAddPassphraseView)
        
        elif button_data[selected_menu_num] == self.DONE:
            seed_num = self.controller.storage.finalize_pending_seed()
            return Destination(SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True)
            

            
class SeedDiscardView(View):
    KEEP = "Keep Seed"
    DISCARD = ("Discard", None, None, "red")

    def __init__(self, seed_num: int = None):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is not None:
            self.seed = self.controller.get_seed(self.seed_num)
        else:
            self.seed = self.controller.storage.pending_seed


    def run(self):
        button_data = [self.KEEP, self.DISCARD]

        fingerprint = self.seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK))
        selected_menu_num = self.run_screen(
            WarningScreen,
            title="Discard Seed?",
            status_headline=None,
            text=f"Wipe seed {fingerprint} from the device?",
            show_back_button=False,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.KEEP:
            # Use skip_current_view=True to prevent BACK from landing on this warning screen
            if self.seed_num is not None:
                return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num}, skip_current_view=True)
            else:
                return Destination(SeedFinalizeView, skip_current_view=True)

        elif button_data[selected_menu_num] == self.DISCARD:
            if self.seed_num is not None:
                self.controller.discard_seed(self.seed_num)
            else:
                self.controller.storage.clear_pending_seed()
            return Destination(MainMenuView, clear_history=True)



class SeedElectrumMnemonicStartView(View):
    """
    Currently just a warning display before entering an Electrum seed.
    
    Could be expanded with a follow-up View to specify Electrum seed type.
    """
    def run(self):
        self.run_screen(
                WarningScreen,
                title="Electrum warning",
                status_headline=None,
                text="Some features are disabled for Electrum seeds.",
                show_back_button=False,
        )

        self.controller.storage.init_pending_mnemonic(num_words=12, is_electrum=True)

        return Destination(SeedMnemonicEntryView)



"""****************************************************************************
    Views for actions on individual seeds:
****************************************************************************"""
class SeedOptionsView(View):
    SCAN_PSBT = ("Scan PSBT", SeedSignerIconConstants.QRCODE)
    VERIFY_ADDRESS = "Verify Addr"
    EXPORT_XPUB = "Export Xpub"
    EXPLORER = "Address Explorer"
    SIGN_MESSAGE = "Sign Message"
    BACKUP = ("Backup Seed", None, None, None, SeedSignerIconConstants.CHEVRON_RIGHT)
    BIP85_CHILD_SEED = "BIP-85 Child Seed"
    DISCARD = ("Discard Seed", None, None, "red")


    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)


    def run(self):
        from seedsigner.views.psbt_views import PSBTOverviewView

        if self.controller.unverified_address:
            if self.controller.resume_main_flow == Controller.FLOW__VERIFY_SINGLESIG_ADDR:
                # Jump straight back into the single sig addr verification flow
                self.controller.resume_main_flow = None
                return Destination(SeedAddressVerificationView, view_args=dict(seed_num=self.seed_num), skip_current_view=True)

        if self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER:
            # Jump straight back into the address explorer script type selection flow
            # But don't cancel the `resume_main_flow` as we'll still need that after
            # derivation path is specified.
            return Destination(SeedExportXpubScriptTypeView, view_args=dict(seed_num=self.seed_num, sig_type=SettingsConstants.SINGLE_SIG), skip_current_view=True)

        elif self.controller.resume_main_flow == Controller.FLOW__SIGN_MESSAGE:
            self.controller.sign_message_data["seed_num"] = self.seed_num
            return Destination(SeedSignMessageConfirmMessageView, skip_current_view=True)

        if self.controller.psbt:
            if PSBTParser.has_matching_input_fingerprint(self.controller.psbt, self.seed, network=self.settings.get_value(SettingsConstants.SETTING__NETWORK)):
                if self.controller.resume_main_flow and self.controller.resume_main_flow == Controller.FLOW__PSBT:
                    # Re-route us directly back to the start of the PSBT flow
                    self.controller.resume_main_flow = None
                    self.controller.psbt_seed = self.seed
                    return Destination(PSBTOverviewView, skip_current_view=True)

        button_data = []

        if self.controller.unverified_address:
            addr = self.controller.unverified_address["address"][:7]
            self.VERIFY_ADDRESS += f" {addr}"
            button_data.append(self.VERIFY_ADDRESS)

        button_data.append(self.SCAN_PSBT)
        
        if self.settings.get_value(SettingsConstants.SETTING__XPUB_EXPORT) == SettingsConstants.OPTION__ENABLED:
            button_data.append(self.EXPORT_XPUB)

        button_data.append(self.EXPLORER)
        button_data.append(self.BACKUP)

        if self.settings.get_value(SettingsConstants.SETTING__MESSAGE_SIGNING) == SettingsConstants.OPTION__ENABLED:
            button_data.append(self.SIGN_MESSAGE)
        
        if self.settings.get_value(SettingsConstants.SETTING__BIP85_CHILD_SEEDS) == SettingsConstants.OPTION__ENABLED and self.seed.bip85_supported:
            button_data.append(self.BIP85_CHILD_SEED)

        button_data.append(self.DISCARD)
        
        selected_menu_num = self.run_screen(
            seed_screens.SeedOptionsScreen,
            button_data=button_data,
            fingerprint=self.seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK)),
            has_passphrase=self.seed.passphrase is not None,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # Force BACK to always return to the Main Menu
            return Destination(MainMenuView)

        if button_data[selected_menu_num] == self.SCAN_PSBT:
            from seedsigner.views.scan_views import ScanPSBTView
            self.controller.psbt_seed = self.controller.get_seed(self.seed_num)
            return Destination(ScanPSBTView)

        elif button_data[selected_menu_num] == self.VERIFY_ADDRESS:
            return Destination(SeedAddressVerificationView, view_args=dict(seed_num=self.seed_num))

        elif button_data[selected_menu_num] == self.EXPORT_XPUB:
            return Destination(SeedExportXpubSigTypeView, view_args=dict(seed_num=self.seed_num))

        elif button_data[selected_menu_num] == self.EXPLORER:
            self.controller.resume_main_flow = Controller.FLOW__ADDRESS_EXPLORER
            return Destination(SeedExportXpubScriptTypeView, view_args=dict(seed_num=self.seed_num, sig_type=SettingsConstants.SINGLE_SIG))

        elif button_data[selected_menu_num] == self.SIGN_MESSAGE:
            from seedsigner.views.scan_views import ScanView
            self.controller.sign_message_data = dict(seed_num=self.seed_num)
            self.controller.resume_main_flow = Controller.FLOW__SIGN_MESSAGE
            return Destination(ScanView)

        elif button_data[selected_menu_num] == self.BACKUP:
            return Destination(SeedBackupView, view_args=dict(seed_num=self.seed_num))

        elif button_data[selected_menu_num] == self.BIP85_CHILD_SEED:
            return Destination(SeedBIP85ApplicationModeView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == self.DISCARD:
            return Destination(SeedDiscardView, view_args=dict(seed_num=self.seed_num))



class SeedBackupView(View):
    VIEW_WORDS = "View Seed Words"
    EXPORT_SEEDQR = "Export as SeedQR"

    def __init__(self, seed_num):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)
    

    def run(self):
        button_data = [self.VIEW_WORDS]

        if self.seed.seedqr_supported:
            button_data.append(self.EXPORT_SEEDQR)

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="Backup Seed",
            button_data=button_data,
            is_bottom_list=True,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == self.VIEW_WORDS:
            return Destination(SeedWordsWarningView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == self.EXPORT_SEEDQR:
            return Destination(SeedTranscribeSeedQRFormatView, view_args={"seed_num": self.seed_num})



"""****************************************************************************
    Export Xpub flow
****************************************************************************"""
class SeedExportXpubSigTypeView(View):
    SINGLE_SIG = "Single Sig"
    MULTISIG = "Multisig"

    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        if len(self.settings.get_value(SettingsConstants.SETTING__SIG_TYPES)) == 1:
            # Nothing to select; skip this screen
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": self.settings.get_value(SettingsConstants.SETTING__SIG_TYPES)[0]}, skip_current_view=True)

        button_data=[self.SINGLE_SIG, self.MULTISIG]

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="Export Xpub",
            button_data=button_data
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == self.SINGLE_SIG:
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": SettingsConstants.SINGLE_SIG})

        elif button_data[selected_menu_num] == self.MULTISIG:
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": SettingsConstants.MULTISIG})



class SeedExportXpubScriptTypeView(View):
    def __init__(self, seed_num: int, sig_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type


    def run(self):
        from .tools_views import ToolsAddressExplorerAddressTypeView
        args = {"seed_num": self.seed_num, "sig_type": self.sig_type}

        script_types = self.settings.get_value(SettingsConstants.SETTING__SCRIPT_TYPES)

        seed = self.controller.storage.seeds[self.seed_num]
        if seed.script_override:
            # This seed only allows one script type
            # TODO: Does it matter if the Settings don't have the override script type
            # enabled?
            script_types = [seed.script_override]

        if len(script_types) == 1:
            # Nothing to select; skip this screen
            args["script_type"] = script_types[0]

            if self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER:
                del args["sig_type"]
                return Destination(ToolsAddressExplorerAddressTypeView, view_args=args, skip_current_view=True)
            else:
                return Destination(SeedExportXpubCoordinatorView, view_args=args, skip_current_view=True)
        
        title = "Export Xpub"
        if self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER:
            title = "Address Explorer"

        button_data = []
        for script_type in self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__SCRIPT_TYPES):
            button_data.append(script_type)

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=title,
            is_button_text_centered=False,
            button_data=button_data,
            is_bottom_list=True,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # If previous view is SeedOptionsView then that should be where resume_main_flow started (otherwise it would have been skipped).
            if len(self.controller.back_stack) >= 2 and self.controller.back_stack[-2].View_cls == SeedOptionsView:
                self.controller.resume_main_flow = None
            return Destination(BackStackView)

        else:
            script_types_settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__SCRIPT_TYPES)
            selected_display_name = button_data[selected_menu_num]
            args["script_type"] = script_types_settings_entry.get_selection_option_value_by_display_name(selected_display_name)

            if args["script_type"] == SettingsConstants.CUSTOM_DERIVATION:
                return Destination(SeedExportXpubCustomDerivationView, view_args=args)

            if self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER:
                del args["sig_type"]
                return Destination(ToolsAddressExplorerAddressTypeView, view_args=args)
            else:
                return Destination(SeedExportXpubCoordinatorView, view_args=args)



class SeedExportXpubCustomDerivationView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.custom_derivation_path = "m/"


    def run(self):
        ret = self.run_screen(
            seed_screens.SeedExportXpubCustomDerivationScreen,
            initial_value=self.custom_derivation_path,
        )

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        # ret will be the custom derivation path
        custom_derivation = ret

        if self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER:
            from .tools_views import ToolsAddressExplorerAddressTypeView
            return Destination(ToolsAddressExplorerAddressTypeView, view_args=dict(seed_num=self.seed_num, script_type=self.script_type, custom_derivation=custom_derivation))

        return Destination(
            SeedExportXpubCoordinatorView,
            view_args={
                "seed_num": self.seed_num,
                "sig_type": self.sig_type,
                "script_type": self.script_type,
                "custom_derivation": custom_derivation,
            }
        )



class SeedExportXpubCoordinatorView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str, custom_derivation: str = None):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.custom_derivation = custom_derivation


    def run(self):
        args = {
            "seed_num": self.seed_num,
            "sig_type": self.sig_type,
            "script_type": self.script_type,
            "custom_derivation": self.custom_derivation,
        }
        if len(self.settings.get_value(SettingsConstants.SETTING__COORDINATORS)) == 1:
            # Nothing to select; skip this screen
            args["coordinator"] = self.settings.get_value(SettingsConstants.SETTING__COORDINATORS)[0]
            return Destination(SeedExportXpubWarningView, view_args=args, skip_current_view=True)

        button_data = self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__COORDINATORS)

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="Export Xpub",
            is_button_text_centered=False,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        coordinators_settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__COORDINATORS)
        selected_display_name = button_data[selected_menu_num]
        args["coordinator"] = coordinators_settings_entry.get_selection_option_value_by_display_name(selected_display_name)

        return Destination(SeedExportXpubWarningView, view_args=args)




class SeedExportXpubWarningView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str, custom_derivation: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.coordinator = coordinator
        self.custom_derivation = custom_derivation


    def run(self):
        destination = Destination(
            SeedExportXpubDetailsView,
            view_args={
                "seed_num": self.seed_num,
                "sig_type": self.sig_type,
                "script_type": self.script_type,
                "coordinator": self.coordinator,
                "custom_derivation": self.custom_derivation,
            },
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )

        if self.settings.get_value(SettingsConstants.SETTING__PRIVACY_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            # Skip the WarningView entirely
            return destination

        selected_menu_num = self.run_screen(
            WarningScreen,
            status_headline="Privacy Leak!",
            text="""Xpub can be used to view all future transactions.""",
        )

        if selected_menu_num == 0:
            # User clicked "I Understand"
            return destination

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubDetailsView(View):
    """
        Collects the user input from all the previous screens leading up to this and
        finally calculates the xpub and displays the summary view to the user.
    """
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str, custom_derivation: str):
        super().__init__()
        self.sig_type = sig_type
        self.script_type = script_type
        self.coordinator = coordinator
        self.custom_derivation = custom_derivation
        
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)


    def run(self):
        seed_derivation_override = self.seed.derivation_override(self.sig_type)
        if self.script_type == SettingsConstants.CUSTOM_DERIVATION:
            derivation_path = self.custom_derivation
        elif seed_derivation_override:
            derivation_path = seed_derivation_override
        else:
            derivation_path = embit_utils.get_standard_derivation_path(
                network=self.settings.get_value(SettingsConstants.SETTING__NETWORK),
                wallet_type=self.sig_type,
                script_type=self.script_type
            )

        if self.settings.get_value(SettingsConstants.SETTING__XPUB_DETAILS) == SettingsConstants.OPTION__DISABLED:
            # We're just skipping right past this screen
            selected_menu_num = 0

        else:
            # The derivation calc takes a few moments. Run the loading screen while we wait.
            from seedsigner.gui.screens.screen import LoadingScreenThread
            self.loading_screen = LoadingScreenThread(text="Generating xpub...")
            self.loading_screen.start()

            try:
                embit_network = NETWORKS[SettingsConstants.map_network_to_embit(self.settings.get_value(SettingsConstants.SETTING__NETWORK))]
                version = self.seed.detect_version(
                    derivation_path,
                    self.settings.get_value(SettingsConstants.SETTING__NETWORK),
                    self.sig_type
                )
                root = embit.bip32.HDKey.from_seed(
                    self.seed.seed_bytes,
                    version=embit_network["xprv"]
                )
                fingerprint = hexlify(root.child(0).fingerprint).decode('utf-8')
                xprv = root.derive(derivation_path)
                xpub = xprv.to_public()
                xpub_base58 = xpub.to_string(version=version)

            finally:
                self.loading_screen.stop()

            selected_menu_num = self.run_screen(
                seed_screens.SeedExportXpubDetailsScreen,
                fingerprint=fingerprint,
                has_passphrase=self.seed.passphrase is not None,
                derivation_path=derivation_path,
                xpub=xpub_base58,
            )

        if selected_menu_num == 0:
            return Destination(
                SeedExportXpubQRDisplayView,
                dict(seed_num=self.seed_num,
                     coordinator=self.coordinator,
                     derivation_path=derivation_path,
                     sig_type=self.sig_type
                )
            )

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubQRDisplayView(View):
    def __init__(self, seed_num: int, coordinator: str, derivation_path: str, sig_type: str = SettingsConstants.SINGLE_SIG):
        super().__init__()
        self.seed = self.controller.get_seed(seed_num)

        encoder_args = dict(
            seed=self.seed,
            derivation=derivation_path,
            network=self.settings.get_value(SettingsConstants.SETTING__NETWORK),
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
            sig_type=sig_type
        )

        if coordinator == SettingsConstants.COORDINATOR__SPECTER_DESKTOP:
            self.qr_encoder = SpecterXPubQrEncoder(**encoder_args)

        elif coordinator in [SettingsConstants.COORDINATOR__BLUE_WALLET,
                             SettingsConstants.COORDINATOR__KEEPER,
                             SettingsConstants.COORDINATOR__NUNCHUK]:
            self.qr_encoder = StaticXpubQrEncoder(**encoder_args)

        else:
            self.qr_encoder = UrXpubQrEncoder(**encoder_args)


    def run(self):
        self.run_screen(
            QRDisplayScreen,
            qr_encoder=self.qr_encoder
        )

        return Destination(MainMenuView)



"""****************************************************************************
    View Seed Words flow
****************************************************************************"""
class SeedWordsWarningView(View):
    def __init__(self, seed_num: int, bip85_data: dict = None):
        super().__init__()
        self.seed_num = seed_num
        self.bip85_data = bip85_data


    def run(self):
        destination = Destination(
            SeedWordsView,
            view_args=dict(
                seed_num=self.seed_num,
                page_index=0,
                bip85_data=self.bip85_data
            ),
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )
        if self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            # Forward straight to showing the words
            return destination

        selected_menu_num = self.run_screen(
            DireWarningScreen,
            text="""Never input your seed phrase into a device that connects to the internet.""",
        )

        if selected_menu_num == 0:
            # User clicked "I Understand"
            return destination

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedWordsView(View):
    def __init__(self, seed_num: int, bip85_data: dict = None, page_index: int = 0):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is None:
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.seed = self.controller.get_seed(self.seed_num)
        self.bip85_data = bip85_data
        self.page_index = page_index


    def run(self):
        NEXT = "Next"
        DONE = "Done"

        # Slice the mnemonic to our current 4-word section
        words_per_page = 4  # TODO: eventually make this configurable for bigger screens?

        if self.bip85_data is not None:
            mnemonic = self.seed.get_bip85_child_mnemonic(self.bip85_data["child_index"], self.bip85_data["num_words"]).split()
            title = f"""Child #{self.bip85_data["child_index"]}"""
        else:
            mnemonic = self.seed.mnemonic_display_list
            title = "Seed Words"
        words = mnemonic[self.page_index*words_per_page:(self.page_index + 1)*words_per_page]

        button_data = []
        num_pages = int(len(mnemonic)/words_per_page)
        if self.page_index < num_pages - 1 or self.seed_num is None:
            button_data.append(NEXT)
        else:
            button_data.append(DONE)

        selected_menu_num = seed_screens.SeedWordsScreen(
            title=f"{title}: {self.page_index+1}/{num_pages}",
            words=words,
            page_index=self.page_index,
            num_pages=num_pages,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == NEXT:
            if self.seed_num is None and self.page_index == num_pages - 1:
                return Destination(
                    SeedWordsBackupTestPromptView,
                    view_args=dict(seed_num=self.seed_num, bip85_data=self.bip85_data),
                )
            else:
                return Destination(
                    SeedWordsView,
                    view_args=dict(seed_num=self.seed_num, page_index=self.page_index + 1, bip85_data=self.bip85_data)
                )

        elif button_data[selected_menu_num] == DONE:
            # Must clear history to avoid BACK button returning to private info
            return Destination(
                SeedWordsBackupTestPromptView,
                view_args=dict(seed_num=self.seed_num, bip85_data=self.bip85_data),
            )



"""****************************************************************************
    BIP85 - Derive child mnemonic (seed) flow
****************************************************************************"""
class SeedBIP85ApplicationModeView(View):
    """
        * Ask the user the application type as defined in the BIP0085 spec.
        * Currently only Word mode of 12, 24 words (Application number: 39')
        * Possible future additions are
        *  WIF (HDSEED)
        *  XPRV (BIP32)
    """
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.num_words = 0
        self.bip85_app_num = 39     # TODO: Support other Application numbers


    def run(self):
        # TODO: Future enhancement to display WIF (HD-SEED) and XPRV (Bip32)?
        WORDS_12 = "12 Words"
        WORDS_24 = "24 Words"

        button_data = [WORDS_12, WORDS_24]

        selected_menu_num = ButtonListScreen(
            title="BIP-85 Num Words",
            button_data=button_data
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == WORDS_12:
            self.num_words = 12
        elif button_data[selected_menu_num] == WORDS_24:
            self.num_words = 24

        return Destination(
            SeedBIP85SelectChildIndexView,
            view_args=dict(seed_num=self.seed_num, num_words=self.num_words)
        )



# View to retrieve the derived seed index
class SeedBIP85SelectChildIndexView(View):
    def __init__(self, seed_num: int, num_words: int):
        super().__init__()
        self.seed_num = seed_num
        self.num_words = num_words


    def run(self):
        # Change this later to use the generic Screen input keyboard
        ret = seed_screens.SeedBIP85SelectChildIndexScreen().display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if not 0 <= int(ret) < 2**31:
            return Destination(
                SeedBIP85InvalidChildIndexView,
                view_args=dict(
                    seed_num=self.seed_num, 
                    num_words=self.num_words
                ),
                skip_current_view=True
            )

        return Destination(
            SeedWordsWarningView,
            view_args=dict(
                seed_num=self.seed_num,
                bip85_data=dict(child_index=int(ret), num_words=self.num_words),
            )
        )


class SeedBIP85InvalidChildIndexView(View):
    def __init__(self, seed_num: int, num_words: int):
        super().__init__()
        self.seed_num = seed_num
        self.num_words = num_words


    def run(self):
        DireWarningScreen(
            title="BIP-85 Index Error",
            show_back_button=False,
            status_headline="Invalid Child Index",
            text=f"BIP-85 Child Index must be between 0 and {2**31-1}.",
            button_data=["Try Again"]
        ).display()

        return Destination(
                SeedBIP85SelectChildIndexView,
                view_args=dict(
                    seed_num=self.seed_num, 
                    num_words=self.num_words
                ),
                skip_current_view=True
            )



"""****************************************************************************
    Seed Words Backup Test
****************************************************************************"""
class SeedWordsBackupTestPromptView(View):
    def __init__(self, seed_num: int, bip85_data: dict = None):
        super().__init__()
        self.seed_num = seed_num
        self.bip85_data = bip85_data


    def run(self):
        VERIFY = "Verify"
        SKIP = "Skip"
        button_data = [VERIFY, SKIP]
        selected_menu_num = seed_screens.SeedWordsBackupTestPromptScreen(
            button_data=button_data,
        ).display()

        if button_data[selected_menu_num] == VERIFY:
            return Destination(
                SeedWordsBackupTestView,
                view_args=dict(seed_num=self.seed_num, bip85_data=self.bip85_data),
            )

        elif button_data[selected_menu_num] == SKIP:
            if self.seed_num is not None:
                return Destination(SeedOptionsView, view_args=dict(seed_num=self.seed_num))
            else:
                return Destination(SeedFinalizeView)



class SeedWordsBackupTestView(View):
    def __init__(self, seed_num: int, bip85_data: dict = None, confirmed_list: List[bool] = None, cur_index: int = None):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is None:
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.seed = self.controller.get_seed(self.seed_num)
        self.bip85_data = bip85_data

        if self.bip85_data is not None:
            self.mnemonic_list = self.seed.get_bip85_child_mnemonic(self.bip85_data["child_index"], self.bip85_data["num_words"]).split()
        else:
            self.mnemonic_list = self.seed.mnemonic_display_list

        self.confirmed_list = confirmed_list
        if not self.confirmed_list:
            self.confirmed_list = []

        self.cur_index = cur_index


    def run(self):
        if self.cur_index is None:
            self.cur_index = int(random.random() * len(self.mnemonic_list))
            while self.cur_index in self.confirmed_list:
                self.cur_index = int(random.random() * len(self.mnemonic_list))

        real_word = self.mnemonic_list[self.cur_index]
        fake_word1 = bip39.WORDLIST[int(random.random() * 2047)]
        fake_word2 = bip39.WORDLIST[int(random.random() * 2047)]
        fake_word3 = bip39.WORDLIST[int(random.random() * 2047)]

        button_data = [real_word, fake_word1, fake_word2, fake_word3]
        random.shuffle(button_data)

        selected_menu_num = ButtonListScreen(
            title=f"Verify Word #{self.cur_index + 1}",
            show_back_button=False,
            button_data=button_data,
            is_bottom_list=True,
            is_button_text_centered=True,
        ).display()

        if button_data[selected_menu_num] == real_word:
            self.confirmed_list.append(self.cur_index)
            if len(self.confirmed_list) == len(self.mnemonic_list):
                # Successfully confirmed the full mnemonic!
                return Destination(
                    SeedWordsBackupTestSuccessView,
                    view_args=dict(seed_num=self.seed_num),
                )
            else:
                # Continue testing the remaining words
                return Destination(
                    SeedWordsBackupTestView,
                    view_args=dict(seed_num=self.seed_num, confirmed_list=self.confirmed_list, bip85_data=self.bip85_data),
                )

        else:
            # Picked the WRONG WORD!
            return Destination(
                SeedWordsBackupTestMistakeView,
                view_args=dict(
                    seed_num=self.seed_num,
                    bip85_data=self.bip85_data,
                    cur_index=self.cur_index,
                    wrong_word=button_data[selected_menu_num],
                    confirmed_list=self.confirmed_list,
                )
            )



class SeedWordsBackupTestMistakeView(View):
    def __init__(self, seed_num: int, bip85_data: dict = None, cur_index: int = None, wrong_word: str = None, confirmed_list: List[bool] = None):
        super().__init__()
        self.seed_num = seed_num
        self.bip85_data = bip85_data
        self.cur_index = cur_index
        self.wrong_word = wrong_word
        self.confirmed_list = confirmed_list


    def run(self):
        REVIEW = "Review Seed Words"
        RETRY = "Try Again"
        button_data = [REVIEW, RETRY]

        selected_menu_num = DireWarningScreen(
            title="Verification Error",
            show_back_button=False,
            status_headline="Wrong Word!",
            text=f"Word #{self.cur_index + 1} is not \"{self.wrong_word}\"!",
            button_data=button_data,
        ).display()

        if button_data[selected_menu_num] == REVIEW:
            return Destination(
                SeedWordsView,
                view_args=dict(seed_num=self.seed_num, bip85_data=self.bip85_data),
            )

        elif button_data[selected_menu_num] == RETRY:
            return Destination(
                SeedWordsBackupTestView,
                view_args=dict(
                    seed_num=self.seed_num,
                    confirmed_list=self.confirmed_list,
                    cur_index=self.cur_index,
                    bip85_data=self.bip85_data,
                )
            )



class SeedWordsBackupTestSuccessView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num

    def run(self):
        LargeIconStatusScreen(
            title="Backup Verified",
            show_back_button=False,
            status_headline="Success!",
            text="All mnemonic backup words were successfully verified!",
            button_data=["OK"]
        ).display()

        if self.seed_num is not None:
            return Destination(SeedOptionsView, view_args=dict(seed_num=self.seed_num), clear_history=True)
        else:
            return Destination(SeedFinalizeView)



"""****************************************************************************
    Export as SeedQR
****************************************************************************"""
class SeedTranscribeSeedQRFormatView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        seed = self.controller.get_seed(self.seed_num)
        if len(seed.mnemonic_list) == 12:
            STANDARD = "Standard: 25x25"
            COMPACT = "Compact: 21x21"
            num_modules_standard = 25
            num_modules_compact = 21
        else:
            STANDARD = "Standard: 29x29"
            COMPACT = "Compact: 25x25"
            num_modules_standard = 29
            num_modules_compact = 25

        if self.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR) != SettingsConstants.OPTION__ENABLED:
            # Only configured for standard SeedQR
            return Destination(
                SeedTranscribeSeedQRWarningView,
                view_args={
                    "seed_num": self.seed_num,
                    "seedqr_format": QRType.SEED__SEEDQR,
                    "num_modules": num_modules_standard,
                },
                skip_current_view=True,
            )

        button_data = [STANDARD, COMPACT]

        selected_menu_num = seed_screens.SeedTranscribeSeedQRFormatScreen(
            title="SeedQR Format",
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        if button_data[selected_menu_num] == STANDARD:
            seedqr_format = QRType.SEED__SEEDQR
            num_modules = num_modules_standard
        else:
            seedqr_format = QRType.SEED__COMPACTSEEDQR
            num_modules = num_modules_compact
        
        return Destination(
            SeedTranscribeSeedQRWarningView,
                view_args={
                    "seed_num": self.seed_num,
                    "seedqr_format": seedqr_format,
                    "num_modules": num_modules,
                }
            )



class SeedTranscribeSeedQRWarningView(View):
    def __init__(self, seed_num: int, seedqr_format: str = QRType.SEED__SEEDQR, num_modules: int = 29):
        super().__init__()
        self.seed_num = seed_num
        self.seedqr_format = seedqr_format
        self.num_modules = num_modules
    

    def run(self):
        destination = Destination(
            SeedTranscribeSeedQRWholeQRView,
            view_args={
                "seed_num": self.seed_num,
                "seedqr_format": self.seedqr_format,
                "num_modules": self.num_modules,
            },
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )

        if self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            # Forward straight to transcribing the SeedQR
            return destination

        selected_menu_num = DireWarningScreen(
            status_headline="SeedQR is your private key!",
            text="""Never photograph or scan it into a device that connects to the internet.""",
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        else:
            # User clicked "I Understand"
            return destination
    


class SeedTranscribeSeedQRWholeQRView(View):
    def __init__(self, seed_num: int, seedqr_format: str, num_modules: int):
        super().__init__()
        self.seed_num = seed_num
        self.seedqr_format = seedqr_format
        self.num_modules = num_modules
        self.seed = self.controller.get_seed(seed_num)
    

    def run(self):
        encoder_args = dict(mnemonic=self.seed.mnemonic_list,
                            wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE))
        if self.seedqr_format == QRType.SEED__SEEDQR:
            e = SeedQrEncoder(**encoder_args)
        elif self.seedqr_format == QRType.SEED__COMPACTSEEDQR:
            e = CompactSeedQrEncoder(**encoder_args)

        data = e.next_part()

        ret = seed_screens.SeedTranscribeSeedQRWholeQRScreen(
            qr_data=data,
            num_modules=self.num_modules,
        ).display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        else:
            return Destination(
                SeedTranscribeSeedQRZoomedInView,
                view_args={
                    "seed_num": self.seed_num,
                    "seedqr_format": self.seedqr_format
                }
            )



class SeedTranscribeSeedQRZoomedInView(View):
    def __init__(self, seed_num: int, seedqr_format: str):
        super().__init__()
        self.seed_num = seed_num
        self.seedqr_format = seedqr_format
        self.seed = self.controller.get_seed(seed_num)
    

    def run(self):
        encoder_args = dict(mnemonic=self.seed.mnemonic_list,
                            wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE))
        if self.seedqr_format == QRType.SEED__SEEDQR:
            e = SeedQrEncoder(**encoder_args)
        elif self.seedqr_format == QRType.SEED__COMPACTSEEDQR:
            e = CompactSeedQrEncoder(**encoder_args)

        data = e.next_part()

        if len(self.seed.mnemonic_list) == 24:
            if self.seedqr_format == QRType.SEED__COMPACTSEEDQR:
                num_modules = 25
            else:
                num_modules = 29
        else:
            if self.seedqr_format == QRType.SEED__COMPACTSEEDQR:
                num_modules = 21
            else:
                num_modules = 25

        seed_screens.SeedTranscribeSeedQRZoomedInScreen(
            qr_data=data,
            num_modules=num_modules,
        ).display()

        return Destination(SeedTranscribeSeedQRConfirmQRPromptView, view_args={"seed_num": self.seed_num})



class SeedTranscribeSeedQRConfirmQRPromptView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(seed_num)
    

    def run(self):
        SCAN = ("Confirm SeedQR", SeedSignerIconConstants.QRCODE)
        DONE = "Done"
        button_data = [SCAN, DONE]

        selected_menu_option = seed_screens.SeedTranscribeSeedQRConfirmQRPromptScreen(
            title="Confirm SeedQR?",
            button_data=button_data,
        ).display()

        if selected_menu_option == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_option] == SCAN:
            return Destination(SeedTranscribeSeedQRConfirmScanView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_option] == DONE:
            return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num}, clear_history=True)



class SeedTranscribeSeedQRConfirmScanView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(seed_num)

    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen

        # Run the live preview and QR code capture process
        # TODO: Does this belong in its own BaseThread?
        wordlist_language_code = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        self.decoder = DecodeQR(wordlist_language_code=wordlist_language_code)
        ScanScreen(decoder=self.decoder, instructions_text="Scan your SeedQR").display()

        if self.decoder.is_complete:
            if self.decoder.is_seed:
                seed_mnemonic = self.decoder.get_seed_phrase()
                # Found a valid mnemonic seed! But does it match?
                if seed_mnemonic != self.seed.mnemonic_list:
                    DireWarningScreen(
                        title="Confirm SeedQR",
                        status_headline="Error!",
                        text="Your transcribed SeedQR does not match your original seed!",
                        show_back_button=False,
                        button_data=["Review SeedQR"],
                    ).display()

                    return Destination(BackStackView, skip_current_view=True)
                
                else:
                    LargeIconStatusScreen(
                        title="Confirm SeedQR",
                        status_headline="Success!",
                        text="Your transcribed SeedQR successfully scanned and yielded the same seed.",
                        show_back_button=False,
                        button_data=["OK"],
                    ).display()

                    return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num})

            else:
                # Will this case ever happen? Will trigger if a different kind of QR code is scanned
                DireWarningScreen(
                    title="Confirm SeedQR",
                    status_headline="Error!",
                    text="Your transcribed SeedQR could not be read!",
                    show_back_button=False,
                    button_data=["Review SeedQR"],
                ).display()

                return Destination(BackStackView, skip_current_view=True)



"""****************************************************************************
    Address verification
****************************************************************************"""
class AddressVerificationStartView(View):
    def __init__(self, address: str, script_type: str, network: str):
        super().__init__()
        self.controller.unverified_address = dict(
            address=address,
            script_type=script_type,
            network=network
        )


    def run(self):
        if self.controller.unverified_address["script_type"] == SettingsConstants.LEGACY_P2PKH:
            # Legacy P2PKH addresses are always singlesig
            sig_type = SettingsConstants.SINGLE_SIG
            destination = Destination(SeedSelectSeedView, skip_current_view=True)

        if self.controller.unverified_address["script_type"] == SettingsConstants.NESTED_SEGWIT:
            # No way to differentiate single sig from multisig
            return Destination(AddressVerificationSigTypeView, skip_current_view=True)

        if self.controller.unverified_address["script_type"] == SettingsConstants.NATIVE_SEGWIT:
            if len(self.controller.unverified_address["address"]) >= 62:
                # Mainnet/testnet are 62, regtest is 64
                sig_type = SettingsConstants.MULTISIG
                if self.controller.multisig_wallet_descriptor:
                    # Can jump straight to the brute-force verification View
                    destination = Destination(SeedAddressVerificationView, skip_current_view=True)
                else:
                    self.controller.resume_main_flow = Controller.FLOW__VERIFY_MULTISIG_ADDR
                    destination = Destination(LoadMultisigWalletDescriptorView, skip_current_view=True)

            else:
                sig_type = SettingsConstants.SINGLE_SIG
                destination = Destination(SeedSelectSeedView, skip_current_view=True)

        elif self.controller.unverified_address["script_type"] == SettingsConstants.TAPROOT:
            # TODO: add Taproot support
            return Destination(NotYetImplementedView)

        derivation_path = embit_utils.get_standard_derivation_path(
            network=self.controller.unverified_address["network"],
            wallet_type=sig_type,
            script_type=self.controller.unverified_address["script_type"]
        )

        self.controller.unverified_address["sig_type"] = sig_type
        self.controller.unverified_address["derivation_path"] = derivation_path

        return destination



class AddressVerificationSigTypeView(View):
    SINGLE_SIG = "Single Sig"
    MULTISIG = "Multisig"

    def run(self):
        button_data = [self.SINGLE_SIG, self.MULTISIG]
        selected_menu_num = self.run_screen(
            seed_screens.AddressVerificationSigTypeScreen,
            title="Verify Address",
            text="Sig type can't be auto-detected from this address. Please specify:",
            button_data=button_data,
            is_bottom_list=True,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            self.controller.unverified_address = None
            return Destination(BackStackView)
        
        elif button_data[selected_menu_num] == self.SINGLE_SIG:
            sig_type = SettingsConstants.SINGLE_SIG
            destination = Destination(SeedSelectSeedView, view_args=dict(flow=Controller.FLOW__VERIFY_SINGLESIG_ADDR))

        elif button_data[selected_menu_num] == self.MULTISIG:
            sig_type = SettingsConstants.MULTISIG
            if self.controller.multisig_wallet_descriptor:
                destination = Destination(SeedAddressVerificationView)
            else:
                self.controller.resume_main_flow = Controller.FLOW__VERIFY_MULTISIG_ADDR
                destination = Destination(LoadMultisigWalletDescriptorView)

        self.controller.unverified_address["sig_type"] = sig_type
        derivation_path = embit_utils.get_standard_derivation_path(
            network=self.controller.unverified_address["network"],
            wallet_type=sig_type,
            script_type=self.controller.unverified_address["script_type"]
        )
        self.controller.unverified_address["derivation_path"] = derivation_path

        return destination



class SeedAddressVerificationView(View):
    """
        Creates a worker thread to brute-force calculate addresses. Writes its
        iteration status to a shared `ThreadsafeCounter`.

        The `ThreadsafeCounter` is sent to the display Screen which is monitored in
        its own `ProgressThread` to show the current iteration onscreen.

        Performs single sig verification on `seed_num` if specified, otherwise assumes
        multisig.
    """
    def __init__(self, seed_num: int = None):
        super().__init__()
        self.seed_num = seed_num
        self.is_multisig = self.controller.unverified_address["sig_type"] == SettingsConstants.MULTISIG
        self.seed_derivation_override = ""
        if not self.is_multisig:
            if seed_num is None:
                raise Exception("Can't validate a single sig addr without specifying a seed")
            self.seed_num = seed_num
            self.seed = self.controller.get_seed(seed_num)
            self.seed_derivation_override = self.seed.derivation_override(sig_type=SettingsConstants.SINGLE_SIG)
        else:
            self.seed = None
        self.address = self.controller.unverified_address["address"]
        self.derivation_path = self.seed_derivation_override if self.seed_derivation_override else self.controller.unverified_address["derivation_path"]
        self.script_type = self.controller.unverified_address["script_type"]
        self.sig_type = self.controller.unverified_address["sig_type"]
        self.network = self.controller.unverified_address["network"]

        if self.script_type == SettingsConstants.TAPROOT:
            # TODO: Taproot addr verification
            return Destination(NotYetImplementedView)

        # TODO: This should be in `Seed` or `PSBT` utility class
        embit_network = SettingsConstants.map_network_to_embit(self.network)

        # The ThreadsafeCounter will be shared by the brute-force thread to keep track of
        # its current addr index number and the Screen to display its progress and
        # respond to UI requests to jump the index ahead.
        self.threadsafe_counter = ThreadsafeCounter()

        # Shared coordination var so the display thread can detect success
        self.verified_index = ThreadsafeCounter(initial_value=None)
        self.verified_index_is_change = ThreadsafeCounter(initial_value=None)

        # Create the brute-force calculation thread that will run in the background
        self.addr_verification_thread = self.BruteForceAddressVerificationThread(
            address=self.address,
            seed=self.seed,
            descriptor=self.controller.multisig_wallet_descriptor,
            script_type=self.script_type,
            embit_network=embit_network,
            derivation_path=self.derivation_path,
            threadsafe_counter=self.threadsafe_counter,
            verified_index=self.verified_index,
            verified_index_is_change=self.verified_index_is_change,
        )


    def run(self):
        # Start brute-force calculations from the zero-th index
        self.addr_verification_thread.start()

        SKIP_10 = "Skip 10"
        CANCEL = "Cancel"
        button_data = [SKIP_10, CANCEL]

        script_type_settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__SCRIPT_TYPES)
        script_type_display = script_type_settings_entry.get_selection_option_display_name_by_value(self.script_type)

        sig_type_settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__SIG_TYPES)
        sig_type_display = sig_type_settings_entry.get_selection_option_display_name_by_value(self.sig_type)

        network_settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__NETWORK)
        network_display = network_settings_entry.get_selection_option_display_name_by_value(self.network)
        mainnet = network_settings_entry.get_selection_option_display_name_by_value(SettingsConstants.MAINNET)

        # Display the Screen to show the brute-forcing progress.
        # Using a loop here to handle the SKIP_10 button presses to increment the counter
        # and resume displaying the screen. User won't even notice that the Screen is
        # being re-constructed.
        while True:
            selected_menu_num = self.run_screen(
                seed_screens.SeedAddressVerificationScreen,
                address=self.address,
                derivation_path=self.derivation_path,
                script_type=script_type_display,
                sig_type=sig_type_display,
                network=network_display,
                is_mainnet=network_display == mainnet,
                threadsafe_counter=self.threadsafe_counter,
                verified_index=self.verified_index,
                button_data=button_data,
            )

            if self.verified_index.cur_count is not None:
                break

            if selected_menu_num == RET_CODE__BACK_BUTTON:
                break

            if selected_menu_num is None:
                # Only happens in the test suite; the screen isn't actually executed so
                # it returns before the brute force thread has completed.
                time.sleep(0.1)
                continue

            if button_data[selected_menu_num] == SKIP_10:
                self.threadsafe_counter.increment(10)

            elif button_data[selected_menu_num] == CANCEL:
                break

        if self.verified_index.cur_count is not None:
            # Successfully verified the addr; update the data
            self.controller.unverified_address["verified_index"] = self.verified_index.cur_count
            self.controller.unverified_address["verified_index_is_change"] = self.verified_index_is_change.cur_count == 1
            return Destination(AddressVerificationSuccessView, view_args=dict(seed_num=self.seed_num))

        else:
            # Halt the thread if the user gave up (will already be stopped if it verified the
            # target addr).
            self.addr_verification_thread.stop()
            while self.addr_verification_thread.is_alive():
                time.sleep(0.01)

        return Destination(MainMenuView)



    class BruteForceAddressVerificationThread(BaseThread):
        def __init__(self, address: str, seed: Seed, descriptor: Descriptor, script_type: str, embit_network: str, derivation_path: str, threadsafe_counter: ThreadsafeCounter, verified_index: ThreadsafeCounter, verified_index_is_change: ThreadsafeCounter):
            """
                Either seed or descriptor will be None
            """
            super().__init__()
            self.address = address
            self.seed = seed
            self.descriptor = descriptor
            self.script_type = script_type
            self.embit_network = embit_network
            self.derivation_path = derivation_path
            self.threadsafe_counter = threadsafe_counter
            self.verified_index = verified_index
            self.verified_index_is_change = verified_index_is_change

            if self.seed:
                self.xpub = self.seed.get_xpub(wallet_path=self.derivation_path, network=Settings.get_instance().get_value(SettingsConstants.SETTING__NETWORK))
 

        def run(self):
            while self.keep_running:
                if self.threadsafe_counter.cur_count % 10 == 0:
                    logger.info(f"Incremented to {self.threadsafe_counter.cur_count}")
                
                i = self.threadsafe_counter.cur_count

                if self.descriptor:
                    receive_address = embit_utils.get_multisig_address(descriptor=self.descriptor, index=i, is_change=False, embit_network=self.embit_network)
                    change_address = embit_utils.get_multisig_address(descriptor=self.descriptor, index=i, is_change=True, embit_network=self.embit_network)

                else:
                    receive_address = embit_utils.get_single_sig_address(xpub=self.xpub, script_type=self.script_type, index=i, is_change=False, embit_network=self.embit_network)
                    change_address = embit_utils.get_single_sig_address(xpub=self.xpub, script_type=self.script_type, index=i, is_change=True, embit_network=self.embit_network)
                    
                if self.address == receive_address:
                    self.verified_index.set_value(i)
                    self.verified_index_is_change.set_value(0)
                    self.keep_running = False
                    break

                elif self.address == change_address:
                    self.verified_index.set_value(i)
                    self.verified_index_is_change.set_value(1)
                    self.keep_running = False
                    break

                # Increment our index counter
                self.threadsafe_counter.increment()
        


class AddressVerificationSuccessView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is not None:
            self.seed = self.controller.get_seed(seed_num)
    

    def run(self):
        address = self.controller.unverified_address["address"]
        sig_type = self.controller.unverified_address["sig_type"]
        verified_index = self.controller.unverified_address["verified_index"]
        verified_index_is_change = self.controller.unverified_address["verified_index_is_change"]

        if sig_type == SettingsConstants.MULTISIG:
            source = "multisig"
        else:
            source = f"seed {self.seed.get_fingerprint()}"

        LargeIconStatusScreen(
            status_headline="Address Verified",
            text=f"""{address[:7]} = {source}'s {"change" if verified_index_is_change else "receive"} address #{verified_index}.""",
            show_back_button=False,
        ).display()

        return Destination(MainMenuView)



class LoadMultisigWalletDescriptorView(View):
    SCAN = ("Scan Descriptor", SeedSignerIconConstants.QRCODE)
    CANCEL = "Cancel"

    def run(self):
        button_data = [
            self.SCAN,
            self.CANCEL
        ]
        selected_menu_num = self.run_screen(
            seed_screens.LoadMultisigWalletDescriptorScreen,
            button_data=button_data,
            show_back_button=False,
        )

        if button_data[selected_menu_num] == self.SCAN:
            from seedsigner.views.scan_views import ScanWalletDescriptorView
            return Destination(ScanWalletDescriptorView)

        elif button_data[selected_menu_num] == self.CANCEL:
            if self.controller.resume_main_flow == Controller.FLOW__PSBT:
                return Destination(BackStackView)
            else:
                return Destination(MainMenuView)



class MultisigWalletDescriptorView(View):
    RETURN = "Return to PSBT"
    VERIFY_ADDR = "Verify Addr"
    ADDRESS_EXPLORER = "Address Explorer"
    OK = "OK"

    def run(self):
        descriptor = self.controller.multisig_wallet_descriptor

        fingerprints = []
        for key in descriptor.keys:
            fingerprint = hexlify(key.fingerprint).decode()
            fingerprints.append(fingerprint)
        
        policy = descriptor.brief_policy.split("multisig")[0].strip()

        button_data = [self.OK]
        if self.controller.resume_main_flow:
            if self.controller.resume_main_flow == Controller.FLOW__PSBT:
                button_data = [self.RETURN]
            elif self.controller.resume_main_flow == Controller.FLOW__VERIFY_MULTISIG_ADDR and self.controller.unverified_address:
                verify_addr_display = f"""{self.VERIFY_ADDR} {self.controller.unverified_address["address"][:7]}"""
                button_data = [verify_addr_display]
            elif self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER:
                button_data = [self.ADDRESS_EXPLORER]

        selected_menu_num = self.run_screen(
            seed_screens.MultisigWalletDescriptorScreen,
            policy=policy,
            fingerprints=fingerprints,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            self.controller.multisig_wallet_descriptor = None
            return Destination(BackStackView)
        
        elif button_data[selected_menu_num] == self.RETURN:
            # Jump straight back to PSBT change verification
            from seedsigner.views.psbt_views import PSBTChangeDetailsView
            self.controller.resume_main_flow = None
            return Destination(PSBTChangeDetailsView, view_args=dict(change_address_num=0))

        elif button_data[selected_menu_num].startswith(self.VERIFY_ADDR):
            self.controller.resume_main_flow = None
            return Destination(SeedAddressVerificationView)

        elif button_data[selected_menu_num] == self.ADDRESS_EXPLORER:
            from seedsigner.views.tools_views import ToolsAddressExplorerAddressTypeView
            self.controller.resume_main_flow = None
            return Destination(ToolsAddressExplorerAddressTypeView)

        return Destination(MainMenuView)



"""****************************************************************************
    Sign Message Views
****************************************************************************"""
class SeedSignMessageStartView(View):
    """
    Routes users straight through to the "Sign" screen if a signing `seed_num` has
    already been selected. Otherwise routes to `SeedSelectSeedView` to select or
    load a seed first.
    """
    def __init__(self, derivation_path: str, message: str):
        super().__init__()
        self.derivation_path = derivation_path
        self.message = message

        if self.settings.get_value(SettingsConstants.SETTING__MESSAGE_SIGNING) == SettingsConstants.OPTION__DISABLED:
            self.set_redirect(Destination(OptionDisabledView, view_args=dict(settings_attr=SettingsConstants.SETTING__MESSAGE_SIGNING)))
            return

        # calculate the actual receive address
        addr_format = embit_utils.parse_derivation_path(derivation_path)
        if not addr_format["clean_match"]:
            self.set_redirect(Destination(NotYetImplementedView, view_args=dict(text="Signing messages for custom derivation paths not supported")))
            self.controller.resume_main_flow = None
            return

        # Note: addr_format["network"] can be MAINNET or [TESTNET, REGTEST]
        if self.settings.get_value(SettingsConstants.SETTING__NETWORK) not in addr_format["network"]:
            from seedsigner.views.view import NetworkMismatchErrorView
            self.set_redirect(Destination(NetworkMismatchErrorView, view_args=dict(text=f"Current network setting ({self.settings.get_value_display_name(SettingsConstants.SETTING__NETWORK)}) doesn't match {self.derivation_path}")))

            # cleanup. Note: We could leave this in place so the user can resume the
            # flow, but for now we avoid complications and keep things simple.
            self.controller.resume_main_flow = None
            return

        data = self.controller.sign_message_data
        if not data:
            data = {}
            self.controller.sign_message_data = data
        data["derivation_path"] = derivation_path
        data["message"] = message
        data["addr_format"] = addr_format

        # May be None
        self.seed_num = data.get("seed_num")
    
        if self.seed_num is not None:
            # We already know which seed we're signing with
            self.set_redirect(Destination(SeedSignMessageConfirmMessageView, skip_current_view=True))
        else:
            self.set_redirect(Destination(SeedSelectSeedView, view_args=dict(flow=Controller.FLOW__SIGN_MESSAGE), skip_current_view=True))



class SeedSignMessageConfirmMessageView(View):
    def __init__(self, page_num: int = 0):
        super().__init__()
        self.page_num = page_num  # Note: zero-indexed numbering!

        self.seed_num = self.controller.sign_message_data.get("seed_num")
        if self.seed_num is None:
            raise Exception("Routing error: seed_num hasn't been set")


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedSignMessageConfirmMessageScreen

        selected_menu_num = self.run_screen(
            SeedSignMessageConfirmMessageScreen,
            page_num=self.page_num,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            if self.page_num == 0:
                # We're exiting this flow entirely
                self.controller.resume_main_flow = None
                self.controller.sign_message_data = None
            return Destination(BackStackView)

        # User clicked "Next"
        if self.page_num == len(self.controller.sign_message_data["paged_message"]) - 1:
            # We've reached the end of the paged message
            return Destination(SeedSignMessageConfirmAddressView)
        else:
            return Destination(SeedSignMessageConfirmMessageView, view_args=dict(page_num=self.page_num + 1))



class SeedSignMessageConfirmAddressView(View):
    def __init__(self):
        super().__init__()
        data = self.controller.sign_message_data
        seed_num = data.get("seed_num")
        self.derivation_path = data.get("derivation_path")

        if seed_num is None or not self.derivation_path:
            raise Exception("Routing error: sign_message_data hasn't been set")

        seed = self.controller.storage.seeds[seed_num]
        addr_format = data.get("addr_format")

        # calculate the actual receive address
        seed = self.controller.storage.seeds[seed_num]
        addr_format = embit_utils.parse_derivation_path(self.derivation_path)
        if not addr_format["clean_match"] or addr_format["script_type"] == SettingsConstants.CUSTOM_DERIVATION:
            raise Exception("Signing messages for custom derivation paths not supported")

        if addr_format["network"] != SettingsConstants.MAINNET:
            # We're in either Testnet or Regtest or...?
            if self.settings.get_value(SettingsConstants.SETTING__NETWORK) in [SettingsConstants.TESTNET, SettingsConstants.REGTEST]:
                addr_format["network"] = self.settings.get_value(SettingsConstants.SETTING__NETWORK)
            else:
                from seedsigner.views.view import NetworkMismatchErrorView
                self.set_redirect(Destination(NetworkMismatchErrorView, view_args=dict(text=f"Current network setting ({self.settings.get_value_display_name(SettingsConstants.SETTING__NETWORK)}) doesn't match {self.derivation_path}")))

                # cleanup. Note: We could leave this in place so the user can resume the
                # flow, but for now we avoid complications and keep things simple.
                self.controller.resume_main_flow = None
                self.controller.sign_message_data = None
                return

        xpub = seed.get_xpub(wallet_path=addr_format["wallet_derivation_path"], network=addr_format["network"])
        embit_network = embit_utils.get_embit_network_name(addr_format["network"])
        self.address = embit_utils.get_single_sig_address(xpub=xpub, script_type=addr_format["script_type"], index=addr_format["index"], is_change=addr_format["is_change"], embit_network=embit_network)


    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedSignMessageConfirmAddressScreen
        selected_menu_num = self.run_screen(
            SeedSignMessageConfirmAddressScreen,
            derivation_path=self.derivation_path,
            address=self.address,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # User clicked "Sign Message"
        return Destination(SeedSignMessageSignedMessageQRView)



class SeedSignMessageSignedMessageQRView(View):
    """
    Displays the signed message as a QR code.
    """
    def __init__(self):
        super().__init__()
        data = self.controller.sign_message_data

        self.seed_num = data["seed_num"]
        seed = self.controller.get_seed(self.seed_num)
        derivation_path = data["derivation_path"]
        message: str = data["message"]

        self.signed_message = embit_utils.sign_message(seed_bytes=seed.seed_bytes, derivation=derivation_path, msg=message.encode())


    def run(self):
        qr_encoder = GenericStaticQrEncoder(data=self.signed_message)
        
        self.run_screen(
            QRDisplayScreen,
            qr_encoder=qr_encoder,
        )
    
        # cleanup
        self.controller.resume_main_flow = None
        self.controller.sign_message_data = None

        # Exiting/Canceling the QR display screen always returns Home
        return Destination(MainMenuView, skip_current_view=True)
