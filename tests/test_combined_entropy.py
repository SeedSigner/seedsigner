import random
from unittest.mock import Mock

import pytest
from PIL import Image

# Must import this before the Controller and Views.
from base import BaseTest

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.helpers import hybrid_entropy, mnemonic_generation
from seedsigner.views import tools_views
from seedsigner.views.seed_views import SeedWordsWarningView
from seedsigner.views.view import MainMenuView


ACCEPTED_ROLLS = ("123456" * 16) + "1234"
REJECTED_ROLLS = "6" * 100


def _noise_image(seed: int, width: int = 64, height: int = 64) -> Image.Image:
    rng = random.Random(seed)
    return Image.frombytes(
        "RGB",
        (width, height),
        bytes(rng.getrandbits(8) for _ in range(width * height * 3)),
    )


class TestHybridEntropyFlow(BaseTest):
    def test_menu_routes_to_hybrid_camera_flow(self):
        view = tools_views.ToolsMenuView()
        view.run_screen = Mock(return_value=2)

        destination = view.run()

        assert destination.View_cls == tools_views.ToolsImageEntropyLivePreviewView
        assert destination.view_args == {"is_combined": True}


    def test_accepted_final_image_routes_directly_to_commitment(self):
        self.controller.image_entropy_final_image = _noise_image(1)
        view = tools_views.ToolsImageEntropyFinalImageView(is_combined=True)
        view.canvas_width = 240
        view.canvas_height = 240
        view.run_screen = Mock(return_value=None)

        destination = view.run()

        assert destination.View_cls == tools_views.ToolsHybridEntropyCameraCommitmentView


    def test_camera_commitment_freezes_hidden_value_and_clears_images(self):
        image = _noise_image(2)
        expected_camera = hybrid_entropy.camera256_from_rgb(
            image.width,
            image.height,
            image.tobytes(),
        )
        expected_commitment = hybrid_entropy.camera_commitment(expected_camera)
        self.controller.image_entropy_preview_frames = [_noise_image(3)]
        self.controller.image_entropy_final_image = image

        view = tools_views.ToolsHybridEntropyCameraCommitmentView()
        view.run_screen = Mock(side_effect=[0, None])
        destination = view.run()

        assert destination.View_cls == tools_views.ToolsDiceEntropyEntryView
        assert destination.view_args == {"total_rolls": 100, "is_combined": True}
        assert self.controller.hybrid_entropy_camera_value == expected_camera
        assert self.controller.hybrid_entropy_camera_commitment == expected_commitment
        assert self.controller.hybrid_entropy_dice_value is None
        assert self.controller.image_entropy_preview_frames is None
        assert self.controller.image_entropy_final_image is None

        qr_encoder = view.run_screen.call_args_list[1].kwargs["qr_encoder"]
        assert qr_encoder.next_part() == hybrid_entropy.commitment_record(
            expected_commitment
        )


    def test_camera_commitment_cancel_wipes_hidden_value(self):
        camera_references = []
        self.controller.image_entropy_final_image = _noise_image(4)
        view = tools_views.ToolsHybridEntropyCameraCommitmentView()

        def cancel_after_commitment(*args, **kwargs):
            camera_references.append(
                self.controller.hybrid_entropy_camera_value
            )
            return 1

        view.run_screen = Mock(side_effect=cancel_after_commitment)

        destination = view.run()

        assert destination.View_cls == MainMenuView
        assert destination.clear_history
        assert self.controller.hybrid_entropy_camera_value is None
        assert camera_references[0] == bytearray(32)


    def test_accepted_dice_block_is_frozen_before_camera_reveal(self):
        camera_value = bytearray(range(32))
        self.controller.hybrid_entropy_camera_value = camera_value
        self.controller.hybrid_entropy_camera_commitment = (
            hybrid_entropy.camera_commitment(camera_value)
        )

        view = tools_views.ToolsDiceEntropyEntryView(
            total_rolls=100,
            is_combined=True,
        )
        view.run_screen = Mock(return_value=ACCEPTED_ROLLS)
        destination = view.run()

        assert destination.View_cls == tools_views.ToolsHybridEntropyCameraRevealView
        assert self.controller.hybrid_entropy_dice_value == (
            hybrid_entropy.extract_uniform_dice256(ACCEPTED_ROLLS)
        )
        assert self.controller.hybrid_entropy_camera_value is camera_value
        assert self.controller.storage.get_pending_seed() is None


    def test_rejected_dice_block_requires_a_fresh_block(self):
        camera_value = bytearray(range(32))
        self.controller.hybrid_entropy_camera_value = camera_value
        self.controller.hybrid_entropy_camera_commitment = (
            hybrid_entropy.camera_commitment(camera_value)
        )

        view = tools_views.ToolsDiceEntropyEntryView(
            total_rolls=100,
            is_combined=True,
        )
        view.run_screen = Mock(side_effect=[REJECTED_ROLLS, 0])
        destination = view.run()

        assert destination.View_cls == tools_views.ToolsDiceEntropyEntryView
        assert destination.view_args == {"total_rolls": 100, "is_combined": True}
        assert destination.skip_current_view
        assert self.controller.hybrid_entropy_camera_value is camera_value
        assert self.controller.hybrid_entropy_dice_value is None


    def test_reveal_verifies_commitment_generates_seed_and_wipes_secrets(self):
        camera_value = bytearray(range(32))
        dice_value = bytearray(
            hybrid_entropy.extract_uniform_dice256(ACCEPTED_ROLLS)
        )
        commitment = hybrid_entropy.camera_commitment(camera_value)
        expected_mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(
            hybrid_entropy.xor256(camera_value, dice_value)
        )
        self.controller.hybrid_entropy_camera_value = camera_value
        self.controller.hybrid_entropy_camera_commitment = commitment
        self.controller.hybrid_entropy_dice_value = dice_value

        view = tools_views.ToolsHybridEntropyCameraRevealView()
        view.run_screen = Mock(side_effect=[0, None])
        destination = view.run()

        assert destination.View_cls == SeedWordsWarningView
        assert destination.clear_history
        assert self.controller.storage.get_pending_seed().mnemonic_list == expected_mnemonic
        assert self.controller.hybrid_entropy_camera_value is None
        assert self.controller.hybrid_entropy_camera_commitment is None
        assert self.controller.hybrid_entropy_dice_value is None
        assert camera_value == bytearray(32)
        assert dice_value == bytearray(32)

        qr_encoder = view.run_screen.call_args_list[1].kwargs["qr_encoder"]
        assert qr_encoder.next_part() == hybrid_entropy.camera_reveal_record(
            bytes(range(32))
        )


    def test_dice_back_cancels_and_wipes_camera_value(self):
        camera_value = bytearray(range(32))
        self.controller.hybrid_entropy_camera_value = camera_value
        self.controller.hybrid_entropy_camera_commitment = (
            hybrid_entropy.camera_commitment(camera_value)
        )
        view = tools_views.ToolsDiceEntropyEntryView(
            total_rolls=100,
            is_combined=True,
        )
        view.run_screen = Mock(return_value=RET_CODE__BACK_BUTTON)

        destination = view.run()

        assert destination.View_cls == MainMenuView
        assert destination.clear_history
        assert self.controller.hybrid_entropy_camera_value is None
        assert camera_value == bytearray(32)


    def test_reveal_rejects_tampered_commitment_and_wipes_secrets(self):
        camera_value = bytearray(range(32))
        dice_value = bytearray(
            hybrid_entropy.extract_uniform_dice256(ACCEPTED_ROLLS)
        )
        self.controller.hybrid_entropy_camera_value = camera_value
        self.controller.hybrid_entropy_camera_commitment = bytes(32)
        self.controller.hybrid_entropy_dice_value = dice_value

        view = tools_views.ToolsHybridEntropyCameraRevealView()
        with pytest.raises(RuntimeError, match="commitment verification failed"):
            view.run()

        assert camera_value == bytearray(32)
        assert dice_value == bytearray(32)
        assert self.controller.hybrid_entropy_camera_value is None
        assert self.controller.hybrid_entropy_dice_value is None
