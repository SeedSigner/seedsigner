import pytest

from seedsigner.helpers.ur2.bytewords import Bytewords, Bytewords_Style_minimal, Bytewords_Style_standard
from seedsigner.helpers.ur2.crc32 import crc32, crc32n



class TestBytewordsChecksum:
    """
    The Bytewords checksum is a fixed-width 4-byte big-endian CRC32. Sizing it to the
    value's bit length emits 3 bytes whenever the CRC is below 2**24 (~1 in 256), and
    `decode()` always strips 4, so the payload silently loses its last byte.
    """

    # crc32 of this payload is 0x00b6cdbc, i.e. below 2**24
    SHORT_CRC_PAYLOAD = bytes.fromhex("9cce484ad8a364ed9360fa24ca015240")


    def test_crc32n_is_always_four_bytes(self):
        assert crc32(self.SHORT_CRC_PAYLOAD) < 2**24, "vector no longer exercises the short-CRC case"
        assert len(crc32n(self.SHORT_CRC_PAYLOAD)) == 4

        # Also cover a CRC below 2**16
        for i in range(500_000):
            candidate = i.to_bytes(4, "big")
            if crc32(candidate) < 2**16:
                assert len(crc32n(candidate)) == 4
                break
        else:
            pytest.skip("no sub-2**16 CRC found in the search range")


    @pytest.mark.parametrize("style", [Bytewords_Style_minimal, Bytewords_Style_standard])
    def test_round_trip_with_short_crc(self, style):
        """The payload must survive a round-trip even when its CRC is small."""
        encoded = Bytewords.encode(style, self.SHORT_CRC_PAYLOAD)
        decoded = bytes(Bytewords.decode(style, encoded))
        assert decoded == self.SHORT_CRC_PAYLOAD


    def test_round_trip_sweep(self):
        """Sweep payload lengths and contents; ~1 in 256 hits the short-CRC path."""
        import os
        for _ in range(300):
            for n in [10, 16, 32, 64]:
                payload = os.urandom(n)
                encoded = Bytewords.encode(Bytewords_Style_minimal, payload)
                assert bytes(Bytewords.decode(Bytewords_Style_minimal, encoded)) == payload


    def test_corrupted_payload_is_rejected(self):
        """The checksum comparison in decode() must actually run."""
        payload = b"the times 03/Jan/2009"
        encoded = Bytewords.encode(Bytewords_Style_minimal, payload)

        # Corrupt the first byteword (each byte is 2 chars in the minimal style)
        corrupted = ("ae" if encoded[0:2] != "ae" else "ad") + encoded[2:]

        with pytest.raises(ValueError):
            Bytewords.decode(Bytewords_Style_minimal, corrupted)
