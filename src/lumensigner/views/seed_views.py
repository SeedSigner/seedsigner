import random
from typing import List

from embit import bip39

from lumensigner.controller import Controller
from lumensigner.gui.components import (
    FontAwesomeIconConstants,
    SeedSignerCustomIconConstants,
)
from lumensigner.gui.screens import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen,
    WarningScreen,
    DireWarningScreen,
    seed_screens,
)
from lumensigner.gui.screens.screen import (
    LargeIconStatusScreen,
)
from lumensigner.models.decode_qr import DecodeQR
from lumensigner.models.encode_qr import EncodeQR
from lumensigner.models.qr_type import QRType
from lumensigner.models.seed import InvalidSeedException, Seed
from lumensigner.models.settings import SettingsConstants
from lumensigner.views.view import View, Destination, BackStackView, MainMenuView


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
            from lumensigner.views.tools_views import (
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
            from lumensigner.views.tools_views import (
                ToolsCalcFinalWordShowFinalWordView,
            )

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

        if self.controller.resume_main_flow == Controller.FLOW__SIGN_HASH:
            from lumensigner.views.sign_hash_views import SignHashDireWarningView

            self.controller.resume_main_flow = None
            address_index = self.controller.sign_hash_data[0]
            return Destination(
                SignHashDireWarningView,
                view_args=dict(seed=self.seed, address_index=address_index),
                skip_current_view=True,
            )

        if self.controller.resume_main_flow == Controller.FLOW__REQUEST_ADDRESS:
            from lumensigner.views.request_address import RequestAddressShareAddressView

            self.controller.resume_main_flow = None
            address_index = self.controller.request_address_data
            return Destination(
                RequestAddressShareAddressView,
                view_args=dict(seed=self.seed, address_index=address_index),
                skip_current_view=True,
            )

        if self.controller.resume_main_flow == Controller.FLOW__SIGN_TX:
            from lumensigner.views.sign_tx_views import TransactionDetailsView

            self.controller.resume_main_flow = None
            address_index, te = self.controller.tx_data
            return Destination(
                TransactionDetailsView,
                view_args=dict(te=te, seed=self.seed, address_index=address_index),
                skip_current_view=True,
            )

        if self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER:
            from lumensigner.views.tools_views import AddressExporterView

            self.controller.resume_main_flow = None
            return Destination(
                AddressExporterView,
                view_args=dict(seed_num=self.seed_num),
                skip_current_view=True,
            )

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
            from lumensigner.views.scan_views import ScanView

            self.controller.sign_seed = self.controller.get_seed(self.seed_num)
            return Destination(ScanView)

        # export stellar address
        elif button_data[selected_menu_num] == EXPLORER:
            from lumensigner.views.tools_views import AddressExporterView
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
        from lumensigner.views.tools_views import ToolsAddressExplorerAddressListView

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


class SeedWordsWarningView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num

    def run(self):
        destination = Destination(
            SeedWordsView,
            view_args=dict(seed_num=self.seed_num, page_index=0),
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
    def __init__(self, seed_num: int, page_index: int = 0):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is None:
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.seed = self.controller.get_seed(self.seed_num)
        self.page_index = page_index

    def run(self):
        NEXT = "Next"
        DONE = "Done"

        # Slice the mnemonic to our current 4-word section
        words_per_page = (
            4  # TODO: eventually make this configurable for bigger screens?
        )

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
                    view_args=dict(seed_num=self.seed_num),
                )
            else:
                return Destination(
                    SeedWordsView,
                    view_args=dict(
                        seed_num=self.seed_num,
                        page_index=self.page_index + 1,
                    ),
                )

        elif button_data[selected_menu_num] == DONE:
            # Must clear history to avoid BACK button returning to private info
            return Destination(
                SeedWordsBackupTestPromptView,
                view_args=dict(seed_num=self.seed_num),
            )


"""****************************************************************************
    Seed Words Backup Test
****************************************************************************"""


class SeedWordsBackupTestPromptView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num

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
                view_args=dict(seed_num=self.seed_num),
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
        confirmed_list: List[bool] = None,
        cur_index: int = None,
    ):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is None:
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.seed = self.controller.get_seed(self.seed_num)

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
                    ),
                )

        else:
            # Picked the WRONG WORD!
            return Destination(
                SeedWordsBackupTestMistakeView,
                view_args=dict(
                    seed_num=self.seed_num,
                    cur_index=self.cur_index,
                    wrong_word=button_data[selected_menu_num],
                    confirmed_list=self.confirmed_list,
                ),
            )


class SeedWordsBackupTestMistakeView(View):
    def __init__(
        self,
        seed_num: int,
        cur_index: int = None,
        wrong_word: str = None,
        confirmed_list: List[bool] = None,
    ):
        super().__init__()
        self.seed_num = seed_num
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
                view_args=dict(seed_num=self.seed_num),
            )

        elif button_data[selected_menu_num] == RETRY:
            return Destination(
                SeedWordsBackupTestView,
                view_args=dict(
                    seed_num=self.seed_num,
                    confirmed_list=self.confirmed_list,
                    cur_index=self.cur_index,
                ),
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
        from lumensigner.gui.screens.scan_screens import ScanScreen

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
