from enum import IntEnum
from embit import psbt, bip39
from binascii import b2a_base64
from seedsigner.helpers.ur2.ur_encoder import UREncoder
from seedsigner.helpers.ur2.cbor_lite import CBOREncoder
from seedsigner.helpers.ur2.ur import UR
from seedsigner.helpers.bcur import (bc32encode, cbor_encode, bcur_encode)
from seedsigner.helpers.qr import QR
from seedsigner.models.decode_qr import QRType

###
### EncodeQR Class
### Purpose: used to encode psbt for displaying as qr image
###

class EncodeQR:

    def __init__(self, p, qr_type=None, qr_density=None):
        if qr_type == None and self.psbt != None:
            self.qr_type = QRType.PSBTSPECTER
        else:
            self.qr_type = qr_type

        if self.qr_type in (QRType.PSBTSPECTER, QRType.PSBTUR2):
            self.psbt = p
        else:
            self.psbt = None

        if qr_density == None:
            self.qr_density = EncodeQRDensity.MEDIUM
        else:
            self.qr_density = qr_density

        self.qr = QR()

        self.encoder = None
        if qr_type == QRType.PSBTSPECTER:
            self.encoder = SpecterEncodePSBTQR(self.psbt, self.qr_density)
        elif qr_type == QRType.PSBTUR2:
            self.encoder = UREncodePSBTQR(self.psbt, self.qr_density)
        elif qr_type == QRType.SEEDSSQR:
            seed_phrase = p
            self.encoder = SeedSSQR(seed_phrase)
        else:
            raise Exception('Encoder Type not Supported')

    def totalParts(self):
        return self.encoder.seqLen()

    def nextPart(self):
        return self.encoder.nextPart()

    def part2Image(self, part, width=240, height=240, border=3):
        return self.qr.qrimage_io(part, width, height, border)

    def nextPartImage(self, width=240, height=240, border=3):
        part = self.nextPart()
        return self.qr.qrimage_io(part, width, height, border)

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

        cbor_encoder = CBOREncoder()
        cbor_encoder.encodeBytes(self.psbt.serialize())
        qr_ur_bytes = UR("crypto-psbt", cbor_encoder.get_bytes())

        self.ur2_encode = UREncoder(qr_ur_bytes,self.qr_max_fragement_size,0)

        if qr_density == EncodeQRDensity.LOW:
            self.qr_max_fragement_size = 10
        elif qr_density == EncodeQRDensity.MEDIUM:
            self.qr_max_fragement_size = 20
        elif qr_density == EncodeQRDensity.HIGH:
            self.qr_max_fragement_size = 80

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

        if qr_density == EncodeQRDensity.LOW:
            self.qr_max_fragement_size = 40
        elif qr_density == EncodeQRDensity.MEDIUM:
            self.qr_max_fragement_size = 65
        elif qr_density == EncodeQRDensity.HIGH:
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

class SeedSSQR:

    def __init__(self, seed_phrase):
        self.seed_phrase = seed_phrase

    def seqLen(self):
        return 1

    def nextPart(self):
        data = ""
        for word in self.seed_phrase:
            index = bip39.WORDLIST.index(word)
            data += str("%04d" % index)

        return data

    def isComplete(self):
        return True


class EncodeQRDensity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3