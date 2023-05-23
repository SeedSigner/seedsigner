import random
import time
from binascii import hexlify
from typing import List

from embit import bip39
from embit.descriptor import Descriptor

from seedsigner.controller import Controller
from seedsigner.gui.components import (
    FontAwesomeIconConstants,
    SeedSignerCustomIconConstants,
)
from seedsigner.gui.screens import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen,
    WarningScreen,
    DireWarningScreen,
    seed_screens,
)
from seedsigner.gui.screens.screen import (
    LargeIconStatusScreen,
    LoadingScreenThread,
    QRDisplayScreen,
)
from seedsigner.helpers import embit_utils
from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.encode_qr import EncodeQR
from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import InvalidSeedException, Seed
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.settings_definition import SettingsDefinition
from seedsigner.models.threads import BaseThread, ThreadsafeCounter
from seedsigner.views.psbt_views import PSBTChangeDetailsView
from seedsigner.views.scan_views import ScanView
from .view import NotYetImplementedView, View, Destination, BackStackView, MainMenuView


class SeedsMenuView(View):
    def __init__(self):
        super().__init__()
        self.seeds = []
        for seed in self.controller.storage.seeds:
            self.seeds.append({"fingerprint": seed.get_fingerprint()})

    def run(self):
        if not self.seeds:
            # Nothing to do here unless we have a seed loaded
            return Destination(LoadSeedView, clear_history=True)

        button_data = []
        for seed in self.seeds:
            button_data.append(
                (seed["fingerprint"], SeedSignerCustomIconConstants.FINGERPRINT, "blue")
            )
        button_data.append("Load a seed")

        selected_menu_num = ButtonListScreen(
            title="In-Memory Seeds",
            is_button_text_centered=False,
            button_data=button_data,
        ).display()

        if len(self.seeds) > 0 and selected_menu_num < len(self.seeds):
            return Destination(
                SeedOptionsView, view_args={"seed_num": selected_menu_num}
            )

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
        TYPE_12WORD = ("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
        TYPE_24WORD = ("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)
        CREATE = (" Create a seed", FontAwesomeIconConstants.PLUS)
        button_data = [
            SEED_QR,
            TYPE_12WORD,
            TYPE_24WORD,
            CREATE,
        ]

        selected_menu_num = ButtonListScreen(
            title="Load A Seed", is_button_text_centered=False, button_data=button_data
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == SEED_QR:
            from .scan_views import ScanView

            return Destination(ScanView)

        elif button_data[selected_menu_num] == TYPE_12WORD:
            self.controller.storage.init_pending_mnemonic(num_words=12)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == TYPE_24WORD:
            self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == CREATE:
            from .tools_views import ToolsMenuView

            return Destination(ToolsMenuView)


class SeedMnemonicEntryView(View):
    def __init__(self, cur_word_index: int = 0, is_calc_final_word: bool = False):
        super().__init__()
        self.cur_word_index = cur_word_index
        self.cur_word = self.controller.storage.get_pending_mnemonic_word(
            cur_word_index
        )
        self.is_calc_final_word = is_calc_final_word

    def run(self):
        ret = seed_screens.SeedMnemonicEntryScreen(
            title=f"Seed Word #{self.cur_word_index + 1}",  # Human-readable 1-indexing!
            initial_letters=list(self.cur_word) if self.cur_word else ["a"],
            wordlist=Seed.get_wordlist(
                wordlist_language_code=self.settings.get_value(
                    SettingsConstants.SETTING__WORDLIST_LANGUAGE
                )
            ),
        ).display()

        if ret == RET_CODE__BACK_BUTTON:
            if self.cur_word_index > 0:
                return Destination(BackStackView)
                # return Destination(
                #     SeedMnemonicEntryView,
                #     view_args={
                #         "cur_word_index": self.cur_word_index - 1,
                #         "is_calc_final_word": self.is_calc_final_word
                #     }
                # )
            else:
                self.controller.storage.discard_pending_mnemonic()
                return Destination(MainMenuView)

        # ret will be our new mnemonic word
        self.controller.storage.update_pending_mnemonic(ret, self.cur_word_index)

        if (
            self.is_calc_final_word
            and self.cur_word_index
            == self.controller.storage.pending_mnemonic_length - 2
        ):
            # Time to calculate the last word. User must decide how they want to specify
            # the last bits of entropy for the final word.
            from seedsigner.views.tools_views import (
                ToolsCalcFinalWordFinalizePromptView,
            )

            return Destination(ToolsCalcFinalWordFinalizePromptView)

        if (
            self.is_calc_final_word
            and self.cur_word_index
            == self.controller.storage.pending_mnemonic_length - 1
        ):
            # Time to calculate the last word. User must either select a final word to
            # contribute entropy to the checksum word OR we assume 0 ("abandon").
            from seedsigner.views.tools_views import ToolsCalcFinalWordShowFinalWordView

            return Destination(ToolsCalcFinalWordShowFinalWordView)

        if self.cur_word_index < self.controller.storage.pending_mnemonic_length - 1:
            return Destination(
                SeedMnemonicEntryView,
                view_args={
                    "cur_word_index": self.cur_word_index + 1,
                    "is_calc_final_word": self.is_calc_final_word,
                },
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
        self.fingerprint = self.seed.get_fingerprint()

    def run(self):
        FINALIZE = "Done"
        PASSPHRASE = "BIP-39 Passphrase"
        button_data = []

        button_data.append(FINALIZE)

        if (
            self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE)
            != SettingsConstants.OPTION__DISABLED
        ):
            button_data.append(PASSPHRASE)

        selected_menu_num = seed_screens.SeedFinalizeScreen(
            fingerprint=self.fingerprint,
            button_data=button_data,
        ).display()

        if button_data[selected_menu_num] == FINALIZE:
            seed_num = self.controller.storage.finalize_pending_seed()
            return Destination(
                SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True
            )

        elif button_data[selected_menu_num] == PASSPHRASE:
            return Destination(SeedAddPassphraseView)


class SeedAddPassphraseView(View):
    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()

    def run(self):
        ret = seed_screens.SeedAddPassphraseScreen(
            passphrase=self.seed.passphrase
        ).display()

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # The new passphrase will be the return value; it might be empty.
        self.seed.set_passphrase(ret)
        if len(self.seed.passphrase) > 0:
            return Destination(SeedReviewPassphraseView)
        else:
            return Destination(SeedFinalizeView)


class SeedReviewPassphraseView(View):
    """
    Display the completed passphrase back to the user.
    """

    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()

    def run(self):
        EDIT = "Edit passphrase"
        DONE = "Done"
        button_data = [EDIT, DONE]

        # Get the before/after fingerprints
        network = self.settings.get_value(SettingsConstants.SETTING__NETWORK)
        passphrase = self.seed.passphrase
        fingerprint_with = self.seed.get_fingerprint()
        self.seed.set_passphrase("")
        fingerprint_without = self.seed.get_fingerprint()
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
            return Destination(
                SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True
            )


class SeedDiscardView(View):
    def __init__(self, seed_num: int = None):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is not None:
            self.seed = self.controller.get_seed(self.seed_num)
        else:
            self.seed = self.controller.storage.pending_seed

    def run(self):
        KEEP = "Keep Seed"
        DISCARD = ("Discard", None, None, "red")
        button_data = [KEEP, DISCARD]

        fingerprint = self.seed.get_fingerprint()
        selected_menu_num = WarningScreen(
            title="Discard Seed?",
            status_headline=None,
            text=f"Wipe seed {fingerprint} from the device?",
            show_back_button=False,
            button_data=button_data,
        ).display()

        if button_data[selected_menu_num] == KEEP:
            # Use skip_current_view=True to prevent BACK from landing on this warning screen
            if self.seed_num is not None:
                return Destination(
                    SeedOptionsView,
                    view_args={"seed_num": self.seed_num},
                    skip_current_view=True,
                )
            else:
                return Destination(SeedFinalizeView, skip_current_view=True)

        elif button_data[selected_menu_num] == DISCARD:
            if self.seed_num is not None:
                self.controller.discard_seed(self.seed_num)
            else:
                self.controller.storage.clear_pending_seed()
            return Destination(MainMenuView, clear_history=True)


"""****************************************************************************
    Views for actions on individual seeds:
****************************************************************************"""


class SeedOptionsView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)

    def run(self):
        from seedsigner.views.psbt_views import PSBTOverviewView

        SCAN_TX = ("Scan Transaction", FontAwesomeIconConstants.QRCODE)
        EXPLORER = "Address Explorer"
        BACKUP = (
            "Backup Seed",
            None,
            None,
            None,
            SeedSignerCustomIconConstants.SMALL_CHEVRON_RIGHT,
        )
        DISCARD = ("Discard Seed", None, None, "red")

        button_data = []

        # if self.controller.psbt:
        #     if PSBTParser.has_matching_input_fingerprint(
        #         self.controller.psbt,
        #         self.seed,
        #         network=self.settings.get_value(SettingsConstants.SETTING__NETWORK),
        #     ):
        #         if (
        #             self.controller.resume_main_flow
        #             and self.controller.resume_main_flow == Controller.FLOW__PSBT
        #         ):
        #             # Re-route us directly back to the start of the PSBT flow
        #             self.controller.resume_main_flow = None
        #             self.controller.psbt_seed = self.seed
        #             return Destination(PSBTOverviewView, skip_current_view=True)

        button_data.append(SCAN_TX)
        button_data.append(EXPLORER)
        button_data.append(BACKUP)

        button_data.append(DISCARD)

        selected_menu_num = seed_screens.SeedOptionsScreen(
            button_data=button_data,
            fingerprint=self.seed.get_fingerprint(),
            has_passphrase=self.seed.passphrase is not None,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # Force BACK to always return to the Main Menu
            return Destination(MainMenuView)

        if button_data[selected_menu_num] == SCAN_TX:
            from seedsigner.views.scan_views import ScanView

            self.controller.psbt_seed = self.controller.get_seed(self.seed_num)
            return Destination(ScanView)

        # export stellar address
        elif button_data[selected_menu_num] == EXPLORER:
            self.controller.resume_main_flow = Controller.FLOW__ADDRESS_EXPLORER
            return Destination(
                AddressExporterView, view_args=dict(seed_num=self.seed_num)
            )

        elif button_data[selected_menu_num] == BACKUP:
            return Destination(SeedBackupView, view_args=dict(seed_num=self.seed_num))

        elif button_data[selected_menu_num] == DISCARD:
            return Destination(SeedDiscardView, view_args=dict(seed_num=self.seed_num))


class AddressExporterView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        seed = self.controller.storage.seeds[seed_num]
        data = dict(
            seed=seed,
        )
        self.controller.address_explorer_data = data

    def run(self):
        from seedsigner.views.tools_views import ToolsAddressExplorerAddressListView

        return Destination(
            ToolsAddressExplorerAddressListView,
            skip_current_view=True,
        )


class SeedBackupView(View):
    def __init__(self, seed_num):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)

    def run(self):
        VIEW_WORDS = "View Seed Words"
        EXPORT_SEEDQR = "Export as SeedQR"
        button_data = [VIEW_WORDS, EXPORT_SEEDQR]

        selected_menu_num = ButtonListScreen(
            title="Backup Seed",
            button_data=button_data,
            is_bottom_list=True,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == VIEW_WORDS:
            return Destination(
                SeedWordsWarningView, view_args={"seed_num": self.seed_num}
            )

        elif button_data[selected_menu_num] == EXPORT_SEEDQR:
            return Destination(
                SeedTranscribeSeedQRFormatView, view_args={"seed_num": self.seed_num}
            )


"""****************************************************************************
    View Seed Words flow
****************************************************************************"""


# TODO: remove bip85 support
class SeedWordsWarningView(View):
    def __init__(self, seed_num: int, bip85_data: dict = None):
        super().__init__()
        self.seed_num = seed_num
        self.bip85_data = bip85_data

    def run(self):
        destination = Destination(
            SeedWordsView,
            view_args=dict(
                seed_num=self.seed_num, page_index=0, bip85_data=self.bip85_data
            ),
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )
        if (
            self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS)
            == SettingsConstants.OPTION__DISABLED
        ):
            # Forward straight to showing the words
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
        words_per_page = (
            4  # TODO: eventually make this configurable for bigger screens?
        )

        if self.bip85_data is not None:
            mnemonic = self.seed.get_bip85_child_mnemonic(
                self.bip85_data["child_index"], self.bip85_data["num_words"]
            ).split()
            title = f"""Child #{self.bip85_data["child_index"]}"""
        else:
            mnemonic = self.seed.mnemonic_display_list
            title = "Seed Words"
        words = mnemonic[
            self.page_index * words_per_page : (self.page_index + 1) * words_per_page
        ]

        button_data = []
        num_pages = int(len(mnemonic) / words_per_page)
        if self.page_index < num_pages - 1 or self.seed_num is None:
            button_data.append(NEXT)
        else:
            button_data.append(DONE)

        selected_menu_num = seed_screens.SeedWordsScreen(
            title=f"{title}: {self.page_index + 1}/{num_pages}",
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
                    view_args=dict(
                        seed_num=self.seed_num,
                        page_index=self.page_index + 1,
                        bip85_data=self.bip85_data,
                    ),
                )

        elif button_data[selected_menu_num] == DONE:
            # Must clear history to avoid BACK button returning to private info
            return Destination(
                SeedWordsBackupTestPromptView,
                view_args=dict(seed_num=self.seed_num, bip85_data=self.bip85_data),
            )


"""****************************************************************************
    Seed Words Backup Test
****************************************************************************"""


class SeedWordsBackupTestPromptView(View):
    def __init__(self, seed_num: int, bip85_data: dict = None):
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
                return Destination(
                    SeedOptionsView, view_args=dict(seed_num=self.seed_num)
                )
            else:
                return Destination(SeedFinalizeView)


class SeedWordsBackupTestView(View):
    def __init__(
        self,
        seed_num: int,
        bip85_data: dict = None,
        confirmed_list: List[bool] = None,
        cur_index: int = None,
    ):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is None:
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.seed = self.controller.get_seed(self.seed_num)
        self.bip85_data = bip85_data

        if self.bip85_data is not None:
            self.mnemonic_list = self.seed.get_bip85_child_mnemonic(
                self.bip85_data["child_index"], self.bip85_data["num_words"]
            ).split()
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
                    view_args=dict(
                        seed_num=self.seed_num,
                        confirmed_list=self.confirmed_list,
                        bip85_data=self.bip85_data,
                    ),
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
                ),
            )


class SeedWordsBackupTestMistakeView(View):
    def __init__(
        self,
        seed_num: int,
        bip85_data: dict = None,
        cur_index: int = None,
        wrong_word: str = None,
        confirmed_list: List[bool] = None,
    ):
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
            status_headline=f"Wrong Word!",
            text=f'Word #{self.cur_index + 1} is not "{self.wrong_word}"!',
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
                ),
            )


class SeedWordsBackupTestSuccessView(View):
    def __init__(self, seed_num: int):
        self.seed_num = seed_num

    def run(self):
        LargeIconStatusScreen(
            title="Backup Verified",
            show_back_button=False,
            status_headline="Success!",
            text="All mnemonic backup words were successfully verified!",
            button_data=["OK"],
        ).display()

        if self.seed_num is not None:
            return Destination(
                SeedOptionsView,
                view_args=dict(seed_num=self.seed_num),
                clear_history=True,
            )
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

        if (
            self.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR)
            != SettingsConstants.OPTION__ENABLED
        ):
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
            },
        )


class SeedTranscribeSeedQRWarningView(View):
    def __init__(
        self,
        seed_num: int,
        seedqr_format: str = QRType.SEED__SEEDQR,
        num_modules: int = 29,
    ):
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

        if (
            self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS)
            == SettingsConstants.OPTION__DISABLED
        ):
            # Forward straight to transcribing the SeedQR
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
            wordlist_language_code=self.settings.get_value(
                SettingsConstants.SETTING__WORDLIST_LANGUAGE
            ),
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
                    "seedqr_format": self.seedqr_format,
                },
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
            wordlist_language_code=self.settings.get_value(
                SettingsConstants.SETTING__WORDLIST_LANGUAGE
            ),
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

        return Destination(
            SeedTranscribeSeedQRConfirmQRPromptView,
            view_args={"seed_num": self.seed_num},
        )


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
            return Destination(
                SeedTranscribeSeedQRConfirmScanView,
                view_args={"seed_num": self.seed_num},
            )

        elif button_data[selected_menu_option] == DONE:
            return Destination(
                SeedOptionsView,
                view_args={"seed_num": self.seed_num},
                clear_history=True,
            )


class SeedTranscribeSeedQRConfirmScanView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(seed_num)

    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen

        # Run the live preview and QR code capture process
        # TODO: Does this belong in its own BaseThread?
        wordlist_language_code = self.settings.get_value(
            SettingsConstants.SETTING__WORDLIST_LANGUAGE
        )
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

                    return Destination(
                        SeedOptionsView, view_args={"seed_num": self.seed_num}
                    )

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
            address=address, script_type=script_type, network=network
        )

    def run(self):
        if (
            self.controller.unverified_address["script_type"]
            == SettingsConstants.NESTED_SEGWIT
        ):
            # No way to differentiate single sig from multisig
            return Destination(AddressVerificationSigTypeView, skip_current_view=True)

        if (
            self.controller.unverified_address["script_type"]
            == SettingsConstants.NATIVE_SEGWIT
        ):
            if len(self.controller.unverified_address["address"]) >= 62:
                # Mainnet/testnet are 62, regtest is 64
                sig_type = SettingsConstants.MULTISIG
                if self.controller.multisig_wallet_descriptor:
                    # Can jump straight to the brute-force verification View
                    destination = Destination(
                        SeedAddressVerificationView, skip_current_view=True
                    )
                else:
                    self.controller.resume_main_flow = (
                        Controller.FLOW__VERIFY_MULTISIG_ADDR
                    )
                    destination = Destination(
                        LoadMultisigWalletDescriptorView, skip_current_view=True
                    )

            else:
                sig_type = SettingsConstants.SINGLE_SIG
                destination = Destination(
                    SeedSingleSigAddressVerificationSelectSeedView,
                    skip_current_view=True,
                )

        elif (
            self.controller.unverified_address["script_type"]
            == SettingsConstants.TAPROOT
        ):
            # TODO: add Taproot support
            return Destination(NotYetImplementedView)

        elif (
            self.controller.unverified_address["script_type"]
            == SettingsConstants.LEGACY_P2PKH
        ):
            # TODO: detect single sig vs multisig or have to prompt?
            return Destination(NotYetImplementedView)

        derivation_path = embit_utils.get_standard_derivation_path(
            network=self.controller.unverified_address["network"],
            wallet_type=sig_type,
            script_type=self.controller.unverified_address["script_type"],
        )

        self.controller.unverified_address["sig_type"] = sig_type
        self.controller.unverified_address["derivation_path"] = derivation_path

        return destination


class AddressVerificationSigTypeView(View):
    def run(self):
        sig_type_settings_entry = SettingsDefinition.get_settings_entry(
            SettingsConstants.SETTING__SIG_TYPES
        )
        SINGLE_SIG = sig_type_settings_entry.get_selection_option_display_name_by_value(
            SettingsConstants.SINGLE_SIG
        )
        MULTISIG = sig_type_settings_entry.get_selection_option_display_name_by_value(
            SettingsConstants.MULTISIG
        )

        button_data = [SINGLE_SIG, MULTISIG]
        selected_menu_num = seed_screens.AddressVerificationSigTypeScreen(
            title="Verify Address",
            text="Sig type can't be auto-detected from this address. Please specify:",
            button_data=button_data,
            is_bottom_list=True,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            self.controller.unverified_address = None
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == SINGLE_SIG:
            sig_type = SettingsConstants.SINGLE_SIG
            destination = Destination(SeedSingleSigAddressVerificationSelectSeedView)

        elif button_data[selected_menu_num] == MULTISIG:
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
            script_type=self.controller.unverified_address["script_type"],
        )
        self.controller.unverified_address["derivation_path"] = derivation_path

        return destination


class SeedSingleSigAddressVerificationSelectSeedView(View):
    def run(self):
        seeds = self.controller.storage.seeds

        SCAN_SEED = ("Scan a seed", FontAwesomeIconConstants.QRCODE)
        TYPE_12WORD = ("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
        TYPE_24WORD = ("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)
        button_data = []

        text = "Load the seed to verify"

        for seed in seeds:
            button_str = seed.get_fingerprint()
            button_data.append(
                (button_str, SeedSignerCustomIconConstants.FINGERPRINT, "blue")
            )
            text = "Select seed to verify"

        button_data.append(SCAN_SEED)
        button_data.append(TYPE_12WORD)
        button_data.append(TYPE_24WORD)

        selected_menu_num = (
            seed_screens.SeedSingleSigAddressVerificationSelectSeedScreen(
                title="Verify Address",
                text=text,
                is_button_text_centered=False,
                button_data=button_data,
            ).display()
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if len(seeds) > 0 and selected_menu_num < len(seeds):
            # User selected one of the n seeds
            return Destination(
                SeedAddressVerificationView,
                view_args=dict(
                    seed_num=selected_menu_num,
                ),
            )

        self.controller.resume_main_flow = Controller.FLOW__VERIFY_SINGLESIG_ADDR

        if button_data[selected_menu_num] == SCAN_SEED:
            from seedsigner.views.scan_views import ScanView

            return Destination(ScanView)

        elif button_data[selected_menu_num] in [TYPE_12WORD, TYPE_24WORD]:
            from seedsigner.views.seed_views import SeedMnemonicEntryView

            if button_data[selected_menu_num] == TYPE_12WORD:
                self.controller.storage.init_pending_mnemonic(num_words=12)
            else:
                self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)


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
        self.is_multisig = (
            self.controller.unverified_address["sig_type"] == SettingsConstants.MULTISIG
        )
        if not self.is_multisig:
            if seed_num is None:
                raise Exception(
                    "Can't validate a single sig addr without specifying a seed"
                )
            self.seed_num = seed_num
            self.seed = self.controller.get_seed(seed_num)
        else:
            self.seed = None
        self.address = self.controller.unverified_address["address"]
        self.derivation_path = self.controller.unverified_address["derivation_path"]
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

        script_type_settings_entry = SettingsDefinition.get_settings_entry(
            SettingsConstants.SETTING__SCRIPT_TYPES
        )
        script_type_display = (
            script_type_settings_entry.get_selection_option_display_name_by_value(
                self.script_type
            )
        )

        sig_type_settings_entry = SettingsDefinition.get_settings_entry(
            SettingsConstants.SETTING__SIG_TYPES
        )
        sig_type_display = (
            sig_type_settings_entry.get_selection_option_display_name_by_value(
                self.sig_type
            )
        )

        network_settings_entry = SettingsDefinition.get_settings_entry(
            SettingsConstants.SETTING__NETWORK
        )
        network_display = (
            network_settings_entry.get_selection_option_display_name_by_value(
                self.network
            )
        )
        mainnet = network_settings_entry.get_selection_option_display_name_by_value(
            SettingsConstants.MAINNET
        )

        # Display the Screen to show the brute-forcing progress.
        # Using a loop here to handle the SKIP_10 button presses to increment the counter
        # and resume displaying the screen. User won't even notice that the Screen is
        # being re-constructed.
        while True:
            selected_menu_num = seed_screens.SeedAddressVerificationScreen(
                address=self.address,
                derivation_path=self.derivation_path,
                script_type=script_type_display,
                sig_type=sig_type_display,
                network=network_display,
                is_mainnet=network_display == mainnet,
                threadsafe_counter=self.threadsafe_counter,
                verified_index=self.verified_index,
                button_data=button_data,
            ).display()

            if self.verified_index.cur_count is not None:
                break

            if selected_menu_num == RET_CODE__BACK_BUTTON:
                break

            if button_data[selected_menu_num] == SKIP_10:
                self.threadsafe_counter.increment(10)

            elif button_data[selected_menu_num] == CANCEL:
                break

        if self.verified_index.cur_count is not None:
            # Successfully verified the addr; update the data
            self.controller.unverified_address[
                "verified_index"
            ] = self.verified_index.cur_count
            self.controller.unverified_address["verified_index_is_change"] = (
                self.verified_index_is_change.cur_count == 1
            )
            return Destination(
                AddressVerificationSuccessView, view_args=dict(seed_num=self.seed_num)
            )

        else:
            # Halt the thread if the user gave up (will already be stopped if it verified the
            # target addr).
            self.addr_verification_thread.stop()
            while self.addr_verification_thread.is_alive():
                time.sleep(0.01)

        return Destination(MainMenuView)

    class BruteForceAddressVerificationThread(BaseThread):
        def __init__(
            self,
            address: str,
            seed: Seed,
            descriptor: Descriptor,
            script_type: str,
            embit_network: str,
            derivation_path: str,
            threadsafe_counter: ThreadsafeCounter,
            verified_index: ThreadsafeCounter,
            verified_index_is_change: ThreadsafeCounter,
        ):
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
                self.xpub = self.seed.get_xpub(
                    wallet_path=self.derivation_path,
                    network=Settings.get_instance().get_value(
                        SettingsConstants.SETTING__NETWORK
                    ),
                )

        def run(self):
            while self.keep_running:
                if self.threadsafe_counter.cur_count % 10 == 0:
                    print(f"Incremented to {self.threadsafe_counter.cur_count}")

                i = self.threadsafe_counter.cur_count

                if self.descriptor:
                    receive_address = embit_utils.get_multisig_address(
                        descriptor=self.descriptor,
                        index=i,
                        is_change=False,
                        embit_network=self.embit_network,
                    )
                    change_address = embit_utils.get_multisig_address(
                        descriptor=self.descriptor,
                        index=i,
                        is_change=True,
                        embit_network=self.embit_network,
                    )

                else:
                    receive_address = embit_utils.get_single_sig_address(
                        xpub=self.xpub,
                        script_type=self.script_type,
                        index=i,
                        is_change=False,
                        embit_network=self.embit_network,
                    )
                    change_address = embit_utils.get_single_sig_address(
                        xpub=self.xpub,
                        script_type=self.script_type,
                        index=i,
                        is_change=True,
                        embit_network=self.embit_network,
                    )

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
        verified_index_is_change = self.controller.unverified_address[
            "verified_index_is_change"
        ]

        if sig_type == SettingsConstants.MULTISIG:
            source = "multisig"
        else:
            source = f"seed {self.seed.get_fingerprint()}"

        LargeIconStatusScreen(
            status_headline="Address Verified",
            text=f"""{address[:7]} = {source}'s {"change" if verified_index_is_change else "receive"} address #{verified_index}.""",
        ).display()

        return Destination(MainMenuView)


class LoadMultisigWalletDescriptorView(View):
    def run(self):
        SCAN = ("Scan Descriptor", FontAwesomeIconConstants.QRCODE)
        CANCEL = "Cancel"
        button_data = [SCAN, CANCEL]
        selected_menu_num = seed_screens.LoadMultisigWalletDescriptorScreen(
            button_data=button_data,
            show_back_button=False,
        ).display()

        if button_data[selected_menu_num] == SCAN:
            return Destination(ScanView)

        elif button_data[selected_menu_num] == CANCEL:
            if self.controller.resume_main_flow == Controller.FLOW__PSBT:
                return Destination(BackStackView)
            else:
                return Destination(MainMenuView)


class MultisigWalletDescriptorView(View):
    def run(self):
        descriptor = self.controller.multisig_wallet_descriptor

        fingerprints = []
        for key in descriptor.keys:
            fingerprint = hexlify(key.fingerprint).decode()
            fingerprints.append(fingerprint)

        policy = descriptor.brief_policy.split("multisig")[0].strip()

        RETURN = "Return to PSBT"
        VERIFY = "Verify Addr"
        EXPLORER = "Address Explorer"
        OK = "OK"

        button_data = [OK]
        if self.controller.resume_main_flow:
            if self.controller.resume_main_flow == Controller.FLOW__PSBT:
                button_data = [RETURN]
            elif (
                self.controller.resume_main_flow
                == Controller.FLOW__VERIFY_MULTISIG_ADDR
                and self.controller.unverified_address
            ):
                VERIFY += f""" {self.controller.unverified_address["address"][:7]}"""
                button_data = [VERIFY]
            elif self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER:
                button_data = [EXPLORER]

        selected_menu_num = seed_screens.MultisigWalletDescriptorScreen(
            policy=policy,
            fingerprints=fingerprints,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            self.controller.multisig_wallet_descriptor = None
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == RETURN:
            # Jump straight back to PSBT change verification
            self.controller.resume_main_flow = None
            return Destination(
                PSBTChangeDetailsView, view_args=dict(change_address_num=0)
            )

        elif button_data[selected_menu_num] == VERIFY:
            self.controller.resume_main_flow = None
            return Destination(SeedAddressVerificationView)

        elif button_data[selected_menu_num] == EXPLORER:
            from seedsigner.views.tools_views import ToolsAddressExplorerAddressTypeView

            self.controller.resume_main_flow = None
            return Destination(ToolsAddressExplorerAddressTypeView)

        return Destination(MainMenuView)
