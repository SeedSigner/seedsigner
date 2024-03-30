import pytest

# Must import this before the Controller
from base import BaseTest

from seedsigner.controller import Controller
from seedsigner.models.settings_definition import SettingsConstants


class TestController(BaseTest):

    def test_reset_controller(self):
        """ The reset_controller util should completely reset the Controller singleton """
        controller = Controller.get_instance()
        controller.address_explorer_data = "foo"

        BaseTest.reset_controller()
        controller = Controller.get_instance()
        assert controller.address_explorer_data is None


    def test_singleton_init_fails(self):
        """ The Controller should not allow any code to instantiate it via Controller() """
        with pytest.raises(Exception):
            c = Controller()


    def test_handle_exception(reset_controller):
        """ Handle exceptions that get caught by the controller """

        def process_exception_asserting_valid_error(exception_type, exception_msg=None):
            """
            Exceptions caught by the controller are forwarded to the
            UnhandledExceptionView with view_args["error"] being a list
            of three strings, ie: [exception_type, line_info, exception_msg]
            """
            try:
                if exception_msg:
                    raise exception_type(exception_msg)
                else:
                    raise exception_type()
            except Exception as e:
                error = controller.handle_exception(e).view_args["error"]

            # assert that error structure is valid
            assert len(error) == 3
            assert error[0] in str(exception_type)
            assert type(error[1]) == str
            if exception_msg:
                assert exception_msg in error[2]
            else:
                assert error[2] == ""

        # Initialize the controller
        controller = Controller.get_instance()

        exception_tests = [
            # exceptions with an exception_msg
            (Exception, "foo"),
            (KeyError, "key not found"),
            # exceptions without an exception_msg
            (Exception, ""),
            (Exception, None),
        ]
            
        for exception_type, exception_msg in exception_tests:
            process_exception_asserting_valid_error(exception_type, exception_msg)


    def test_singleton_get_instance_preserves_state(self):
        """ Changes to the Controller singleton should be preserved across calls to get_instance() """

        # Initialize the instance and verify that it read the config settings
        controller = Controller.get_instance()
        assert controller.unverified_address is None

        # Change a value in the instance...
        controller.unverified_address = "123abc"

        # ...get a new copy of the instance and confirm change
        controller = Controller.get_instance()
        assert controller.unverified_address == "123abc"


    def test_missing_settings_get_defaults(self):
        """ Should gracefully handle all missing fields from `settings.json` """

        controller = Controller.get_instance()

        # Settings defaults
        assert controller.settings.get_value(SettingsConstants.SETTING__LANGUAGE) == SettingsConstants.LANGUAGE__ENGLISH
        assert controller.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE) == SettingsConstants.WORDLIST_LANGUAGE__ENGLISH
        assert controller.settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS) == SettingsConstants.OPTION__DISABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__COORDINATORS) == [i for i,j in SettingsConstants.ALL_COORDINATORS if i!="kpr"]
        assert controller.settings.get_value(SettingsConstants.SETTING__BTC_DENOMINATION) == SettingsConstants.BTC_DENOMINATION__THRESHOLD

        # Advanced Settings defaults
        assert controller.settings.get_value(SettingsConstants.SETTING__NETWORK) == SettingsConstants.MAINNET
        assert controller.settings.get_value(SettingsConstants.SETTING__QR_DENSITY) == SettingsConstants.DENSITY__MEDIUM
        assert controller.settings.get_value(SettingsConstants.SETTING__XPUB_EXPORT) == SettingsConstants.OPTION__ENABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__SIG_TYPES) == [i for i,j in SettingsConstants.ALL_SIG_TYPES]
        assert controller.settings.get_value(SettingsConstants.SETTING__SCRIPT_TYPES) == [SettingsConstants.NATIVE_SEGWIT, SettingsConstants.NESTED_SEGWIT, SettingsConstants.TAPROOT]
        assert controller.settings.get_value(SettingsConstants.SETTING__XPUB_DETAILS) == SettingsConstants.OPTION__ENABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__PASSPHRASE) == SettingsConstants.OPTION__ENABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__CAMERA_ROTATION) == SettingsConstants.CAMERA_ROTATION__180
        assert controller.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR) == SettingsConstants.OPTION__ENABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__BIP85_CHILD_SEEDS) == SettingsConstants.OPTION__DISABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__MESSAGE_SIGNING) == SettingsConstants.OPTION__DISABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__PRIVACY_WARNINGS) == SettingsConstants.OPTION__ENABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__ENABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__QR_BRIGHTNESS_TIPS) == SettingsConstants.OPTION__ENABLED
        assert controller.settings.get_value(SettingsConstants.SETTING__PARTNER_LOGOS) == SettingsConstants.OPTION__ENABLED

        # Hidden Settings defaults
        assert controller.settings.get_value(SettingsConstants.SETTING__QR_BRIGHTNESS) == 62

