import logging
import re
from enum import IntEnum
from typing import Optional, List, Union

from PIL.Image import Image
from embit import bip39
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol
from stellar_sdk.helpers import parse_transaction_envelope_from_xdr

from . import QRType, Seed, QRTYPE_SPLITTER
from .settings import SettingsConstants

logger = logging.getLogger(__name__)


class DecodeQRStatus(IntEnum):
    """
    Used in DecodeQR to communicate status of adding qr frame/segment
    """

    PART_COMPLETE = 1
    PART_EXISTING = 2
    COMPLETE = 3
    FALSE = 4
    INVALID = 5


class DecodeQR:
    """
    Used to process images or string data from animated qr codes.
    """

    def __init__(
        self, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH
    ):
        self.wordlist_language_code = wordlist_language_code
        self.complete = False
        self.qr_type = None
        self.decoder = None

    def add_image(self, image: Optional[Image]):
        data = DecodeQR.extract_qr_data(image, is_binary=True)
        if data is None:
            return DecodeQRStatus.FALSE

        return self.add_data(data)

    def add_data(self, data):
        if data is None:
            return DecodeQRStatus.FALSE

        qr_type = DecodeQR.detect_segment_type(
            data, wordlist_language_code=self.wordlist_language_code
        )

        if self.qr_type is None:
            self.qr_type = qr_type
            if self.qr_type in (QRType.SEED__SEEDQR, QRType.SEED__COMPACTSEEDQR):
                self.decoder = SeedQrDecoder(
                    wordlist_language_code=self.wordlist_language_code
                )
            elif self.qr_type == QRType.SIGN_HASH:
                self.decoder = SignHashQrDecoder()
            elif self.qr_type == QRType.SIGN_TX:
                self.decoder = SignTransactionQrDecode()
        elif self.qr_type != qr_type:
            raise Exception("QR Fragment Unexpected Type Change")

        if not self.decoder:
            # Did not find any recognizable format
            return DecodeQRStatus.INVALID

        # Process the binary formats first
        if self.qr_type == QRType.SEED__COMPACTSEEDQR:
            rt = self.decoder.add(data, QRType.SEED__COMPACTSEEDQR)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

        # Convert to string data
        if type(data) == bytes:
            # Should always be bytes, but the test suite has some manual datasets that
            # are strings.
            # TODO: Convert the test suite rather than handle here?
            qr_str = data.decode("utf-8")
        else:
            # it's already str data
            qr_str = data

        rt = self.decoder.add(qr_str, self.qr_type)
        if rt == DecodeQRStatus.COMPLETE:
            self.complete = True
        return rt

    def get_seed_phrase(self):
        if self.is_seed:
            return self.decoder.get_seed_phrase()

    def get_sign_hash_data(self):
        if self.is_sign_hash:
            return self.decoder.address_index, self.decoder.hash

    def get_sign_transaction_data(self):
        if self.is_transaction:
            return self.decoder.get_data()

    def get_percent_complete(self) -> int:
        if not self.decoder:
            return 0

        elif self.qr_type == QRType.SIGN_TX:
            if self.decoder.total_segments is None:
                return 0
            return int(
                (self.decoder.collected_segments / self.decoder.total_segments) * 100
            )

        elif self.decoder.total_segments == 1:
            # The single frame QR formats are all or nothing
            if self.decoder.complete:
                return 100
            else:
                return 0
        else:
            return 0

    @property
    def is_complete(self) -> bool:
        return self.complete

    @property
    def is_invalid(self) -> bool:
        return self.qr_type == QRType.INVALID

    @property
    def is_seed(self):
        return self.qr_type in [
            QRType.SEED__SEEDQR,
            QRType.SEED__COMPACTSEEDQR,
        ]

    @property
    def is_sign_hash(self):
        return self.qr_type == QRType.SIGN_HASH

    @property
    def is_transaction(self):
        return self.qr_type == QRType.SIGN_TX

    @staticmethod
    def extract_qr_data(
        image: Optional[Image], is_binary: bool = False
    ) -> Optional[str]:
        if image is None:
            return None

        barcodes = pyzbar.decode(image, symbols=[ZBarSymbol.QRCODE], binary=is_binary)

        # if barcodes:
        # print("--------------- extract_qr_data ---------------")
        # print(barcodes)

        for barcode in barcodes:
            # Only pull and return the first barcode
            return barcode.data

    @staticmethod
    def detect_segment_type(s, wordlist_language_code=None):
        # print("-------------- DecodeQR.detect_segment_type --------------")
        # print(type(s))
        # print(len(s))

        try:
            # Convert to str data
            if type(s) == bytes:
                # Should always be bytes, but the test suite has some manual datasets that
                # are strings.
                # TODO: Convert the test suite rather than handle here?
                s = s.decode("utf-8")
            print("detect_segment_type s: ", s)
            if re.search(f"^{QRType.SIGN_HASH},m/44'/148'/\\d+',[\\da-fA-F]{{64}}$", s):
                return QRType.SIGN_HASH
            elif re.search(f"^p\\d+of\\d+,{QRType.SIGN_TX},.+$", s):
                return QRType.SIGN_TX
            if re.search(r"\d{48,96}", s):
                return QRType.SEED__SEEDQR

        except UnicodeDecodeError:
            # Probably this isn't meant to be string data; check if it's valid byte data
            # below.
            pass

        # Is it byte data?
        # 32 bytes for 24-word CompactSeedQR; 16 bytes for 12-word CompactSeedQR
        if len(s) == 32 or len(s) == 16:
            try:
                bitstream = ""
                for b in s:
                    bitstream += bin(b).lstrip("0b").zfill(8)
                # print(bitstream)

                return QRType.SEED__COMPACTSEEDQR
            except Exception as e:
                # Couldn't extract byte data; assume it's not a byte format
                pass

        return QRType.INVALID


class BaseQrDecoder:
    def __init__(self):
        self.total_segments = None
        self.collected_segments = 0
        self.complete = False

    @property
    def is_complete(self) -> bool:
        return self.complete

    def add(self, segment, qr_type):
        raise Exception("Not implemented in child class")


class BaseSingleFrameQrDecoder(BaseQrDecoder):
    def __init__(self):
        super().__init__()
        self.total_segments = 1


class BaseAnimatedQrDecoder(BaseQrDecoder):
    def __init__(self):
        super().__init__()
        self.segments = []

    def current_segment_num(self, segment) -> int:
        raise Exception("Not implemented in child class")

    def total_segment_nums(self, segment) -> int:
        raise Exception("Not implemented in child class")

    def parse_segment(self, segment) -> str:
        raise Exception("Not implemented in child class")

    @property
    def is_valid(self) -> bool:
        return True

    def add(self, segment, qr_type=None):
        if self.total_segments is None:
            self.total_segments = self.total_segment_nums(segment)
            self.segments: List[Union[str, None]] = [None] * self.total_segments
        elif self.total_segments != self.total_segment_nums(segment):
            raise Exception("Segment total changed unexpectedly")

        segment_index: int = self.current_segment_num(segment) - 1
        if self.segments[segment_index] is None:
            self.segments[segment_index] = self.parse_segment(segment)
            self.collected_segments += 1
            if self.total_segments == self.collected_segments:
                if self.is_valid:
                    self.complete = True
                    return DecodeQRStatus.COMPLETE
                else:
                    return DecodeQRStatus.INVALID
            return DecodeQRStatus.PART_COMPLETE  # new segment added

        return (
            DecodeQRStatus.PART_EXISTING
        )  # segment not added because it's already been added


class SignHashQrDecoder(BaseSingleFrameQrDecoder):
    def __init__(self):
        super().__init__()
        self.address_index: Optional[int] = None
        self.hash: Optional[str] = None

    def add(self, segment: str, qr_type=QRType.SIGN_HASH):
        print("Segment: ", segment)
        _, derivation_path, self.hash = segment.split(QRTYPE_SPLITTER)
        self.address_index = parse_address_index_from_derivation_path(derivation_path)
        self.complete = True
        self.collected_segments = 1
        return DecodeQRStatus.COMPLETE


class SignTransactionQrDecode(BaseAnimatedQrDecoder):
    def is_complete(self) -> bool:
        return self.complete

    def get_data(self):
        raw_data = "".join(self.segments)
        data = re.split(r"(?<!\\)" + QRTYPE_SPLITTER, raw_data)
        if len(data) != 3:
            raise ValueError("Invalid data")
        derivation_path, network_passphrase, transaction_base64 = data

        network_passphrase.replace("\\" + QRTYPE_SPLITTER, QRTYPE_SPLITTER)
        try:
            transaction = parse_transaction_envelope_from_xdr(
                transaction_base64, network_passphrase=network_passphrase
            )
        except Exception as e:
            raise ValueError(f"Invalid transaction envelope: {e}")

        address_index = parse_address_index_from_derivation_path(derivation_path)

        return address_index, network_passphrase, transaction

    def current_segment_num(self, segment) -> int:
        r = re.search(r"^p(\d+)of(\d+),", segment, re.IGNORECASE)
        if r:
            num = int(r.group(1))
            print("Current segment num: ", num)
            return num
        else:
            return 1

    def total_segment_nums(self, segment) -> int:
        r = re.search(r"^p(\d+)of(\d+),", segment, re.IGNORECASE)
        if r:
            num = int(r.group(2))
            print("Total segment num: ", num)
            return num
        else:
            return 1

    def parse_segment(self, segment) -> str:
        s = re.search(r"^p(\d+)of(\d+),(.+$)", segment, re.IGNORECASE).group(3)
        if not s.startswith("sign-transaction,"):
            raise Exception("Invalid sign transaction segment")
        return s[len("sign-transactions,") - 1 :]


class SeedQrDecoder(BaseSingleFrameQrDecoder):
    """
    Decodes single frame representing a seed.
    Supports SeedSigner SeedQR numeric (wordlist indices) representation of a seed.
    Supports SeedSigner CompactSeedQR entropy byte representation of a seed.
    Supports mnemonic seed phrase string data.
    """

    def __init__(self, wordlist_language_code):
        super().__init__()
        self.seed_phrase = []
        self.wordlist_language_code = wordlist_language_code
        self.wordlist = Seed.get_wordlist(wordlist_language_code)

    def add(self, segment, qr_type=QRType.SEED__SEEDQR):
        # `segment` data will either be bytes or str, depending on the qr_type
        if qr_type == QRType.SEED__SEEDQR:
            try:
                self.seed_phrase = []

                # Parse 12 or 24-word QR code
                num_words = int(len(segment) / 4)
                for i in range(0, num_words):
                    index = int(segment[i * 4 : (i * 4) + 4])
                    word = self.wordlist[index]
                    self.seed_phrase.append(word)
                if len(self.seed_phrase) > 0:
                    if not self.is_12_or_24_word_phrase():
                        return DecodeQRStatus.INVALID
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
                else:
                    return DecodeQRStatus.INVALID
            except Exception as e:
                return DecodeQRStatus.INVALID

        if qr_type == QRType.SEED__COMPACTSEEDQR:
            try:
                self.seed_phrase = bip39.mnemonic_from_bytes(segment).split()
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                logger.exception(repr(e))
                return DecodeQRStatus.INVALID

        elif qr_type == QRType.SEED__MNEMONIC:
            try:
                seed_phrase_list = self.seed_phrase = segment.strip().split(" ")

                # embit mnemonic code to validate
                seed = Seed(
                    seed_phrase_list,
                    passphrase="",
                    wordlist_language_code=self.wordlist_language_code,
                )
                if not seed:
                    # seed is not valid, return invalid
                    return DecodeQRStatus.INVALID
                self.seed_phrase = seed_phrase_list
                if self.is_12_or_24_word_phrase() == False:
                    return DecodeQRStatus.INVALID
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                return DecodeQRStatus.INVALID

        elif qr_type == QRType.SEED__FOUR_LETTER_MNEMONIC:
            try:
                seed_phrase_list = segment.strip().split(" ")
                words = []
                for s in seed_phrase_list:
                    # TODO: Pre-calculate this once on startup
                    _4LETTER_WORDLIST = [word[:4].strip() for word in self.wordlist]
                    words.append(self.wordlist[_4LETTER_WORDLIST.index(s)])

                # embit mnemonic code to validate
                seed = Seed(
                    words,
                    passphrase="",
                    wordlist_language_code=self.wordlist_language_code,
                )
                if not seed:
                    # seed is not valid, return invalid
                    return DecodeQRStatus.INVALID
                self.seed_phrase = words
                if self.is_12_or_24_word_phrase() == False:
                    return DecodeQRStatus.INVALID
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                return DecodeQRStatus.INVALID

        else:
            return DecodeQRStatus.INVALID

    def get_seed_phrase(self):
        if self.complete:
            return self.seed_phrase[:]
        return []

    def is_12_or_24_word_phrase(self):
        if len(self.seed_phrase) in (12, 24):
            return True
        return False


def parse_address_index_from_derivation_path(derivation_path: str) -> int:
    regex = "m/44'\\/148'\\/(\\d+)'"
    matches = re.search(regex, derivation_path)
    if matches:
        return int(matches.group(1))
    raise ValueError(
        f"Could not parse address index from derivation path: {derivation_path}"
    )
