import pytest
from seedsigner.helpers.ur2.cbor_lite import (
    CBOREncoder, CBORDecoder
)
from seedsigner.helpers.ur2.bytewords import Bytewords, Bytewords_Style_minimal
from seedsigner.helpers.ur2.ur import UR
from seedsigner.helpers.ur2.ur_encoder import UREncoder
from seedsigner.helpers.ur2.ur_decoder import URDecoder, InvalidScheme, InvalidPathLength


class TestCBORRoundTrip:
    """
    Round-trip encoding and decoding tests for various CBOR types.
    """
    def test_unsigned_roundtrip(self):
        """
        Should successfully encode and decode various unsigned integers, 
        handling boundary values for different CBOR integer sizes.
        """
        for n in [0, 23, 24, 255, 256, 65535]:
            enc = CBOREncoder()
            enc.encodeUnsigned(n)
            val, _ = CBORDecoder(enc.get_bytes()).decodeUnsigned()
            assert val == n

    def test_bytes_roundtrip(self):
        """
        Should successfully encode and decode a byte payload.
        """
        payload = b'\xde\xad\xbe\xef'
        enc = CBOREncoder()
        enc.encodeBytes(payload)
        val, _ = CBORDecoder(enc.get_bytes()).decodeBytes()
        assert val == payload

    def test_text_roundtrip(self):
        """
        Should successfully encode and decode text using UTF-8.
        """
        enc = CBOREncoder()
        enc.encodeText("bitcoin")
        val, _ = CBORDecoder(enc.get_bytes()).decodeText()
        assert bytes(val).decode('utf8') == "bitcoin"

    def test_text_non_ascii_roundtrip(self):
        """
        Should correctly encode non-ASCII text using UTF-8 byte length
        (not character count) in the CBOR header.
        e.g. 'café' is 4 characters but 5 UTF-8 bytes.
        """
        enc = CBOREncoder()
        enc.encodeText("café")
        raw = enc.get_bytes()
        assert raw[0] == (3 << 5) | 5
        val, _ = CBORDecoder(raw).decodeText()
        assert bytes(val).decode('utf8') == "café"

    def test_map_size_roundtrip(self):
        """
        Should successfully encode and decode map sizes.
        """
        for n in [0, 1, 23, 24]:
            enc = CBOREncoder()
            enc.encodeMapSize(n)
            val, _ = CBORDecoder(enc.get_bytes()).decodeMapSize()
            assert val == n

    def test_array_size_roundtrip(self):
        """
        Should successfully encode and decode array sizes.
        """
        enc = CBOREncoder()
        enc.encodeArraySize(5)
        val, _ = CBORDecoder(enc.get_bytes()).decodeArraySize()
        assert val == 5


class TestBytewords:
    """
    Bytewords encoding and decoding tests.
    """
    def test_minimal_roundtrip(self):
        """
        Given a byte payload, should yield a valid "minimal" style Bytewords string 
        that can be decoded back to the original payload.
        """
        payload = bytes(range(8))
        encoded = Bytewords.encode(Bytewords_Style_minimal, payload)
        decoded = Bytewords.decode(Bytewords_Style_minimal, encoded)
        assert bytes(decoded) == payload

    def test_invalid_byteword_raises(self):
        """
        Should raise a ValueError when attempting to decode invalid Bytewords data.
        """
        with pytest.raises(ValueError, match="Invalid Bytewords"):
            Bytewords.decode(Bytewords_Style_minimal, "zzzz")


class TestURRoundTrip:
    """
    Tests for UREncoder and URDecoder handling of animated QR UR strings.
    """
    UR_TYPE = "bytes"

    def _make_ur(self, payload: bytes) -> UR:
        """
        Helper method to wrap a byte payload in a CBOR-encoded UR object.
        """
        enc = CBOREncoder()
        enc.encodeBytes(payload)
        return UR(self.UR_TYPE, enc.get_bytes())

    def test_single_part_roundtrip(self):
        """
        Should successfully encode a small payload as a single-part 'ur:bytes' string 
        and decode it back to original bytes.
        """
        payload = b'\x11\x22\x33\x44'
        ur = self._make_ur(payload)
        encoded_str = UREncoder.encode(ur)
        assert encoded_str.startswith("ur:")
        decoded_ur = URDecoder.decode(encoded_str)
        val, _ = CBORDecoder(bytearray(decoded_ur.cbor)).decodeBytes()
        assert bytes(val) == payload

    def test_multi_part_animated_qr_roundtrip(self):
        """
        Given a large payload, should successfully encode it into multiple fountain-coded parts 
        and decode them back once the decoder has received sufficient parts.
        """
        payload = bytes(range(100))
        ur = self._make_ur(payload)
        encoder = UREncoder(ur, max_fragment_len=20)
        decoder = URDecoder()

        for _ in range(500):
            decoder.receive_part(encoder.next_part())
            if decoder.is_complete():
                break

        assert decoder.is_complete()
        assert decoder.is_success()
        val, _ = CBORDecoder(bytearray(decoder.result_message().cbor)).decodeBytes()
        assert bytes(val) == payload

    def test_invalid_scheme_raises(self):
        """
        Should raise InvalidScheme when decoding a string that doesn't start with 'ur:'.
        """
        with pytest.raises(InvalidScheme):
            URDecoder.decode("bitcoin:abc123")

    def test_invalid_path_length_raises(self):
        """
        Should raise InvalidPathLength when the UR string is missing required components.
        """
        with pytest.raises(InvalidPathLength):
            URDecoder.decode("ur:bytes")
