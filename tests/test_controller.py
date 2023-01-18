import configparser
import pytest
from mock import MagicMock
from seedsigner.controller import Controller
from seedsigner.hardware.microsd import MicroSD
from seedsigner.models.settings_definition import SettingsConstants



def test_singleton_init_fails():
    """ The Controller should not allow any code to instantiate it via Controller() """
    with pytest.raises(Exception):
        c = Controller()


def test_singleton_get_instance_preserves_state():
    """ Changes to the Controller singleton should be preserved across calls to get_instance() """

    # Must reset Singleton instances; pytest cannot properly isolate Singletons for us
    # automatically.
    # TODO: Cleaner solution here would be nice.
    MicroSD._instance = None
    Controller._instance = None

    # Initialize the instance and verify that it read the config settings
    Controller.configure_instance(disable_hardware=True)
    controller = Controller.get_instance()
    assert controller.unverified_address is None

    # Change a value in the instance...
    controller.unverified_address = "123abc"

    # ...get a new copy of the instance and confirm change
    controller = Controller.get_instance()
    assert controller.unverified_address == "123abc"


def test_missing_settings_get_defaults():
    """ Should gracefully handle any missing fields from `settings.ini` """
    # TODO: This is not complete; currently only handles missing compact_seedqr_enabled.

    # Must reset Singleton instances; pytest cannot properly isolate Singletons for us
    # automatically.
    # TODO: Cleaner solution here would be nice.
    MicroSD._instance = None
    Controller._instance = None

    # Controller should parse the settings fine, even though a field is missing
    Controller.configure_instance(disable_hardware=True)

    # Controller should still have a default value
    controller = Controller.get_instance()
    assert controller.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR) == SettingsConstants.OPTION__ENABLED

