import logging
import pytest
import sys
from unittest.mock import patch, call

# Must import from base.py before any other SeedSigner dependency to mock out certain imports
from base import BaseTest

sys.path.insert(0,'src')
from main import main


class TestMain(BaseTest):
    """
    The `main.Controller` has to be patched / mocked out otherwise the virtual SeedSigner
    will just keep running and cause the test to hang.
    """
    @patch("main.Controller")
    def test_main__argparse__default(self, patched_controller):
        main([])
        assert logging.root.level == logging.INFO
        assert logging.getLogger().getEffectiveLevel() == logging.INFO
        patched_controller.assert_has_calls(
            [call.get_instance(), call.get_instance().start()]
        )


    @patch("main.Controller")
    def test_main__argparse__enable_debug_logging(self, patched_controller):
        main(["--loglevel", "DEBUG"])
        assert logging.root.level == logging.DEBUG
        assert logging.getLogger().getEffectiveLevel() == logging.DEBUG
        patched_controller.assert_has_calls(
            [call.get_instance(), call.get_instance().start()]
        )


    def test_main__argparse__invalid_arg(self):
        with pytest.raises(SystemExit):
            main(["--invalid"])


    @patch("main.Controller")
    def test_main__logging__writes_to_stderr(self, patched_controller, capsys):
        main([])
        _, err = capsys.readouterr()
        assert "Starting SeedSigner" in err and "INFO" in err
        patched_controller.assert_has_calls(
            [call.get_instance(), call.get_instance().start()]
        )