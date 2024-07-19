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
from urtypes.crypto import Account, Output
from urtypes.bytes import Bytes

from seedsigner.helpers.ur2.ur_decoder import URDecoder
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants


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

        if self.qr_type == None:
            self.qr_type = qr_type

            if self.qr_type in [QRType.PSBT__UR2, QRType.OUTPUT__UR, QRType.ACCOUNT__UR, QRType.BYTES__UR]:
                self.decoder = URDecoder() # BCUR Decoder

            elif self.qr_type == QRType.PSBT__SPECTER:
                self.decoder = SpecterPsbtQrDecoder() # Specter Desktop PSBT QR base64 decoder

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

            elif self.qr_type == QRType.SIGN_MESSAGE:
                self.decoder = SignMessageQrDecoder() # Single Segment sign message request

            elif self.qr_type == QRType.WALLET__SPECTER:
                self.decoder = SpecterWalletQrDecoder() # Specter Desktop Wallet Export decoder

            elif self.qr_type == QRType.WALLET__GENERIC:
                self.decoder = GenericWalletQrDecoder()
                
            elif self.qr_type == QRType.WALLET__CONFIGFILE:
                self.decoder = MultiSigConfigFileQRDecoder()

        elif self.qr_type != qr_type:
            raise Exception('QR Fragment Unexpected Type Change')
        
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
            qr_str = data.decode('utf-8')
        else:
            # it's already str data
            qr_str = data

        if self.qr_type in [QRType.PSBT__UR2, QRType.OUTPUT__UR, QRType.ACCOUNT__UR, QRType.BYTES__UR]:
            added_part = self.decoder.receive_part(qr_str)
            if self.decoder.is_complete():
                self.complete = True
                return DecodeQRStatus.COMPLETE
            if added_part:
                return DecodeQRStatus.PART_COMPLETE
            else:
                return DecodeQRStatus.PART_EXISTING

        else:
            # All other formats use the same method signature
            rt = self.decoder.add(qr_str, self.qr_type)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt


    # TODO: Refactor all of these specific `get_` to just something generic like
    #   `get_data` and let each QRDecoder class return whatever it needs to as a
    #   str, tuple, dict, etc?
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
            return self.decoder.data


    def get_address(self):
        if self.is_address:
            return self.decoder.get_address()


    def get_address_type(self):
        if self.is_address:
            return self.decoder.get_address_type()


    def get_qr_data(self) -> dict:
        """
        This provides a single access point for external code to retrieve the QR data,
        regardless of which decoder is actually instantiated.
        """
        # TODO: Implement this approach across all decoders
        return self.decoder.get_qr_data()


    def get_wallet_descriptor(self):
        if self.is_wallet_descriptor:
            if self.qr_type in [QRType.OUTPUT__UR, QRType.ACCOUNT__UR, QRType.BYTES__UR]:
                cbor = self.decoder.result_message().cbor
                if self.qr_type == QRType.OUTPUT__UR:
                    return Output.from_cbor(cbor).descriptor()
                elif self.qr_type == QRType.ACCOUNT__UR:
                    return Account.from_cbor(cbor).output_descriptors[0].descriptor()
                elif self.qr_type == QRType.BYTES__UR:
                    raw = Bytes.from_cbor(cbor).data
                    descriptor = DecodeQR.multisig_setup_file_to_descriptor(raw.decode("utf-8"))
                    return descriptor
            else:
                # All the other wallet output descriptor decoder types use the same method signature
                return self.decoder.get_wallet_descriptor()


    def get_percent_complete(self, weight_mixed_frames: bool = False) -> int:
        if not self.decoder:
            return 0

        if self.qr_type in [QRType.PSBT__UR2, QRType.OUTPUT__UR, QRType.ACCOUNT__UR, QRType.BYTES__UR]:
            return int(self.decoder.estimated_percent_complete(weight_mixed_frames=weight_mixed_frames) * 100)

        elif self.qr_type in [QRType.PSBT__SPECTER]:
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
    def is_sign_message(self):
        return self.qr_type == QRType.SIGN_MESSAGE
        

    @property
    def is_wallet_descriptor(self):
        check = self.qr_type in [QRType.WALLET__SPECTER, QRType.WALLET__UR, QRType.WALLET__CONFIGFILE, QRType.WALLET__GENERIC, QRType.OUTPUT__UR]
        
        if self.qr_type in [QRType.BYTES__UR]:
            cbor = self.decoder.result_message().cbor
            raw = Bytes.from_cbor(cbor).data
            data = raw.decode("utf-8").lower()
            check = 'policy:' in data and "format:" in data and "derivation:" in data
        
        return check

    @property
    def is_settings(self):
        return self.qr_type == QRType.SETTINGS


    @staticmethod
    def extract_qr_data(image, is_binary:bool = False) -> str | None:
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

            elif re.search("^UR:CRYPTO-OUTPUT/", s, re.IGNORECASE):
                return QRType.OUTPUT__UR

            elif re.search("^UR:CRYPTO-ACCOUNT/", s, re.IGNORECASE):
                return QRType.ACCOUNT__UR

            elif re.search(r'^p(\d+)of(\d+) ([A-Za-z0-9+\/=]+$)', s, re.IGNORECASE): #must be base64 characters only in segment
                return QRType.PSBT__SPECTER

            elif re.search("^UR:BYTES/", s, re.IGNORECASE):
                return QRType.BYTES__UR

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

            elif "multisig setup file" in s.lower():
                return QRType.WALLET__CONFIGFILE

            elif "sortedmulti" in s:
                return QRType.WALLET__GENERIC

            # Seed
            if re.search(r'\d{48,96}', s):
                return QRType.SEED__SEEDQR

            # Bitcoin Address
            elif DecodeQR.is_bitcoin_address(s):
                return QRType.BITCOIN_ADDRESS

            # message signing
            elif s.startswith("signmessage"):
                return QRType.SIGN_MESSAGE

            # config data
            if s.startswith("settings::"):
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
        elif re.search(r'^((bc1|tb1|bcr|[123]|[mn])[a-zA-HJ-NP-Z0-9]{25,62})$', s):
            # TODO: Handle regtest bcrt?
            return True
        else:
            return False


    @staticmethod
    def multisig_setup_file_to_descriptor(text) -> str:
        # sample text file, parse the contents and create descriptor
        """
        Name: SeedSigner Dev Funds
        Policy: 4 of 6
        Derivation: m/48'/0'/0'/2'
        Format: P2WSH
        
        E0811B6B: xpub6E8v7uy63pCeJvHe5W8ea8zTnCtKMFgMRb5bueWWcUFMw6sWmUwTqxM8cFiKQRWkA2Fxth9HJZufJwjWTTvU1UGZNpTrh9khrswYMgeHiCt
        852B308F: xpub6ErhgAWfnEqW7xDBm1iLq5JjNyUS65YUFnjHLrRv9zmdDEtuE75bpWQ8o6bSBnpT6AkrrsA8eA5SmEFArZn11KEPaZJzx9mHTXPWZCsxLyh
        7EDF9C59: xpub6DaFfKoe7WpofrbYeNo3Wv2AiLUMeyrPwotXfukFxUHbK4JxaLHTd5394QtH5wnjFzBgr2YnJpHhXv25Zsqv2APmMFvH1DsKHj5LCr3pmXs
        B433E095: xpub6EF51itHko2YhGTjVeuYbBgJjVbTzzpYzn2a3JwZHpDrMePRVgXGBHMx2Yv1KwgLsUn9i7ExcAo8uqMx4pDjVRY9J7qnceFAwRRj16dd5AS
        184D07EB: xpub6EEoTpcQu7N4R8D84pJjZ69j3minevnYLDDoo2HBzYBXTQ4rGVf4XGTyCYFwJuZdsF9MyFYJNzYEjg5LGMA1ubTGWuDnjHAZz6ficVRDTSy
        3E451EFE: xpub6ExQPvQxGBMaPxr8Fv7Vq91ztJFFX3VWvtpvex6UPZ1AptTeuAiJGCtKkgwJkrwpMZMagh9ex6rL4sM8axfFcdQbERoFCRUKTJxrBkJh56g
        """
        
        lines = text.split('\n')
        
        m = 0
        n = 0
        xpubs = []
        x = 0
        derivation = ''
        descriptor = ''
        
        lines = text.split('\n')
        
        for l in lines:
            if l.find('#') == 0:
                # skip comments
                continue
        
            l = l.strip()
        
            if ':' not in l:
                # when label/value divider not found, skip line
                continue
                        
            label, value = l.split(':', 1)
            label = label.strip().lower()
            value = value.strip()
        
            if label == 'policy':
                try:
                    match = re.search(r'(\d+)\D*(\d+)', value)
                    m = int(match.group(1))
                    n = int(match.group(2))
                except:
                    raise Exception(f"Policy line not supported")
            elif label == 'derivation':
                derivation = value
            elif label == 'format':
                if value.lower() in ['p2wsh', 'p2sh-p2wsh', 'p2wsh-p2sh']:
                    script_type = value.lower()
            elif len(label) == 8:
                if len(xpubs) == 0:
                    xpubs = [None] * n
        
                xpubs[x] = {'xfp': label, 'key': value}
                x += 1
        
        if None in xpubs or len(xpubs) != n:
            raise Exception(f"bad or missing xpub")
        
        if m <= 0 or m > 9 or n <= 0 or n > 9:
            raise Exception(f"bad or missing policy")
        
        if len(derivation) == 0:
            raise Exception(f"bad or missing derivation path")
        
        if script_type not in ['p2wsh', 'p2sh-p2wsh', 'p2wsh-p2sh']:
            raise Exception(f"bad or missing script format")
        
        # create descriptor string
        
        if script_type == "p2wsh":
            script_open = "wsh(sortedmulti(" + str(m)
            script_close = "))"
        elif script_type in ["p2sh-p2wsh", 'p2wsh-p2sh']:
            script_open = "sh(wsh(sortedmulti(" + str(m)
            script_close = ")))"
        
        descriptor = script_open
        
        for x in xpubs:
            if derivation[0] == 'm':
                derivation = derivation[1:]
            derivation = derivation.replace("'", "h")
            descriptor += ',[' + x['xfp'] + derivation + "]" + x['key'] + "/{0,1}/*"
        
        descriptor += script_close

        return descriptor



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
    
    def get_qr_data(self) -> dict:
        # TODO: standardize this approach across all decoders (example: SignMessageQrDecoder)
        raise Exception("get_qr_data must be implemented in decoder child class")



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



class SettingsQrDecoder(BaseSingleFrameQrDecoder):
    """
        Decodes settings data from the SettingsQR Generator.
    """
    def __init__(self):
        super().__init__()
        self.data = None


    def add(self, segment, qr_type=QRType.SETTINGS):
        """
            * Ignores unrecognized settings options.
            * Raises an Exception if a settings value is invalid.

            See `Settings.update()` for info on settings validation, especially for
            missing settings.
        """
        if not segment.startswith("settings::"):
            raise Exception("Invalid SettingsQR data")
        
        # Leave any other parsing or validation up to the Settings class itself.
        # SettingsQR are just ascii data to hand it over as-is.
        self.data = segment

        self.complete = True
        self.collected_segments = 1
        return DecodeQRStatus.COMPLETE



class SignMessageQrDecoder(BaseSingleFrameQrDecoder):
    def __init__(self):
        super().__init__()
        self.message = None
        self.derivation_path = None


    def add(self, segment, qr_type=QRType.SIGN_MESSAGE):
        """
            Expected QR data format:

            signmessage {derivation_path} ascii:{message}
        """
        parts = segment.split()
        self.derivation_path = parts[1].replace("h", "'")
        fmt = parts[2].split(":")[0]
        self.message = segment.split(f"{fmt}:")[1]

        # TODO: support formats other than ascii?
        if fmt != "ascii":
            logger.info(f"Sign message: Unsupported format: {fmt}")
            return DecodeQRStatus.INVALID

        self.complete = True
        self.collected_segments = 1

        return DecodeQRStatus.COMPLETE


    def get_qr_data(self) -> dict:
        return dict(derivation_path=self.derivation_path, message=self.message)



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
                    # Nested segwit single sig (p2sh-p2wpkh), nested segwit multisig (p2sh-p2wsh), or legacy multisig (p2sh); mainnet
                    # TODO: Would be more correct to use a P2SH constant
                    self.address_type = (SettingsConstants.NESTED_SEGWIT, SettingsConstants.MAINNET)

                elif r == "2":
                    # Nested segwit single sig (p2sh-p2wpkh), nested segwit multisig (p2sh-p2wsh), or legacy multisig (p2sh); testnet / regtest
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
            self.complete = True
            return DecodeQRStatus.COMPLETE
        except Exception as e:
            logger.info(repr(e), exc_info=True)
        return DecodeQRStatus.INVALID
    

    def get_wallet_descriptor(self):
        return self.descriptor



class MultiSigConfigFileQRDecoder(GenericWalletQrDecoder):    
    def add(self, segment, qr_type=QRType.WALLET__CONFIGFILE):
        descriptor = DecodeQR.multisig_setup_file_to_descriptor(segment)
        return super().add(descriptor,qr_type=QRType.WALLET__CONFIGFILE)
