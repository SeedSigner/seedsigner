
# Must import this before the Controller
from typing import Type

from mock import MagicMock, Mock
from base import FlowTest, FlowStep

from seedsigner.controller import Controller
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
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
                    button_data_selection=MainMenuView.TOOLS
                ),
                FlowStep(
                    expected_view=tools_views.ToolsMenuView,
                    button_data_selection=tools_views.ToolsMenuView.EXPLORER
                ),
                FlowStep(
                    expected_view=tools_views.ToolsAddressExplorerSelectSourceView,
                    screen_return_value=0  # ret 1st onboard seed
                ),
                FlowStep(
                    expected_view=seed_views.SeedExportXpubScriptTypeView,
                    button_data_selection=SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__SCRIPT_TYPES).get_selection_option_display_name_by_value(SettingsConstants.NATIVE_SEGWIT)
                ),
                FlowStep(
                    expected_view=tools_views.ToolsAddressExplorerAddressTypeView,
                    button_data_selection=tools_views.ToolsAddressExplorerAddressTypeView.RECEIVE
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
                    button_data_selection=MainMenuView.TOOLS
                ),
                FlowStep(
                    expected_view=tools_views.ToolsMenuView,
                    button_data_selection=tools_views.ToolsMenuView.EXPLORER
                ),
                FlowStep(
                    expected_view=tools_views.ToolsAddressExplorerSelectSourceView,
                    button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED
                ),
                FlowStep(
                    expected_view=scan_views.ScanView,
                    run_before=load_seed_into_decoder,  # simulate read SeedQR
                ),
                FlowStep(
                    expected_view=seed_views.SeedFinalizeView,
                    button_data_selection=seed_views.SeedFinalizeView.FINALIZE
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
                    button_data_selection=seed_views.SeedFinalizeView.PASSPHRASE
                ),
                FlowStep(
                    expected_view=seed_views.SeedAddPassphraseView,
                    screen_return_value="mypassphrase",
                ),
                FlowStep(
                    expected_view=seed_views.SeedReviewPassphraseView,
                    button_data_selection=seed_views.SeedReviewPassphraseView.DONE
                ),
                FlowStep(
                    expected_view=seed_views.SeedOptionsView,
                    # SeedOptionsView should auto-route away
                ),
            ]
        )
        # Flow should resume at Script Type selection
        assert destination.View_cls == seed_views.SeedExportXpubScriptTypeView
