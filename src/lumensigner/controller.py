import logging
import traceback
from typing import List, Union, Optional

from PIL.Image import Image
from stellar_sdk import TransactionEnvelope, FeeBumpTransactionEnvelope

from lumensigner.gui.renderer import Renderer
from lumensigner.hardware.buttons import HardwareButtons
from lumensigner.hardware.microsd import MicroSD
from lumensigner.models import (
    Seed,
    SeedStorage,
    Settings,
    Singleton,
    SettingsConstants,
)
from lumensigner.views.screensaver import ScreensaverScreen
from lumensigner.views.view import (
    Destination,
    NotYetImplementedView,
    UnhandledExceptionView,
)
from lumensigner.helpers.dev_tools import DEV_MODE_ENABLED, set_dev_mnemonic

logger = logging.getLogger(__name__)


class BackStack(List[Destination]):
    def __repr__(self):
        if len(self) == 0:
            return "[]"
        out = "[\n"
        for index, destination in reversed(list(enumerate(self))):
            out += f"    {index:2d}: {destination}\n"
        out += "]"
        return out


class Controller(Singleton):
    """
    The Controller is a globally available singleton that maintains SeedSigner state.

    It only makes sense to ever have a single Controller instance so it is
    implemented here as a singleton. One departure from the typical singleton pattern
    is the addition of a `configure_instance()` call to pass run-time settings into
    the Controller.

    Any code that needs to interact with the one and only Controller can just run:
    ```
    from seedsigner.controller import Controller
    controller = Controller.get_instance()
    ```
    Note: In many/most cases you'll need to do the Controller import within a method
    rather than at the top in order avoid circular imports.
    """

    # Declare class member vars with type hints to enable richer IDE support throughout
    # the code.
    buttons: HardwareButtons = None
    storage: SeedStorage = None
    settings: Settings = None
    renderer: Renderer = None

    # TODO: Refactor these flow-related attrs that survive across multiple Screens.
    # TODO: Should all in-memory flow-related attrs get wiped on MainMenuView?
    image_entropy_preview_frames: List[Image] = None
    image_entropy_final_image: Image = None

    address_explorer_data: Optional[dict] = None
    # TODO: end refactor section

    # Destination placeholder for when we need to jump out to a side flow but intend to
    # return navigation to the main flow
    FLOW__SIGN_TX = "sign_tx"
    FLOW__SIGN_HASH = "sign_hash"
    FLOW__REQUEST_ADDRESS = "request_address"
    FLOW__ADDRESS_EXPLORER = "address_explorer"
    resume_main_flow: Optional[str] = None

    back_stack: BackStack = None
    screensaver: ScreensaverScreen = None

    def __init__(self):
        super().__init__()

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance:
            return cls._instance
        else:
            # Instantiate the one and only Controller instance
            return cls.configure_instance()

    @classmethod
    def configure_instance(cls, disable_hardware=False):
        """
        - `disable_hardware` is only meant to be used by the test suite so that it
        can keep re-initializing a Controller in however many tests it needs to. But
        this is only possible if the hardware isn't already being reserved. Without
        this you get:

        RuntimeError: Conflicting edge detection already enabled for this GPIO channel

        each time you try to re-initialize a Controller.
        """
        # Must be called before the first get_instance() call
        if cls._instance:
            raise Exception("Instance already configured")

        # Instantiate the one and only Controller instance
        controller = cls.__new__(cls)
        cls._instance = controller

        # Input Buttons
        if disable_hardware:
            controller.buttons = None
        else:
            controller.buttons = HardwareButtons.get_instance()

        # models
        # TODO: Rename "storage" to something more indicative of its temp, in-memory state
        controller.storage = SeedStorage()
        controller.settings = Settings.get_instance()

        controller.microsd = MicroSD.get_instance()
        controller.microsd.start_detection()

        # Configure the Renderer
        Renderer.configure_instance()

        controller.screensaver = ScreensaverScreen(controller.buttons)

        controller.back_stack = BackStack()

        # Other behavior constants
        controller.screensaver_activation_ms = 120 * 1000

        return cls._instance

    @property
    def camera(self):
        from .hardware.camera import Camera

        return Camera.get_instance()

    def get_seed(self, seed_num: int) -> Seed:
        if seed_num < len(self.storage.seeds):
            return self.storage.seeds[seed_num]
        else:
            raise Exception(
                f"There is no seed_num {seed_num}; only {len(self.storage.seeds)} in memory."
            )

    def discard_seed(self, seed_num: int):
        if seed_num < len(self.storage.seeds):
            del self.storage.seeds[seed_num]
        else:
            raise Exception(
                f"There is no seed_num {seed_num}; only {len(self.storage.seeds)} in memory."
            )

    def pop_prev_from_back_stack(self):
        from .views import Destination

        if len(self.back_stack) > 0:
            # Pop the top View (which is the current view_cls)
            self.back_stack.pop()

            if len(self.back_stack) > 0:
                # One more pop back gives us the actual "back" view_cls
                return self.back_stack.pop()
        return Destination(None)

    def clear_back_stack(self):
        self.back_stack = BackStack()

    def start(self) -> None:
        from .views import MainMenuView, BackStackView
        from .views.screensaver import OpeningSplashScreen

        opening_splash = OpeningSplashScreen()
        opening_splash.start()

        # add a default seed in dev mode
        if DEV_MODE_ENABLED:
            set_dev_mnemonic(
                self.storage.seeds,
                self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE),
            )

        """ Class references can be stored as variables in python!

            This loop receives a View class to execute and stores it in the `view_cls`
            var along with any input arguments in the `init_args` dict.

            The `view_cls` is instantiated with `init_args` passed in and then run(). It
            returns either a new View class to execute next or None.

            Example:
                class MyView(View)
                    def run(self, some_arg, other_arg):
                        print(other_arg)

                class OtherView(View):
                    def run(self):
                        return (MyView, dict(some_arg=1, other_arg="hello"))

            When `OtherView` is instantiated and run, we capture its return values:

                (view_cls, init_args) = OtherView().run()

            And then we can instantiate and run that View class:

                view_cls(**init_args).run()
        """
        try:
            next_destination = Destination(MainMenuView)
            while True:
                # Destination(None) is a special case; render the Home screen
                if next_destination.view_cls is None:
                    next_destination = Destination(MainMenuView)

                if next_destination.view_cls == MainMenuView:
                    # Home always wipes the back_stack
                    self.clear_back_stack()

                    # Home always wipes the back_stack/state of temp vars
                    self.address_explorer_data = None
                    self.sign_hash_data: Optional[tuple[int, str]] = None
                    self.tx_data: Optional[
                        tuple[
                            int, Union[TransactionEnvelope, FeeBumpTransactionEnvelope]
                        ]
                    ] = None
                    self.tx_data: Optional[int] = None

                print(f"back_stack: {self.back_stack}")

                try:
                    print(f"Executing {next_destination}")
                    next_destination = next_destination.run()
                except Exception as e:
                    # Display user-friendly error screen w/debugging info
                    next_destination = self.handle_exception(e)

                if not next_destination:
                    # Should only happen during dev when you hit an unimplemented option
                    next_destination = Destination(NotYetImplementedView)

                if next_destination.skip_current_view:
                    # Remove the current View from history; it's forwarding us straight
                    # to the next View so it should be as if this View never happened.
                    current_view = self.back_stack.pop()
                    print(f"Skipping current view: {current_view}")

                # Hang on to this reference...
                clear_history = next_destination.clear_history

                if next_destination.view_cls == BackStackView:
                    # "Back" arrow was clicked; load the previous view
                    next_destination = self.pop_prev_from_back_stack()

                # ...now apply it, if needed
                if clear_history:
                    self.clear_back_stack()

                # The next_destination up always goes on the back_stack, even if it's the
                #   one we just popped.
                # Do not push a "new" destination if it is the same as the current one on
                # the top of the stack.
                if len(self.back_stack) == 0 or self.back_stack[-1] != next_destination:
                    print(f"Appending next destination: {next_destination}")
                    self.back_stack.append(next_destination)
                else:
                    print(f"NOT appending {next_destination}")

                print("-" * 30)

        finally:
            if self.screensaver.is_running:
                self.screensaver.stop()

            # Clear the screen when exiting
            print("Clearing screen, exiting")
            Renderer.get_instance().display_blank_screen()

    def start_screensaver(self):
        self.screensaver.start()

    def handle_exception(self, e) -> Destination:
        """
        Displays a user-friendly error screen and includes debugging info to help
        devs diagnose what went wrong.

        Shows:
            * Exception type
            * python file, line num, method name
            * Exception message
        """
        logger.exception(e)

        # The final exception output line is:
        # "foo.bar.ExceptionType: The exception message"
        # So we extract the Exception type and trim off any "foo.bar." namespacing:
        last_line = traceback.format_exc().splitlines()[-1]
        exception_type = last_line.split(":")[0].split(".")[-1]
        exception_msg = last_line.split(":")[1]

        # Scan for the last debugging line that includes a line number reference
        line_info = None
        for i in range(len(traceback.format_exc().splitlines()) - 1, 0, -1):
            traceback_line = traceback.format_exc().splitlines()[i]
            if ", line " in traceback_line:
                line_info = (
                    traceback_line.split("/")[-1].replace('"', "").replace("line ", "")
                )
                break

        error = [
            exception_type,
            line_info,
            exception_msg,
        ]
        return Destination(
            UnhandledExceptionView, view_args={"error": error}, clear_history=True
        )
