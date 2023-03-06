import sys
from dataclasses import dataclass
from mock import MagicMock, patch
from typing import Callable, List, Tuple, Type, Union

# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.gui.renderer'] = MagicMock()
sys.modules['seedsigner.gui.screens.screensaver'] = MagicMock()
sys.modules['seedsigner.hardware.buttons'] = MagicMock()
sys.modules['seedsigner.hardware.camera'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()

from seedsigner.controller import Controller
from seedsigner.models import Settings
from seedsigner.views.view import Destination, View



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

        * expected_view:         verify that the next step in the sequence ended up at the right View.
        * run_before:            function that takes a View instance as an arg and modifies it before running the View.
        * screen_return_value:   mocked Screen interaction result: raw return value as if from the Screen.
        * button_data_selection: mocked Screen interaction result: the View.button_data value of the desired option.
    """
    expected_view: Type[View] = None
    run_before: Callable = None
    screen_return_value: Union[int,str] = None
    button_data_selection: Union[str,Tuple] = None

    def __post_init__(self):
        if self.screen_return_value is not None and self.button_data_selection is not None:
            raise Exception("Should only specify screen_return_value or button_data_selection")



class FlowTest(BaseTest):
    """ Base class for any tests that do flow-based testing """

    def run_sequence(self, initial_destination: Destination, sequence: List[FlowStep]) -> Destination:
        """
            Runs the given sequence of FlowSteps starting from the initial_destination:
            * verifies that we landed on the expected_view (if provided).
            * mocks out the `View.run_screen()` to prevent the associated Screen class from instantiating.
            * patches in the FlowStep's screen_return_value (as if it came from user interaction).
            * OR retrieves the index number of the specified button_data_selection and provides that as the Screen return value.
            * optional `run_before` method modifies the View when necessary to be compatible w/test suite limitations.
            * Runs the View and receives the resulting next Destination.
            * then repeats the process on the next Destination until the sequence is complete.

            Returns the final Destination.
        """
        next_destination = initial_destination
        for flow_step in sequence:
            try:
                # Validate that the next Destination's View is what we expected
                if flow_step.expected_view:
                    assert next_destination.View_cls == flow_step.expected_view

                # Patch the `View.run_screen()` so we don't actually instantiate the Screen
                qualname = ".".join([next_destination.View_cls.__module__, next_destination.View_cls.__name__])
                with patch(qualname + ".run_screen") as mock_run_screen:
                    next_destination._instantiate_view()

                    if flow_step.run_before:
                        flow_step.run_before(next_destination.view)
                    
                    if flow_step.button_data_selection:
                        mock_run_screen.return_value = next_destination.view.button_data.index(flow_step.button_data_selection)
                    else:
                        mock_run_screen.return_value = flow_step.screen_return_value

                    # Now we can run the View and grab its resulting next Destination
                    next_destination = next_destination._run_view()
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"{next_destination} | {flow_step}")
                raise e
        
        return next_destination
