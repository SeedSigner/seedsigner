import logging

import pytest
from unittest.mock import patch, call

from seedsigner.main import main


@patch("seedsigner.main.Controller")
def test_main__argparse__default(patched_controller):
    main([])
    assert logging.root.level == 20
    assert logging.getLogger().getEffectiveLevel() == 20
    patched_controller.assert_has_calls(
        [call.get_instance(), call.get_instance().start()]
    )


@patch("seedsigner.main.Controller")
def test_main__argparse__enable_debug_logging(patched_controller):
    main(["--loglevel", "DEBUG"])
    assert logging.root.level == 10
    assert logging.getLogger().getEffectiveLevel() == 10
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
