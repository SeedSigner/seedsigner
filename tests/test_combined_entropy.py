import random
from unittest.mock import Mock

from PIL import Image

# Must import this before the Controller and Views.
from base import BaseTest

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.helpers import mnemonic_generation
from seedsigner.views import tools_views
from seedsigner.views.seed_views import SeedWordsWarningView
from seedsigner.views.view import MainMenuView


def _noise_image(seed: int, width: int = 64, height: int = 64) -> Image.Image:
    rng = random.Random(seed)
    return Image.frombytes(
        "RGB",
        (width, height),
        bytes(rng.getrandbits(8) for _ in range(width * height * 3)),
    )


class TestCombinedEntropyFlow(BaseTest):
    def test_menu_routes_to_combined_camera_flow(self):
        view = tools_views.ToolsMenuView()
        view.run_screen = Mock(return_value=2)

        destination = view.run()

        assert destination.View_cls == tools_views.ToolsImageEntropyLivePreviewView
        assert destination.view_args == {"is_combined": True}


    def test_camera_stage_retains_only_digest_then_routes_to_dice(self):
        self.controller.image_entropy_preview_frames = [_noise_image(1)]
        self.controller.image_entropy_final_image = _noise_image(2)

        view = tools_views.ToolsImageEntropyMnemonicLengthView(is_combined=True)
        view.run_screen = Mock(return_value=0)
        destination = view.run()

        assert destination.View_cls == tools_views.ToolsDiceEntropyEntryView
        assert destination.view_args == {"total_rolls": 50, "is_combined": True}
        assert len(self.controller.combined_entropy_camera_digest) == 32
        assert self.controller.image_entropy_preview_frames is None
        assert self.controller.image_entropy_final_image is None


    def test_dice_stage_generates_combined_seed_and_wipes_digest(self):
        rng = random.Random(0)
        dice_rolls = "".join(rng.choice("123456") for _ in range(50))
        camera_digest = bytearray(range(32))
        expected_mnemonic = mnemonic_generation.generate_mnemonic_from_camera_and_dice(
            camera_digest,
            dice_rolls,
        )
        self.controller.combined_entropy_camera_digest = camera_digest

        view = tools_views.ToolsDiceEntropyEntryView(total_rolls=50, is_combined=True)
        view.run_screen = Mock(return_value=dice_rolls)
        destination = view.run()

        assert destination.View_cls == SeedWordsWarningView
        assert self.controller.storage.get_pending_seed().mnemonic_list == expected_mnemonic
        assert self.controller.combined_entropy_camera_digest is None
        assert camera_digest == bytearray(32)


    def test_combined_dice_back_cancels_and_wipes_digest(self):
        camera_digest = bytearray(range(32))
        self.controller.combined_entropy_camera_digest = camera_digest
        view = tools_views.ToolsDiceEntropyEntryView(total_rolls=50, is_combined=True)
        view.run_screen = Mock(return_value=RET_CODE__BACK_BUTTON)

        destination = view.run()

        assert destination.View_cls == MainMenuView
        assert destination.clear_history
        assert self.controller.combined_entropy_camera_digest is None
        assert camera_digest == bytearray(32)
