from typing import List
import embit
import time
from binascii import hexlify
from embit.networks import NETWORKS
from seedsigner.models.decode_qr import DecodeQR

from seedsigner.models.settings_definition import SettingsDefinition

from .view import NotYetImplementedView, View, Destination, BackStackView, MainMenuView

from seedsigner.gui.components import FontAwesomeIconConstants, SeedSignerCustomIconConstants
from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen,
    LargeButtonScreen, WarningScreen, DireWarningScreen, seed_screens)
from seedsigner.gui.screens.screen import LargeIconStatusScreen, LoadingScreenThread, QRDisplayScreen
from seedsigner.models.threads import BaseThread, ThreadsafeCounter
from seedsigner.models.encode_qr import EncodeQR
from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import InvalidSeedException, Seed
from seedsigner.models.settings import SettingsConstants



class SeedsMenuView(View):
    def __init__(self):
        super().__init__()
        self.seeds = []
        for seed in self.controller.storage.seeds:
            self.seeds.append({
                "fingerprint": seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK)),
                "has_passphrase": seed.passphrase is not None
            })


    def run(self):
        if not self.seeds:
            # Nothing to do here unless we have a seed loaded
            return Destination(LoadSeedView, clear_history=True)

        button_data = []
        for seed in self.seeds:
            button_data.append((seed["fingerprint"], SeedSignerCustomIconConstants.FINGERPRINT, "blue"))
        button_data.append("Load a seed")

        selected_menu_num = ButtonListScreen(
            title="In-Memory Seeds",
            is_button_text_centered=False,
            button_data=button_data
        ).display()

        if len(self.seeds) > 0 and selected_menu_num < len(self.seeds):
            return Destination(SeedOptionsView, view_args={"seed_num": selected_menu_num})

        elif selected_menu_num == len(self.seeds):
            return Destination(LoadSeedView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



"""****************************************************************************
    Loading seeds, passphrases, etc
****************************************************************************"""
class LoadSeedView(View):
    def run(self):
        SEED_QR = (" Scan a SeedQR", FontAwesomeIconConstants.QRCODE)
        TYPE_24WORD = ("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)
        TYPE_12WORD = ("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
        CREATE = (" Create a seed", FontAwesomeIconConstants.PLUS)
        button_data=[
            SEED_QR,
            TYPE_24WORD,
            TYPE_12WORD,
            CREATE,
        ]

        selected_menu_num = ButtonListScreen(
            title="Load A Seed",
            is_button_text_centered=False,
            button_data=button_data
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        if button_data[selected_menu_num] == SEED_QR:
            from .scan_views import ScanView
            return Destination(ScanView)
        
        elif button_data[selected_menu_num] == TYPE_24WORD:
            self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == TYPE_12WORD:
            self.controller.storage.init_pending_mnemonic(num_words=12)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == CREATE:
            from .tools_views import ToolsMenuView
            return Destination(ToolsMenuView)



class SeedMnemonicEntryView(View):
    def __init__(self, cur_word_index: int = 0, is_calc_final_word: bool=False):
        super().__init__()
        self.cur_word_index = cur_word_index
        self.cur_word = self.controller.storage.get_pending_mnemonic_word(cur_word_index)
        self.is_calc_final_word = is_calc_final_word


    def run(self):
        ret = seed_screens.SeedMnemonicEntryScreen(
            title=f"Seed Word #{self.cur_word_index + 1}",  # Human-readable 1-indexing!
            initial_letters=list(self.cur_word) if self.cur_word else ["a"],
            wordlist=Seed.get_wordlist(wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)),
        ).display()

        if ret == RET_CODE__BACK_BUTTON:
            if self.cur_word_index > 0:
                return Destination(
                    SeedMnemonicEntryView,
                    view_args={
                        "cur_word_index": self.cur_word_index - 1,
                        "is_calc_final_word": self.is_calc_final_word
                    }
                )
            else:
                self.controller.storage.discard_pending_mnemonic()
                return Destination(MainMenuView)
        
        # ret will be our new mnemonic word
        self.controller.storage.update_pending_mnemonic(ret, self.cur_word_index)

        if self.is_calc_final_word and self.cur_word_index == self.controller.storage.pending_mnemonic_length - 2:
            # Time to calculate the last word
            # TODO: Option to add missing entropy for the last word:
            #   * 3 bits for a 24-word seed
            #   * 7 bits for a 12-word seed
            from seedsigner.helpers import mnemonic_generation
            from seedsigner.views.tools_views import ToolsCalcFinalWordShowFinalWordView
            full_mnemonic = mnemonic_generation.calculate_checksum(
                self.controller.storage.pending_mnemonic[:-1],  # Must omit the last word's empty value
                wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
            )
            self.controller.storage.update_pending_mnemonic(full_mnemonic[-1], self.cur_word_index+1)
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
    def __init__(self):
        super().__init__()
        self.mnemonic: List[str] = self.controller.storage.pending_mnemonic


    def run(self):
        EDIT = "Review & Edit"
        DISCARD = ("Discard", None, None, "red")
        button_data = [EDIT, DISCARD]

        selected_menu_num = WarningScreen(
            title="Invalid Mnemonic!",
            status_headline=None,
            text=f"Checksum failure; not a valid seed phrase.",
            show_back_button=False,
            button_data=button_data,
        ).display()

        if button_data[selected_menu_num] == EDIT:
            return Destination(SeedMnemonicEntryView, view_args={"cur_word_index": 0})

        elif button_data[selected_menu_num] == DISCARD:
            self.controller.storage.discard_pending_mnemonic()
            return Destination(MainMenuView)



class SeedFinalizeView(View):
    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()
        self.fingerprint = self.seed.get_fingerprint(network=self.settings.get_value(SettingsConstants.SETTING__NETWORK))


    def run(self):
        FINALIZE = "Done"
        PASSPHRASE = ("Add Passphrase", FontAwesomeIconConstants.LOCK)
        button_data = []

        button_data.append(FINALIZE)

        if self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE) != SettingsConstants.OPTION__DISABLED:
            button_data.append(PASSPHRASE)

        selected_menu_num = seed_screens.SeedFinalizeScreen(
            fingerprint=self.fingerprint,
            button_data=button_data,
        ).display()

        if button_data[selected_menu_num] == FINALIZE:
            seed_num = self.controller.storage.finalize_pending_seed()
            return Destination(SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True)

        elif button_data[selected_menu_num] == PASSPHRASE:
            return Destination(SeedAddPassphraseView)



class SeedAddPassphraseView(View):
    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()


    def run(self):
        ret = seed_screens.SeedAddPassphraseScreen(passphrase=self.seed.passphrase).display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        # The new passphrase will be the return value
        self.seed.set_passphrase(ret)
        return Destination(SeedReviewPassphraseView)



class SeedReviewPassphraseView(View):
    """
        Display the completed passphrase back to the user.
    """
    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()
        print(f"SeedReviewPassphraseView self.seed: {self.seed}")


    def run(self):
        EDIT = "Edit passphrase"
        DONE = "Done"
        button_data = [EDIT, DONE]

        # Get the before/after fingerprints
        network = self.settings.get_value(SettingsConstants.SETTING__NETWORK)
        passphrase = self.seed.passphrase
        fingerprint_with = self.seed.get_fingerprint(network=network)
        self.seed.set_passphrase("")
        fingerprint_without = self.seed.get_fingerprint(network=network)
        self.seed.set_passphrase(passphrase)
        
        # Because we have ane explicit "Edit" button, we disable "BACK" to keep the
        # routing options sane.
        selected_menu_num = seed_screens.SeedReviewPassphraseScreen(
            fingerprint_without=fingerprint_without,
            fingerprint_with=fingerprint_with,
            passphrase=self.seed.passphrase,
            button_data=button_data,
            show_back_button=False,
        ).display()

        if button_data[selected_menu_num] == EDIT:
            return Destination(SeedAddPassphraseView)
        
        elif button_data[selected_menu_num] == DONE:
            seed_num = self.controller.storage.finalize_pending_seed()
            return Destination(SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True)
            
            
            
class SeedDiscardView(View):
    def __init__(self, seed_num: int = None):
        super().__init__()
        self.seed_num = seed_num
        print(f"self.seed_num: {self.seed_num}")
        if self.seed_num is not None:
            self.seed = self.controller.get_seed(self.seed_num)
        else:
            self.seed = self.controller.storage.pending_seed


    def run(self):
        KEEP = "Keep Seed"
        DISCARD = ("Discard", None, None, "red")
        button_data = [KEEP, DISCARD]

        fingerprint = self.seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK))
        selected_menu_num = WarningScreen(
            title="Discard Seed?",
            status_headline=None,
            text=f"Wipe seed {fingerprint} from the device?",
            show_back_button=False,
            button_data=button_data,
        ).display()

        print(f"selected_menu_num: {selected_menu_num}")

        if button_data[selected_menu_num] == KEEP:
            if self.seed_num is not None:
                return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num})
            else:
                return Destination(SeedFinalizeView)

        elif button_data[selected_menu_num] == DISCARD:
            if self.seed_num is not None:
                self.controller.discard_seed(self.seed_num)
            else:
                self.controller.storage.clear_pending_seed()
            return Destination(MainMenuView)



"""****************************************************************************
    Views for actions on individual seeds:
****************************************************************************"""
class SeedOptionsView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)


    def run(self):
        SCAN_PSBT = ("Scan PSBT", FontAwesomeIconConstants.QRCODE)
        REVIEW_PSBT = "Review PSBT"
        EXPORT_XPUB = "Export Xpub"
        VIEW_WORDS = "View Seed Words"
        EXPORT_SEEDQR = "Export Seed as QR"
        DISCARD = ("Discard Seed", None, None, "red")

        button_data = []

        if self.controller.psbt:
            if not PSBTParser.has_matching_input_fingerprint(self.controller.psbt, self.seed, network=self.settings.get_value(SettingsConstants.SETTING__NETWORK)):
                # This seed does not seem to be a signer for this PSBT
                # TODO: How sure are we? Should disable this entirely if we're 100% sure?
                REVIEW_PSBT += " (?)"
            button_data.append(REVIEW_PSBT)
        else:
            button_data.append(SCAN_PSBT)
        
        if self.settings.get_value(SettingsConstants.SETTING__XPUB_EXPORT) == SettingsConstants.OPTION__ENABLED:
            button_data.append(EXPORT_XPUB)
        
        button_data.append(VIEW_WORDS)
        button_data.append(EXPORT_SEEDQR)
        button_data.append(DISCARD)

        selected_menu_num = seed_screens.SeedOptionsScreen(
            button_data=button_data,
            fingerprint=self.seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK)),
            has_passphrase=self.seed.passphrase is not None
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == REVIEW_PSBT:
            from seedsigner.views.psbt_views import PSBTOverviewView
            self.controller.psbt_seed = self.controller.get_seed(self.seed_num)
            return Destination(PSBTOverviewView)

        if button_data[selected_menu_num] == SCAN_PSBT:
            from seedsigner.views.scan_views import ScanView
            return Destination(ScanView)

        elif button_data[selected_menu_num] == VIEW_WORDS:
            return Destination(SeedWordsWarningView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == EXPORT_XPUB:
            return Destination(SeedExportXpubSigTypeView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == EXPORT_SEEDQR:
            return Destination(SeedTranscribeSeedQRFormatView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == DISCARD:
            return Destination(SeedDiscardView, view_args={"seed_num": self.seed_num})



"""****************************************************************************
    Export Xpub flow
****************************************************************************"""
class SeedExportXpubSigTypeView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        if len(self.settings.get_value(SettingsConstants.SETTING__SIG_TYPES)) == 1:
            # Nothing to select; skip this screen
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": self.settings.get_value(SettingsConstants.SETTING__SIG_TYPES)[0]}, skip_current_view=True)

        SINGLE_SIG = "Single Sig"
        MULTISIG = "Multisig"
        button_data=[SINGLE_SIG, MULTISIG]

        selected_menu_num = ButtonListScreen(
            title="Export Xpub",
            button_data=button_data
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == SINGLE_SIG:
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": SettingsConstants.SINGLE_SIG})

        elif button_data[selected_menu_num] == MULTISIG:
            return Destination(SeedExportXpubScriptTypeView, view_args={"seed_num": self.seed_num, "sig_type": SettingsConstants.MULTISIG})



class SeedExportXpubScriptTypeView(View):
    def __init__(self, seed_num: int, sig_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type


    def run(self):
        args = {"seed_num": self.seed_num, "sig_type": self.sig_type}
        if len(self.settings.get_value(SettingsConstants.SETTING__SCRIPT_TYPES)) == 1:
            # Nothing to select; skip this screen
            args["script_type"] = self.settings.get_value(SettingsConstants.SETTING__SCRIPT_TYPES)[0]
            return Destination(SeedExportXpubCoordinatorView, view_args=args, skip_current_view=True)

        button_data = []
        for script_type in self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__SCRIPT_TYPES):
            button_data.append(script_type)
        selected_menu_num = ButtonListScreen(
            title="Export Xpub",
            is_button_text_centered=False,
            button_data=button_data,
        ).display()

        if selected_menu_num < len(SettingsConstants.ALL_SCRIPT_TYPES):
            script_types_settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__SCRIPT_TYPES)
            selected_display_name = button_data[selected_menu_num]
            args["script_type"] = script_types_settings_entry.get_selection_option_value_by_display_name(selected_display_name)

            if button_data[selected_menu_num] == SettingsConstants.CUSTOM_DERIVATION:
                return Destination(SeedExportXpubCustomDerivationView, view_args=args)

            return Destination(SeedExportXpubCoordinatorView, view_args=args)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubCustomDerivationView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.custom_derivation_path = self.settings.custom_derivation

    def run(self):
        ret = seed_screens.SeedExportXpubCustomDerivationScreen(
            derivation_path=self.custom_derivation_path
        ).display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        # ret should be the custom derivation path; store it in Settings
        self.settings.custom_derivation = ret

        return Destination(
            SeedExportXpubCoordinatorView,
            view_args={
                "seed_num": self.seed_num,
                "sig_type": self.sig_type,
                "script_type": self.script_type,
            }
        )



class SeedExportXpubCoordinatorView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type


    def run(self):
        args = {
            "seed_num": self.seed_num,
            "sig_type": self.sig_type,
            "script_type": self.script_type,
        }
        if len(self.settings.get_value(SettingsConstants.SETTING__COORDINATORS)) == 1:
            # Nothing to select; skip this screen
            args["coordinator"] = self.settings.get_value(SettingsConstants.SETTING__COORDINATORS)[0]
            return Destination(SeedExportXpubWarningView, view_args=args, skip_current_view=True)

        selected_menu_num = ButtonListScreen(
            title="Export Xpub",
            is_button_text_centered=False,
            button_data=self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__COORDINATORS),
        ).display()

        if selected_menu_num < len(self.settings.get_value(SettingsConstants.SETTING__COORDINATORS)):
            args["coordinator"] = self.settings.get_value(SettingsConstants.SETTING__COORDINATORS)[selected_menu_num]
            return Destination(SeedExportXpubWarningView, view_args=args)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubWarningView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str):
        super().__init__()
        self.seed_num = seed_num
        self.sig_type = sig_type
        self.script_type = script_type
        self.coordinator = coordinator


    def run(self):
        destination = Destination(
            SeedExportXpubDetailsView,
            view_args={
                "seed_num": self.seed_num,
                "sig_type": self.sig_type,
                "script_type": self.script_type,
                "coordinator": self.coordinator,
            }
        )

        if self.settings.get_value(SettingsConstants.SETTING__PRIVACY_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            destination.skip_current_view = True
            return destination

        selected_menu_num = WarningScreen(
            status_headline="Privacy Leak!",
            text="""Xpub can be used to view all future transactions.""",
        ).display()

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
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str):
        super().__init__()
        self.sig_type = sig_type
        self.script_type = script_type
        self.coordinator = coordinator
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)


    def run(self):
        # The calc_derivation takes a few moments. Run the loading screen while we wait.
        self.loading_screen = LoadingScreenThread(text="Generating xpub...")
        self.loading_screen.start()

        if self.script_type == SettingsConstants.CUSTOM_DERIVATION:
            derivation_path = self.settings.custom_derivation
        else:
            derivation_path = PSBTParser.calc_derivation(
                network=self.settings.get_value(SettingsConstants.SETTING__NETWORK),
                wallet_type=self.sig_type,
                script_type=self.script_type
            )

        if self.settings.get_value(SettingsConstants.SETTING__XPUB_DETAILS) == SettingsConstants.OPTION__ENABLED:
            embit_network = NETWORKS[SettingsConstants.map_network_to_embit(self.settings.get_value(SettingsConstants.SETTING__NETWORK))]
            version = embit.bip32.detect_version(
                derivation_path,
                default="xpub",
                network=embit_network
            )

            root = embit.bip32.HDKey.from_seed(
                self.seed.seed_bytes,
                version=embit_network["xprv"]
            )

            fingerprint = hexlify(root.child(0).fingerprint).decode('utf-8')
            xprv = root.derive(derivation_path)
            xpub = xprv.to_public()
            xpub_base58 = xpub.to_string(version=version)

            screen = seed_screens.SeedExportXpubDetailsScreen(
                fingerprint=fingerprint,
                has_passphrase=self.seed.passphrase is not None,
                derivation_path=derivation_path,
                xpub=xpub_base58,
            )

            self.loading_screen.stop()

            selected_menu_num = screen.display()
        else:
            self.loading_screen.stop()
            selected_menu_num = 0

        if selected_menu_num == 0:
            return Destination(
                SeedExportXpubQRDisplayView,
                {
                    "seed_num": self.seed_num,
                    "sig_type": self.sig_type,
                    "script_type": self.script_type,
                    "coordinator": self.coordinator,
                    "derivation_path": derivation_path,
                }
            )

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedExportXpubQRDisplayView(View):
    def __init__(self, seed_num: int, sig_type: str, script_type: str, coordinator: str, derivation_path: str):
        super().__init__()
        self.seed = self.controller.get_seed(seed_num)

        qr_density = self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY)
        if coordinator == SettingsConstants.COORDINATOR__SPECTER_DESKTOP:
            qr_type = QRType.XPUB__SPECTER

        elif coordinator == SettingsConstants.COORDINATOR__BLUE_WALLET:
            qr_type = QRType.XPUB

        elif coordinator == SettingsConstants.COORDINATOR__NUNCHUK:
            qr_type = QRType.XPUB__UR

            # As of 2022-03-02 Nunchuk doesn't seem to support animated QRs for Xpub import
            qr_density = SettingsConstants.DENSITY__HIGH

        else:
            qr_type = QRType.XPUB__UR

        self.qr_encoder = EncodeQR(
            seed_phrase=self.seed.mnemonic_list,
            passphrase=self.seed.passphrase,
            derivation=derivation_path,
            network=self.settings.get_value(SettingsConstants.SETTING__NETWORK),
            qr_type=qr_type,
            qr_density=qr_density,
            wordlist_language_code=self.seed.wordlist_language_code
        )


    def run(self):
        QRDisplayScreen(qr_encoder=self.qr_encoder).display()

        return Destination(MainMenuView)



"""****************************************************************************
    View Seed Words flow
****************************************************************************"""
class SeedWordsWarningView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        destination = Destination(SeedWordsView, view_args={"seed_num": self.seed_num, "page_index": 0})
        if self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            # Forward straight to showing the words
            destination.skip_current_view = True
            return destination

        selected_menu_num = DireWarningScreen(
            text="""You must keep your seed words private & away from all online devices.""",
        ).display()

        if selected_menu_num == 0:
            # User clicked "I Understand"
            return destination

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedWordsView(View):
    def __init__(self, seed_num: int, page_index: int = 0):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is None:
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.seed = self.controller.get_seed(self.seed_num)
        self.page_index = page_index
        self.num_pages=int(len(self.seed.mnemonic_list)/4)


    def run(self):
        NEXT = "Next"
        DONE = "Done"

        button_data = []
        if self.page_index < self.num_pages - 1 or self.seed_num is None:
            button_data.append(NEXT)
        else:
            button_data.append(DONE)

        selected_menu_num = seed_screens.SeedWordsScreen(
            seed=self.seed,
            page_index=self.page_index,
            num_pages=self.num_pages,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == NEXT:
            if self.seed_num is None and self.page_index == self.num_pages - 1:
                return Destination(SeedFinalizeView)
            else:
                return Destination(SeedWordsView, view_args={"seed_num": self.seed_num, "page_index": self.page_index + 1})

        elif button_data[selected_menu_num] == DONE:
            # Must clear history to avoid BACK button returning to private info
            return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num}, clear_history=True)



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
            }
        )

        if self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            # Forward straight to transcribing the SeedQR
            destination.skip_current_view = True
            return destination

        selected_menu_num = DireWarningScreen(
            status_headline="SeedQR is your private key!",
            text="""Never photograph it or scan it into an online device.""",
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
        e = EncodeQR(
            seed_phrase=self.seed.mnemonic_list,
            qr_type=self.seedqr_format,
            wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        )
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
        e = EncodeQR(
            seed_phrase=self.seed.mnemonic_list,
            qr_type=self.seedqr_format,
            wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        )
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
        SCAN = ("Confirm SeedQR", FontAwesomeIconConstants.QRCODE)
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


class SeedSingleSigAddressVerificationView(View):
    """
        TODO: Reserved for Nick.
        
        This was previously part of the PSBT flow but was moved here when we
        figured out how to avoid having to brute force the change addr verification.

        But instead this code can be altered to be used to brute force single sig
        address validation as its own separate flow.

        Creates a worker thread to brute force calculate addresses. Writes its
        iteration status to a shared `ThreadsafeCounter`.

        The `ThreadsafeCounter` is sent to the display Screen which is monitored in
        its own `ProgressThread` to show the current iteration onscreen.
    """
    def __init__(self, seed_num: int, address: str):
        super().__init__()
        self.seed = self.controller.get_seed(seed_num)
        self.address = address
    

    def run(self):
        threadsafe_counter = ThreadsafeCounter()

        addr_verification_thread = SeedSingleSigAddressVerificationView.SingleSigAddressVerificationThread(
            address=self.address,
            seed=self.seed,
            threadsafe_counter=threadsafe_counter
        )
        addr_verification_thread.start()

        selected_menu_num = seed_screens.SingleSigAddressVerificationScreen(
            address=self.address,
            threadsafe_counter=threadsafe_counter,
        ).display()

        addr_verification_thread.stop()


        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)


    class SingleSigAddressVerificationThread(BaseThread):
        def __init__(self, address: str, seed: Seed, threadsafe_counter: ThreadsafeCounter):
            super().__init__()
            self.address = address
            self.threadsafe_counter = threadsafe_counter
            self.verified_index: int = 0
            self.verified_index_is_change: bool = None


        def run(self):
            while self.keep_running:
                # Do work to verify addr
                # TODO: Reserved for Nick

                # For now mocking that up with time consuming... sleep
                time.sleep(0.25)

                # Increment our index counter
                self.threadsafe_counter.increment()

                if self.threadsafe_counter.cur_count % 10 == 0:
                    print(f"Incremented to {self.threadsafe_counter.cur_count}")

                # On successfully verifying addr, set:
                # self.verified_index = self.counter.cur_count
                # self.verified_index_is_change = True
                # break   # Will instance stick around if run() exits?

                # TODO: This should be in `Seed` or `PSBT` utility class
                # def verify_single_sig_addr(self, address:str):
                #     import embit
                #     network = embit.NETWORKS[self.settings.get_value(SettingsConstants.SETTING__NETWORK)]
                #     version = embit.bip32.detect_version(derivation, default="xpub", network=network)
                #     root = embit.bip32.HDKey.from_seed(seed.seed, version=network["xprv"])
                #     fingerprint = hexlify(root.child(0).fingerprint).decode('utf-8')
                #     xprv = root.derive(derivation)
                #     xpub = xprv.to_public()
                #     for i in range(500):
                #         r_pubkey = xpub.derive([0,i]).key
                #         c_pubkey = xpub.derive([1,i]).key
                        
                #         recieve_address = ""
                #         change_address = ""
                        
                #         if "P2PKH" in address_type:
                #             recieve_address = embit.script.p2pkh(r_pubkey).address(network=network)
                #             change_address = embit.script.p2pkh(c_pubkey).address(network=network)
                #         elif "Bech32" in address_type:
                #             recieve_address = embit.script.p2wpkh(r_pubkey).address(network=network)
                #             change_address = embit.script.p2wpkh(c_pubkey).address(network=network)
                #         elif "P2SH" in address_type:
                #             recieve_address = embit.script.p2sh(embit.script.p2wpkh(r_pubkey)).address(network=network)
                #             change_address = embit.script.p2sh(embit.script.p2wpkh(c_pubkey)).address(network=network)
                            
                #         if address == recieve_address:
                #             self.menu_view.draw_modal(["Receive Address "+str(i), "Verified"], "", "Right to Exit")
                #             input = self.buttons.wait_for([B.KEY_RIGHT])
                #             return Path.MAIN_MENU
                #         if address == change_address:
                #             self.menu_view.draw_modal(["Change Address "+str(i), "Verified"], "", "Right to Exit")
                #             input = self.buttons.wait_for([B.KEY_RIGHT])
                #             return Path.MAIN_MENU
                #         else:
                #             self.menu_view.draw_modal(["Checking Address "+str(i), "..."], "", "Right to Abort")
                #             if self.buttons.check_for_low(B.KEY_RIGHT) or self.buttons.check_for_low(B.KEY_LEFT):
                #                 return Path.MAIN_MENU
