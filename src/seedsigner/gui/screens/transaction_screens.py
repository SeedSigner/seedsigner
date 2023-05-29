from dataclasses import dataclass

from seedsigner.hardware.buttons import HardwareButtonsConstants
from . import BaseTopNavScreen
from ..components import (
    TextArea,
)


@dataclass
class TxDetailsScreen(BaseTopNavScreen):
    def _run(self):
        while True:
            user_input = self.hw_inputs.wait_for(
                HardwareButtonsConstants.ALL_KEYS,
                check_release=True,
                release_keys=HardwareButtonsConstants.KEYS__ANYCLICK,
            )

            with self.renderer.lock:
                if not self.top_nav.is_selected and user_input in [
                    HardwareButtonsConstants.KEY_LEFT,
                ]:
                    self.top_nav.is_selected = True
                    self.top_nav.render_buttons()

                elif self.top_nav.is_selected and user_input in [
                    HardwareButtonsConstants.KEY_DOWN,
                    HardwareButtonsConstants.KEY_RIGHT,
                ]:
                    self.top_nav.is_selected = False
                    self.top_nav.render_buttons()

                elif (
                        self.top_nav.is_selected
                        and user_input in HardwareButtonsConstants.KEYS__ANYCLICK
                ):
                    return self.top_nav.selected_button

                else:
                    return user_input

                # Write the screen updates
                self.renderer.show_image()


@dataclass
class PaymentOperationScreen(TxDetailsScreen):
    operation_index: int = None

    # destination: str = None
    # amount: str = None

    def __post_init__(self):
        self.title = f"Operation {self.operation_index + 1}"
        self.show_back_button = True
        super().__post_init__()

        self.components.append(
            TextArea(
                text="Demo.",
                screen_y=self.top_nav.height,
                height=self.canvas_height - self.top_nav.height,
            )
        )
