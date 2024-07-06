import pytest
from unittest.mock import patch, call

# Must import this before anything else that imports the Controller
import base

from seedsigner.main import main


@patch("seedsigner.main.logging.basicConfig")
@patch("seedsigner.main.Controller")
def test_main__argparse__default(patched_controller, patched_logging):
    main([])
    patched_logging.assert_called_once_with(
        level=20,
        format="%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    patched_controller.assert_has_calls(
        [call.get_instance(), call.get_instance().start()]
    )


@patch("seedsigner.main.logging.basicConfig")
@patch("seedsigner.main.Controller")
def test_main__argparse__enable_debug_logging(patched_controller, patched_logging):
    main(["--loglevel", "DEBUG"])
    patched_logging.assert_called_once_with(
        level=10,
        format="%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    patched_controller.assert_has_calls(
        [call.get_instance(), call.get_instance().start()]
    )


def test_main__argparse__invalid_arg():
    with pytest.raises(SystemExit):
        main(["--invalid"])


@patch("seedsigner.main.Controller")
def test_main__logging__writes_to_stderr(patched_controller, capsys):
    main([])
    _, err = capsys.readouterr()
    assert "INFO:	Starting Seedsigner with: {'loglevel': 'INFO'}" in err
