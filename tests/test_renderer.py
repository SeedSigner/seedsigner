import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch

# Must import this before any SeedSigner imports
from base import BaseTest

import seedsigner.gui
from seedsigner.models.settings_definition import SettingsConstants



def load_real_renderer_module():
    """
    The test suite replaces `seedsigner.gui.renderer` with a mock (see base.py) so that
    nothing tries to drive a real display. These tests need the real Renderer, so load
    it from its file under another name; the suite's mock stays in place.
    """
    path = Path(seedsigner.gui.__file__).parent / "renderer.py"
    spec = importlib.util.spec_from_file_location("real_renderer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



class TestRendererColorInversion(BaseTest):
    """
    The Renderer must hand the saved "Invert colors" setting to the display driver
    every time the display starts up, which happens on boot and on restart.
    """

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.renderer_module = load_real_renderer_module()


    def start_display(self) -> Mock:
        """
        Starts the real Renderer with a fake display driver in place of the hardware.
        Returns the fake driver so a test can check what the Renderer asked of it.
        """
        driver = Mock(width=240, height=240)
        with patch.object(self.renderer_module.DisplayDriverFactory, "instantiate_display_driver", return_value=driver):
            self.renderer_module.Renderer.configure_instance()
        return driver


    def test_disabled_is_applied_at_startup(self):
        """
        Regression test. "Disabled" used to be skipped at startup, so the display kept
        whatever inversion its driver's init had set.
        """
        self.settings.set_value(SettingsConstants.SETTING__DISPLAY_COLOR_INVERTED, SettingsConstants.OPTION__DISABLED)

        driver = self.start_display()

        driver.set_color_inversion.assert_called_once_with(False)


    def test_enabled_is_applied_at_startup(self):
        """ "Enabled" must reach the display driver at startup too """
        self.settings.set_value(SettingsConstants.SETTING__DISPLAY_COLOR_INVERTED, SettingsConstants.OPTION__ENABLED)

        driver = self.start_display()

        driver.set_color_inversion.assert_called_once_with(True)
