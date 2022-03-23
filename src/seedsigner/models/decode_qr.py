import base64
import json
import logging
import re

from binascii import a2b_base64, b2a_base64
from enum import IntEnum
from embit import psbt, bip39
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol
from urtypes.crypto import PSBT as UR_PSBT

from seedsigner.helpers.ur2.ur_decoder import URDecoder
from seedsigner.helpers.bcur import (cbor_decode, bc32decode)
from seedsigner.models.psbt_parser import PSBTParser

from . import QRType, Seed
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
    def __init__(self, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH):
        self.wordlist_language_code = wordlist_language_code
        self.complete = False
        self.qr_type = None
        self.decoder = None


    def add_image(self, image):
        data = DecodeQR.extract_qr_data(image, is_binary=True)
        if data == None:
            return DecodeQRStatus.FALSE

        return self.add_data(data)


    def add_data(self, data):
        if data == None:
            return DecodeQRStatus.FALSE

        qr_type = DecodeQR.detect_segment_type(data, wordlist_language_code=self.wordlist_language_code)

        print(qr_type)

        if self.qr_type == None:
            self.qr_type = qr_type

            if self.qr_type == QRType.PSBT__UR2:
                self.decoder = URDecoder() # UR2 decoder

            elif self.qr_type == QRType.PSBT__SPECTER:
                self.decoder = SpecterPsbtQrDecoder() # Specter Desktop PSBT QR base64 decoder

            elif self.qr_type == QRType.PSBT__LEGACY_UR:
                self.decoder = LegacyUrPsbtQrDecoder() # UR Legacy decoder

            elif self.qr_type == QRType.PSBT__BASE64:
                self.decoder = Base64PsbtQrDecoder() # Single Segments Base64

            elif self.qr_type == QRType.PSBT__BASE43:
                self.decoder = Base43PsbtQrDecoder() # Single Segment Base43

            elif self.qr_type in [QRType.SEED__SEEDQR, QRType.SEED__COMPACTSEEDQR, QRType.SEED__MNEMONIC, QRType.SEED__FOUR_LETTER_MNEMONIC, QRType.SEED__UR2]:
                self.decoder = SeedQrDecoder(wordlist_language_code=self.wordlist_language_code)          

            elif self.qr_type == QRType.SETTINGS:
                self.decoder = SettingsQrDecoder()  # Settings config

            elif self.qr_type == QRType.BITCOIN_ADDRESS:
                self.decoder = BitcoinAddressQrDecoder() # Single Segment bitcoin address

            elif self.qr_type == QRType.WALLET__SPECTER:
                self.decoder = SpecterWalletQrDecoder() # Specter Desktop Wallet Export decoder

            elif self.qr_type == QRType.WALLET__GENERIC:
                self.decoder = GenericWalletQrDecoder()

        elif self.qr_type != qr_type:
            raise Exception('QR Fragment Unexpected Type Change')

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
            qr_str = data.decode('utf-8')
        else:
            # it's already str data
            qr_str = data

        if self.qr_type == QRType.PSBT__UR2:
            self.decoder.receive_part(qr_str)
            if self.decoder.is_complete():
                self.complete = True
                return DecodeQRStatus.COMPLETE
            return DecodeQRStatus.PART_COMPLETE # segment added to ur2 decoder

        else:
            # All other formats use the same method signature
            rt = self.decoder.add(qr_str, self.qr_type)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt


    def get_psbt(self):
        if self.complete:
            data = self.get_data_psbt()
            if data != None:
                try:
                    return psbt.PSBT.parse(data)
                except:
                    return None
        return None


    def get_data_psbt(self):
        if self.complete:
            if self.qr_type == QRType.PSBT__UR2:
                cbor = self.decoder.result_message().cbor
                return UR_PSBT.from_cbor(cbor).data

            else:
                # All the other psbt decoder types use the same method signature
                return self.decoder.get_data()

        return None


    def get_base64_psbt(self):
        if self.complete:
            data = self.get_data_psbt()
            b64_psbt = b2a_base64(data)

            if b64_psbt[-1:] == b"\n":
                b64_psbt = b64_psbt[:-1]

            return b64_psbt.decode("utf-8")
        return None


    def get_seed_phrase(self):
        if self.is_seed:
            return self.decoder.get_seed_phrase()


    def get_settings_data(self):
        if self.is_settings:
            return self.decoder.settings


    def get_settings_config_name(self):
        if self.is_settings:
            return self.decoder.config_name


    def get_address(self):
        if self.is_address:
            return self.decoder.get_address()


    def get_address_type(self):
        if self.is_address:
            return self.decoder.get_address_type()


    def get_wallet_descriptor(self):
        if self.is_wallet_descriptor:
            return self.decoder.get_wallet_descriptor()


    def get_percent_complete(self) -> int:
        if not self.decoder:
            return 0

        if self.qr_type == QRType.PSBT__UR2:
            return int(self.decoder.estimated_percent_complete() * 100)

        elif self.qr_type in [QRType.PSBT__SPECTER, QRType.PSBT__LEGACY_UR]:
            if self.decoder.total_segments == None:
                return 0
            return int((self.decoder.collected_segments / self.decoder.total_segments) * 100)

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
    def is_psbt(self) -> bool:
        return self.qr_type in [
            QRType.PSBT__UR2,
            QRType.PSBT__SPECTER,
            QRType.PSBT__LEGACY_UR, 
            QRType.PSBT__BASE64,
            QRType.PSBT__BASE43,
        ]


    @property
    def is_seed(self):
        return self.qr_type in [
            QRType.SEED__SEEDQR,
            QRType.SEED__COMPACTSEEDQR,
            QRType.SEED__UR2,
            QRType.SEED__MNEMONIC, 
            QRType.SEED__FOUR_LETTER_MNEMONIC,
        ]
    

    @property
    def is_json(self):
        return self.qr_type in [QRType.SETTINGS, QRType.JSON]
        

    @property
    def is_address(self):
        return self.qr_type == QRType.BITCOIN_ADDRESS
        

    @property
    def is_wallet_descriptor(self):
        return self.qr_type in [QRType.WALLET__SPECTER, QRType.WALLET__UR, QRType.WALLET__BLUEWALLET, QRType.WALLET__GENERIC]
    

    @property
    def is_settings(self):
        return self.qr_type == QRType.SETTINGS


    @staticmethod
    def extract_qr_data(image, is_binary:bool = False) -> str:
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
                s = s.decode('utf-8')

            # PSBT
            if re.search("^UR:CRYPTO-PSBT/", s, re.IGNORECASE):
                return QRType.PSBT__UR2

            elif re.search(r'^p(\d+)of(\d+) ([A-Za-z0-9+\/=]+$)', s, re.IGNORECASE): #must be base64 characters only in segment
                return QRType.PSBT__SPECTER

            elif re.search("^UR:BYTES/", s, re.IGNORECASE):
                return QRType.PSBT__LEGACY_UR

            elif DecodeQR.is_base64_psbt(s):
                return QRType.PSBT__BASE64

            # Wallet Descriptor
            desc_str = s.replace("\n","").replace(" ","")
            if re.search(r'^p(\d+)of(\d+) ', s, re.IGNORECASE):
                # when not a SPECTER Base64 PSBT from above, assume it's json
                return QRType.WALLET__SPECTER

            elif re.search(r'^\{\"label\".*\"descriptor\"\:.*', desc_str, re.IGNORECASE):
                # if json starting with label and contains descriptor, assume specter wallet json
                return QRType.WALLET__SPECTER
            
            elif "sortedmulti" in s:
                return QRType.WALLET__GENERIC

            # Seed
            if re.search(r'\d{48,96}', s):
                return QRType.SEED__SEEDQR

            # Bitcoin Address
            elif DecodeQR.is_bitcoin_address(s):
                return QRType.BITCOIN_ADDRESS

            # config data
            if "type=settings" in s:
                return QRType.SETTINGS

            # Seed
            # create 4 letter wordlist only if not PSBT (performance gain)
            wordlist = Seed.get_wordlist(wordlist_language_code)
            try:
                _4LETTER_WORDLIST = [word[:4].strip() for word in wordlist]
            except:
                _4LETTER_WORDLIST = []
            
            if all(x in wordlist for x in s.strip().split(" ")):
                # checks if all words in list are in bip39 word list
                return QRType.SEED__MNEMONIC

            elif all(x in _4LETTER_WORDLIST for x in s.strip().split(" ")):
                # checks if all 4 letter words are in list are in 4 letter bip39 word list
                return QRType.SEED__FOUR_LETTER_MNEMONIC

            elif DecodeQR.is_base43_psbt(s):
                return QRType.PSBT__BASE43

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
                    bitstream += bin(b).lstrip('0b').zfill(8)
                # print(bitstream)

                return QRType.SEED__COMPACTSEEDQR
            except Exception as e:
                # Couldn't extract byte data; assume it's not a byte format
                pass

        return QRType.INVALID


    @staticmethod   
    def is_base64(s):
        try:
            return base64.b64encode(base64.b64decode(s)) == s.encode('ascii')
        except Exception:
            return False


    @staticmethod   
    def is_base64_psbt(s):
        try:
            if DecodeQR.is_base64(s):
                psbt.PSBT.parse(a2b_base64(s))
                return True
        except Exception:
            return False
        return False


    @staticmethod
    def is_base43_psbt(s):
        try:
            psbt.PSBT.parse(DecodeQR.base43_decode(s))
            return True
        except Exception:
            return False


    @staticmethod
    def base43_decode(s):
        chars = b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ$*+-./:' #base43 chars

        if isinstance(s, bytes):
            v = s
        if isinstance(s, str):
            v = s.encode('ascii')
        elif isinstance(s, bytearray):
            v = bytes(s)
            
        long_value = 0
        power_of_base = 1
        for c in v[::-1]:
            digit = chars.find(bytes([c]))
            if digit == -1:
                raise Exception('Forbidden character {} for base {}'.format(c, 43))
            # naive but slow variant:   long_value += digit * (base**i)
            long_value += digit * power_of_base
            power_of_base *= 43
        result = bytearray()
        while long_value >= 256:
            div, mod = divmod(long_value, 256)
            result.append(mod)
            long_value = div
        result.append(long_value)
        nPad = 0
        for c in v:
            if c == chars[0]:
                nPad += 1
            else:
                break
        result.extend(b'\x00' * nPad)
        result.reverse()
        return bytes(result)


    @staticmethod
    def is_bitcoin_address(s):
        if re.search(r'^bitcoin\:.*', s, re.IGNORECASE):
            return True
        elif re.search(r'^((bc1|tb1|[123]|[mn])[a-zA-HJ-NP-Z0-9]{25,62})$', s):
            # TODO: Handle regtest bcrt?
            return True
        else:
            return False



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
        if self.total_segments == None:
            self.total_segments = self.total_segment_nums(segment)
            self.segments = [None] * self.total_segments
        elif self.total_segments != self.total_segment_nums(segment):
            raise Exception('Segment total changed unexpectedly')

        if self.segments[self.current_segment_num(segment) - 1] == None:
            self.segments[self.current_segment_num(segment) - 1] = self.parse_segment(segment)
            self.collected_segments += 1
            if self.total_segments == self.collected_segments:
                if self.is_valid:
                    self.complete = True
                    return DecodeQRStatus.COMPLETE
                else:
                    return DecodeQRStatus.INVALID
            return DecodeQRStatus.PART_COMPLETE # new segment added

        return DecodeQRStatus.PART_EXISTING # segment not added because it's already been added



class SpecterPsbtQrDecoder(BaseAnimatedQrDecoder):
    """
        Used to decode Specter Desktop Animated QR PSBT encoding.
    """
    def get_base64_data(self) -> str:
        base64 = "".join(self.segments)
        if self.complete and DecodeQR.is_base64(base64):
            return base64

        return None


    def get_data(self):
        base64 = self.get_base64_data()
        if base64 != None:
            return a2b_base64(base64)

        return None


    def current_segment_num(self, segment) -> int:
        if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
            return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(1))


    def total_segment_nums(self, segment) -> int:
        if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
            return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(2))


    def parse_segment(self, segment) -> str:
        return segment.split(" ")[-1].strip()



class LegacyUrPsbtQrDecoder(BaseAnimatedQrDecoder):
    """
        Decodes Legacy UR animated qr encoding
    """
    def get_base64_data(self) -> str:
        bc32_cbor = "".join(self.segments)
        raw = cbor_decode(bc32decode(bc32_cbor))
        base64 = b2a_base64(raw)

        if self.complete:
            return base64

        return None


    def get_data(self):
        if not self.complete:
            return None

        bc32_cbor = "".join(self.segments)
        raw = cbor_decode(bc32decode(bc32_cbor))
        return raw


    def parse_current_segment_num(self, segment) -> int:
        if re.search(r'^UR:BYTES/(\d+)OF(\d+)', segment, re.IGNORECASE) != None:
            return int(re.search(r'^UR:BYTES/(\d+)OF(\d+)', segment, re.IGNORECASE).group(1))
        else:
            raise Exception('Unexpected Legacy UR Error')


    def parse_total_segment_nums(self, segment) -> int:
        if re.search(r'^UR:BYTES/(\d+)OF(\d+)', segment, re.IGNORECASE) != None:
            return int(re.search(r'^UR:BYTES/(\d+)OF(\d+)', segment, re.IGNORECASE).group(2))
        else:
            return 1


    def parse_segment(self, segment) -> str:
        return segment.split("/")[-1].strip()



class Base64PsbtQrDecoder(BaseSingleFrameQrDecoder):
    """
        Decodes single frame base64 encoded qr image.
        Does not support animated qr because no indicator of segments or their order
    """
    def add(self, segment, qr_type=QRType.PSBT__BASE64):
        if DecodeQR.is_base64(segment):
            self.complete = True
            self.data = segment
            self.collected_segments = 1
            return DecodeQRStatus.COMPLETE

        return DecodeQRStatus.INVALID


    def get_base64_data(self) -> str:
        return self.data


    def get_data(self):
        base64 = self.get_base64_data()
        if base64 != None:
            return a2b_base64(base64)

        return None



class Base43PsbtQrDecoder(BaseSingleFrameQrDecoder):
    """
        Decodes single frame base43 encoded qr image.
        Does not support animated qr because no indicator of segments or their order
    """
    def add(self, segment, qr_type=QRType.PSBT__BASE43):
        if DecodeQR.is_base43_psbt(segment):
            self.complete = True
            self.data = DecodeQR.base43_decode(segment)
            self.collected_segments = 1
            return DecodeQRStatus.COMPLETE

        return DecodeQRStatus.INVALID


    def get_data(self):
        return self.data



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
                    index = int(segment[i * 4: (i*4) + 4])
                    word = self.wordlist[index]
                    self.seed_phrase.append(word)
                if len(self.seed_phrase) > 0:
                    if self.is_12_or_24_word_phrase() == False:
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
                seed = Seed(seed_phrase_list, passphrase="", wordlist_language_code=self.wordlist_language_code)
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
                seed = Seed(words, passphrase="", wordlist_language_code=self.wordlist_language_code)
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



# TODO: Refactor this to work with the new SettingsDefinition
class SettingsQrDecoder(BaseSingleFrameQrDecoder):
    def __init__(self):
        super().__init__()
        self.settings = {}
        self.config_name = None


    def add(self, segment, qr_type=QRType.SETTINGS):
        # print(f"SettingsQR:\n{segment}")
        try:
            self.settings = {}

            # QR Settings format is space-separated key/value pairs, but should also
            # parse \n-separated keys.
            for entry in segment.split():
                key = entry.split("=")[0].strip()
                value = entry.split("=")[1].strip()
                self.settings[key] = value

            # Remove values only needed for import
            self.settings.pop("type", None)
            version = self.settings.pop("version", None)
            if not version or int(version) != 1:
                raise Exception(f"Settings QR version {version} not supported")

            self.config_name = self.settings.pop("name", None)
            if self.config_name:
                self.config_name = self.config_name.replace("_", " ")
            
            # Have to translate the abbreviated settings into the human-readable values
            # used in the normal Settings.
            map_abbreviated_enable = {
                "0": SettingsConstants.OPTION__DISABLED,
                "1": SettingsConstants.OPTION__ENABLED,
                "2": SettingsConstants.OPTION__PROMPT,
            }
            map_abbreviated_sig_types = {
                "s": SettingsConstants.SINGLE_SIG,
                "m": SettingsConstants.MULTISIG,
            }
            map_abbreviated_scripts = {
                "na": SettingsConstants.NATIVE_SEGWIT,
                "ne": SettingsConstants.NESTED_SEGWIT,
                "tr": SettingsConstants.TAPROOT,
                "cu": SettingsConstants.CUSTOM_DERIVATION,
            }
            map_abbreviated_coordinators = {
                "bw": SettingsConstants.COORDINATOR__BLUE_WALLET,
                "sw": SettingsConstants.COORDINATOR__SPARROW,
                "sd": SettingsConstants.COORDINATOR__SPECTER_DESKTOP,
            }

            def convert_abbreviated_value(category, key, abbreviation_map, is_list=False, new_key_name=None):
                try:
                    if key not in self.settings:
                        print(f"'{key}' not found in settings")
                        return
                    value = self.settings[key]

                    if not is_list:
                        new_value = abbreviation_map.get(value)
                        if not new_value:
                            logger.error(f"No abbreviation map value for \"{value}\" for setting {key}")
                            return
                    else:
                        # `value` is a comma-separated list; yields list of map matches
                        values = value.split(",")
                        new_value = []
                        for v in values:
                            mapped_value = abbreviation_map.get(v)
                            if not mapped_value:
                                logger.error(f"No abbreviation map value for \"{v}\" for setting {key}")
                                return
                            new_value.append(mapped_value)
                    del self.settings[key]
                    if new_key_name:
                        key = new_key_name
                    if category not in self.settings:
                        self.settings[category] = {}
                    self.settings[category][key] = new_value
                except Exception as e:
                    logger.exception(e)
                    return

            convert_abbreviated_value("wallet", "coord", map_abbreviated_coordinators, is_list=True, new_key_name="coordinators")
            convert_abbreviated_value("features", "xpub", map_abbreviated_enable, new_key_name="xpub_export")
            convert_abbreviated_value("features", "sigs", map_abbreviated_sig_types, is_list=True, new_key_name="sig_types")
            convert_abbreviated_value("features", "scripts", map_abbreviated_scripts, is_list=True, new_key_name="script_types")
            convert_abbreviated_value("features", "xp_det", map_abbreviated_enable, new_key_name="show_xpub_details")
            convert_abbreviated_value("features", "passphrase", map_abbreviated_enable)
            convert_abbreviated_value("features", "priv_warn", map_abbreviated_enable, new_key_name="show_privacy_warnings")
            convert_abbreviated_value("features", "dire_warn", map_abbreviated_enable, new_key_name="show_dire_warnings")

            self.complete = True
            self.collected_segments = 1
            return DecodeQRStatus.COMPLETE
        except Exception as e:
            logger.exception(e)
            return DecodeQRStatus.INVALID



class BitcoinAddressQrDecoder(BaseSingleFrameQrDecoder):
    """
        Decodes single frame representing a bitcoin address
    """
    def __init__(self):
        super().__init__()
        self.address = None
        self.address_type = None


    def add(self, segment, qr_type=QRType.BITCOIN_ADDRESS):
        r = re.search(r'((bc1q|tb1q|bcrt1q|bc1p|tb1p|bcrt1p|[123]|[mn])[a-zA-HJ-NP-Z0-9]{25,64})', segment)
        if r != None:
            self.address = r.group(1)
        
            if re.search(r'^((bc1q|tb1q|bcrt1q|bc1p|tb1p|bcrt1p|[123]|[mn])[a-zA-HJ-NP-Z0-9]{25,64})$', self.address) != None:
                self.complete = True
                self.collected_segments = 1
                
                # get address type
                r = re.search(r'^((bc1q|tb1q|bcrt1q|bc1p|tb1p|bcrt1p|[123]|[mn])[a-zA-HJ-NP-Z0-9]{25,64})$', self.address)
                if r != None:
                    r = r.group(2)
                
                if r == "1":
                    # Legacy P2PKH. mainnet
                    self.address_type = (SettingsConstants.LEGACY_P2PKH, SettingsConstants.MAINNET)

                elif r == "m" or r == "n":
                    self.address_type = (SettingsConstants.LEGACY_P2PKH, SettingsConstants.TESTNET)

                elif r == "3":
                    # Nested Segwit Single Sig (P2WPKH in P2SH) or Multisig (P2WSH in P2SH); mainnet
                    self.address_type = (SettingsConstants.NESTED_SEGWIT, SettingsConstants.MAINNET)

                elif r == "2":
                    # Nested Segwit Single Sig (P2WPKH in P2SH) or Multisig (P2WSH in P2SH); testnet
                    self.address_type = (SettingsConstants.NESTED_SEGWIT, SettingsConstants.TESTNET)

                elif r == "bc1q":
                    # Native Segwit (single sig or multisig), mainnet 
                    self.address_type = (SettingsConstants.NATIVE_SEGWIT, SettingsConstants.MAINNET)

                elif r == "tb1q":
                    # Native Segwit (single sig or multisig), testnet
                    self.address_type = (SettingsConstants.NATIVE_SEGWIT, SettingsConstants.TESTNET)

                elif r == "bcrt1q":
                    # Native Segwit (single sig or multisig), regtest
                    self.address_type = (SettingsConstants.NATIVE_SEGWIT, SettingsConstants.REGTEST)

                elif r == "bc1p":
                    # Native Segwit (single sig or multisig), mainnet 
                    self.address_type = (SettingsConstants.TAPROOT, SettingsConstants.MAINNET)

                elif r == "tb1p":
                    # Native Segwit (single sig or multisig), testnet
                    self.address_type = (SettingsConstants.TAPROOT, SettingsConstants.TESTNET)

                elif r == "bcrt1p":
                    # Native Segwit (single sig or multisig), regtest
                    self.address_type = (SettingsConstants.TAPROOT, SettingsConstants.REGTEST)
                
                return DecodeQRStatus.COMPLETE

        return DecodeQRStatus.INVALID


    def get_address(self):
        if self.address != None:
            return self.address
        return None
        

    def get_address_type(self):
        if self.address != None:
            if self.address_type != None:
                return self.address_type
            else:
                return "Unknown"
        return None



class SpecterWalletQrDecoder(BaseAnimatedQrDecoder):
    """
        Decodes animated frames to get a wallet descriptor from Specter Desktop
    """
    def validate_json(self) -> str:
        try:
            j = "".join(self.segments)
            json.loads(j)
        except json.decoder.JSONDecodeError:
            return False
        return True


    @property
    def is_valid(self):
        if self.validate_json():
            j = "".join(self.segments)
            data = json.loads(j)
            if "descriptor" in data:
                return True
            return False


    def get_wallet_descriptor(self) -> str:
        if self.is_valid:
            j = "".join(self.segments)
            data = json.loads(j)
            return data['descriptor']
        return None


    def is_complete(self) -> bool:
        return self.complete and self.is_valid()


    def current_segment_num(self, segment) -> int:
        if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
            return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(1))
        else:
            return 1


    def total_segment_nums(self, segment) -> int:
        if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
            return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(2))
        else:
            return 1


    def parse_segment(self, segment) -> str:
        try:
            return re.search(r'^p(\d+)of(\d+) (.+$)', segment, re.IGNORECASE).group(3)
        except:
            return segment



class GenericWalletQrDecoder(BaseSingleFrameQrDecoder):
    def __init__(self):
        super().__init__()
        self.descriptor = None


    def add(self, segment, qr_type=QRType.WALLET__GENERIC):
        from embit.descriptor import Descriptor
        try:
            # Validate via embit
            Descriptor.from_string(segment)
            self.descriptor = segment
            return DecodeQRStatus.COMPLETE
        except Exception as e:
            print(repr(e))
        return DecodeQRStatus.INVALID
    

    def get_wallet_descriptor(self):
        return self.descriptor

