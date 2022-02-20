import math

from embit import bip32
from embit.networks import NETWORKS
from binascii import b2a_base64, hexlify
from dataclasses import dataclass
from typing import List
from embit import bip32
from embit.networks import NETWORKS
from embit.psbt import PSBT
from seedsigner.helpers.ur2.ur_encoder import UREncoder
from seedsigner.helpers.ur2.ur import UR
from seedsigner.helpers.qr import QR
from seedsigner.models import Seed, QRType

from urtypes.crypto import PSBT as UR_PSBT
from urtypes.crypto import Account, HDKey, Output, Keypath, PathComponent, SCRIPT_EXPRESSION_TAG_MAP



@dataclass
class EncodeQR:
    """
       Encode psbt for displaying as qr image
    """
    # TODO: Refactor so that this is a base class with implementation classes for each
    # QR type. No reason exterior code can't directly instantiate the encoder it needs.
    psbt: PSBT = None
    seed_phrase: List[str] = None
    passphrase: str = None
    derivation: str = None
    network: str = None
    qr_type: str = None
    qr_density: str = None
    wordlist_language_code: str = None

    DENSITY__LOW = "Low"
    DENSITY__MEDIUM = "Medium"
    DENSITY__HIGH = "High"
    ALL_DENSITIES = [DENSITY__LOW, DENSITY__MEDIUM, DENSITY__HIGH]
    
    WORDLIST = None


    def __post_init__(self):
        self.qr = QR()

        if self.qr_type == None:
            raise Exception('Encoder Type Required')

        if self.qr_density == None:
            self.qr_density = EncodeQR.DENSITY__MEDIUM

        self.encoder = None
        if self.qr_type == QRType.PSBTSPECTER:
            self.encoder = SpecterEncodePSBTQR(self.psbt, self.qr_density)
        elif self.qr_type == QRType.PSBTUR2:
            self.encoder = UREncodePSBTQR(self.psbt, self.qr_density)
        elif self.qr_type == QRType.URXPUBQR:
            self.encoder = URXPubQR(self.seed_phrase, self.passphrase, self.derivation, self.network, self.qr_density, self.wordlist_language_code)
        elif self.qr_type == QRType.XPUBQR:
            self.encoder = XPubQR(self.seed_phrase, self.passphrase, self.derivation, self.network, self.wordlist_language_code)
        elif self.qr_type == QRType.SPECTERXPUBQR:
            self.encoder = SpecterXPubQR(self.seed_phrase, self.passphrase, self.derivation, self.network, self.qr_density, self.wordlist_language_code)
        elif self.qr_type == QRType.SEEDQR:
            self.encoder = SeedQR(self.seed_phrase, self.wordlist_language_code)
        elif self.qr_type == QRType.COMPACTSEEDQR:
            self.encoder = CompactSeedQR(self.seed_phrase, self.wordlist_language_code)
        else:
            raise Exception('Encoder Type not Supported')


    def totalParts(self):
        return self.encoder.seqLen()


    def nextPart(self):
        return self.encoder.nextPart()


    def part2Image(self, part, width=240, height=240, border=3):
        return self.qr.qrimage_io(part, width, height, border)


    def nextPartImage(self, width=240, height=240, border=3, background_color="bdbdbd"):
        part = self.nextPart()
        if self.qr_type == QRType.SEEDQR:
            return self.qr.qrimage(part, width, height, border)
        else:
            return self.qr.qrimage_io(part, width, height, border, background_color=background_color)


    def isComplete(self):
        return self.encoder.isComplete()


    def getQRDensity(self):
        return self.qr_density


    def getQRType(self):
        return self.qr_type



class UREncodePSBTQR:
    def __init__(self, p, qr_density):
        self.psbt = p
        self.qr_max_fragement_size = 20
        
        qr_ur_bytes = UR("crypto-psbt", UR_PSBT(self.psbt.serialize()).to_cbor())

        if qr_density == EncodeQR.DENSITY__LOW:
            self.qr_max_fragement_size = 10
        elif qr_density == EncodeQR.DENSITY__MEDIUM:
            self.qr_max_fragement_size = 30
        elif qr_density == EncodeQR.DENSITY__HIGH:
            self.qr_max_fragement_size = 120

        self.ur2_encode = UREncoder(qr_ur_bytes,self.qr_max_fragement_size,0)


    def seqLen(self):
        return self.ur2_encode.fountain_encoder.seq_len()


    def nextPart(self) -> str:
        return self.ur2_encode.next_part().upper()


    def isComplete(self):
        return self.ur2_encode.is_complete()



class SpecterEncodePSBTQR:
    def __init__(self, p, qr_density):
        self.psbt = p
        self.qr_max_fragement_size = 65
        self.parts = []
        self.part_num_sent = 0
        self.sent_complete = False

        if qr_density == EncodeQR.DENSITY__LOW:
            self.qr_max_fragement_size = 40
        elif qr_density == EncodeQR.DENSITY__MEDIUM:
            self.qr_max_fragement_size = 65
        elif qr_density == EncodeQR.DENSITY__HIGH:
            self.qr_max_fragement_size = 90

        self.__createParts()


    def __createParts(self):
        base64_psbt = b2a_base64(self.psbt.serialize())

        if base64_psbt[-1:] == b"\n":
            base64_psbt = base64_psbt[:-1]

        base64_psbt = base64_psbt.decode('utf-8')

        start = 0
        stop = self.qr_max_fragement_size
        qr_cnt = ((len(base64_psbt)-1) // self.qr_max_fragement_size) + 1

        if qr_cnt == 1:
            self.parts.append(base64_psbt[start:stop])

        cnt = 0
        while cnt < qr_cnt and qr_cnt != 1:
            part = "p" + str(cnt+1) + "of" + str(qr_cnt) + " " + base64_psbt[start:stop]
            self.parts.append(part)

            start = start + self.qr_max_fragement_size
            stop = stop + self.qr_max_fragement_size
            if stop > len(base64_psbt):
                stop = len(base64_psbt)
            cnt += 1


    def seqLen(self):
        return len(self.parts)


    def nextPart(self) -> str:
        # if part num sent is gt number of parts, start at 0
        if self.part_num_sent > (len(self.parts) - 1):
            self.part_num_sent = 0

        part = self.parts[self.part_num_sent]

        # when parts sent eq num of parts in list
        if self.part_num_sent == (len(self.parts) - 1):
            self.sent_complete = True

        # increment to next part
        self.part_num_sent += 1

        return part


    def isComplete(self):
        return self.sent_complete



class SeedQR:
    def __init__(self, seed_phrase: List[str], wordlist_language_code: str):
        self.seed_phrase = seed_phrase
        self.wordlist = Seed.get_wordlist(wordlist_language_code)
        
        if self.wordlist == None:
            raise Exception('Wordlist Required')


    def seqLen(self):
        return 1


    def nextPart(self):
        data = ""
        # Output as Numeric data format
        for word in self.seed_phrase:
            index = self.wordlist.index(word)
            data += str("%04d" % index)
        return data


    def isComplete(self):
        return True


class CompactSeedQR(SeedQR):
    def nextPart(self):
        # Output as binary data format
        binary_str = ""
        for word in self.seed_phrase:
            index = self.wordlist.index(word)

            # Convert index to binary, strip out '0b' prefix; zero-pad to 11 bits
            binary_str += bin(index).split('b')[1].zfill(11)

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
            as_bytes.append(int('0b' + binary_str[i*8:(i+1)*8], 2))
        
        # Must return data as `bytes` for `qrcode` to properly recognize it as byte data
        return bytes(as_bytes)



class XPubQR:
    def __init__(self, seed_phrase, passphrase, derivation, network, wordlist_language_code):
        self.seed_phrase = seed_phrase
        self.passphrase = passphrase
        self.derivation = derivation
        self.wordlist = Seed.get_wordlist(wordlist_language_code)
        self.parts = []
        self.part_num_sent = 0
        self.sent_complete = False

        if self.wordlist == None:
            raise Exception('Wordlist Required')
            
        version = bip32.detect_version(self.derivation, default="xpub", network=NETWORKS[network])
        self.seed = Seed(mnemonic=self.seed_phrase, passphrase=self.passphrase, wordlist_language_code=wordlist_language_code)
        self.root = bip32.HDKey.from_seed(self.seed.seed, version=NETWORKS[network]["xprv"])
        self.fingerprint = self.root.child(0).fingerprint
        self.xprv = self.root.derive(self.derivation)
        self.xpub = self.xprv.to_public()
        self.xpub_base58 = self.xpub.to_string(version=version)
        self.network = network

        self.xpubstring = "[%s%s]%s" % (hexlify(self.fingerprint).decode('utf-8'),self.derivation[1:],self.xpub_base58)

        if isinstance(self, XPubQR):
            self.__createParts()


    def __createParts(self):
        self.parts = []
        self.parts.append(self.xpubstring)


    def nextPart(self) -> str:
        if len(self.parts) > 0:
            self.sent_complete = True
            return self.parts[0]


    def seqLen(self):
        return len(self.parts)


    def isComplete(self):
        return self.sent_complete



class SpecterXPubQR(XPubQR):
    def __init__(self, seed_phrase, passphrase, derivation, network, qr_density, wordlist_language_code):
        self.qr_max_fragement_size = 65
        if qr_density == EncodeQR.DENSITY__LOW:
            self.qr_max_fragement_size = 40
        elif qr_density == EncodeQR.DENSITY__MEDIUM:
            self.qr_max_fragement_size = 65
        elif qr_density == EncodeQR.DENSITY__HIGH:
            self.qr_max_fragement_size = 90

        super().__init__(seed_phrase, passphrase, derivation, network, wordlist_language_code)
        self.__createParts()


    def __createParts(self):
        self.parts = []

        start = 0
        stop = self.qr_max_fragement_size
        qr_cnt = ((len(self.xpubstring)-1) // self.qr_max_fragement_size) + 1

        if qr_cnt == 1:
            self.parts.append(self.xpubstring[start:stop])

        cnt = 0
        while cnt < qr_cnt and qr_cnt != 1:
            part = "p" + str(cnt+1) + "of" + str(qr_cnt) + " " + self.xpubstring[start:stop]
            self.parts.append(part)

            start = start + self.qr_max_fragement_size
            stop = stop + self.qr_max_fragement_size
            if stop > len(self.xpubstring):
                stop = len(self.xpubstring)
            cnt += 1


    def nextPart(self) -> str:
        # if part num sent is gt number of parts, start at 0
        if self.part_num_sent > (len(self.parts) - 1):
            self.part_num_sent = 0

        part = self.parts[self.part_num_sent]

        # when parts sent eq num of parts in list
        if self.part_num_sent == (len(self.parts) - 1):
            self.sent_complete = True

        # increment to next part
        self.part_num_sent += 1

        return part


    def seqLen(self):
        return len(self.parts)


    def isComplete(self):
        return self.sent_complete
    


class URXPubQR(XPubQR):    
    def __init__(self, seed_phrase, passphrase, derivation, network, qr_density, wordlist_language_code):
        super().__init__(seed_phrase, passphrase, derivation, network, wordlist_language_code)
        
        if qr_density == EncodeQR.DENSITY__LOW:
            self.qr_max_fragement_size = 10
        elif qr_density == EncodeQR.DENSITY__MEDIUM:
            self.qr_max_fragement_size = 30
        elif qr_density == EncodeQR.DENSITY__HIGH:
            self.qr_max_fragement_size = 120
        
        def derivation_to_keypath(path: str) -> list:
            arr = path.split("/")
            if arr[0] == "m":
                arr = arr[1:]
            if len(arr) == 0:
                return Keypath([],self.root.my_fingerprint, None)
            if arr[-1] == "":
                # trailing slash
                arr = arr[:-1]

            for i, e in enumerate(arr):
                if e[-1] == "h" or e[-1] == "'":
                    arr[i] = PathComponent(int(e[:-1]), True)
                else:
                    arr[i] = PathComponent(int(e), False)
                    
            return Keypath(arr, self.root.my_fingerprint, len(arr))
            
        origin = derivation_to_keypath(derivation)
        
        self.ur_hdkey = HDKey({ 'key': self.xpub.key.serialize(),
        'chain_code': self.xpub.chain_code,
        'origin': origin,
        'parent_fingerprint': self.xpub.fingerprint})

        ur_outputs = []

        if len(origin.components) > 0:
            if origin.components[0].index == 84: # Native Single Sig
                ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[404]],self.ur_hdkey))
            elif origin.components[0].index == 49: # Nested Single Sig
                ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[400], SCRIPT_EXPRESSION_TAG_MAP[404]],self.ur_hdkey))
            elif origin.components[0].index == 48: # Multisig
                if len(origin.components) >= 4:
                    if origin.components[3].index == 2:  # Native Multisig
                        ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[401]],self.ur_hdkey))
                    elif origin.components[3].index == 1:  # Nested Multisig
                        ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[400], SCRIPT_EXPRESSION_TAG_MAP[401]],self.ur_hdkey))
        
        # If empty, add all script types
        if len(ur_outputs) == 0:
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[404]],self.ur_hdkey))
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[400], SCRIPT_EXPRESSION_TAG_MAP[404]],self.ur_hdkey))
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[401]],self.ur_hdkey))
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[400], SCRIPT_EXPRESSION_TAG_MAP[401]],self.ur_hdkey))
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[403]],self.ur_hdkey))
        
        ur_account = Account(self.root.my_fingerprint, ur_outputs)

        qr_ur_bytes = UR("crypto-account", ur_account.to_cbor())

        self.ur2_encode = UREncoder(qr_ur_bytes, self.qr_max_fragement_size, 0)


    def seqLen(self):
            return self.ur2_encode.fountain_encoder.seq_len()


    def nextPart(self) -> str:
        return self.ur2_encode.next_part().upper()


    def isComplete(self):
        return self.sent_complete



class URXPubQR(XPubQR):
    def __init__(self, seed_phrase, passphrase, derivation, network, qr_density, wordlist_language_code):
        super().__init__(self, seed_phrase, passphrase, derivation, network, wordlist_language_code)
        if qr_density == EncodeQR.LOW:
            self.qr_max_fragement_size = 10
        elif qr_density == EncodeQR.MEDIUM:
            self.qr_max_fragement_size = 30
        elif qr_density == EncodeQR.HIGH:
            self.qr_max_fragement_size = 120
        
        def derivation_to_keypath(path: str) -> list:
            arr = path.split("/")
            if arr[0] == "m":
                arr = arr[1:]
            if len(arr) == 0:
                return Keypath([],self.root.my_fingerprint, None)
            if arr[-1] == "":
                # trailing slash
                arr = arr[:-1]

            for i, e in enumerate(arr):
                if e[-1] == "h" or e[-1] == "'":
                    arr[i] = PathComponent(int(e[:-1]), True)
                else:
                    arr[i] = PathComponent(int(e), False)
                    
            return Keypath(arr, self.root.my_fingerprint, len(arr))
            
        origin = derivation_to_keypath(derivation)
        
        self.ur_hdkey = HDKey({ 'key': self.xpub.key.serialize(),
        'chain_code': self.xpub.chain_code,
        'origin': origin,
        'parent_fingerprint': self.xpub.fingerprint})

        ur_outputs = []

        if len(origin.components) > 0:
            if origin.components[0].index == 84: # Native Single Sig
                ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[404]],self.ur_hdkey))
            elif origin.components[0].index == 49: # Nested Single Sig
                ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[400], SCRIPT_EXPRESSION_TAG_MAP[404]],self.ur_hdkey))
            elif origin.components[0].index == 48: # Multisig
                if len(origin.components) >= 4:
                    if origin.components[3].index == 2:  # Native Multisig
                        ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[401]],self.ur_hdkey))
                    elif origin.components[3].index == 1:  # Nested Multisig
                        ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[400], SCRIPT_EXPRESSION_TAG_MAP[401]],self.ur_hdkey))
        
        # If empty, add all script types
        if len(ur_outputs) == 0:
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[404]],self.ur_hdkey))
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[400], SCRIPT_EXPRESSION_TAG_MAP[404]],self.ur_hdkey))
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[401]],self.ur_hdkey))
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[400], SCRIPT_EXPRESSION_TAG_MAP[401]],self.ur_hdkey))
            ur_outputs.append(Output([SCRIPT_EXPRESSION_TAG_MAP[403]],self.ur_hdkey))
        
        ur_account = Account(self.root.my_fingerprint, ur_outputs)

        qr_ur_bytes = UR("crypto-account", ur_account.to_cbor())

        self.ur2_encode = UREncoder(qr_ur_bytes, self.qr_max_fragement_size, 0)


    def seqLen(self):
            return self.ur2_encode.fountain_encoder.seq_len()


    def nextPart(self) -> str:
        return self.ur2_encode.next_part().upper()


    def isComplete(self):
        return self.ur2_encode.is_complete()
