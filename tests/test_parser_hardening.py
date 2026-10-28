"""Hardening tests for the core QR parsers.

Each case feeds a malformed or hostile payload to the real parser and asserts it is
rejected in-band (or parsed without raising), never IndexError/TypeError.
"""

from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus


# "signmessage m\n/84h/0h/0..." with garbage where the "{fmt}:{message}" part should be
SIGNMESSAGE_TRUNCATED = bytes.fromhex(
    "7369676e6d657373616765206d0a2f3834682f30682f301d75723a7363695c693a68656c6c01"
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
