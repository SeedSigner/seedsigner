from base import FlowTest, FlowStep
from seedsigner.views.view import MainMenuView, BackStackView
from seedsigner.views import scan_views, tools_views, seed_views
from seedsigner.models.settings import SettingsConstants
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.controller import Controller
from seedsigner.models.seed import Seed
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.gui.components import SeedSignerIconConstants

class TestIssue775(FlowTest):
    def test_scan_view_cancellation_returns_to_back_stack(self):
        """
        Scenario 1: Simple Tool Flow (Address Explorer)
        Cancelling a scan should return to the previous screen (ToolsMenuView).
        """
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            # Simulate the user cancelling the scan (ScanScreen returns False on KEY_LEFT/RIGHT)
            FlowStep(scan_views.ScanAddressView, screen_return_value=False),
            # We expect to go back to the previous screen (ToolsMenuView)
            FlowStep(tools_views.ToolsMenuView),
        ])

    def test_scan_view_cancellation_clears_flow_state(self):
        """
        Scenario 2: State-Dependent Flow (Sign Message)
        Cancelling the scan must CLEAR the 'resume_main_flow' state.
        If it doesn't, returning to SeedOptionsView will cause it to infinite-loop 
        forward into the next step with missing data, causing a crash.
        """
        # Enable message signing
        self.settings.set_value(SettingsConstants.SETTING__MESSAGE_SIGNING, SettingsConstants.OPTION__ENABLED)
        
        # Load a dummy seed so we can access SeedOptions
        seed = Seed(mnemonic=["abandon"]*11 + ["about"])
        self.controller.storage.seeds.append(seed)
        seed_num = 0
        fingerprint = seed.get_fingerprint()

        self.run_sequence(
            sequence=[
                # 1. Start at Main Menu
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                
                # 2. Select the first seed (SeedsMenuView)
                FlowStep(seed_views.SeedsMenuView, button_data_selection=ButtonOption(fingerprint, SeedSignerIconConstants.FINGERPRINT)),
                
                # 3. In SeedOptions, select "Sign Message"
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.SIGN_MESSAGE),
                
                # 4. This enters ScanView. We simulate a cancel (False return).
                # Crucially, BEFORE we leave this view, the Controller's flow state must be cleared.
                FlowStep(scan_views.ScanView, screen_return_value=False),
                
                # 5. We should land back at SeedOptionsView.
                # If flow state wasn't cleared, this view would try to auto-forward us 
                # to the next step (SeedSignMessageConfirmMessageView), failing the test.
                FlowStep(seed_views.SeedOptionsView),
            ]
        )
        
        # Verify the flow state was actually cleared
        assert self.controller.resume_main_flow is None
