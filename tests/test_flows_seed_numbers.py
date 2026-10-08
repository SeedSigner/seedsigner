import random

import pytest

from base import FlowTest, FlowStep
from seedsigner.controller import Controller
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.helpers.index_bits import format_index1
from seedsigner.models.seed import Seed
from seedsigner.views.seed_views import (
    SeedBackupView,
    SeedFinalizeView,
    SeedIndexesBackupTestMistakeView,
    SeedIndexesBackupTestSuccessView,
    SeedIndexesBackupTestView,
    SeedIndexesView,
    SeedIndexesWarningView,
    SeedOptionsView,
    SeedWordsBackupTestPromptView,
    SeedsMenuView,
)
from seedsigner.views.tools_views import (
    ToolsMenuView,
    ToolsSeedIndexesEntryView,
    ToolsSeedIndexesInvalidView,
    ToolsSeedIndexesLoadView,
    ToolsSeedIndexesNumWordsView,
    ToolsSeedIndexesView,
)
from seedsigner.views.view import MainMenuView


# Do not use with real funds
MNEMONIC_12 = ("abandon " * 11 + "about").split()
BAD_MNEMONIC_12 = ("abandon " * 12).split()
MNEMONIC_24 = ("abandon " * 23 + "art").split()
BAD_MNEMONIC_24 = ("abandon " * 24).split()


def _load_seed(controller: Controller, mnemonic: list[str]) -> Seed:
    seed = Seed(mnemonic=mnemonic)
    controller.storage.set_pending_seed(seed)
    controller.storage.finalize_pending_seed()
    return seed


def _entry_steps(mnemonic: list[str]) -> list[FlowStep]:
    """Entry screen returns the BIP-39 word, not the raw index."""
    return [
        FlowStep(ToolsSeedIndexesEntryView, screen_return_value=word)
        for word in mnemonic
    ]


def _backup_to_first_index() -> list[FlowStep]:
    return [
        FlowStep(SeedOptionsView, button_data_selection=SeedOptionsView.BACKUP),
        FlowStep(SeedBackupView, button_data_selection=SeedBackupView.VIEW_INDEXES),
        FlowStep(SeedIndexesWarningView, screen_return_value=0),
        FlowStep(SeedIndexesView),
    ]


def _backup_walk_to_prompt(mnemonic: list[str]) -> list[FlowStep]:
    steps = _backup_to_first_index()[:-1]
    for _ in range(len(mnemonic) - 1):
        steps.append(FlowStep(SeedIndexesView, button_data_selection=SeedIndexesView.NEXT))
    steps.append(FlowStep(SeedIndexesView, button_data_selection=SeedIndexesView.DONE))
    return steps


QUIZ_RAND_SEED = 42


def _pin_quiz_word(word_index: int):
    """Fix which mnemonic word is quizzed and how the 4 options are shuffled."""
    def _before_run(view):
        view.rand_seed = QUIZ_RAND_SEED
        view.cur_index = word_index
    return _before_run


def _quiz_option_index(mnemonic: list[str], word_index: int, pick_correct: bool) -> int:
    """Replay SeedIndexesBackupTestView RNG so screen_return_value hits the right button."""
    seed = Seed(mnemonic=mnemonic)
    random.seed(QUIZ_RAND_SEED + word_index)
    real_index1 = seed.wordlist.index(mnemonic[word_index]) + 1
    real_label = f"#{format_index1(real_index1)}"
    decoys = set()
    while len(decoys) < 3:
        candidate = int(random.random() * 2048) + 1
        if candidate != real_index1:
            decoys.add(candidate)
    labels = [real_label] + [f"#{format_index1(i)}" for i in decoys]
    random.shuffle(labels)
    if pick_correct:
        return labels.index(real_label)
    return next(i for i, label in enumerate(labels) if label != real_label)


def _quiz_to_prompt(mnemonic: list[str]) -> list[FlowStep]:
    steps = _backup_walk_to_prompt(mnemonic)
    steps.append(FlowStep(
        SeedWordsBackupTestPromptView,
        button_data_selection=SeedWordsBackupTestPromptView.VERIFY,
    ))
    return steps


class TestSeedIndexesNav(FlowTest):
    def test_tools_menu_opens_indexes(self):
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(ToolsMenuView, button_data_selection=ToolsMenuView.WORD_INDEX),
            FlowStep(ToolsSeedIndexesView),
        ])

    def test_tools_indexes_back(self):
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(ToolsMenuView, button_data_selection=ToolsMenuView.WORD_INDEX),
            FlowStep(ToolsSeedIndexesView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(ToolsMenuView),
        ])

    @pytest.mark.parametrize("fmt", ["NUMBERS", "BINARY"])
    def test_tools_indexes_picks_format(self, fmt):
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(ToolsMenuView, button_data_selection=ToolsMenuView.WORD_INDEX),
            FlowStep(ToolsSeedIndexesView, button_data_selection=getattr(ToolsSeedIndexesView, fmt)),
            FlowStep(ToolsSeedIndexesNumWordsView),
        ])


class TestSeedIndexesLoad(FlowTest):
    """Tools → Indexes → Numbers|Binary → 12|24 → each word → Load seed."""

    @pytest.mark.parametrize("fmt,length_opt,mnemonic", [
        ("NUMBERS", "TWELVE", MNEMONIC_12),
        ("BINARY", "TWELVE", MNEMONIC_12),
        ("NUMBERS", "TWENTY_FOUR", MNEMONIC_24),
        ("BINARY", "TWENTY_FOUR", MNEMONIC_24),
    ])
    def test_load_seed_by_indexes(self, fmt, length_opt, mnemonic):
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(ToolsMenuView, button_data_selection=ToolsMenuView.WORD_INDEX),
            FlowStep(ToolsSeedIndexesView, button_data_selection=getattr(ToolsSeedIndexesView, fmt)),
            FlowStep(ToolsSeedIndexesNumWordsView, button_data_selection=getattr(ToolsSeedIndexesNumWordsView, length_opt)),
        ]
        sequence.extend(_entry_steps(mnemonic))
        sequence.append(FlowStep(ToolsSeedIndexesLoadView, button_data_selection=ToolsSeedIndexesLoadView.LOAD))
        sequence.append(FlowStep(SeedFinalizeView))

        self.run_sequence(sequence)

        pending = self.controller.storage.get_pending_seed()
        assert pending.mnemonic_list == mnemonic

    @pytest.mark.parametrize("fmt,length_opt,mnemonic", [
        ("NUMBERS", "TWELVE", BAD_MNEMONIC_12),
        ("BINARY", "TWELVE", BAD_MNEMONIC_12),
        ("NUMBERS", "TWENTY_FOUR", BAD_MNEMONIC_24),
        ("BINARY", "TWENTY_FOUR", BAD_MNEMONIC_24),
    ])
    def test_invalid_checksum_goes_to_invalid_view(self, fmt, length_opt, mnemonic):
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(ToolsMenuView, button_data_selection=ToolsMenuView.WORD_INDEX),
            FlowStep(ToolsSeedIndexesView, button_data_selection=getattr(ToolsSeedIndexesView, fmt)),
            FlowStep(ToolsSeedIndexesNumWordsView, button_data_selection=getattr(ToolsSeedIndexesNumWordsView, length_opt)),
        ]
        sequence.extend(_entry_steps(mnemonic))
        sequence.append(FlowStep(ToolsSeedIndexesInvalidView))
        self.run_sequence(sequence)

    def test_entry_back_on_first_word(self):
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(ToolsMenuView, button_data_selection=ToolsMenuView.WORD_INDEX),
            FlowStep(ToolsSeedIndexesView, button_data_selection=ToolsSeedIndexesView.NUMBERS),
            FlowStep(ToolsSeedIndexesNumWordsView, button_data_selection=ToolsSeedIndexesNumWordsView.TWELVE),
            FlowStep(ToolsSeedIndexesEntryView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(ToolsSeedIndexesNumWordsView),
        ])


class TestSeedIndexesBackup(FlowTest):
    """Loaded 12/24-word seed → Backup → Seed Word Indexes."""

    @pytest.mark.parametrize("mnemonic", [MNEMONIC_12, MNEMONIC_24])
    def test_backup_opens_first_index(self, mnemonic):
        seed = _load_seed(self.controller, mnemonic)
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=_backup_to_first_index(),
        )

    @pytest.mark.parametrize("mnemonic", [MNEMONIC_12, MNEMONIC_24])
    def test_backup_walks_all_words(self, mnemonic):
        seed = _load_seed(self.controller, mnemonic)
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=_backup_walk_to_prompt(mnemonic),
        )

    def test_from_seeds_menu(self):
        _load_seed(self.controller, MNEMONIC_12)
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, screen_return_value=0),
            FlowStep(SeedOptionsView, button_data_selection=SeedOptionsView.BACKUP),
            FlowStep(SeedBackupView, button_data_selection=SeedBackupView.VIEW_INDEXES),
            FlowStep(SeedIndexesWarningView, screen_return_value=0),
            FlowStep(SeedIndexesView),
        ])

    @pytest.mark.parametrize("mnemonic", [MNEMONIC_12, MNEMONIC_24])
    def test_backup_done_opens_verify_prompt(self, mnemonic):
        seed = _load_seed(self.controller, mnemonic)
        steps = _backup_walk_to_prompt(mnemonic)
        steps.append(FlowStep(SeedWordsBackupTestPromptView))
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=steps,
        )

    @pytest.mark.parametrize("mnemonic", [MNEMONIC_12, MNEMONIC_24])
    def test_backup_prompt_skip_returns_to_seed_options(self, mnemonic):
        seed = _load_seed(self.controller, mnemonic)
        steps = _backup_walk_to_prompt(mnemonic)
        steps.append(FlowStep(
            SeedWordsBackupTestPromptView,
            button_data_selection=SeedWordsBackupTestPromptView.SKIP,
        ))
        steps.append(FlowStep(SeedOptionsView))
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=steps,
        )

    @pytest.mark.parametrize("mnemonic", [MNEMONIC_12, MNEMONIC_24])
    def test_backup_prompt_verify_opens_index_quiz(self, mnemonic):
        seed = _load_seed(self.controller, mnemonic)
        steps = _quiz_to_prompt(mnemonic)
        steps.append(FlowStep(SeedIndexesBackupTestView))
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=steps,
        )

    @pytest.mark.parametrize("mnemonic", [MNEMONIC_12, MNEMONIC_24])
    def test_quiz_wrong_answer_opens_mistake(self, mnemonic):
        seed = _load_seed(self.controller, mnemonic)
        steps = _quiz_to_prompt(mnemonic)
        steps.append(FlowStep(
            SeedIndexesBackupTestView,
            before_run=_pin_quiz_word(0),
            screen_return_value=_quiz_option_index(mnemonic, 0, pick_correct=False),
        ))
        steps.append(FlowStep(SeedIndexesBackupTestMistakeView))
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=steps,
        )

    def test_quiz_mistake_review_returns_to_indexes(self):
        mnemonic = MNEMONIC_12
        seed = _load_seed(self.controller, mnemonic)
        steps = _quiz_to_prompt(mnemonic)
        steps.append(FlowStep(
            SeedIndexesBackupTestView,
            before_run=_pin_quiz_word(0),
            screen_return_value=_quiz_option_index(mnemonic, 0, pick_correct=False),
        ))
        steps.append(FlowStep(
            SeedIndexesBackupTestMistakeView,
            button_data_selection=SeedIndexesBackupTestMistakeView.REVIEW,
        ))
        steps.append(FlowStep(SeedIndexesView))
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=steps,
        )

    def test_quiz_mistake_retry_returns_to_quiz(self):
        mnemonic = MNEMONIC_12
        seed = _load_seed(self.controller, mnemonic)
        steps = _quiz_to_prompt(mnemonic)
        steps.append(FlowStep(
            SeedIndexesBackupTestView,
            before_run=_pin_quiz_word(0),
            screen_return_value=_quiz_option_index(mnemonic, 0, pick_correct=False),
        ))
        steps.append(FlowStep(
            SeedIndexesBackupTestMistakeView,
            button_data_selection=SeedIndexesBackupTestMistakeView.RETRY,
        ))
        steps.append(FlowStep(SeedIndexesBackupTestView))
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=steps,
        )

    @pytest.mark.parametrize("mnemonic", [MNEMONIC_12, MNEMONIC_24])
    def test_quiz_all_correct_reaches_success(self, mnemonic):
        seed = _load_seed(self.controller, mnemonic)
        steps = _quiz_to_prompt(mnemonic)
        for word_index in range(len(mnemonic)):
            steps.append(FlowStep(
                SeedIndexesBackupTestView,
                before_run=_pin_quiz_word(word_index),
                screen_return_value=_quiz_option_index(mnemonic, word_index, pick_correct=True),
            ))
        steps.append(FlowStep(SeedIndexesBackupTestSuccessView))
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=steps,
        )

    def test_quiz_success_ok_returns_to_seed_options(self):
        mnemonic = MNEMONIC_12
        seed = _load_seed(self.controller, mnemonic)
        steps = _quiz_to_prompt(mnemonic)
        for word_index in range(len(mnemonic)):
            steps.append(FlowStep(
                SeedIndexesBackupTestView,
                before_run=_pin_quiz_word(word_index),
                screen_return_value=_quiz_option_index(mnemonic, word_index, pick_correct=True),
            ))
        steps.append(FlowStep(SeedIndexesBackupTestSuccessView, screen_return_value=0))
        steps.append(FlowStep(SeedOptionsView))
        self.run_sequence(
            initial_destination_view_args=dict(seed=seed),
            sequence=steps,
        )
