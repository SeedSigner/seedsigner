import sys
from unittest.mock import MagicMock, patch
import pytest

# Mock hardware dependencies (replacing BaseTest functionality)
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['spidev'] = MagicMock()

from seedsigner.controller import Controller
from seedsigner.gui.screens.seed_screens import SeedSignMessageConfirmMessageScreen
from seedsigner.gui.components import TextDoesNotFitException
from seedsigner.gui.renderer import Renderer

class TestIssue550:
    @pytest.fixture
    def mock_controller(self):
        # Standard controller mocking pattern for SeedSigner
        with patch('seedsigner.controller.Controller') as MockController:
            controller_instance = MockController.get_instance.return_value
            yield controller_instance

    def test_long_message_overflow(self):
        controller = Controller.get_instance()
        
        renderer = Renderer.get_instance()
        renderer.canvas_width = 240
        renderer.canvas_height = 240

        long_message = "A" * 100
        
        controller.sign_message_data = {
            "message": long_message,
        }
        
        try:
            screen = SeedSignMessageConfirmMessageScreen(page_num=0)
        except TextDoesNotFitException:
            pytest.fail("SeedSignMessageConfirmMessageScreen raised TextDoesNotFitException on long message")

        assert "paged_message" in controller.sign_message_data
        assert len(controller.sign_message_data["paged_message"]) > 0
        
        assert controller.sign_message_data["paged_message"][0].startswith("AAAA")
