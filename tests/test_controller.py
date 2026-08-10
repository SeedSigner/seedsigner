import pytest

# Must import this before the Controller
from base import BaseTest

from seedsigner.controller import Controller


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


    def test_clear_hybrid_entropy_wipes_secret_values(self):
        controller = Controller.get_instance()
        camera_value = bytearray(range(32))
        dice_value = bytearray(reversed(range(32)))
        controller.hybrid_entropy_camera_value = camera_value
        controller.hybrid_entropy_camera_commitment = bytes([7]) * 32
        controller.hybrid_entropy_dice_value = dice_value

        controller.clear_hybrid_entropy()

        assert controller.hybrid_entropy_camera_value is None
        assert controller.hybrid_entropy_camera_commitment is None
        assert controller.hybrid_entropy_dice_value is None
        assert camera_value == bytearray(32)
        assert dice_value == bytearray(32)


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
