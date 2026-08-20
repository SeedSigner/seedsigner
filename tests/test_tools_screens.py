import hashlib
import os

from unittest.mock import MagicMock, patch

from PIL import Image

# Must import test base before the Controller
from base import BaseTest

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.hardware.camera import Camera


"""
    We don't test other Screens; they mostly have simple UI nav, text entry, or button
    select behavior. But the image entropy screens have critical user interaction review
    checks that could impact the security of the generated seed. So explicit tests of
    those interactions are warranted.

    These tests have to simulate user button press sequences AND duration at various
    stages of the image entropy live review loop and final image review.

    These tests are not concerned with actual image content, entropy, etc.
"""


def make_noise_frame(width: int = 240, height: int = 240) -> Image.Image:
    # Random bytes are fine here: tests only need frames that are non-blank and
    # distinct from one another; nothing here feeds real entropy.
    return Image.frombytes("RGBA", (width, height), os.urandom(width * height * 4))


def make_blank_frame(color: tuple = (0, 0, 0, 255), width: int = 240, height: int = 240) -> Image.Image:
    """ A frame of a single flat color: every pixel identical, as from a covered camera. """
    return Image.new("RGBA", (width, height), color)


# A blank frame is any frame of one uniform color: a covered lens reads full black, an
# overexposed one reads full white, and a color cast reads as some other single color.
BLANK_FRAME_COLORS = [
    (0, 0, 0, 255),        # full black
    (255, 255, 255, 255),  # full white
    (128, 128, 128, 255),  # a flat mid grey
    (255, 0, 0, 255),      # one saturated channel is still a single flat color
    (0, 255, 0, 255),
    (0, 0, 255, 255),
    # ...and so is any color whose three channels each hold their own unchanging value
] + [(value, (value * 7) % 256, (value * 13) % 256, 255) for value in range(1, 55)]


def make_mock_camera(frames: list) -> MagicMock:
    """
    Returns a mocked Camera whose read_video_stream() plays back the given frames in
    order.
    """
    camera = MagicMock()
    frame_feed = list(frames)

    def read_video_stream(as_image: bool = False):
        if not frame_feed:
            raise AssertionError("Camera frame script exhausted; the screen loop should have exited by now")
        return frame_feed.pop(0)

    camera.read_video_stream.side_effect = read_video_stream
    return camera


def make_mock_hw_inputs(left_script: list = None, anyclick_script: list = None) -> MagicMock:
    """
    Returns a mocked HardwareButtons whose check_for_low() plays back scripted
    responses.

    There are two types of input checks:
    * check_for_low(specific_key_constant). e.g. was KEY_LEFT (back) pressed?

    * check_for_low(keys=list_of_keys). e.g. was ANYCLICK pressed? (any of the click buttons)
    """
    left_feed = list(left_script or [])
    anyclick_feed = list(anyclick_script or [])
    hw_inputs = MagicMock()

    def check_for_low(key=None, keys=None):
        if keys is None:
            return left_feed.pop(0) if left_feed else False
        return anyclick_feed.pop(0) if anyclick_feed else False

    hw_inputs.check_for_low.side_effect = check_for_low
    return hw_inputs


def count_anyclick_checks(mock_hw_inputs: MagicMock) -> int:
    """
    How many times the screen polled the ANYCLICK group.
    """
    from seedsigner.hardware.buttons import HardwareButtonsConstants
    return sum(1 for c in mock_hw_inputs.check_for_low.call_args_list if c.kwargs.get("keys") == HardwareButtonsConstants.KEYS__ANYCLICK)



class ImageEntropyScreenTestBase(BaseTest):

    def setup_method(self):
        super().setup_method()

        from seedsigner.gui.renderer import Renderer

        # tests/base.py mocks the whole renderer module; give each test a fresh renderer
        # whose canvas dims are real ints (the screens do math on them). Exposed as a
        # patch so screen construction restores the original when its `with` exits.
        self.mock_renderer = MagicMock()
        self.mock_renderer.canvas_width = 240
        self.mock_renderer.canvas_height = 240
        self.renderer_patch = patch.object(Renderer, "get_instance", return_value=self.mock_renderer)



class TestToolsImageEntropyLivePreviewScreen(ImageEntropyScreenTestBase):

    def build_screen(self, mock_camera: MagicMock, mock_hw_inputs: MagicMock):
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyLivePreviewScreen

        # Run within our mocked Renderer context
        with self.renderer_patch:
            with patch.object(Camera, "get_instance", return_value=mock_camera):
                screen = ToolsImageEntropyLivePreviewScreen()

        screen.hw_inputs = mock_hw_inputs
        return screen


    def test_screen_returns_exactly_50_unique_frames(self):
        """
        The screen should return 50 unique frames from its preview pool.
        """
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyLivePreviewScreen
        num_required = ToolsImageEntropyLivePreviewScreen.PREVIEW_POOL_SIZE

        frames = [make_noise_frame() for i in range(num_required)]

        # One extra read happens on the capture pass; feed it a duplicate of the last
        # frame, which the dedupe check rejects (so the returned pool is untouched).
        duplicate = frames[-1].copy()
        mock_camera = make_mock_camera(frames + [duplicate])
        mock_hw_inputs = make_mock_hw_inputs(anyclick_script=[False, True])
        screen = self.build_screen(mock_camera, mock_hw_inputs)

        result = screen._run()

        assert result == frames
        mock_camera.stop_video_stream_mode.assert_called_once()


    def test_button_held_from_start_never_captures_until_released(self):
        """
        A button already held down when the screen starts must not trigger the final
        image capture -- not even after the entropy pool has filled. Only a fresh
        press after all buttons have been seen released may capture.
        """
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyLivePreviewScreen
        num_required = ToolsImageEntropyLivePreviewScreen.PREVIEW_POOL_SIZE

        # The pool fills at frame 50; the held button registers as still held for the next
        # two loop iterations, released on the third (that's the go-ahead to arm the watch
        # for the final click), then finally pressed on the fourth.
        frames = [make_noise_frame() for i in range(num_required + 3)]
        mock_camera = make_mock_camera(frames)
        mock_hw_inputs = make_mock_hw_inputs(anyclick_script=[True, True, False, True])
        screen = self.build_screen(mock_camera, mock_hw_inputs)

        result = screen._run()

        # The pool is a moving window of the LAST 50 admitted frames.
        assert result == frames[3:]
        assert len(result) == num_required

        # The ANYCLICK checks should only start after the preview pool is filled so we
        # should only see the four checks scripted above.
        assert count_anyclick_checks(mock_hw_inputs) == 4
        mock_camera.stop_video_stream_mode.assert_called_once()


    def test_blank_frames_are_never_admitted(self):
        """
        Flat single-color frames (e.g. covered camera, all white, all turquoise, etc) are
        never counted, the final capture click is never armed, and the back button still
        exits.
        """
        # One frame per flat color, more of them than the pool needs, and all distinct.
        blanks = [make_blank_frame(color) for color in BLANK_FRAME_COLORS]
        mock_camera = make_mock_camera(blanks)
        mock_hw_inputs = make_mock_hw_inputs(left_script=[False] * (len(blanks) - 1) + [True])
        screen = self.build_screen(mock_camera, mock_hw_inputs)

        result = screen._run()

        assert result == RET_CODE__BACK_BUTTON

        # The pool never filled, so the final capture click (ANYCLICK) was never checked.
        assert count_anyclick_checks(mock_hw_inputs) == 0
        mock_camera.stop_video_stream_mode.assert_called_once()


    def test_duplicate_frames_are_only_counted_once(self):
        """
        A frame whose bytes exactly match an already-admitted frame cannot be included in
        the preview pool again.
        """
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyLivePreviewScreen
        num_required = ToolsImageEntropyLivePreviewScreen.PREVIEW_POOL_SIZE

        test_frame = make_noise_frame()
        fillers = [make_noise_frame() for i in range(num_required)]

        feed = fillers[:10] + [test_frame] + fillers[10:20] + [test_frame] + fillers[20:]
        mock_camera = make_mock_camera(feed)
        mock_hw_inputs = make_mock_hw_inputs(anyclick_script=[False, True])
        screen = self.build_screen(mock_camera, mock_hw_inputs)

        result = screen._run()

        assert test_frame in result
        # PIL Images are unhashable, so uniqueness is checked on their bytes
        assert len(set(frame.tobytes() for frame in result)) == num_required  # all unique



    def test_back_button_exits_immediately(self):
        """ KEY_LEFT backs out at any time, even before any frame is read. """
        mock_camera = make_mock_camera([])
        mock_hw_inputs = make_mock_hw_inputs(left_script=[True])
        screen = self.build_screen(mock_camera, mock_hw_inputs)

        result = screen._run()

        assert result == RET_CODE__BACK_BUTTON
        mock_camera.stop_video_stream_mode.assert_called_once()
        mock_camera.read_video_stream.assert_not_called()


class TestToolsImageEntropyFinalImageScreen(ImageEntropyScreenTestBase):

    def build_screen(self, mock_hw_inputs: MagicMock):
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyFinalImageScreen

        # Run within our mocked Renderer context
        with self.renderer_patch:
            screen = ToolsImageEntropyFinalImageScreen(final_image=MagicMock())
        screen.hw_inputs = mock_hw_inputs
        return screen


    def test_held_button_must_be_released_before_review_input(self):
        """
        The click that captured the photo can still be held down when the review
        screen appears; it must be released before accept/reshoot input is read, so
        one long press can never accept the photo sight unseen.
        """
        from seedsigner.hardware.buttons import HardwareButtonsConstants

        # Button held for two polls, released on the third; only then is the real
        # accept/reshoot decision awaited.
        mock_hw_inputs = make_mock_hw_inputs(anyclick_script=[True, True, False])
        mock_hw_inputs.wait_for.return_value = HardwareButtonsConstants.KEY_LEFT
        screen = self.build_screen(mock_hw_inputs)

        # Screen returns the back button code when the user chooses to reshoot (KEY_LEFT).
        result = screen._run()

        assert mock_hw_inputs.check_for_low.call_count == 3
        mock_hw_inputs.wait_for.assert_called_once()
        assert result == RET_CODE__BACK_BUTTON


    def test_accept_returns_none_to_advance(self):
        """ A (fresh) accept click falls through: the screen returns None. """
        from seedsigner.hardware.buttons import HardwareButtonsConstants

        mock_hw_inputs = make_mock_hw_inputs(anyclick_script=[False])
        mock_hw_inputs.wait_for.return_value = HardwareButtonsConstants.KEY_RIGHT
        screen = self.build_screen(mock_hw_inputs)

        result = screen._run()

        assert result is None
        mock_hw_inputs.wait_for.assert_called_once()
