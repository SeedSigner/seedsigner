import base64
import math
from dataclasses import dataclass
from typing import List, Optional

from lumensigner.helpers.qr import QR
from lumensigner.models import Seed, QRType, QRTYPE_SPLITTER
from lumensigner.models.settings import SettingsConstants


@dataclass
class EncodeQR:
    """
    Encode data for displaying as qr image
    """

    # TODO: Refactor so that this is a base class with implementation classes for each
    # QR type. No reason exterior code can't directly instantiate the encoder it needs.

    # Dataclass input vars on __init__()
    seed_phrase: List[str] = None
    derivation: str = None
    qr_type: str = None
    qr_density: str = SettingsConstants.DENSITY__MEDIUM
    wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH
    stellar_address: str = None
    signature: bytes = None

    def __post_init__(self):
        self.qr = QR()

        if not self.qr_type:
            raise Exception("qr_type is required")

        if self.qr_density is None:
            self.qr_density = SettingsConstants.DENSITY__MEDIUM

        self.encoder: Optional[BaseQrEncoder] = None
        # SeedQR formats
        if self.qr_type == QRType.SEED__SEEDQR:
            self.encoder = SeedQrEncoder(
                seed_phrase=self.seed_phrase,
                wordlist_language_code=self.wordlist_language_code,
            )

        elif self.qr_type == QRType.SEED__COMPACTSEEDQR:
            self.encoder = CompactSeedQrEncoder(
                seed_phrase=self.seed_phrase,
                wordlist_language_code=self.wordlist_language_code,
            )
        elif self.qr_type == QRType.STELLAR_ADDRESS:
            self.encoder = StellarAddressEncoder(
                address=self.stellar_address, derivation_path=self.derivation
            )
        elif self.qr_type == QRType.STELLAR_ADDRESS_NO_PREFIX:
            self.encoder = StellarAddressNoPrefixEncoder(address=self.stellar_address)
        elif self.qr_type == QRType.STELLAR_SIGNATURE:
            self.encoder = StellarSignatureEncoder(signature=self.signature)
        else:
            raise Exception("QR Type not supported")

    def total_parts(self) -> int:
        return self.encoder.seq_len()

    def next_part(self):
        return self.encoder.next_part()

    def part_to_image(self, part, width=240, height=240, border=3):
        return self.qr.qrimage_io(part, width, height, border)

    def next_part_image(
        self, width=240, height=240, border=3, background_color="bdbdbd"
    ):
        part = self.next_part()
        if self.qr_type == QRType.SEED__SEEDQR:
            return self.qr.qrimage(part, width, height, border)
        else:
            return self.qr.qrimage_io(
                part, width, height, border, background_color=background_color
            )

    # TODO: Make these properties?
    def is_complete(self):
        return self.encoder.is_complete

    def get_qr_density(self):
        return self.qr_density

    def get_qr_type(self):
        return self.qr_type


class BaseQrEncoder:
    def seq_len(self):
        raise Exception("Not implemented in child class")

    def next_part(self) -> str:
        raise Exception("Not implemented in child class")

    @property
    def is_complete(self):
        raise Exception("Not implemented in child class")

    def _create_parts(self):
        raise Exception("Not implemented in child class")


class SeedQrEncoder(BaseQrEncoder):
    def __init__(self, seed_phrase: List[str], wordlist_language_code: str):
        super().__init__()
        self.seed_phrase = seed_phrase
        self.wordlist = Seed.get_wordlist(wordlist_language_code)

        if self.wordlist is None:
            raise Exception("Wordlist Required")

    def seq_len(self):
        return 1

    def next_part(self):
        data = ""
        # Output as Numeric data format
        for word in self.seed_phrase:
            index = self.wordlist.index(word)
            data += str("%04d" % index)
        return data

    @property
    def is_complete(self):
        return True


class CompactSeedQrEncoder(SeedQrEncoder):
    def next_part(self):
        # Output as binary data format
        binary_str = ""
        for word in self.seed_phrase:
            index = self.wordlist.index(word)

            # Convert index to binary, strip out '0b' prefix; zero-pad to 11 bits
            binary_str += bin(index).split("b")[1].zfill(11)

        # We can exclude the checksum bits at the end
        if len(self.seed_phrase) == 24:
            # 8 checksum bits in a 24-word seed
            binary_str = binary_str[:-8]

        elif len(self.seed_phrase) == 12:
            # 4 checksum bits in a 12-word seed
            binary_str = binary_str[:-4]

        # Now convert to bytes, 8 bits at a time
        as_bytes = bytearray()
        for i in range(0, math.ceil(len(binary_str) / 8)):
            # int conversion reads byte data as a string prefixed with '0b'
            as_bytes.append(int("0b" + binary_str[i * 8 : (i + 1) * 8], 2))

        # Must return data as `bytes` for `qrcode` to properly recognize it as byte data
        return bytes(as_bytes)


class StellarAddressEncoder(BaseQrEncoder):
    def __init__(self, address: str, derivation_path: str):
        super().__init__()
        self.address = address
        self.derivation_path = derivation_path

    def seq_len(self):
        return 1

    def next_part(self):
        return f"{QRType.STELLAR_ADDRESS}{QRTYPE_SPLITTER}{self.derivation_path}{QRTYPE_SPLITTER}{self.address}"

    @property
    def is_complete(self):
        return True


class StellarAddressNoPrefixEncoder(BaseQrEncoder):
    def __init__(self, address: str):
        super().__init__()
        self.address = address

    def seq_len(self):
        return 1

    def next_part(self):
        return self.address

    @property
    def is_complete(self):
        return True


class StellarSignatureEncoder(BaseQrEncoder):
    def __init__(self, signature: bytes):
        super().__init__()
        self.signature = signature

    def seq_len(self):
        return 1

    def next_part(self):
        sig = base64.b64encode(self.signature).decode("utf-8")
        return f"{QRType.STELLAR_SIGNATURE}{QRTYPE_SPLITTER}{sig}"

    @property
    def is_complete(self):
        return True
