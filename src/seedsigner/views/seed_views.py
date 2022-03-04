import time
import embit
from binascii import hexlify
from embit.networks import NETWORKS

from seedsigner.gui.components import FontAwesomeIconConstants, SeedSignerCustomIconConstants

from .view import NotYetImplementedView, View, Destination, BackStackView, MainMenuView

from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen,
    LargeButtonScreen, WarningScreen, DireWarningScreen, seed_screens)
from seedsigner.gui.screens.screen import LoadingScreenThread, QRDisplayScreen
from seedsigner.helpers.threads import BaseThread, ThreadsafeCounter
from seedsigner.models.encode_qr import EncodeQR
from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
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
            return Destination(LoadSeedView)

        button_data = []
        for seed in self.seeds:
            button_data.append((seed["fingerprint"], SeedSignerCustomIconConstants.FINGERPRINT))
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
            return Destination(SeedMnemonicEntryView, view_args={"num_words": 24})

        elif button_data[selected_menu_num] == TYPE_12WORD:
            return Destination(SeedMnemonicEntryView, view_args={"num_words": 12})

        elif button_data[selected_menu_num] == CREATE:
            from .tools_views import ToolsMenuView
            return Destination(ToolsMenuView)



class SeedMnemonicEntryView(View):
    def __init__(self, num_words: int = 24, cur_word_index: int = 0):
        super().__init__()
        self.num_words = num_words
        self.cur_word_index = cur_word_index
        self.cur_word = self.controller.storage.get_pending_mnemonic_word(cur_word_index)


    def run(self):
        ret = seed_screens.SeedMnemonicEntryScreen(
            title=f"Seed Word #{self.cur_word_index + 1}",  # Human-readable 1-indexing!
            initial_letters=list(self.cur_word) if self.cur_word else ["a"],
            wordlist=Seed.get_wordlist(wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)),
        ).display()

        if ret == RET_CODE__BACK_BUTTON:
            if self.cur_word_index > 0:
                return Destination(SeedMnemonicEntryView, view_args={"num_words": self.num_words, "cur_word_index": self.cur_word_index - 1})
            else:
                self.controller.storage.discard_pending_mnemonic()
                return Destination(MainMenuView)
        
        # ret will be our new mnemonic word
        self.controller.storage.update_pending_mnemonic(ret, self.cur_word_index)

        if self.cur_word_index < self.num_words - 1:
            return Destination(SeedMnemonicEntryView, view_args={"num_words": self.num_words, "cur_word_index": self.cur_word_index + 1})
        else:
            # Attempt to finalize the mnemonic
            try:
                self.controller.storage.convert_pending_mnemonic_to_pending_seed()
            except Seed.InvalidSeedException:
                # TODO: Route to invalid mnemonic View
                return Destination(NotYetImplementedView)

            return Destination(SeedValidView)



"""****************************************************************************
    Loading seeds, passphrases, etc
****************************************************************************"""
class SeedValidView(View):
    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()
        self.fingerprint = self.seed.get_fingerprint(network=self.settings.get_value(SettingsConstants.SETTING__NETWORK))


    def run(self):
        from .psbt_views import PSBTOverviewView

        SIGN_PSBT = "Review PSBT"
        SCAN_PSBT = ("Scan a PSBT", FontAwesomeIconConstants.QRCODE)
        PASSPHRASE = ("Add Passphrase", FontAwesomeIconConstants.UNLOCK)
        SEED_TOOLS = "Seed Options"
        button_data = []

        if self.controller.psbt:
            if not PSBTParser.has_matching_input_fingerprint(psbt=self.controller.psbt, seed=self.seed, network=self.settings.get_value(SettingsConstants.SETTING__NETWORK)):
                # Seed doesn't match any input fingerprints
                # TODO: Is there ever a use-case for letting someone try to sign with a
                # seed that doesn't match? 
                SIGN_PSBT += " (?)"
            else:
                # Don't auto-route to a signable psbt. Just display the button.
                pass
            button_data.append(SIGN_PSBT)
        else:
            button_data.append(SCAN_PSBT)

        if self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE) in [
                SettingsConstants.OPTION__ENABLED,
                SettingsConstants.OPTION__PROMPT,
                SettingsConstants.OPTION__REQUIRED]:
            if self.seed.passphrase:
                PASSPHRASE = "Edit Passphrase"
            button_data.append(PASSPHRASE)
        
        button_data.append(SEED_TOOLS)

        selected_menu_num = seed_screens.SeedValidScreen(
            fingerprint=self.fingerprint,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # Warning message that this will discard the pending seed
            return Destination(SeedDiscardView)

        elif button_data[selected_menu_num] == SIGN_PSBT:
            self.controller.storage.finalize_pending_seed()
            self.controller.psbt_seed = self.seed
            return Destination(PSBTOverviewView, clear_history=True)

        elif button_data[selected_menu_num] == SCAN_PSBT:
            self.controller.storage.finalize_pending_seed()
            # Jump back to the Scan mode, but this time to sign a PSBT
            from .scan_views import ScanView
            return Destination(ScanView, clear_history=True)
        
        elif button_data[selected_menu_num] == PASSPHRASE:
            return Destination(SeedAddPassphraseView)

        elif button_data[selected_menu_num] == SEED_TOOLS:
            # Jump straight to the Seed Tools for this seed
            seed_num = self.controller.storage.finalize_pending_seed()
            return Destination(SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True)



class SeedDiscardView(View):
    def run(self):
        YES = "Yes"
        NO = "No"
        button_data = [YES, NO]

        selected_menu_num = LargeButtonScreen(
            title="Discard Seed?",
            button_data=button_data,
            show_top_nav_left_button=False,
        ).display()

        if button_data[selected_menu_num] == YES:
            self.controller.storage.clear_pending_seed()
            return Destination(MainMenuView)

        elif button_data[selected_menu_num] == NO:
            return Destination(SeedValidView)



class SeedAddPassphrasePromptView(View):
    def run(self):
        YES = "Yes"
        NO = "No"
        button_data = [YES, NO]

        selected_menu_num = LargeButtonScreen(
            title="Add Passphrase?",
            button_data=button_data
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == YES:
            return Destination(SeedAddPassphraseView)

        elif button_data[selected_menu_num] == NO:
            return Destination(SeedValidView)



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
        CONTINUE = "Continue"
        button_data = [EDIT, CONTINUE]

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
            show_top_nav_left_button=False,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        elif button_data[selected_menu_num] == EDIT:
            return Destination(SeedAddPassphraseView)
        
        elif button_data[selected_menu_num] == CONTINUE:
            return Destination(SeedValidView)



"""****************************************************************************
    Views for actions on individual seeds:
****************************************************************************"""

class SeedOptionsView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)


    def run(self):
        REVIEW_PSBT = "Review PSBT"
        VIEW_WORDS = "View Seed Words"
        EXPORT_XPUB = "Export Xpub"
        EXPORT_SEEDQR = "Export Seed as QR"
        button_data = []

        if self.controller.psbt:
            if not PSBTParser.has_matching_input_fingerprint(self.controller.psbt, self.seed, network=self.settings.get_value(SettingsConstants.SETTING__NETWORK)):
                # This seed does not seem to be a signer for this PSBT
                # TODO: How sure are we? Should disable this entirely if we're 100% sure?
                REVIEW_PSBT += " (?)"
            button_data.append(REVIEW_PSBT)
        
        button_data.append(VIEW_WORDS)

        if self.settings.get_value(SettingsConstants.SETTING__XPUB_EXPORT) == SettingsConstants.OPTION__ENABLED:
            button_data.append(EXPORT_XPUB)
        
        button_data.append(EXPORT_SEEDQR)

        selected_menu_num = seed_screens.SeedOptionsScreen(
            button_data=button_data,
            fingerprint=self.seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK)),
            has_passphrase=self.seed.passphrase is not None
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == REVIEW_PSBT:
            from seedsigner.views.psbt_views import PSBTOverviewView
            return Destination(PSBTOverviewView)

        elif button_data[selected_menu_num] == VIEW_WORDS:
            return Destination(SeedWordsWarningView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == EXPORT_XPUB:
            return Destination(SeedExportXpubSigTypeView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == EXPORT_SEEDQR:
            return Destination(NotYetImplementedView)
            # return Destination(SeedExportSeedQRView, view_args={"seed_num": self.seed_num})



"""****************************************************************************
    View Seed Words flow
****************************************************************************"""
class SeedWordsWarningView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        destination = Destination(SeedWordsView, view_args={"seed_num": self.seed_num})
        if self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            # Forward straight to showing the words
            destination.skip_current_view = True
            return destination

        selected_menu_num = DireWarningScreen(
            warning_text="""You must keep your seed words private & away from all online devices.""",
        ).display()

        if selected_menu_num == 0:
            # User clicked "I Understand"
            return destination

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedWordsView(View):
    def __init__(self, seed_num: int, is_first_page: bool = True):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)
        self.is_first_page = is_first_page


    def run(self):
        NEXT_12 = "Next"
        SEED_OPTIONS = "Seed Options"

        button_data = []
        if self.is_first_page and len(self.seed.mnemonic_list) == 24:
            button_data.append(NEXT_12)
        else:
            button_data.append(SEED_OPTIONS)

        selected_menu_num = seed_screens.SeedWordsScreen(
            seed=self.seed,
            is_first_page=self.is_first_page,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == NEXT_12:
            # Go on to page 2
            return Destination(SeedWordsView, view_args={"seed_num": self.seed_num, "is_first_page": False})

        elif button_data[selected_menu_num] == SEED_OPTIONS:
            # Back to SeedOptions for this seed; cannot back ("<") to this View.
            return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num}, clear_history=True)



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

        selected_menu_num = LargeButtonScreen(
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

        selected_menu_num = ButtonListScreen(
            title="Export Xpub",
            is_button_text_centered=False,
            is_bottom_list=True,
            button_data=self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__SCRIPT_TYPES),
        ).display()

        if selected_menu_num < len(SettingsConstants.ALL_SCRIPT_TYPES):
            args["script_type"] = SettingsConstants.ALL_SCRIPT_TYPES[selected_menu_num][0]

            if SettingsConstants.ALL_SCRIPT_TYPES[selected_menu_num][0] == SettingsConstants.CUSTOM_DERIVATION:
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
            is_bottom_list=True,
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
            warning_headline="Privacy Leak!",
            warning_text="""Xpub can be used to view all future transactions.""",
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
            qr_density=qr_density if qr_density else self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
            wordlist_language_code=self.seed.wordlist_language_code
        )


    def run(self):
        QRDisplayScreen(qr_encoder=self.qr_encoder).display()

        return Destination(MainMenuView)



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
