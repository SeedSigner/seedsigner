from base import FlowTest, FlowStep
from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants
from seedsigner.views.view import MainMenuView, ErrorView
from seedsigner.views import seed_views, scan_views
from seedsigner.views.seed_views import SeedsMenuView
from seedsigner.helpers.mnemonic_generation import combine_mnemonics_with_xor

from seedxor_test_vectors import EXAMPLE_24_A, EXAMPLE_24_B, EXAMPLE_24_C, EXAMPLE_12_A


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
