import configparser
import pytest
from mock import MagicMock
from seedsigner.controller import Controller
from seedsigner.models.settings import Settings



def test_singleton_init_fails():
    """ The Controller should not allow any code to instantiate it via Controller() """
    with pytest.raises(Exception):
        c = Controller()

def test_singleton_get_instance_without_configure_fails():
    """ Calling get_instance() without first calling configure_instance() should fail """
    with pytest.raises(Exception):
        c = Controller.get_instance()

def test_singleton_get_instance_preserves_state():
    """ Changes to the Controller singleton should be preserved across calls to get_instance() """

    # Must reset Singleton instances; pytest cannot properly isolate Singletons for us
    # automatically.
    # TODO: Cleaner solution here would be nice.
    Settings._instance = None
    Controller._instance = None

    settings = """
        [system]
        debug = False
        default_language = en
        persistent_settings = False

        [display]
        text_color = ORANGE
        qr_background_color = FFFFFF
        camera_rotation = 0

        [wallet]
        network = main
        software = Prompt
        qr_density = 2
        custom_derivation = m/0/0
        compact_seedqr_enabled = False
    """
    config = configparser.ConfigParser()
    config.read_string(settings)

    # Initialize the instance and verify that it read the config settings
    Controller.configure_instance(config, disable_hardware=True)
    controller = Controller.get_instance()
    assert controller.color == "ORANGE"

    # Change a value in the instance...
    controller.color = "purple"

    # ...get a new copy of the instance and confirm change
    controller = Controller.get_instance()
    assert controller.color == "purple"


def test_missing_settings_get_defaults():
    """ Should gracefully handle any missing fields from `settings.ini` """
    # TODO: This is not complete; currently only handles missing compact_seedqr_enabled.

    # Must reset Singleton instances; pytest cannot properly isolate Singletons for us
    # automatically.
    # TODO: Cleaner solution here would be nice.
    Settings._instance = None
    Controller._instance = None

    # Intentionally omit `compact_seedqr_enabled` from settings:
    settings = """
        [system]
        debug = False
        default_language = en
        persistent_settings = False

        [display]
        text_color = ORANGE
        qr_background_color = FFFFFF
        camera_rotation = 0

        [wallet]
        network = main
        software = Prompt
        qr_density = 2
        custom_derivation = m/0/0
    """
    config = configparser.ConfigParser()
    config.read_string(settings)

    # Controller should parse the settings fine, even though a field is missing
    Controller.configure_instance(config, disable_hardware=True)

    # Controller should still have a default value
    controller = Controller.get_instance()
    assert controller.settings.compact_seedqr_enabled is False
