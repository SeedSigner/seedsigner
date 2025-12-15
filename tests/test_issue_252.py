import sys
from unittest.mock import MagicMock, patch

sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['spidev'] = MagicMock()

import pytest
from seedsigner.gui.screens.screen import RET_CODE__UP_BUTTON, RET_CODE__DOWN_BUTTON, RET_CODE__BACK_BUTTON
from seedsigner.views.seed_views import SeedTranscribeSeedQRWholeQRView, SeedTranscribeSeedQRZoomedInView
from seedsigner.models.qr_type import QRType

class TestIssue252:
    @pytest.fixture
    def mock_controller(self):
        with patch('seedsigner.controller.Controller') as MockController:
            controller_instance = MockController.get_instance.return_value
            controller_instance.screen = MagicMock()
            controller_instance.screen.change_brightness = MagicMock()
            
            controller_instance.storage.seeds = []
            controller_instance.get_seed.return_value = MagicMock()
            controller_instance.get_seed.return_value.mnemonic_list = ["abandon"] * 12
            
            yield controller_instance

    @pytest.fixture
    def mock_settings(self):
        with patch('seedsigner.models.settings.Settings') as MockSettings:
            settings_instance = MockSettings.get_instance.return_value
            settings_instance.get_value.return_value = "en"
            yield settings_instance

    @pytest.fixture
    def mock_renderer(self):
        with patch('seedsigner.gui.Renderer') as MockRenderer:
            renderer_instance = MockRenderer.get_instance.return_value
            renderer_instance.canvas_width = 240
            renderer_instance.canvas_height = 240
            yield renderer_instance

    def test_whole_qr_brightness_control(self, mock_controller, mock_settings, mock_renderer):
        view = SeedTranscribeSeedQRWholeQRView(seed_num=0, seedqr_format=QRType.SEED__SEEDQR, num_modules=21)
        
        view.run_screen = MagicMock(side_effect=[
            RET_CODE__UP_BUTTON,
            RET_CODE__DOWN_BUTTON,
            RET_CODE__BACK_BUTTON
        ])

        view.run()

        assert mock_controller.screen.change_brightness.call_count == 2
        mock_controller.screen.change_brightness.assert_any_call(increment=1)
        mock_controller.screen.change_brightness.assert_any_call(increment=-1)

    def test_zoomed_in_brightness_control(self, mock_controller, mock_settings, mock_renderer):
        view = SeedTranscribeSeedQRZoomedInView(seed_num=0, seedqr_format=QRType.SEED__SEEDQR)
        
        view.run_screen = MagicMock(side_effect=[
            RET_CODE__UP_BUTTON,
            RET_CODE__DOWN_BUTTON,
            RET_CODE__BACK_BUTTON 
        ])
        
        view.run()
        
        assert mock_controller.screen.change_brightness.call_count == 2
        mock_controller.screen.change_brightness.assert_any_call(increment=1)
        mock_controller.screen.change_brightness.assert_any_call(increment=-1)
