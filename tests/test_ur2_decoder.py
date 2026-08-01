import time

from seedsigner.helpers.ur2.bytewords import Bytewords, Bytewords_Style_minimal
from seedsigner.helpers.ur2.fountain_decoder import FountainDecoder, MAX_SEQ_LEN
from seedsigner.helpers.ur2.fountain_encoder import Part
from seedsigner.helpers.ur2.ur_decoder import URDecoder



class TestFountainDecoderSeqLen:
    """
    `seq_len` arrives from a scanned QR. `validate_part()` builds a set of that many
    indexes and `choose_fragments()` runs a shuffle that is quadratic in seq_len, so an
    unbounded value lets a single frame exhaust memory or hang the device.
    """

    def make_part(self, seq_num: int, seq_len: int) -> Part:
        return Part(seq_num=seq_num, seq_len=seq_len, message_len=32, checksum=0,
                    data=b"\x00" * 32)


    def test_plausible_seq_len_is_accepted(self):
        decoder = FountainDecoder()
        assert decoder.validate_part(self.make_part(1, 50)) is True
        assert decoder.expected_part_count() == 50


    def test_oversized_seq_len_is_rejected(self):
        for seq_len in [MAX_SEQ_LEN + 1, 10**6, 2**32, 2**64 - 1]:
            decoder = FountainDecoder()
            assert decoder.validate_part(self.make_part(1, seq_len)) is False, seq_len
            # Nothing was allocated
            assert decoder.expected_part_indexes is None


    def test_zero_and_negative_seq_len_are_rejected(self):
        for seq_len in [0, -1]:
            decoder = FountainDecoder()
            assert decoder.validate_part(self.make_part(1, seq_len)) is False


    def test_oversized_seq_len_returns_promptly(self):
        """
            A frame declaring a huge seq_len must not do work proportional to it.

            Without the bound this allocates a set of `seq_len` ints and then runs an
            O(seq_len^2) shuffle in choose_fragments().
        """
        part = self.make_part(seq_num=10**7 + 1, seq_len=10**7)
        decoder = FountainDecoder()

        start = time.time()
        assert decoder.receive_part(part) is False
        assert time.time() - start < 1.0


    def test_oversized_seq_len_rejected_through_the_ur_decoder(self):
        """Same thing via the scanner's actual entry point."""
        seq_len = 10**7
        part = self.make_part(seq_num=1, seq_len=seq_len)
        body = Bytewords.encode(Bytewords_Style_minimal, bytes(part.cbor()))
        frame = f"ur:crypto-psbt/1-{seq_len}/{body}"

        decoder = URDecoder()
        start = time.time()
        assert decoder.receive_part(frame) is False
        assert time.time() - start < 1.0
        assert not decoder.is_complete()
