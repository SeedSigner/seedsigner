"""Red-team regression tests for the SeedXOR rebuild flow.

Covers F1: resume_main_flow leaks that misrouted later normal seed loads
into the SeedXOR fingerprint view.
"""
from base import FlowTest, FlowStep
from seedsigner.models.settings import SettingsConstants
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.views.view import MainMenuView, ErrorView
from seedsigner.views import seed_views, scan_views
from seedsigner.views.seed_views import SeedsMenuView, SeedFinalizeView

from seedxor_test_vectors import EXAMPLE_12_A, EXAMPLE_12_B


def type_mnemonic(mnemonic: str):
    return [FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=w) for w in mnemonic.split()]


class TestResumeFlowLeak(FlowTest):
    def test_back_out_of_word0_then_normal_seed_load_not_misrouted(self):
        """Start SeedXOR typed entry, BACK out at word 0, back out to
        LoadSeedView, then type a normal seed -> must route to SeedFinalizeView,
        NOT RebuildSeedXORShowFingerprintView."""
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, is_redirect=True),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.REBUILD_SEED_XOR),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
            FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORLoadPartView),  # back-landing
        ]
        self.run_sequence(sequence)

        sequence = [
            FlowStep(seed_views.RebuildSeedXORLoadPartView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORManageView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_A)
        # Fixed behavior: normal seed load routes to SeedFinalizeView.
        sequence += [FlowStep(seed_views.SeedFinalizeView)]
        self.run_sequence(sequence)

    def test_scan_rejected_part_then_normal_seed_load_not_misrouted(self):
        """Scan a valid-but-rejected XOR part (duplicate). After the ErrorView,
        resume_main_flow must be cleared; a later normal seed load routes to
        SeedFinalizeView."""
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        # Load part 1 normally (typed)
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, is_redirect=True),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.REBUILD_SEED_XOR),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_A)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ]
        self.run_sequence(sequence)

        # Scan the SAME part again (duplicate -> rejected)
        def load_seed_qr(view: scan_views.ScanView):
            from seedsigner.models.seed import Seed
            wordlist = Seed.get_wordlist()
            indexes = [wordlist.index(word) for word in EXAMPLE_12_A.split()]
            numeric = "".join([str(i).zfill(4) for i in indexes])
            view.decoder.add_data(numeric)

        sequence = [
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.SCAN_PART),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_qr),
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(ErrorView, button_data_selection=0),   # duplicate part error
            FlowStep(seed_views.RebuildSeedXORLoadPartView),
        ]
        self.run_sequence(sequence)
        assert self.controller.resume_main_flow is None, "resume_main_flow must be cleared after validation error"

        # Back all the way out to LoadSeedView, then type a NORMAL new seed
        sequence = [
            FlowStep(seed_views.RebuildSeedXORLoadPartView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORManageView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_B)
        # Fixed behavior: normal seed load routes to SeedFinalizeView.
        sequence += [FlowStep(seed_views.SeedFinalizeView)]
        self.run_sequence(sequence)
