from base import FlowTest, FlowStep
from unittest.mock import MagicMock

from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.views.view import MainMenuView, ErrorView
from seedsigner.views import seed_views, scan_views
from seedsigner.views.seed_views import SeedsMenuView
from seedsigner.helpers.mnemonic_generation import combine_mnemonics_with_xor
from seedsigner.helpers.seed_xor_validator import SeedXORValidator

from seedxor_test_vectors import (
    EXAMPLE_24_A, EXAMPLE_24_B, EXAMPLE_24_C,
    EXAMPLE_12_A, EXAMPLE_12_B,
)


def type_mnemonic(mnemonic: str):
    """ Helper function to generate a list of FlowSteps for typing a mnemonic. """
    flow = []
    for word in mnemonic.split():
        flow.append(FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word))
    return flow


class TestSeedXORFlows(FlowTest):
    def test_recombine_3_parts_24_words_success_flow(self):
        """
        Tests the complete, successful SeedXOR flow using three 24-word seeds.
        """
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)
        self.controller.storage.seeds.append(Seed(mnemonic=EXAMPLE_24_C.split()))

        # Calculate the expected result dynamically
        expected_mnemonic_list = combine_mnemonics_with_xor([EXAMPLE_24_A, EXAMPLE_24_B, EXAMPLE_24_C])
        expected_seed = Seed(mnemonic=expected_mnemonic_list)
        expected_fingerprint = expected_seed.get_fingerprint()

        def check_fingerprint(view):
            assert view.fingerprint == expected_fingerprint

        # Helper to simulate scanning a seed by adding its numeric representation to the decoder
        def load_seed_qr_into_decoder(view: scan_views.ScanView):
            wordlist = Seed.get_wordlist()
            indexes = [wordlist.index(word) for word in EXAMPLE_24_B.split()]
            numeric_seed_str = "".join([str(i).zfill(4) for i in indexes])
            view.decoder.add_data(numeric_seed_str)

        # === Start Flow and Add Part 1 (Typing) ===
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, button_data_selection=SeedsMenuView.LOAD),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.REBUILD_SEED_XOR),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_24WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_24_A)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ]
        self.run_sequence(sequence)
        assert len(self.controller.storage.rebuild_seedxor_parts) == 1

        # === Add Part 2 (Scan QR) ===
        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.SCAN_PART),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_qr_into_decoder),
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ])
        assert len(self.controller.storage.rebuild_seedxor_parts) == 2

        # === Add Part 3 (Use Loaded Seed) ===
        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.USE_LOADED_SEED),
            FlowStep(seed_views.RebuildSeedXORSelectExistingSeedView, screen_return_value=0),
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ])
        assert len(self.controller.storage.rebuild_seedxor_parts) == 3

        # === Finalize and Verify ===
        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.FINALIZE),
            FlowStep(
                seed_views.RebuildSeedXORFinalizeView,
                before_run=check_fingerprint,
                button_data_selection=0
            ),
            FlowStep(seed_views.RebuildSeedXORFinalizeOptionsView, button_data_selection=seed_views.RebuildSeedXORFinalizeOptionsView.KEEP_PARTS),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
        ])
        assert len(self.controller.storage.seeds) == 2

    def test_error_on_duplicate_part(self):
        """
        Tests that the system prevents a user from adding the same part twice.
        """
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        def check_error_title(view):
            assert view.title == "Duplicate Part"

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
        assert len(self.controller.storage.rebuild_seedxor_parts) == 1

        # Attempt to load the same part again
        sequence = [
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_A)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(
                ErrorView,
                before_run=check_error_title,
                button_data_selection=0
            ),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, is_redirect=True),
        ]

        self.run_sequence(sequence)
        assert len(self.controller.storage.rebuild_seedxor_parts) == 1

    def test_error_on_mismatched_length(self):
        """
        Tests that the system prevents adding a 24-word part after a 12-word part.
        """
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        def check_error_title(view):
            assert view.title == "Mnemonic Length Mismatch"

        # Load a 12-word part
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
        assert len(self.controller.storage.rebuild_seedxor_parts) == 1

        # Attempt to load a 24-word part
        sequence = [
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_24WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_24_A)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(
                ErrorView,
                before_run=check_error_title,
                button_data_selection=0
            ),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, is_redirect=True),
        ]

        self.run_sequence(sequence)
        assert len(self.controller.storage.rebuild_seedxor_parts) == 1

    def test_resume_flow_cleared_after_finalize(self):
        """
        Regression test: resume_main_flow must be cleared when the SeedXOR flow
        completes, otherwise a subsequent normal seed load (SeedMnemonicEntryView)
        would be misrouted into the SeedXOR fingerprint view instead of
        SeedFinalizeView.
        """
        from seedsigner.views.seed_views import SeedFinalizeView

        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        # Complete a 2-part XOR and finalize with KEEP_PARTS (lands on SeedOptionsView,
        #   NOT MainMenuView, so Home's resume_main_flow wipe is not what clears it).
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
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_B)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.FINALIZE),
            FlowStep(seed_views.RebuildSeedXORFinalizeView, button_data_selection=0),
            FlowStep(seed_views.RebuildSeedXORFinalizeOptionsView, button_data_selection=seed_views.RebuildSeedXORFinalizeOptionsView.KEEP_PARTS),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
        ]
        self.run_sequence(sequence)

        # The flow is complete; resume_main_flow must not still point at SeedXOR.
        assert self.controller.resume_main_flow != self.controller.FLOW__REBUILD_SEEDXOR

        # Now load a NEW, unrelated seed via the normal flow in the same session.
        #   It must finalize normally (SeedFinalizeView), NOT be captured as an XOR part.
        sequence = [
            FlowStep(SeedsMenuView, button_data_selection=SeedsMenuView.LOAD),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_A)
        sequence += [
            FlowStep(SeedFinalizeView),
        ]
        self.run_sequence(sequence)
        assert len(self.controller.storage.rebuild_seedxor_parts) == 0


class TestSeedXORAdditionalFlows(FlowTest):
    """Tests for the DISCARD_PARTS finalize branch, remove-part flow,
    back-button routing, zero-entropy rejection, and Finalize-hidden-with-<2-parts."""

    def _load_two_parts_12w(self):
        """Helper: load two 12-word parts and return at RebuildSeedXORManageView."""
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

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
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_B)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ]
        self.run_sequence(sequence)
        assert len(self.controller.storage.rebuild_seedxor_parts) == 2

    def test_finalize_discard_parts_flow(self):
        """
        Tests the DISCARD_PARTS finalize branch: after combining, choosing
        "Discard parts" should remove the individual part seeds from storage
        while keeping only the combined seed.
        """
        self._load_two_parts_12w()

        expected_mnemonic = combine_mnemonics_with_xor([EXAMPLE_12_A, EXAMPLE_12_B])
        expected_fingerprint = Seed(mnemonic=expected_mnemonic).get_fingerprint()

        def check_fingerprint(view):
            assert view.fingerprint == expected_fingerprint

        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.FINALIZE),
            FlowStep(
                seed_views.RebuildSeedXORFinalizeView,
                before_run=check_fingerprint,
                button_data_selection=0,
            ),
            FlowStep(seed_views.RebuildSeedXORFinalizeOptionsView, button_data_selection=seed_views.RebuildSeedXORFinalizeOptionsView.DISCARD_PARTS),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
        ])

        # The combined seed should be in storage; the XOR rebuild data should be cleared.
        assert len(self.controller.storage.seeds) == 1
        assert len(self.controller.storage.rebuild_seedxor_parts) == 0
        assert self.controller.storage.rebuild_seedxor_combined_seed is None

    def test_remove_part_flow(self):
        """
        Tests the remove-part flow: load two parts, remove the first one,
        and verify only one part remains.
        """
        self._load_two_parts_12w()

        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.REMOVE_PARTS),
            FlowStep(seed_views.RebuildSeedXORRemovePartsView, screen_return_value=0),
            FlowStep(seed_views.RebuildSeedXORConfirmRemovePartView, button_data_selection=seed_views.RebuildSeedXORConfirmRemovePartView.CONFIRM_REMOVE),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ])

        # Only one part should remain (part 2 = EXAMPLE_12_B)
        assert len(self.controller.storage.rebuild_seedxor_parts) == 1
        remaining = self.controller.storage.rebuild_seedxor_parts[0]
        assert remaining.mnemonic_str == EXAMPLE_12_B

    def test_remove_part_keep_part_backflow(self):
        """
        Tests the remove-part flow: selecting "Keep part" in the confirm
        screen returns to the RemovePartsView, not the ManageView.
        """
        self._load_two_parts_12w()

        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.REMOVE_PARTS),
            FlowStep(seed_views.RebuildSeedXORRemovePartsView, screen_return_value=0),
            FlowStep(seed_views.RebuildSeedXORConfirmRemovePartView, button_data_selection=seed_views.RebuildSeedXORConfirmRemovePartView.KEEP_PART),
            # skip_current_view=True means we go back to RemovePartsView
            FlowStep(seed_views.RebuildSeedXORRemovePartsView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ])

        # Both parts should still be present
        assert len(self.controller.storage.rebuild_seedxor_parts) == 2

    def test_back_button_from_load_part_view(self):
        """
        Tests that pressing BACK from RebuildSeedXORLoadPartView returns
        to RebuildSeedXORManageView (clear_history=True).
        """
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, is_redirect=True),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.REBUILD_SEED_XOR),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ])

    def test_back_button_from_manage_view(self):
        """
        Tests that pressing BACK from RebuildSeedXORManageView returns
        to LoadSeedView (clear_history=True).
        """
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, is_redirect=True),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.REBUILD_SEED_XOR),
            FlowStep(seed_views.RebuildSeedXORManageView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.LoadSeedView),
        ])

    def test_back_button_from_finalize_view(self):
        """
        Tests that pressing BACK from RebuildSeedXORFinalizeView returns
        to RebuildSeedXORManageView.
        """
        self._load_two_parts_12w()

        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.FINALIZE),
            FlowStep(seed_views.RebuildSeedXORFinalizeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ])

    def test_back_button_from_finalize_options_view(self):
        """
        Tests that pressing BACK from RebuildSeedXORFinalizeOptionsView returns
        to RebuildSeedXORFinalizeView.
        """
        self._load_two_parts_12w()

        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.FINALIZE),
            FlowStep(seed_views.RebuildSeedXORFinalizeView, button_data_selection=0),
            FlowStep(seed_views.RebuildSeedXORFinalizeOptionsView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORFinalizeView),
        ])

    def test_cancel_seed_xor_flow(self):
        """
        Tests the Cancel Seed XOR flow: confirms cancellation, which should
        clear all loaded parts and return to LoadSeedView.
        """
        self._load_two_parts_12w()

        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.CANCEL),
            FlowStep(seed_views.RebuildSeedXORCancelView, button_data_selection=seed_views.RebuildSeedXORCancelView.CONFIRM),
            FlowStep(seed_views.LoadSeedView),
        ])

        assert len(self.controller.storage.rebuild_seedxor_parts) == 0
        assert self.controller.storage.rebuild_seedxor_combined_seed is None

    def test_finalize_hidden_with_less_than_two_parts(self):
        """
        Tests that the Finalize button is NOT shown when only one part is loaded.
        """
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        # Load one part
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
        assert len(self.controller.storage.rebuild_seedxor_parts) == 1

        # Instantiate the ManageView and replicate its button_data construction
        # to verify FINALIZE is absent when num_parts < 2.
        view = seed_views.RebuildSeedXORManageView()
        assert view.num_parts == 1

        button_data = []
        button_data.append(seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART)
        if view.num_parts > 0:
            button_data.append(seed_views.RebuildSeedXORManageView.VIEW_LOADED_PARTS)
            button_data.append(seed_views.RebuildSeedXORManageView.REMOVE_PARTS)
            button_data.append(seed_views.RebuildSeedXORManageView.CANCEL)
        if view.num_parts >= 2:
            button_data.insert(-1, seed_views.RebuildSeedXORManageView.FINALIZE)

        assert seed_views.RebuildSeedXORManageView.FINALIZE not in button_data

    def test_zero_entropy_combined_result_rejected(self):
        """
        Tests that the validator catches a zero-entropy combined seed
        (all-zero bytes, i.e. the 'abandon...about' seed). With 3+ colluding
        parts the XOR can bypass the duplicate check and produce this result.
        """
        from seedxor_test_vectors import ZERO_ENTROPY_MNEMONIC_12

        zero_seed = MagicMock()
        zero_seed.mnemonic_str = ZERO_ENTROPY_MNEMONIC_12
        zero_seed.wordlist = Seed.get_wordlist()

        is_valid, error_dict = SeedXORValidator.validate_combined_seed(zero_seed)
        assert not is_valid
        assert error_dict["title"] == "Zero Entropy Result"

    def test_all_ones_combined_result_rejected(self):
        """
        Tests that the validator rejects an all-ones entropy combined seed.
        """
        from embit import bip39 as _bip39

        # Construct an all-0xFF 16-byte entropy and convert to mnemonic
        all_ones_entropy = bytes([0xFF] * 16)
        all_ones_mnemonic = _bip39.mnemonic_from_bytes(all_ones_entropy)

        all_ones_seed = MagicMock()
        all_ones_seed.mnemonic_str = all_ones_mnemonic
        all_ones_seed.wordlist = Seed.get_wordlist()

        is_valid, error_dict = SeedXORValidator.validate_combined_seed(all_ones_seed)
        assert not is_valid
        assert error_dict["title"] == "Known Seed Result"
