import pytest
from unittest.mock import MagicMock

# Import base test class
from base import BaseTest

# Import project modules
from seedsigner.controller import Controller
from seedsigner.gui.screens.seed_screens import SeedSignMessageConfirmMessageScreen
from seedsigner.gui.components import TextDoesNotFitException
from seedsigner.gui.renderer import Renderer

class TestIssue550(BaseTest):
    def test_long_message_overflow(self):
        """
        Issue #550: TextDoesNotFitException when trying to sign very long messages.
        
        This test simulates a long, uninterrupted string (like a BOLT12 invoice) 
        being passed to the SeedSignMessageConfirmMessageScreen.
        """
        # Setup Controller
        controller = Controller.get_instance()
        
        # Configure Renderer mock dimensions so the layout math works with real integers
        renderer = Renderer.get_instance()
        renderer.canvas_width = 240
        renderer.canvas_height = 240

        # A very long string with no spaces (simulating BOLT12 invoice or similar)
        # 100 chars of 'A' is wider than 240px screen width
        long_message = "A" * 100
        
        # Mock the sign_message_data structure in the controller
        controller.sign_message_data = {
            "message": long_message,
        }
        
        # Instantiate the screen. This triggers __post_init__ which calls reflow_text_into_pages.
        # If the bug is present (allow_text_overflow=False), this raises TextDoesNotFitException.
        try:
            # Fix: Pass page_num=0 to avoid TypeError in __post_init__ validation
            screen = SeedSignMessageConfirmMessageScreen(page_num=0)
        except TextDoesNotFitException:
            pytest.fail("SeedSignMessageConfirmMessageScreen raised TextDoesNotFitException on long message")

        # Verify paged message was created and stored
        assert "paged_message" in controller.sign_message_data
        assert len(controller.sign_message_data["paged_message"]) > 0
        
        # Verify the content is handled (likely truncated/split arbitrarily or overflowed)
        # We just want to ensure it didn't crash.
        print(f"Paged message content: {controller.sign_message_data['paged_message']}")
        assert controller.sign_message_data["paged_message"][0].startswith("AAAA")
