
# Must import this before the Controller
from base import BaseTest, FlowTest, FlowStep

from seedsigner.views.view import Destination, MainMenuView
from seedsigner.views import seed_views, scan_views



class TestSeedFlows(FlowTest):

    def test_scan_seedqr_flow(self):
        """
            Selecting "Scan" from the MainMenuView and scanning a SeedQR should enter the
            Finalize Seed flow and end at the SeedOptionsView.
        """
        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("0000" * 11 + "0003")

        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    button_data_selection=MainMenuView.SCAN
                ),
                FlowStep(
                    expected_view=scan_views.ScanView,
                    run_before=load_seed_into_decoder,  # simulate read SeedQR
                    # ret value is ignored
                ),
                FlowStep(
                    expected_view=seed_views.SeedFinalizeView,
                    button_data_selection=seed_views.SeedFinalizeView.FINALIZE
                ),
            ]
        )
        assert destination.View_cls == seed_views.SeedOptionsView


    def test_mnemonic_entry_flow(self):
        """
            Manually entering a mnemonic should land at the Finalize Seed flow and end at
            the SeedOptionsView.
        """
        def test_with_mnemonic(mnemonic):
            sequence = [
                FlowStep(
                    button_data_selection=MainMenuView.SEEDS
                ),
                FlowStep(
                    expected_view=seed_views.SeedsMenuView,
                    # Nothing to return; auto-forwards to LoadSeedView
                ),
                FlowStep(
                    expected_view=seed_views.LoadSeedView,
                    button_data_selection=seed_views.LoadSeedView.TYPE_12WORD if len(mnemonic) == 12 else seed_views.LoadSeedView.TYPE_24WORD,
                ),
            ]

            # Now add each manual word entry step
            for word in mnemonic:
                sequence.append(
                    FlowStep(
                        expected_view=seed_views.SeedMnemonicEntryView,
                        screen_return_value=word
                    )
                )
            
            # With the mnemonic completely entered, we land on the SeedFinalizeView
            sequence.append(
                FlowStep(
                    expected_view=seed_views.SeedFinalizeView,
                    button_data_selection=seed_views.SeedFinalizeView.FINALIZE
                )
            )
            
            destination = self.run_sequence(
                Destination(MainMenuView),
                sequence=sequence
            )
            assert destination.View_cls == seed_views.SeedOptionsView

        # Test data from iancoleman.io; 12- and 24-word mnemonic
        test_with_mnemonic("tone flat shed cool census soul paddle boy flight fantasy stem social".split())

        BaseTest.reset_controller()

        test_with_mnemonic("cotton artefact spy mind wing there echo steak child oak awful host despair online bicycle divorce middle firm diamond rare execute chimney almost hollow".split())


    def test_invalid_mnemonic(self):
        """ Should be able to go back and edit or discard an invalid mnemonic """
        # Test data from iancoleman.io
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        sequence = [
            FlowStep(
                button_data_selection=seed_views.LoadSeedView.TYPE_12WORD if len(mnemonic) == 12 else seed_views.LoadSeedView.TYPE_24WORD,
            ),
        ]
        for word in mnemonic[:-1]:
            sequence.append(
                FlowStep(
                    expected_view=seed_views.SeedMnemonicEntryView,
                    screen_return_value=word
                )
            )

        sequence += [
            FlowStep(
                expected_view=seed_views.SeedMnemonicEntryView,
                screen_return_value="zoo"       # But finish with an INVALID checksum word
            ),
            FlowStep(
                expected_view=seed_views.SeedMnemonicInvalidView,
                button_data_selection=seed_views.SeedMnemonicInvalidView.EDIT
            ),
        ]

        # Restarts from first word
        for word in mnemonic[:-1]:
            sequence.append(
                FlowStep(
                    expected_view=seed_views.SeedMnemonicEntryView,
                    screen_return_value=word
                )
            )

        sequence += [
            FlowStep(
                expected_view=seed_views.SeedMnemonicEntryView,
                screen_return_value="zebra"     # provide yet another invalid checksum word
            ),
            FlowStep(
                expected_view=seed_views.SeedMnemonicInvalidView,
                button_data_selection=seed_views.SeedMnemonicInvalidView.DISCARD
            ),
        ]

        destination = self.run_sequence(
            Destination(seed_views.LoadSeedView),
            sequence
        )
        assert destination.View_cls == MainMenuView