
# Must import this before the Controller
from base import FlowTest, FlowStep

from seedsigner.controller import Controller
from seedsigner.models.seed import Seed
from seedsigner.views.view import Destination, MainMenuView
from seedsigner.views import seed_views, scan_views



class TestToolsFlows(FlowTest):

    def test_addressexplorer_seedfinalizescreen_flow(self):
        """
            Finalizing a seed during the Address Explorer flow should return to the next
            Address Explorer step upon completion.
        """
        # Set up pending seed leading up to SeedFinalizeView
        controller = Controller.get_instance()
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        controller.storage.set_pending_seed(seed)

        # Set the Address Explorer flow to change routing behavior
        controller.resume_main_flow = Controller.FLOW__ADDRESS_EXPLORER

        # Finalize the new seed w/out passphrase
        destination = self.run_sequence(
            Destination(seed_views.SeedFinalizeView),
            sequence=[
                FlowStep(
                    screen_return_value=0,  # ret DONE
                ),
                FlowStep(
                    expected_view=seed_views.SeedOptionsView,
                    # should auto-route away w/out a selection
                ),
            ]
        )
        # Flow should resume at Script Type selection
        assert destination.View_cls == seed_views.SeedExportXpubScriptTypeView

        # Reset
        controller.storage.seeds.clear()
        controller.storage.set_pending_seed(seed)

        # Finalize the new seed w/passphrase
        destination = self.run_sequence(
            Destination(seed_views.SeedFinalizeView),
            sequence=[
                FlowStep(
                    screen_return_value=1,  # ret PASSPHRASE
                ),
                FlowStep(
                    expected_view=seed_views.SeedAddPassphraseView,
                    screen_return_value="mypassphrase",
                ),
                FlowStep(
                    expected_view=seed_views.SeedReviewPassphraseView,
                    screen_return_value=1,  # ret DONE
                ),
                FlowStep(
                    expected_view=seed_views.SeedOptionsView,
                    # SeedOptionsView should auto-route away
                ),
            ]
        )
        # Flow should resume at Script Type selection
        assert destination.View_cls == seed_views.SeedExportXpubScriptTypeView
