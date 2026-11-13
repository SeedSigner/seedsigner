from seedsigner.hardware.displays.display_driver import BaseDisplayDriver



class FakeDisplayDriver(BaseDisplayDriver):
    """
    A display driver with no hardware behind it. It remembers the last inversion
    state it was told to set, standing in for the panel's controller.
    """
    def invert(self, enabled: bool = True):
        self.controller_inversion = enabled



class FakeDisplayDriverNeedsInversion(FakeDisplayDriver):
    """ Like the ST7789: only shows normal colors with the controller's inversion on. """
    NORMAL_COLORS_REQUIRE_INVERSION = True



class TestSetColorInversion:
    """
    `set_color_inversion()` takes the "Invert colors" setting and decides what to tell
    the panel's controller. "Disabled" must always mean normal colors, whichever
    controller state the panel needs to get there.
    """

    def test_panel_with_normal_colors_by_default(self):
        """ The controller's inversion follows the setting """
        driver = FakeDisplayDriver(_width=240, _height=240)

        driver.set_color_inversion(inverted=False)
        assert driver.controller_inversion == False

        driver.set_color_inversion(inverted=True)
        assert driver.controller_inversion == True


    def test_panel_that_needs_inversion_for_normal_colors(self):
        """ The controller's inversion is the opposite of the setting """
        driver = FakeDisplayDriverNeedsInversion(_width=240, _height=240)

        driver.set_color_inversion(inverted=False)
        assert driver.controller_inversion == True

        driver.set_color_inversion(inverted=True)
        assert driver.controller_inversion == False
