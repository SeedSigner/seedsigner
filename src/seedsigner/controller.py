from typing import List
from embit.psbt import PSBT
from PIL.Image import Image
from seedsigner.gui.renderer import Renderer
from seedsigner.gui.screens.screen import WarningScreen
from seedsigner.hardware.buttons import HardwareButtons
from seedsigner.views.screensaver import ScreensaverView
from seedsigner.views.view import NotYetImplementedView

from .models import Seed, SeedStorage, Settings, Singleton, PSBTParser



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

    VERSION = "0.5.0 Pre-Release 2"

    # Declare class member vars with type hints to enable richer IDE support throughout
    # the code.
    buttons: HardwareButtons = None
    storage: SeedStorage = None
    settings: Settings = None
    renderer: Renderer = None

    psbt: PSBT = None
    psbt_seed: Seed = None
    psbt_parser: PSBTParser = None

    image_entropy_preview_frames: List[Image] = None
    image_entropy_final_image: Image = None


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

        # Store one working psbt in memory
        controller.psbt = None
        controller.psbt_parser = None

        # Configure the Renderer
        Renderer.configure_instance()

        controller.screensaver = ScreensaverView(controller.buttons)

        controller.back_stack = []

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
            raise Exception(f"There is no seed_num {seed_num}; only {len(self.storage.seeds)} in memory.")


    def discard_seed(self, seed_num: int):
        if seed_num < len(self.storage.seeds):
            del self.storage.seeds[seed_num]
        else:
            raise Exception(f"There is no seed_num {seed_num}; only {len(self.storage.seeds)} in memory.")


    def pop_prev_from_back_stack(self):
        from .views import Destination
        if len(self.back_stack) > 0:
            # Pop the top View (which is the current View_cls)
            self.back_stack.pop()

            if len(self.back_stack) > 0:
                # One more pop back gives us the actual "back" View_cls
                return self.back_stack.pop()
        return Destination(None)
    

    def clear_back_stack(self):
        self.back_stack = []


    def start(self) -> None:
        from .views import Destination, MainMenuView, BackStackView
        from .views.screensaver import OpeningSplashView

        opening_splash = OpeningSplashView()
        opening_splash.start()

        # TODO: Remove for v0.5.0 production release
        WarningScreen(
            title="Warning",
            status_headline="Pre-Release Code",
            text="Do not use this with real funds or to create new secure keys!",
            show_back_button=False,
        ).display()


        """ Class references can be stored as variables in python!

            This loop receives a View class to execute and stores it in the `View_cls`
            var along with any input arguments in the `init_args` dict.

            The `View_cls` is instantiated with `init_args` passed in and then run(). It
            returns either a new View class to execute next or None.

            Example:
                class MyView(View)
                    def run(self, some_arg, other_arg):
                        print(other_arg)

                class OtherView():
                    def run(self):
                        return (MyView, {"some_arg": 1, "other_arg": "hello"})

            When `OtherView` is instantiated and run, we capture its return values:

                (View_cls, init_args) = OtherView().run()

            And then we can instantiate and run that View class:

                View_cls(**init_args).run()
        """
        try:
            next_destination = Destination(MainMenuView)
            while True:
                # Destination(None) is a special case; render the Home screen
                if next_destination.View_cls is None:
                    next_destination = Destination(MainMenuView)

                if next_destination.View_cls == MainMenuView:
                    # Home always wipes the back_stack
                    self.clear_back_stack()

                print(f"Executing {next_destination}")
                next_destination = next_destination.run()

                if not next_destination:
                    # Should only happen during dev when you hit an unimplemented option
                    next_destination = Destination(NotYetImplementedView)

                if next_destination.skip_current_view:
                    # Remove the current View from history; it's forwarding us straight
                    # to the next View so it should be as if this View never happened.
                    self.back_stack.pop()

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
                self.back_stack.append(next_destination)

        finally:
            # Clear the screen when exiting
            Renderer.get_instance().display_blank_screen()


    def start_screensaver(self):
        self.screensaver.start()


"""



    ###
    ### Seed Tools Controller Naviation/Launcher
    ###


    ### Create a Seed w/ Dice Screen

    def show_create_seed_with_dice_tool(self) -> int:
        seed = Seed(wordlist=self.settings.wordlist)
        ret_val = True

        while True:
            seed.mnemonic = self.seed_tools_view.display_generate_seed_from_dice()
            if seed:
                break
            else:
                return Path.SEED_TOOLS_SUB_MENU

        # display seed phrase (24 words)
        while True:
            ret_val = self.seed_tools_view.display_seed_phrase(seed.mnemonic_list, show_qr_option=True)
            if ret_val == True:
                break
            else:
                # no-op; can't back out of the seed phrase view
                pass

        # Ask to save seed
        if self.storage.slot_avaliable():
            r = self.renderer.display_generic_selection_menu(["Yes", "No"], "Save Seed?")
            if r == 1: #Yes
                slot_num = self.menu_view.display_saved_seed_menu(self.storage,2,None)
                if slot_num in (1,2,3):
                    self.storage.add_seed(seed, slot_num)
                    self.renderer.draw_modal(["Seed Valid", "Saved to Slot #" + str(slot_num)], "", "Right to Main Menu")
                    input = self.buttons.wait_for([B.KEY_RIGHT])

        return Path.MAIN_MENU


"""