import logging
import random

from gettext import gettext as _

from seedsigner.gui.components import SeedSignerIconConstants
from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, DireWarningScreen)
from seedsigner.gui.screens.screen import ButtonOption, ButtonOptionWithoutTranslation
from seedsigner.models.seed import InvalidSeedException, Seed
from seedsigner.models.settings import SettingsConstants
from seedsigner.views.view import View, Destination, BackStackView, MainMenuView
from seedsigner.views.seed_views import SeedDiscardView, SeedFinalizeView

logger = logging.getLogger(__name__)



"""****************************************************************************
    Entry Seed Numbers Views
****************************************************************************"""
class SeedNumbersFormatView(View):
    """Numbers (1-2048) or 12-bit circles. Same fork as choosing 12 vs 24 words."""
    NUMBERS = ButtonOption("Numbers")
    BINARY = ButtonOption("Binary")

    def run(self):
        from seedsigner.gui.screens.seed_numbers_screens import SeedNumbersFormatScreen
        button_data = [self.NUMBERS, self.BINARY]
        n = self.controller.storage.pending_mnemonic_length
        if n == 24:
            title = _("24-number Seed")
        else:
            title = _("12-number Seed")
        selected_menu_num = self.run_screen(
            SeedNumbersFormatScreen,
            title=title,
            text=_("Valid numbers: 1-2048"),
            is_button_text_centered=True,
            is_bottom_list=True,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            self.controller.storage.discard_pending_mnemonic()
            return Destination(BackStackView)

        mode = "numbers" if button_data[selected_menu_num] == self.NUMBERS else "binary"
        return Destination(SeedNumbersEntryView, view_args={"mode": mode})



class SeedNumbersEntryView(View):
    """
    Same routing as SeedMnemonicEntryView, but each mnemonic slot is entered as a
    1-2048 number (digits or 12 bits) instead of letters.

    `cur_index` is that slot (0-based), the same role as
    SeedMnemonicEntryView.cur_word_index. The screen still returns the BIP-39 word
    so the pending mnemonic storage is unchanged.
    """
    def __init__(self, cur_index: int = 0, mode: str = "binary"):
        super().__init__()
        self.cur_index = cur_index
        self.mode = mode
        self.cur_word = self.controller.storage.get_pending_mnemonic_word(cur_index)


    def run(self):
        from seedsigner.gui.screens.seed_numbers_screens import SeedNumbersEntryScreen

        ret = self.run_screen(
            SeedNumbersEntryScreen,
            # TRANSLATOR_NOTE: Inserts the number's position (e.g. "Seed Number #6")
            title=_("Seed Number #{}").format(self.cur_index + 1),  # Human-readable 1-indexing!
            mode=self.mode,
            initial_word=self.cur_word,
            wordlist=Seed.get_wordlist(wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)),
        )

        if ret == RET_CODE__BACK_BUTTON:
            # Keep the pending mnemonic. FormatView is still on the back stack
            # and discards it only if the user leaves the numbers flow.
            return Destination(BackStackView)

        # ret is the BIP-39 word for the number the user just entered
        self.controller.storage.update_pending_mnemonic(ret, self.cur_index)

        if self.cur_index < self.controller.storage.pending_mnemonic_length - 1:
            return Destination(
                SeedNumbersEntryView,
                view_args={
                    "cur_index": self.cur_index + 1,
                    "mode": self.mode,
                },
            )

        # Attempt to finalize the mnemonic
        try:
            self.controller.storage.convert_pending_mnemonic_to_pending_seed()
        except InvalidSeedException:
            return Destination(SeedNumbersInvalidView, view_args={"mode": self.mode})

        return Destination(SeedNumbersLoadView)



class SeedNumbersLoadView(View):
    """Fingerprint + Load seed / Discard — same fork as Calc 12th/24th word Done."""

    LOAD = ButtonOption("Load seed")
    DISCARD = ButtonOption("Discard", button_label_color="red")

    def run(self):
        from seedsigner.gui.screens.seed_screens import SeedFinalizeScreen

        button_data = [self.LOAD, self.DISCARD]
        fingerprint = self.controller.storage.get_pending_seed().get_fingerprint(
            self.settings.get_value(SettingsConstants.SETTING__NETWORK)
        )
        selected_menu_num = self.run_screen(
            SeedFinalizeScreen,
            fingerprint=fingerprint,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.LOAD:
            return Destination(SeedFinalizeView)

        return Destination(SeedDiscardView)



class SeedNumbersInvalidView(View):
    EDIT = ButtonOption("Review & edit")
    DISCARD = ButtonOption("Discard", button_label_color="red")

    def __init__(self, mode: str):
        super().__init__()
        self.mode = mode

    def run(self):
        button_data = [self.EDIT, self.DISCARD]
        selected_menu_num = self.run_screen(
            DireWarningScreen,
            title=_("Invalid Mnemonic!"),
            status_icon_name=SeedSignerIconConstants.ERROR,
            status_headline=None,
            text=_("Checksum failure; not a valid seed phrase."),
            show_back_button=False,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.EDIT:
            return Destination(
                SeedNumbersEntryView,
                view_args={"cur_index": 0, "mode": self.mode},
            )

        self.controller.storage.discard_pending_mnemonic()
        return Destination(MainMenuView)




"""****************************************************************************
    View Seed Numbers flow
****************************************************************************"""
class SeedNumbersWarningView(View):
    def __init__(self, seed: Seed, bip85_data: dict = None):
        super().__init__()
        self.seed = seed
        self.bip85_data = bip85_data


    def run(self):
        destination = Destination(
            SeedNumbersView,
            view_args=dict(
                seed=self.seed,
                page_index=0,
                bip85_data=self.bip85_data
            ),
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )
        if self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            # Forward straight to showing the numbers
            return destination

        selected_menu_num = self.run_screen(
            DireWarningScreen,
            text=_("Numbers are 1-2048. You must keep your seed numbers private & away from all online devices."),
        )

        if selected_menu_num == 0:
            # User clicked "I Understand"
            return destination

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedNumbersView(View):
    """
    One number per screen. Same routing as SeedWordsView (which shows four words
    per page): Next until the end, then the optional verify prompt.

    `page_index` is which number (0-based), the same role as SeedWordsView.page_index.
    `bip85_data` shows a child mnemonic instead of this seed, same as SeedWordsView.
    """
    NEXT = ButtonOption("Next")
    DONE = ButtonOption("Done")

    def __init__(self, seed: Seed, bip85_data: dict = None, page_index: int = 0):
        super().__init__()
        if seed is None:
            self.is_pending_seed = True
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.is_pending_seed = False
            self.seed = seed
        self.bip85_data = bip85_data
        self.page_index = page_index


    def run(self):
        from seedsigner.gui.screens.seed_numbers_screens import SeedNumbersBackupScreen

        child_index = None
        if self.bip85_data is not None:
            mnemonic = self.seed.get_bip85_child_mnemonic(self.bip85_data["child_index"], self.bip85_data["num_words"]).split()
            child_index = self.bip85_data["child_index"]
        else:
            mnemonic = self.seed.mnemonic_display_list

        n = len(mnemonic)
        word = mnemonic[self.page_index]
        number = self.seed.wordlist.index(word) + 1

        button_data = []
        if self.page_index < n - 1 or self.is_pending_seed:
            button_data.append(self.NEXT)
        else:
            button_data.append(self.DONE)

        selected_menu_num = self.run_screen(
            SeedNumbersBackupScreen,
            page_index=self.page_index,
            num_pages=n,
            child_index=child_index,
            word=word,
            number=number,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if self.is_pending_seed:
            self.seed = None  # Set to None for next View to know it's a pending seed

        if button_data[selected_menu_num] == self.NEXT:
            if self.is_pending_seed and self.page_index == n - 1:
                from seedsigner.views.seed_views import SeedWordsBackupTestPromptView
                return Destination(
                    SeedWordsBackupTestPromptView,
                    view_args=dict(seed=self.seed, bip85_data=self.bip85_data, numbers=True),
                )
            return Destination(
                SeedNumbersView,
                view_args=dict(
                    seed=self.seed,
                    page_index=self.page_index + 1,
                    bip85_data=self.bip85_data,
                ),
            )

        elif button_data[selected_menu_num] == self.DONE:
            from seedsigner.views.seed_views import SeedWordsBackupTestPromptView
            # Must clear history to avoid BACK button returning to private info
            return Destination(
                SeedWordsBackupTestPromptView,
                view_args=dict(seed=self.seed, bip85_data=self.bip85_data, numbers=True),
            )
        


"""****************************************************************************
    Seed Numbers Backup Test
****************************************************************************"""
class SeedNumbersBackupTestView(View):
    def __init__(self, seed: Seed, bip85_data: dict = None, confirmed_list: list = None, cur_index: int = None, rand_seed: int = None):
        """
        Note: `rand_seed` is ONLY USED BY THE SCREENSHOT GENERATOR!!! (to ensure
        consistent screenshot results).

        Same quiz shape as SeedWordsBackupTestView: one real number plus three
        decoys. `cur_index` is the mnemonic position being asked (0-based).
        """
        super().__init__()
        if seed is None:
            self.is_pending_seed = True
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.is_pending_seed = False
            self.seed = seed
        self.bip85_data = bip85_data

        if self.bip85_data is not None:
            self.mnemonic_list = self.seed.get_bip85_child_mnemonic(self.bip85_data["child_index"], self.bip85_data["num_words"]).split()
        else:
            self.mnemonic_list = self.seed.mnemonic_display_list

        self.confirmed_list = confirmed_list
        if not self.confirmed_list:
            self.confirmed_list = []

        self.cur_index = cur_index
        self.rand_seed = rand_seed


    def run(self):
        from seedsigner.helpers.number_bits import format_number

        if self.rand_seed is not None:
            random.seed(self.rand_seed + self.cur_index if self.cur_index is not None else 0)

        if self.cur_index is None:
            self.cur_index = int(random.random() * len(self.mnemonic_list))
            while self.cur_index in self.confirmed_list:
                self.cur_index = int(random.random() * len(self.mnemonic_list))

        real_number = self.seed.wordlist.index(self.mnemonic_list[self.cur_index]) + 1
        real_option = ButtonOptionWithoutTranslation(format_number(real_number))

        decoys = set()
        while len(decoys) < 3:
            candidate = int(random.random() * 2048) + 1
            if candidate != real_number:
                decoys.add(candidate)

        button_data = [real_option] + [
            ButtonOptionWithoutTranslation(format_number(number))
            for number in decoys
        ]
        random.shuffle(button_data)

        # TRANSLATOR_NOTE: Inserts the number's position (e.g. "Verify Number #1")
        title = _("Verify Number #{}").format(self.cur_index + 1)
        from seedsigner.gui.screens.seed_numbers_screens import SeedNumbersBackupTestScreen
        selected_menu_num = self.run_screen(
            SeedNumbersBackupTestScreen,
            title=title,
            options=[option.button_label for option in button_data],
        )

        if self.is_pending_seed:
            self.seed = None  # Set to None for next View to know it's a pending seed

        if button_data[selected_menu_num] == real_option:
            self.confirmed_list.append(self.cur_index)
            if len(self.confirmed_list) == len(self.mnemonic_list):
                # Successfully confirmed the full mnemonic!
                return Destination(
                    SeedNumbersBackupTestSuccessView,
                    view_args=dict(seed=self.seed),
                )
            # Continue testing the remaining numbers
            return Destination(
                SeedNumbersBackupTestView,
                view_args=dict(seed=self.seed, confirmed_list=self.confirmed_list, bip85_data=self.bip85_data),
            )

        # Picked the WRONG number!
        return Destination(
            SeedNumbersBackupTestMistakeView,
            view_args=dict(
                seed=self.seed,
                bip85_data=self.bip85_data,
                cur_index=self.cur_index,
                wrong_number=button_data[selected_menu_num].button_label,
                confirmed_list=self.confirmed_list,
            )
        )



class SeedNumbersBackupTestMistakeView(View):
    REVIEW = ButtonOption("Review seed numbers")
    RETRY = ButtonOption("Try again")

    def __init__(self, seed: Seed, bip85_data: dict = None, cur_index: int = None, wrong_number: str = None, confirmed_list: list = None):
        super().__init__()
        self.seed = seed
        self.bip85_data = bip85_data
        self.cur_index = cur_index
        self.wrong_number = wrong_number
        self.confirmed_list = confirmed_list


    def run(self):
        button_data = [self.REVIEW, self.RETRY]

        # TRANSLATOR_NOTE: Inserts the position and the number (e.g. "Seed Number #1 is not "0001"!")
        text = _("Seed Number #{} is not \"{}\"!").format(self.cur_index + 1, self.wrong_number)

        # TRANSLATOR_NOTE: User selected the wrong number during the seed numbers backup test
        status_headline = _("Wrong Number!")

        selected_menu_num = self.run_screen(
            DireWarningScreen,
            title=_("Verification Error"),
            show_back_button=False,
            status_icon_name=SeedSignerIconConstants.ERROR,
            status_headline=status_headline,
            button_data=button_data,
            text=text,
        )

        if button_data[selected_menu_num] == self.REVIEW:
            return Destination(
                SeedNumbersView,
                view_args=dict(seed=self.seed, bip85_data=self.bip85_data),
            )

        elif button_data[selected_menu_num] == self.RETRY:
            return Destination(
                SeedNumbersBackupTestView,
                view_args=dict(
                    seed=self.seed,
                    confirmed_list=self.confirmed_list,
                    cur_index=self.cur_index,
                    bip85_data=self.bip85_data,
                )
            )



class SeedNumbersBackupTestSuccessView(View):
    def __init__(self, seed: Seed):
        super().__init__()
        self.seed = seed

    def run(self):
        from seedsigner.gui.screens.screen import LargeIconStatusScreen
        self.run_screen(
            LargeIconStatusScreen,
            title=_("Backup Verified"),
            show_back_button=False,
            status_headline=_("Success!"),
            text=_("All seed numbers were successfully verified!"),
            button_data=[ButtonOption("OK")]
        )

        if self.seed is None:
            return Destination(SeedFinalizeView)
        else:
            from seedsigner.views.seed_views import SeedOptionsView
            return Destination(SeedOptionsView, view_args=dict(seed=self.seed), clear_history=True)
