"""Hardening tests for the core QR / PSBT parsers.

Each case feeds a malformed or hostile payload to the real parser and asserts it is
rejected in-band (or parsed without raising), never IndexError/TypeError.
"""

from binascii import a2b_base64

import pytest
from embit.psbt import PSBT

from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus
from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants


# "signmessage m\n/84h/0h/0..." with garbage where the "{fmt}:{message}" part should be
SIGNMESSAGE_TRUNCATED = bytes.fromhex(
    "7369676e6d657373616765206d0a2f3834682f30682f301d75723a7363695c693a68656c6c01"
)

# Singlesig PSBT that embit parses, but whose first output script is one embit's
# script_type() does not recognize (returns None).
PSBT_UNKNOWN_SCRIPT_TYPE = "cHNidP8BAHICAAAAAQDo5ey+2HIrNUkExsFhsImv1OK1cYA9x/bRjYQD+0UaAQAAAAD9////Apg6AAAAAAAAF6kUVuVZEcdpQ2zgABa9dRUNYsignmessageAAAAAAAWABQaLE4t0JbDRg4pNnmcf+cAWIcyawAAAAAAAQEfqGEAAAAAAAAWAbRyuw9od6yuS0yiZljV0X12wG9e5CIGA/ZlEZvQubb6PmcnK+vlnd8aftYnrQ8wHYSxsD8tDp61GIshjoFUAACAAQAAgAAAAIAAAAAAAAAAAAAAAA=="

PSBT_SIGNING_MNEMONIC = (
    "height demise useless trap grow lion found off key clown transfer enroll".split()
)


def test_signmessage_truncated_qr_is_invalid_not_indexerror():
    decoder = DecodeQR()
    status = decoder.add_data(SIGNMESSAGE_TRUNCATED)
    assert status == DecodeQRStatus.INVALID
    assert not decoder.is_complete
    assert decoder.is_invalid


def test_signmessage_too_short_is_invalid():
    decoder = DecodeQR()
    assert decoder.add_data("signmessage") == DecodeQRStatus.INVALID
    assert decoder.is_invalid
    decoder = DecodeQR()
    assert decoder.add_data("signmessage m") == DecodeQRStatus.INVALID
    assert decoder.is_invalid
    decoder = DecodeQR()
    assert decoder.add_data("signmessage m/84h/0h/0h") == DecodeQRStatus.INVALID
    assert decoder.is_invalid


def test_signmessage_valid_qr_still_completes():
    decoder = DecodeQR()
    status = decoder.add_data("signmessage m/84h/0h/0h/0/0 ascii:hello world")
    assert status == DecodeQRStatus.COMPLETE
    data = decoder.get_qr_data()
    assert data["derivation_path"] == "m/84'/0'/0'/0/0"
    assert data["message"] == "hello world"


def test_psbt_unknown_script_type_is_unsupported_not_typeerror():
    """A PSBT that parses but has no recognized output script type must fail closed, not TypeError."""
    psbt = PSBT.parse(a2b_base64(PSBT_UNKNOWN_SCRIPT_TYPE))
    seed = Seed(mnemonic=PSBT_SIGNING_MNEMONIC)
    with pytest.raises(RuntimeError, match="Unsupported output script"):
        PSBTParser(p=psbt, seed=seed, network=SettingsConstants.TESTNET)
