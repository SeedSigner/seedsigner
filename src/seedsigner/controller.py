import logging
import time
import traceback

from embit.descriptor import Descriptor
from embit.psbt import PSBT
from PIL.Image import Image

from seedsigner.gui.toast import BaseToastOverlayManagerThread
from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.seed import Seed
from seedsigner.models.seed_storage import SeedStorage
from seedsigner.models.settings import Settings
from seedsigner.models.singleton import Singleton
from seedsigner.models.threads import BaseThread
from seedsigner.views.screensaver import ScreensaverScreen
from seedsigner.views.view import Destination


logger = logging.getLogger(__name__)



class BackStack(list[Destination]):
    def __repr__(self):
        if len(self) == 0:
            return "[]"
        out = "[\n"
        for index, destination in reversed(list(enumerate(self))):
            out += f"    {index:2d}: {destination}\n"
        out += "]"
        return out
            


class StopFlowBasedTest(Exception):
    """
        This is a special exception that is only raised by the test suite to stop the
        Controller's main loop. It should not be raised by any other code.
    """
    pass



class FlowBasedTestException(Exception):
    """
        This is a special exception that is only raised by the test suite.
        It should not be raised by any other code.
    """
    pass



class BackgroundImportThread(BaseThread):
    def run(self):
        from importlib import import_module

        # import seedsigner.hardware.buttons # slowly imports GPIO along the way

        def time_import(module_name):
            last = time.time()
            import_module(module_name)
            # print(time.time() - last, module_name)

        time_import('embit')
        time_import('seedsigner.helpers.embit_utils')

        # Do costly initializations
        time_import('seedsigner.models.seed_storage')
        from seedsigner.models.seed_storage import SeedStorage
        Controller.get_instance()._storage = SeedStorage()

        # Get MainMenuView ready to respond quickly
        time_import('seedsigner.views.scan_views')

        time_import('seedsigner.views.seed_views')

        time_import('seedsigner.views.tools_views')

        time_import('seedsigner.views.settings_views')



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

    VERSION = "0.8.5"

    # Declare class member vars with type hints to enable richer IDE support throughout
    # the code.
    _storage: SeedStorage = None   # TODO: Rename "storage" to something more indicative of its temp, in-memory state
    settings: Settings = None

    # TODO: Refactor these flow-related attrs that survive across multiple Screens.
    # TODO: Should all in-memory flow-related attrs get wiped on MainMenuView?
    psbt: PSBT = None
    psbt_seed: Seed = None
    psbt_parser: PSBTParser = None

    unverified_address = None

    multisig_wallet_descriptor: Descriptor = None

    image_entropy_preview_frames: list[Image] = None
    image_entropy_final_image: Image = None

    address_explorer_data: dict = None

    sign_message_data: dict = None
    # TODO: end refactor section

    # Destination placeholder for when we need to jump out to a side flow but intend to
    # return navigation to the main flow (e.g. PSBT flow, load multisig descriptor,
    # then resume PSBT flow).
    FLOW__PSBT = "psbt"
    FLOW__VERIFY_MULTISIG_ADDR = "multisig_addr"
    FLOW__VERIFY_SINGLESIG_ADDR = "singlesig_addr"
    FLOW__ADDRESS_EXPLORER = "address_explorer"
    FLOW__SIGN_MESSAGE = "sign_message"
    resume_main_flow: str = None

    back_stack: BackStack = None
    screensaver: ScreensaverScreen = None
    toast_notification_thread: BaseToastOverlayManagerThread = None


    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance:
            return cls._instance
        else:
            # Instantiate the one and only Controller instance
            return cls.configure_instance()
    

    @classmethod
    def reset_instance(cls):
        """
            Currently used by the screenshot generator, but could potentially be used to
            wipe and reset the state of the device.
        """
        cls._instance = None
        cls.configure_instance()


    @classmethod
    def configure_instance(cls):
        from seedsigner.gui.renderer import Renderer
        from seedsigner.hardware.microsd import MicroSD

        # Must be called before the first get_instance() call
        if cls._instance:
            raise Exception("Instance already configured")

        # Instantiate the one and only Controller instance
        controller = cls.__new__(cls)
        cls._instance = controller

        # models
        controller.settings = Settings.get_instance()
        
        controller.microsd = MicroSD.get_instance()
        controller.microsd.start_detection()

        # Store one working psbt in memory
        controller.psbt = None
        controller.psbt_parser = None

        # Configure the Renderer
        Renderer.configure_instance()

        controller.back_stack = BackStack()

        # Other behavior constants
        controller.screensaver_activation_ms = 2 * 60 * 1000  # two minutes
    
        background_import_thread = BackgroundImportThread()
        background_import_thread.start()

        return cls._instance


    @property
    def camera(self):
        from .hardware.camera import Camera
        return Camera.get_instance()
    

    @property
    def storage(self):
        while not self._storage:
            # Wait for the BackgroundImportThread to finish initializing the storage.
            # This is a rare timing issue that likely only occurs in the test suite.
            time.sleep(0.001)
        return self._storage


    def get_seed(self, seed_num: int) -> Seed:
        if seed_num < len(self.storage.seeds):
            return self.storage.seeds[seed_num]
        else:
            raise Exception(f"There is no seed_num {seed_num}; only {len(self.storage.seeds)} in memory.")


    def discard_seed(self, seed_num: int):
        if seed_num < len(self.storage.seeds):
            del self.storage.seeds[seed_num]
        else:
            raise Exception(f"There is no seed_num {seed_num}; only {len(self.storage.seeds)} in memory.")


    def pop_prev_from_back_stack(self):
        if len(self.back_stack) > 0:
            # Pop the top View (which is the current View_cls)
            self.back_stack.pop()

            if len(self.back_stack) > 0:
                # One more pop back gives us the actual "back" View_cls
                return self.back_stack.pop()
        return Destination(None)
    

    def clear_back_stack(self):
        self.back_stack = BackStack()


    def start(self, initial_destination: Destination = None) -> None:
        """
            The main loop of the application.

            * initial_destination: The first View to run. If None, the MainMenuView is
            used. Only used by the test suite.
        """
        from seedsigner.views import MainMenuView, BackStackView
        from seedsigner.views.screensaver import OpeningSplashView
        from seedsigner.gui.toast import RemoveSDCardToastManagerThread

        OpeningSplashView().run()

        """ Class references can be stored as variables in python!

            This loop receives a View class to execute and stores it in the `View_cls`
            var along with any input arguments in the `init_args` dict.

            The `View_cls` is instantiated with `init_args` passed in and then run(). It
            returns either a new View class to execute next or None.

            Example:
                class MyView(View)
                    def run(self, some_arg, other_arg):
                        logger.info(other_arg)

                class OtherView(View):
                    def run(self):
                        return (MyView, dict(some_arg=1, other_arg="hello"))

            When `OtherView` is instantiated and run, we capture its return values:

                (View_cls, init_args) = OtherView().run()

            And then we can instantiate and run that View class:

                View_cls(**init_args).run()
        """
        try:
            if initial_destination:
                next_destination = initial_destination
            else:
                next_destination = Destination(MainMenuView)
            
            # Set up our one-time toast notification tip to remove the SD card
            self.activate_toast(RemoveSDCardToastManagerThread())

            while True:
                # Destination(None) is a special case; render the Home screen
                if next_destination.View_cls is None:
                    next_destination = Destination(MainMenuView)

                if next_destination.View_cls == MainMenuView:
                    # Home always wipes the back_stack
                    self.clear_back_stack()
                    
                    # Home always wipes the back_stack/state of temp vars
                    self.resume_main_flow = None
                    self.multisig_wallet_descriptor = None
                    self.unverified_address = None
                    self.address_explorer_data = None
                    self.psbt = None
                    self.psbt_parser = None
                    self.psbt_seed = None
                
                logger.info(f"\nback_stack: {self.back_stack}")

                try:
                    # Instantiate the View class and run it
                    logger.info(f"Executing {next_destination}")
                    next_destination = next_destination.run()

                except StopFlowBasedTest:
                    # This is a special exception that is only raised by the test suite
                    # to stop the Controller loop and exit the test.
                    return

                except FlowBasedTestException as e:
                    # This is a special exception that is only raised by the test suite.
                    # Re-raise so the test suite can handle it.
                    raise e

                except Exception as e:
                    # Display user-friendly error screen w/debugging info
                    import traceback
                    traceback.print_exc()
                    next_destination = self.handle_exception(e)

                if not next_destination:
                    # Should only happen during dev when you hit an unimplemented option
                    from seedsigner.views.view import NotYetImplementedView
                    next_destination = Destination(NotYetImplementedView)

                if next_destination.skip_current_view:
                    # Remove the current View from history; it's forwarding us straight
                    # to the next View so it should be as if this View never happened.
                    current_view = self.back_stack.pop()
                    logger.info(f"Skipping current view: {current_view}")

                # Hang on to this reference...
                clear_history = next_destination.clear_history

                if next_destination.View_cls == BackStackView:
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
                    logger.info(f"Appending next destination: {next_destination}")
                    self.back_stack.append(next_destination)
                else:
                    logger.info(f"NOT appending {next_destination}")

        finally:
            from seedsigner.gui.renderer import Renderer
            if self.is_screensaver_running:
                self.screensaver.stop()
            
            if self.toast_notification_thread and self.toast_notification_thread.is_alive():
                self.toast_notification_thread.stop()

            # Clear the screen when exiting
            logger.info("Clearing screen, exiting")
            Renderer.get_instance().display_blank_screen()


    @property
    def is_screensaver_running(self):
        return self.screensaver is not None and self.screensaver.is_running


    def start_screensaver(self):
        # If a toast is running, tell it to give up the Renderer.lock; it will then
        # block until the screensaver is done, at which point the toast can re-acquire
        # the Renderer.lock and resume where it left off.
        if self.toast_notification_thread and self.toast_notification_thread.is_alive():
            logger.info(f"Controller: settings toggle_render_lock for {self.toast_notification_thread.__class__.__name__}")
            self.toast_notification_thread.toggle_renderer_lock()

        logger.info("Controller: Starting screensaver")
        if not self.screensaver:
            # Do a lazy/late import and instantiation to reduce Controller initial startup time
            from seedsigner.views.screensaver import ScreensaverScreen
            from seedsigner.hardware.buttons import HardwareButtons
            self.screensaver = ScreensaverScreen(HardwareButtons.get_instance())
        
        # Start the screensaver, but it will block until it can acquire the Renderer.lock.
        self.screensaver.start()
        logger.info("Controller: Screensaver started")
    

    def reset_screensaver_timeout(self):
        """
        Reset the screensaver's timeout starting point to right now (i.e. make it think
        that zero time has elapsed since the last user interaction).
        """
        from seedsigner.hardware.buttons import HardwareButtons
        HardwareButtons.get_instance().update_last_input_time()


    def activate_toast(self, toast_manager_thread: BaseToastOverlayManagerThread):
        """
        Ensures that the Controller has explicit control over which processes get to
        claim the Renderer.lock and which need to (potentially) release it.
        """
        if self.is_screensaver_running:
            # New toast notifications break out of the Screensaver
            logger.info("Controller: stopping screensaver")
            self.screensaver.stop()

        if self.toast_notification_thread and self.toast_notification_thread.is_alive():
            # Can only run one toast at a time
            logger.info(f"Controller: stopping {self.toast_notification_thread.__class__.__name__}")
            self.toast_notification_thread.stop()
        
        self.toast_notification_thread = toast_manager_thread
        logger.info(f"Controller: starting {self.toast_notification_thread.__class__.__name__}")
        self.toast_notification_thread.start()


    def handle_exception(self, e) -> Destination:
        """
            Displays a user-friendly error screen and includes debugging info to help
            devs diagnose what went wrong.

            Shows:
                * Exception type
                * python file, line num, method name
                * Exception message
        """
        from seedsigner.views.view import UnhandledExceptionView
        logger.exception(e)

        # The final exception output line is:
        # "foo.bar.ExceptionType: The exception message"
        # So we extract the Exception type and trim off any "foo.bar." namespacing:
        last_line = traceback.format_exc().splitlines()[-1]
        exception_type = last_line.split(":")[0].split(".")[-1]

        # Extract the error message, if there is one
        if ":" in last_line:
            exception_msg = last_line.split(":")[1]
        else:
            exception_msg = ""

        # Scan for the last debugging line that includes a line number reference
        line_info = None
        for i in range(len(traceback.format_exc().splitlines()) - 1, 0, -1):
            traceback_line = traceback.format_exc().splitlines()[i]
            if ", line " in traceback_line:
                line_info = traceback_line.split("/")[-1].replace("\"", "").replace("line ", "")
                break
        
        error = [
            exception_type,
            line_info,
            exception_msg,
        ]
        return Destination(UnhandledExceptionView, view_args={"error": error}, clear_history=True)
