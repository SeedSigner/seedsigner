# Must import test base before the Controller
from base import FlowTest, FlowStep

from seedsigner.controller import Controller
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views.view import ErrorView, MainMenuView
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

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, screen_return_value=0),  # ret 1st onboard seed
            FlowStep(seed_views.SeedExportXpubScriptTypeView, button_data_selection=SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__SCRIPT_TYPES).get_selection_option_display_name_by_value(SettingsConstants.NATIVE_SEGWIT)),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, button_data_selection=tools_views.ToolsAddressExplorerAddressTypeView.RECEIVE),
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=10),  # ret NEXT page of addrs
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=4),  # ret a specific addr from the list
            FlowStep(tools_views.ToolsAddressExplorerAddressView),  # runs until dismissed; no ret value
            FlowStep(tools_views.ToolsAddressExplorerAddressListView),
        ])


    def test_addressexplorer_loadseed_sideflow(self):
        """
            Finalizing a seed during the Address Explorer flow should return to the next
            Address Explorer step upon completion.
        """
        controller = Controller.get_instance()

        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("0000" * 11 + "0003")

        # Finalize the new seed w/out passphrase
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),  # simulate read SeedQR
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedExportXpubScriptTypeView),
        ])

        assert controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER

        # Reset
        controller.storage.seeds.clear()
        controller.storage.set_pending_seed(Seed(mnemonic=["abandon "* 11 + "about"]))

        # Finalize the new seed w/passphrase
        self.run_sequence(
            sequence=[
                FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.PASSPHRASE),
                FlowStep(seed_views.SeedAddPassphraseView, screen_return_value="mypassphrase"),
                FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.DONE),
                FlowStep(seed_views.SeedOptionsView, is_redirect=True),
                FlowStep(seed_views.SeedExportXpubScriptTypeView),
            ]
        )


    def test_addressexplorer_scan_wrong_qrtype(self):
        """
        Scanning the wrong type of QR code when a SeedQR is expected should route to ErrorView
        """
        def load_wrong_data_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")

        # Finalize the new seed w/out passphrase
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_wrong_data_into_decoder),  # simulate scanning the wrong QR type
            FlowStep(ErrorView),
        ])


    def test_addressexplorer_back_button(self):
        """
        Backing out of AddressExplorer behavior depends on current Settings:
        * Multiple script types enabled: BACK to SeedExportXpubScriptTypeView
        * One script type enabled: BACK to where we started:
            * SeedOptions
            * ToolsAddressExplorerSelectSourceView if seed was already onboard
            * MainMenu if no seed was onboard when we entered via ToolsMenu (loading a
                seed during the flow wipes out any history before the load so our only
                option is to return to MainMenu).
        """
        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("0000" * 11 + "0003")

        controller = Controller.get_instance()
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        controller.storage.set_pending_seed(seed)
        controller.storage.finalize_pending_seed()

        # Scenario 1: Seed already onboard, multiple script types enabled, BACK can still
        #  change script type selection.
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [SettingsConstants.NATIVE_SEGWIT, SettingsConstants.TAPROOT])
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, screen_return_value=0),  # select the first onboard seed
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPLORER),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, screen_return_value=0),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.SeedExportXpubScriptTypeView),
        ])

        # Scenario 2: Seed already onboard, one script type enabled, started from 
        # SeedOptionsView, BACK to SeedOptionsView.
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [SettingsConstants.NATIVE_SEGWIT])
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, screen_return_value=0),  # select the first onboard seed
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPLORER),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.SeedOptionsView),
        ])

        # Scenario 3: Seed already onboard, one script type enabled, started from
        # ToolsMenu, BACK to ToolsAddressExplorerSelectSourceView.
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, screen_return_value=0),  # select the first onboard seed
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView),
        ])

        # Scenario 4: No seed onboard, one script type enabled, started from Tools, BACK
        # can only go to MainMenu because of mid-flow seed load.
        controller.discard_seed(0)
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),  # simulate read SeedQR
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(MainMenuView),
        ])