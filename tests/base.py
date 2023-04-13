import sys
from dataclasses import dataclass
from mock import MagicMock, patch
from typing import Callable

# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.gui.renderer'] = MagicMock()
sys.modules['seedsigner.gui.screens.screensaver'] = MagicMock()
sys.modules['seedsigner.views.screensaver'] = MagicMock()
sys.modules['seedsigner.hardware.buttons'] = MagicMock()
sys.modules['seedsigner.hardware.camera'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()

from seedsigner.controller import Controller, StopControllerCommand
from seedsigner.models import Settings
from seedsigner.views.view import Destination, MainMenuView, View



class BaseTest:

    @classmethod
    def setup_class(cls):
        # Ensure there are no on-disk artifacts after running tests.
        Settings.SETTINGS_FILENAME = "settings-test.json"

        # Mock out the loading screen so it can't spawn.
        patch('seedsigner.gui.screens.screen.LoadingScreenThread').start()


    @classmethod
    def teardown_class(cls):
        pass


    @classmethod
    def reset_settings(cls):
        """ Wipe and re-initialize the Settings singleton """
        Settings._instance = None
        BaseTest.remove_settings()


    @classmethod
    def remove_settings(cls):
        """ If settings were written to disk, delete """
        import os
        try:
            if os.path.exists(Settings.SETTINGS_FILENAME):
                os.remove(Settings.SETTINGS_FILENAME)
        except:
            print(f"{Settings.SETTINGS_FILENAME} not found to be removed")


    @classmethod
    def reset_controller(cls):
        """ Wipe and re-initialize the Controller singleton """
        Controller._instance = None
        Controller.configure_instance()


    def setup_method(self):
        """ Guarantee a clean/default Controller and Settings state for each test case """
        BaseTest.reset_controller()
        BaseTest.reset_settings()
        self.controller = Controller.get_instance()
        self.settings = Settings.get_instance()
    

    def teardown_method(self):
        BaseTest.remove_settings()



@dataclass
class FlowStep:
    """ 
        Trivial helper class to express FlowTest sequences below.

        * expected_view:         verify that the current step in the sequence instantiates the right View.
        * run_before:            function that takes a View instance as an arg and modifies it before running the View.
        * screen_return_value:   mocked Screen interaction result: raw return value as if from the Screen.
        * button_data_selection: mocked Screen interaction result: the View.button_data value of the desired option.
    """
    expected_view: type[View] = None
    run_before: Callable[[View], None] = None
    screen_return_value: int | str = None
    button_data_selection: str | tuple = None
    is_redirect: bool = False

    def __post_init__(self):
        if self.screen_return_value is not None and self.button_data_selection is not None:
            raise Exception("Can't specify both `screen_return_value` and `button_data_selection`")



class FlowDidNotExpectView(AssertionError):
    """ Raised when the FlowTest sequence does not match the View that was run. """
    pass



class FlowTest(BaseTest):
    """ Base class for any tests that do flow-based testing """

    def run_sequence(self, sequence: list[FlowStep], initial_destination_view_args: dict = None) -> None:
        """
        Run a pre-set sequence of Views w/manually-specified return values in order to test
        the Controller's flow control logic and the routing from View to View.
        """
        def verify_next_View_cls_and_run_view(destination: Destination, *args, **kwargs):
            if len(sequence) == 0:
                # We've reached the end of the sequence, so raise StopControllerCommand
                # to stop the Controller and exit the test.
                raise StopControllerCommand()

            # Verify that the View class specified in the test sequence matches the
            # View class that is being run.
            if destination.View_cls != sequence[0].expected_view:
                raise FlowDidNotExpectView(f"Expected {sequence[0].expected_view}, got {destination.View_cls}")

            # Run the optional pre-run function to modify the View.
            if sequence[0].run_before:
                sequence[0].run_before(destination.view)

            if sequence[0].is_redirect:
                # The current View is going to auto-redirect without calling run_screen(),
                # so we need to remove the current step from the sequence before the
                # View.run() call below.
                sequence.pop(0)

            # Some Views reach into their Screen's variables directly (e.g. 
            # Screen.buttons to preserve the scroll position), so we need to mock out the
            # Screen instance that is created by the View.
            destination.view.screen = MagicMock()

            # Run the View (we're mocking out View._run_view() so the Destination
            # won't actually run the View unless we explicitly do so here).
            return destination.view.run()


        def next_return_value(view: View, *args, **kwargs):
            # Return the return value specified in the test sequence and
            # remove the completed test step from the sequence.
            flow_step = sequence.pop(0)
            if flow_step.button_data_selection:
                return view.button_data.index(flow_step.button_data_selection)
            elif type(flow_step.screen_return_value) in [StopControllerCommand, Exception]:
                raise flow_step.screen_return_value
            return flow_step.screen_return_value


        with patch("seedsigner.views.view.Destination._run_view", autospec=True) as mock_run_view:
            # Mock out the View._run_view() method so we can verify the View class
            # that is specified in the test sequence and then run the View.
            mock_run_view.side_effect = verify_next_View_cls_and_run_view

            with patch("seedsigner.views.view.View.run_screen", autospec=True) as mock_run_screen:
                # Mock out the View.run_screen() method so we can provide the
                # return value that is specified in the test sequence.
                mock_run_screen.side_effect = next_return_value

                # Start the Controller with the first View_cls specified in the test sequence
                if sequence[0].expected_view != MainMenuView:
                    initial_destination = Destination(sequence[0].expected_view, view_args=initial_destination_view_args)
                else:
                    initial_destination = None

                # Start the Controller and run the sequence
                Controller.get_instance().start(initial_destination=initial_destination)


