import sys
from unittest.mock import MagicMock

# Mock hardware dependencies
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['spidev'] = MagicMock()

from base import FlowTest, FlowStep
from seedsigner.views.view import MainMenuView
from seedsigner.views import scan_views, tools_views, seed_views
from seedsigner.models.settings import SettingsConstants
from seedsigner.models.seed import Seed
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.gui.components import SeedSignerIconConstants

class TestIssue775(FlowTest):
    def test_scan_view_cancellation_returns_to_back_stack(self):
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, screen_return_value=False),
            FlowStep(tools_views.ToolsMenuView),
        ])

    def test_scan_view_cancellation_clears_flow_state(self):
        self.settings.set_value(SettingsConstants.SETTING__MESSAGE_SIGNING, SettingsConstants.OPTION__ENABLED)
        
        seed = Seed(mnemonic=["abandon"]*11 + ["about"])
        self.controller.storage.seeds.append(seed)
        fingerprint = seed.get_fingerprint()

        self.run_sequence(
            sequence=[
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                FlowStep(seed_views.SeedsMenuView, button_data_selection=ButtonOption(fingerprint, SeedSignerIconConstants.FINGERPRINT)),
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.SIGN_MESSAGE),
                FlowStep(scan_views.ScanView, screen_return_value=False),
                FlowStep(seed_views.SeedOptionsView),
            ]
        )
        
        assert self.controller.resume_main_flow is None
