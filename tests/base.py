import sys
from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch
from typing import Callable

# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.gui.renderer'] = MagicMock()
sys.modules['seedsigner.gui.screens.screensaver'] = MagicMock()
sys.modules['seedsigner.gui.toast'] = MagicMock()
sys.modules['seedsigner.views.screensaver'] = MagicMock()
sys.modules['seedsigner.hardware.buttons'] = MagicMock()
sys.modules['seedsigner.hardware.camera'] = MagicMock()

from seedsigner.controller import Controller, FlowBasedTestException, StopFlowBasedTest
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, RET_CODE__POWER_BUTTON, ButtonOption
from seedsigner.hardware.microsd import MicroSD
from seedsigner.models.settings import Settings
from seedsigner.views.view import Destination, MainMenuView, UnhandledExceptionView, View

import logging
logger = logging.getLogger(__name__)



class BaseTest:

    class MockMicroSD(Mock):
        """
        A test suite-friendly replacement for `MicroSD` that gives a test explicit
        control over the reported state of the SD card.
        """
        # Tests are free to directly manipulate this attribute as needed (it's reset to
        # True before each test in `BaseTest.setup_method()`).
        is_inserted: bool = True


    @classmethod
    def setup_class(cls):
        # Ensure there are no on-disk artifacts after running tests.
        Settings.SETTINGS_FILENAME = "settings-test.json"

        # Mock out the loading screen so it can't spawn. View classes must import locally!
        patch('seedsigner.gui.screens.screen.LoadingScreenThread').start()

        # Instantiate the mocked MicroSD; hold on to the instance so tests can manipulate
        # it later.
        cls.mock_microsd = BaseTest.MockMicroSD()

        # And mock it over `MicroSD`'s instance
        MicroSD.get_instance = Mock(return_value=cls.mock_microsd)


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
            print(f"{Settings.SETTINGS_FILENAME} could not be removed")


    @classmethod
    def reset_controller(cls):
        """ Wipe and re-initialize the Controller singleton """
        Controller._instance = None
        Controller.configure_instance()


    def setup_method(self):
        """ Guarantee a clean/default Controller, Settings, & MicroSD state for each test case """
        BaseTest.reset_controller()
        BaseTest.reset_settings()
        self.controller = Controller.get_instance()
        self.settings = Settings.get_instance()
        self.mock_microsd.is_inserted = True
    

    def teardown_method(self):
        BaseTest.remove_settings()



class TestBaseTest(BaseTest):
    def test_howto_log_from_test(self):
        """
            Not actually a test, just a demonstration of how to use/access logs while
            testing.

            Enable log visibility by running with:
                --log-cli-level=NOTSET (or the level of your choice)
                -o log_cli=1
            
            Enable print() visibility by running with:
                -s or --capture=no
        """
        print("This is a test print message")
        logger.info("This is a test log message")
        logger.debug("This is a test debug message")
        logger.warning("This is a test warning message")
        logger.error("This is a test error message")
        logger.critical("This is a test critical message")



@dataclass
class FlowStep:
    """ 
        Trivial helper class to express FlowTest sequences below.

        * expected_view:         verify that the current step in the sequence instantiates the right View.
        * before_run:            function that takes a View instance as an arg and modifies it before running the View.
        * screen_return_value:   mocked Screen interaction result: raw return value as if from the Screen.
        * button_data_selection: mocked Screen interaction result: the View.button_data value of the desired option.
        * is_redirect:           expects the Destination to specify `skip_current_view=True`.
    """
    expected_view: type[View] = None
    before_run: Callable[[View], None] = None
    screen_return_value: int | str = None
    button_data_selection: str | tuple = None
    is_redirect: bool = False

    def __post_init__(self):
        if self.screen_return_value is not None and self.button_data_selection is not None:
            raise Exception("Can't specify both `screen_return_value` and `button_data_selection`")



class FlowTestInvalidButtonDataInstanceTypeException(FlowBasedTestException):
    """ The button_data contained an item that was not a ButtonOption instance """
    pass



class FlowTestInvalidButtonDataSelectionException(FlowBasedTestException):
    """ The FlowStep's button_data_selection value was not found in the View's button_data """
    pass



class FlowTestUnexpectedViewException(FlowBasedTestException):
    """ The Controller's current View did not match the expected View in the FlowStep sequence """
    pass



class FlowTestUnexpectedRedirectException(FlowBasedTestException):
    """ The Controller's current View triggered a redirect that was not expected by the current FlowStep in the sequence """
    pass


class FlowTestMissingRedirectException(FlowBasedTestException):
    """ The Controller's current View did NOT trigger a redirect when one was expected by the current FlowStep in the sequence """
    pass


class FlowTest(BaseTest):
    """ Base class for any tests that do flow-based testing """

    def stop_test(self):
        """ Raise our special Exception to stop the test """
        raise StopFlowBasedTest()


    def run_sequence(self, sequence: list[FlowStep], initial_destination_view_args: dict = None) -> None:
        """
        Run a pre-set sequence of Views w/manually-specified return values in order to test
        the Controller's flow control logic and the routing from View to View.
        """
        with patch("seedsigner.views.view.Destination._run_view", autospec=True) as mock_run_view:
            with patch("seedsigner.views.view.View.run_screen", autospec=True) as mock_run_screen:
                def run_view(destination: Destination, *args, **kwargs):
                    """ Replaces Destination._run_view() """
                    if len(sequence) == 0:
                        # Nothing left to do.
                        self.stop_test()

                    cur_flow_step = sequence[0]

                    # Verify that the View class specified in the test sequence matches the
                    # View class that is being run.
                    if destination.View_cls != cur_flow_step.expected_view:
                        raise FlowTestUnexpectedViewException(f"Expected {cur_flow_step.expected_view}, got {destination.View_cls}")
                    
                    if len(sequence) == 1:
                        # This is the last step in the sequence
                        if cur_flow_step.screen_return_value is None and cur_flow_step.button_data_selection is None:
                            # This is the last View in the sequence and it doesn't specify any
                            # user-mimicking interactions for the Screen. Nothing left to do.
                            self.stop_test()

                    try:
                        if cur_flow_step.is_redirect and destination.view.has_redirect:
                            # Right upon instantiation, the View set its own redirect without
                            # needing to wait for its run() method to be called.

                            # TODO: Migrate all View redirects to use `View.set_redirect()`
                            # in their `__init__()` rather than `run()` and then refactor
                            # here to explicitly require `has_redirect` to be True.
                            # For now: Support the newer `set_redirect()` routing while
                            # still letting redirects get returned by `View.run()` further
                            # below.
                            return destination.view.get_redirect()

                        # Run the optional pre-run function to modify the View.
                        if cur_flow_step.before_run:
                            cur_flow_step.before_run(destination.view)

                        # Some Views reach into their Screen's variables directly (e.g. 
                        # Screen.buttons to preserve the scroll position), so we need to mock out the
                        # Screen instance that is created by the View.
                        destination.view.screen = MagicMock()

                        prev_mock_run_screen_call_count = mock_run_screen.call_count

                        # Run the View (with our mocked run_screen) and get the next Destination that results
                        destination = destination.view.run()

                        if mock_run_screen.call_count == prev_mock_run_screen_call_count and cur_flow_step.is_redirect is not True:
                            # The current View redirected without calling run_screen()
                            # but we weren't expecting it.
                            raise FlowTestUnexpectedRedirectException(f"Unexpected redirect to {destination.View_cls}")

                        elif mock_run_screen.call_count > prev_mock_run_screen_call_count and cur_flow_step.is_redirect:
                            # The View ran its Screen, but the current FlowStep was expecting it
                            # to redirect (is_redirect=True) *instead of* running its Screen.
                            raise FlowTestMissingRedirectException(f"FlowStep expected redirect but {cur_flow_step.expected_view} did not redirect")

                    finally:
                        # Regardless of the outcome, we always move our FlowTest
                        # sequence forward.
                        sequence.pop(0)

                    return destination


                def run_screen(view: View, *args, **kwargs):
                    """
                    Replaces View.run_screen().

                    Just returns the return value specified in the test sequence.
                    """
                    cur_flow_step = sequence[0]

                    if "button_data" in kwargs:
                        # Verify that they are all proper ButtonOption instances
                        for button_option in kwargs.get("button_data"):
                            if not isinstance(button_option, ButtonOption):
                                raise FlowTestInvalidButtonDataInstanceTypeException(f"button_data must be a list of ButtonOption instances, not {type(button_option)}: {button_option}")

                    if cur_flow_step.button_data_selection:
                        # We're mocking out the View.run_screen() method, so we'll get all of the
                        # input args that are normally passed into the Screen.run() method,
                        # including the button_data kwarg.
                        if "button_data" in kwargs:
                            if cur_flow_step.button_data_selection not in kwargs.get("button_data") and cur_flow_step.button_data_selection not in [RET_CODE__BACK_BUTTON, RET_CODE__POWER_BUTTON]:
                                raise FlowTestInvalidButtonDataSelectionException(f"'{cur_flow_step.button_data_selection}' not found in button_data: {kwargs.get('button_data')}")
                            return kwargs.get("button_data").index(cur_flow_step.button_data_selection)
                        else:
                            raise Exception(f"Can't specify `FlowStep.button_data_selection` if `button_data` isn't a kwarg in {view.__class__.__name__}'s run_screen()")

                    elif type(cur_flow_step.screen_return_value) in [StopFlowBasedTest, FlowBasedTestException]:
                        raise cur_flow_step.screen_return_value
                    
                    elif isinstance(cur_flow_step.screen_return_value, Exception):
                        # The FlowStep wants to mimic the Screen raising an exception.
                        raise cur_flow_step.screen_return_value

                    return cur_flow_step.screen_return_value


                # Mock out the Destination._run_view() method so we can verify the View class
                # that is specified in the test sequence and then run the View.
                mock_run_view.side_effect = run_view

                # Mock out the View.run_screen() method so we can provide the
                # return value that is specified in the test sequence.
                mock_run_screen.side_effect = run_screen

                # Start the Controller with the first View_cls specified in the test sequence
                if sequence[0].expected_view != MainMenuView:
                    initial_destination = Destination(sequence[0].expected_view, view_args=initial_destination_view_args)
                else:
                    initial_destination = None

                # Start the Controller and run the sequence
                Controller.get_instance().start(initial_destination=initial_destination)
