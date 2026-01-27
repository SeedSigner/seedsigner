"""
Interim solution while we have to use the original ST7789 driver and the newer st7789_mpy
driver (for the 320x240 displays).

TODO: Eventually all three st7789* files should be reduced down to one. At which point
there will be no need for a parent/child class relationship.
"""

from dataclasses import dataclass
from seedsigner.hardware.displays.display_driver import BaseDisplayDriver
from seedsigner.helpers.l10n import mark_for_translation as _mft


# Gamma curve constants for ST7789 display
# Format: (Human-readable name, Settings value, curve data)
GAMMA_CURVE__SEEDSIGNER_ORIGINAL = (
    _mft("Original curve"),
    "ORIG",
    (
        [0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F, 0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23],
        [0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F, 0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23]
    )
)
GAMMA_CURVE__MPY_DRIVER = (
    _mft("Brighter"),
    "MPY",
    (
        [0xD0, 0x00, 0x02, 0x07, 0x0A, 0x28, 0x32, 0x44, 0x42, 0x06, 0x0E, 0x12, 0x14, 0x17],
        [0xD0, 0x00, 0x02, 0x07, 0x0A, 0x28, 0x31, 0x54, 0x47, 0x0E, 0x1C, 0x17, 0x1B, 0x1E]
    )   
)
GAMMA_CURVE__BUILT_IN_1 = (
    _mft("Built-in 1"),
    "B1",
    1
)
GAMMA_CURVE__BUILT_IN_2 = (
    _mft("Built-in 2"),
    "B2",
    2
)
GAMMA_CURVE__BUILT_IN_3 = (
    _mft("Built-in 3"),
    "B3",
    3
)
GAMMA_CURVE__BUILT_IN_4 = (
    _mft("Built-in 4"),
    "B4",
    4
)
GAMMA_CURVES = [
    GAMMA_CURVE__SEEDSIGNER_ORIGINAL,
    GAMMA_CURVE__MPY_DRIVER,
    GAMMA_CURVE__BUILT_IN_1,
    GAMMA_CURVE__BUILT_IN_2,
    GAMMA_CURVE__BUILT_IN_3,
    # GAMMA_CURVE__BUILT_IN_4  # Looks terrible, don't include
]


@dataclass
class BaseST7789(BaseDisplayDriver):
    initial_gamma_curve: str = None


    def __post_init__(self):
        if not self.initial_gamma_curve:
            self.initial_gamma_curve = self.default_gamma_curve


    @property
    def available_gamma_curves(self) -> list[tuple[str, str]]:
        """ List the available gamma curves. Returns (Human-readable name, Settings value) """
        return [(gc[0], gc[1]) for gc in GAMMA_CURVES]


    def _set_built_in_gamma(self, curve_num: int):
        raise Exception("set_built_in_gamma() must be implemented in child classes")


    def _set_gamma_values(self, positive_gamma: list[bytes], negative_gamma: list[bytes]):
        """Set gamma values for the display"""
        raise Exception("set_gamma_values() must be implemented in child classes")


    def set_gamma_curve(self, curve: str):
        """Set gamma curve via Settings value"""
        gamma_curve = next((gc for gc in GAMMA_CURVES if gc[1] == curve), None)

        # Validate curve name and default to first curve if invalid
        if gamma_curve is None:
            raise BaseST7789.InvalidGammaCurveValue(f"{curve} not in {[(gc[0], gc[1]) for gc in GAMMA_CURVES]}")

        if isinstance(gamma_curve[2], int):
            self._set_built_in_gamma(gamma_curve[2])
        else:
            positive_gamma, negative_gamma = gamma_curve[2]
            self._set_gamma_values(positive_gamma, negative_gamma)
