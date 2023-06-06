import pytest
from lumensigner.hardware.microsd import MicroSD
from lumensigner.controller import Controller
from lumensigner.models.settings_definition import SettingsConstants


@pytest.fixture()
def reset_controller():
    """fixture to setup, then yield to run test, then tear down"""

    # setup
    Controller.configure_instance(disable_hardware=True)

    # yield to run a single test
    yield

    # tear down
    MicroSD._instance = None
    Controller._instance = None


def test_singleton_init_fails(reset_controller):
    """The Controller should not allow any code to instantiate it via Controller()"""
    with pytest.raises(Exception):
        c = Controller()


def test_singleton_get_instance_preserves_state(reset_controller):
    """Changes to the Controller singleton should be preserved across calls to get_instance()"""

    # Initialize the instance and verify that it read the config settings
    controller = Controller.get_instance()
    assert controller.resume_main_flow is None

    # Change a value in the instance...
    controller.resume_main_flow = Controller.FLOW__SIGN_TX

    # ...get a new copy of the instance and confirm change
    controller = Controller.get_instance()
    assert controller.resume_main_flow == Controller.FLOW__SIGN_TX


def test_missing_settings_get_defaults(reset_controller):
    """Should gracefully handle all missing fields from `settings.json`"""

    controller = Controller.get_instance()

    # Settings defaults
    assert (
            controller.settings.get_value(SettingsConstants.SETTING__LANGUAGE)
            == SettingsConstants.LANGUAGE__ENGLISH
    )
    assert (
            controller.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
            == SettingsConstants.WORDLIST_LANGUAGE__ENGLISH
    )
    assert (
            controller.settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS)
            == SettingsConstants.OPTION__DISABLED
    )

    assert (
            controller.settings.get_value(SettingsConstants.SETTING__QR_DENSITY)
            == SettingsConstants.DENSITY__MEDIUM
    )
    assert (
            controller.settings.get_value(SettingsConstants.SETTING__PASSPHRASE)
            == SettingsConstants.OPTION__ENABLED
    )
    assert (
            controller.settings.get_value(SettingsConstants.SETTING__CAMERA_ROTATION)
            == SettingsConstants.CAMERA_ROTATION__0
    )
    assert (
            controller.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR)
            == SettingsConstants.OPTION__ENABLED
    )
    assert (
            controller.settings.get_value(SettingsConstants.SETTING__PRIVACY_WARNINGS)
            == SettingsConstants.OPTION__ENABLED
    )
    # Hidden Settings defaults
    assert (
            controller.settings.get_value(SettingsConstants.SETTING__QR_BRIGHTNESS) == 189
    )
