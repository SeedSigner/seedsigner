import configparser
import pytest
from mock import MagicMock
from seedsigner.controller import Controller
from seedsigner.models.settings_definition import SettingsConstants



@pytest.fixture(scope="module")
def reset_controller():
    Controller._instance = None
    Controller.configure_instance(disable_hardware=True)
    yield Controller

    
def test_singleton_init_fails(reset_controller):
    """ The Controller should not allow any code to instantiate it via Controller() """
    with pytest.raises(Exception):
        c = Controller()


def test_singleton_get_instance_preserves_state(reset_controller):
    """ Changes to the Controller singleton should be preserved across calls to get_instance() """

    # Initialize the instance and verify that it read the config settings
    controller = Controller.get_instance()
    assert controller.unverified_address is None

    # Change a value in the instance...
    controller.unverified_address = "123abc"

    # ...get a new copy of the instance and confirm change
    controller = Controller.get_instance()
    assert controller.unverified_address == "123abc"


def test_missing_settings_get_defaults(reset_controller):
    """ Should gracefully handle any missing fields from `settings.ini` """
    # TODO: This is not complete; currently only handles missing compact_seedqr_enabled.

    # Controller should still have a default value
    controller = Controller.get_instance()
    assert controller.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR) == SettingsConstants.OPTION__DISABLED
