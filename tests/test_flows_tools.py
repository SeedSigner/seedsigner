
# Must import this before the Controller
from typing import Type

from mock import MagicMock
from base import FlowTest, FlowStep

from seedsigner.controller import Controller
from seedsigner.models.seed import Seed
from seedsigner.views.view import Destination, MainMenuView, View
from seedsigner.views import scan_views, seed_views, tools_views



class TestToolsFlows(FlowTest):

    def test_addressexplorer_flow(self):
        """
            Test the simplest AddressExplorer flow when a seed is already loaded.
        """
        controller = Controller.get_instance()
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        controller.storage.set_pending_seed(seed)
        controller.storage.finalize_pending_seed()

        def mock_addrlistview_screen(view: Type[View]):
            # ToolsAddressExplorerAddressListView reaches into its `self.screen` so we need to mock it out
            view.screen = MagicMock()

        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    screen_return_value=2  # ret TOOLS
                ),
                FlowStep(
                    expected_view=tools_views.ToolsMenuView,
                    screen_return_value=3  # ret EXPLORER
                ),
                FlowStep(
                    expected_view=tools_views.ToolsAddressExplorerSelectSourceView,
                    screen_return_value=0  # ret 1st onboard seed
                ),
                FlowStep(
                    expected_view=seed_views.SeedExportXpubScriptTypeView,
                    screen_return_value=0  # ret NATIVE_SEGWIT (1st script type option)
                ),
                FlowStep(
                    expected_view=tools_views.ToolsAddressExplorerAddressTypeView,
                    screen_return_value=0  # ret RECEIVE addrs
                ),
                FlowStep(
                    expected_view=tools_views.ToolsAddressExplorerAddressListView,
                    screen_return_value=10  # ret NEXT page of addrs
                ),
                FlowStep(
                    expected_view=tools_views.ToolsAddressExplorerAddressListView,
                    run_before=mock_addrlistview_screen,
                    screen_return_value=4  # ret a specific addr from the list
                ),
                FlowStep(
                    expected_view=tools_views.ToolsAddressExplorerAddressView,
                    # QRDisplayScreen runs until dismissed; no ret value
                ),
            ]
        )
        # After dismissing QRDisplayScreen, should return to the addr list view
        assert destination.View_cls == tools_views.ToolsAddressExplorerAddressListView


    def test_addressexplorer_loadseed_sideflow(self):
        """
            Finalizing a seed during the Address Explorer flow should return to the next
            Address Explorer step upon completion.
        """
        controller = Controller.get_instance()

        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("0000" * 11 + "0003")

        # Finalize the new seed w/out passphrase
        destination = self.run_sequence(
            Destination(MainMenuView),
            sequence=[
                FlowStep(
                    screen_return_value=2  # ret TOOLS
                ),
                FlowStep(
                    expected_view=tools_views.ToolsMenuView,
                    screen_return_value=3  # ret EXPLORER
                ),
                FlowStep(
                    expected_view=tools_views.ToolsAddressExplorerSelectSourceView,
                    screen_return_value=0  # ret SCAN SeedQR
                ),
                FlowStep(
                    expected_view=scan_views.ScanView,
                    run_before=load_seed_into_decoder,  # simulate read SeedQR
                    screen_return_value=None,
                ),
                FlowStep(
                    expected_view=seed_views.SeedFinalizeView,
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
        assert controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER

        # Reset
        controller.storage.seeds.clear()
        controller.storage.set_pending_seed(Seed(mnemonic=["abandon "* 11 + "about"]))

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
