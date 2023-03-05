import sys
from dataclasses import dataclass
from mock import MagicMock, patch
from typing import Callable, List, Type, Union

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
        """ If settings were written to disk, delete """
        import os
        try:
            os.remove(Settings.SETTINGS_FILENAME)
        except:
            print(f"{Settings.SETTINGS_FILENAME} not found to be removed")


    def reset_controller(self):
        """ Wipe and re-initialize the Controller singleton for each test run """
        Controller._instance = None
        Controller.configure_instance()


    def setup_method(self):
        self.reset_controller()
        self.controller = Controller.get_instance()
        self.settings = Settings.get_instance()



@dataclass
class FlowStep:
    expected_view: Type[View] = None
    run_before: Callable = None
    screen_return_value: Union[int, str] = None



class FlowTest(BaseTest):
    def run_sequence(self, initial_destination: Destination, sequence: List[FlowStep]) -> Destination:
        """
            Runs the given sequence from the initial_destination, mocking out the associated
            Screen and the scenario's return_value, receiving the resulting new Destination,
            and repeating until the sequence is complete.

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
                    mock_run_screen.return_value = flow_step.screen_return_value

                    # Now we can run the View and grab its resulting next Destination
                    next_destination = next_destination.run(run_before=flow_step.run_before)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"{next_destination} | {flow_step}")
                raise e
        
        return next_destination
