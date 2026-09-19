import os
import subprocess
from unittest.mock import patch, MagicMock, call

import pytest
from PIL import Image

from seedsigner.helpers.qr import QR



class TestQrimageIoSecurity:
    """Tests for shell injection prevention and temp file cleanup in QR.qrimage_io().

    qrimage_io shells out to the `qrencode` binary. The previous implementation
    passed user-controlled data directly into a shell command string, enabling
    shell injection via crafted QR payloads (see issue #872). These tests verify
    the hardened implementation.
    """

    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_subprocess_called_without_shell(self, mock_run, mock_open, mock_unlink):
        """subprocess.run must be called with an argument list, never with shell=True."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_img = MagicMock()
        mock_open.return_value.resize.return_value.convert.return_value = mock_img

        qr = QR()
        qr.qrimage_io("test data")

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args

        # First positional arg must be a list (not a string)
        assert isinstance(args[0], list), "subprocess.run must receive an argument list, not a string"

        # shell=True must never be passed
        assert kwargs.get("shell") is not True, "shell=True must not be used"


    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_data_passed_via_stdin(self, mock_run, mock_open, mock_unlink):
        """Data must be passed via stdin to avoid exposure in the process list
        and to prevent shell metacharacter interpretation."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_open.return_value.resize.return_value.convert.return_value = MagicMock()

        qr = QR()
        test_data = "some sensitive xpub data"
        qr.qrimage_io(test_data)

        _, kwargs = mock_run.call_args
        assert "input" in kwargs, "Data must be passed via the input= kwarg (stdin)"
        assert kwargs["input"] == test_data.encode("utf-8")

        # The data string must NOT appear in the command argument list
        cmd_list = mock_run.call_args[0][0]
        assert test_data not in cmd_list, "Data must not appear as a command-line argument"


    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_data_bytes_passed_directly(self, mock_run, mock_open, mock_unlink):
        """When data is already bytes, it should be passed to stdin as-is."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_open.return_value.resize.return_value.convert.return_value = MagicMock()

        qr = QR()
        test_bytes = b"\x00\x01\x02\xff"
        qr.qrimage_io(test_bytes)

        _, kwargs = mock_run.call_args
        assert kwargs["input"] is test_bytes


    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_shell_metacharacters_not_interpreted(self, mock_run, mock_open, mock_unlink):
        """Shell metacharacters in data must not be interpreted. This is the core
        injection vector from issue #872."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_open.return_value.resize.return_value.convert.return_value = MagicMock()

        qr = QR()
        # Payloads that would execute commands under shell=True
        malicious_payloads = [
            '"; rm -rf / #',
            "$(cat /etc/passwd)",
            "`whoami`",
            "data; echo pwned",
        ]

        for payload in malicious_payloads:
            qr.qrimage_io(payload)

            _, kwargs = mock_run.call_args
            # Data is passed via stdin, so the command list should never contain it
            cmd_list = mock_run.call_args[0][0]
            assert payload not in cmd_list
            # stdin receives the raw bytes
            assert kwargs["input"] == payload.encode("utf-8")


    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_temp_file_deleted_after_success(self, mock_run, mock_open, mock_unlink):
        """The temp file must be deleted after the image is read, even on success."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_open.return_value.resize.return_value.convert.return_value = MagicMock()

        qr = QR()
        qr.qrimage_io("test data")

        mock_unlink.assert_called_once_with("/tmp/qrcode.png")


    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_temp_file_deleted_on_image_open_failure(self, mock_run, mock_open, mock_unlink):
        """The temp file must be cleaned up even if Image.open raises an exception."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_open.side_effect = FileNotFoundError("file vanished")

        qr = QR()
        with pytest.raises(FileNotFoundError):
            qr.qrimage_io("test data")

        mock_unlink.assert_called_once_with("/tmp/qrcode.png")


    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_fallback_on_qrencode_failure(self, mock_run):
        """When qrencode returns a non-zero exit code, qrimage_io must fall back
        to the pure-Python qrimage encoder."""
        mock_run.return_value = MagicMock(returncode=1)

        qr = QR()
        with patch.object(qr, "qrimage", return_value=MagicMock()) as mock_fallback:
            result = qr.qrimage_io("test data", width=240, height=240, border=3)
            mock_fallback.assert_called_once_with("test data", 240, 240, 3)
            assert result is mock_fallback.return_value


    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_background_color_validation_accepts_valid_hex(self, mock_run, mock_open, mock_unlink):
        """Valid 6-character hex color strings should be passed through."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_open.return_value.resize.return_value.convert.return_value = MagicMock()

        qr = QR()

        for color in ["ffffff", "000000", "808080", "ABCDEF", "a1B2c3"]:
            qr.qrimage_io("data", background_color=color)
            cmd_list = mock_run.call_args[0][0]
            assert f"--background={color}" in cmd_list


    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_background_color_validation_rejects_invalid(self, mock_run, mock_open, mock_unlink):
        """Invalid background_color values must be replaced with the safe default."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_open.return_value.resize.return_value.convert.return_value = MagicMock()

        qr = QR()

        invalid_colors = [
            "not-hex",
            "fff",           # too short
            "fffffff",       # too long
            "ghijkl",        # non-hex chars
            "; rm -rf /",    # injection attempt
        ]

        for color in invalid_colors:
            qr.qrimage_io("data", background_color=color)
            cmd_list = mock_run.call_args[0][0]
            assert "--background=808080" in cmd_list, (
                f"Invalid color '{color}' was not replaced with default"
            )


    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_border_clamped_to_valid_range(self, mock_run, mock_open, mock_unlink):
        """Border values outside 1-10 should default to 3."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_open.return_value.resize.return_value.convert.return_value = MagicMock()

        qr = QR()

        # Valid borders
        for border in [1, 5, 10]:
            qr.qrimage_io("data", border=border)
            cmd_list = mock_run.call_args[0][0]
            assert cmd_list[2] == str(border)

        # Invalid borders should default to "3"
        for border in [0, -1, 11, 100]:
            qr.qrimage_io("data", border=border)
            cmd_list = mock_run.call_args[0][0]
            assert cmd_list[2] == "3"


    @patch("seedsigner.helpers.qr.os.unlink")
    @patch("seedsigner.helpers.qr.Image.open")
    @patch("seedsigner.helpers.qr.subprocess.run")
    def test_capture_output_enabled(self, mock_run, mock_open, mock_unlink):
        """subprocess.run must use capture_output=True to prevent qrencode stderr
        from leaking to the parent process stdout."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_open.return_value.resize.return_value.convert.return_value = MagicMock()

        qr = QR()
        qr.qrimage_io("data")

        _, kwargs = mock_run.call_args
        assert kwargs.get("capture_output") is True
