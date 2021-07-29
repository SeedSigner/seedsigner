from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol
import re
from enum import IntEnum
from binascii import a2b_base64, b2a_base64
from seedsigner.helpers.ur2.ur_decoder import URDecoder
from seedsigner.helpers.bcur import (cbor_decode, bc32decode)

###
### DecodePSBTQR Class
### Purpose: used to process images or string data from animated qr codes with psbt data to create binary/base64 psbt
###

class DecodePSBTQR:

    def __init__(self, qr_type=None):
        self.complete = False
        self.qr_type = qr_type
        self.ur_decoder = URDecoder() # UR2 decoder
        self.specter_qr = SpecterPSBTQR() # Specter Desktop PSBT QR base64 decoder
        self.legacy_ur = LegacyURQR() # UR Legacy decoder
        self.base64_qr = Base64QR() # Single Segments Base64

    def addString(self, qr_str):
        qr_type = DecodePSBTQR.SegmentType(qr_str)

        if self.qr_type == None:
            self.qr_type = qr_type
        elif self.qr_type != qr_type:
            raise Exception('QR Fragement Unexpected Type Change')

        if self.qr_type == DecodePSBTQRType.UR2:

            self.ur_decoder.receive_part(qr_str)
            if self.ur_decoder.is_complete():
                self.complete = True
                return DecodePSBTQRAddStatus.COMPLETE
            return DecodePSBTQRAddStatus.SUCCESS # segment added to ur2 decoder

        elif self.qr_type == DecodePSBTQRType.SPECTER:

            rt = self.specter_qr.add(qr_str)
            if rt == DecodePSBTQRAddStatus.COMPLETE:
                self.complete = True
            return rt

        elif self.qr_type == DecodePSBTQRType.URLEGACY:

            rt = self.specter_qr.add(qr_str)
            if rt == DecodePSBTQRAddStatus.COMPLETE:
                self.complete = True
            return rt

        elif self.qr_type == DecodePSBTQRType.BASE64:

            rt = self.base64_qr.add(qr_str)
            if rt == DecodePSBTQRAddStatus.COMPLETE:
                self.complete = True
            return rt

        else:
            return DecodePSBTQRAddStatus.INVALID

    def addImage(self, image):
        qr_str = DecodePSBTQR.QR2Str(image)
        if not qr_str:
            return DecodePSBTQRAddStatus.FALSE

        return self.addString(qr_str)

    def getData(self):
        if self.complete:
            if self.qr_type == DecodePSBTQRType.UR2:
                cbor = self.ur_decoder.result_message().cbor
                return cbor_decode(cbor)
            elif self.qr_type == DecodePSBTQRType.SPECTER:
                return self.specter_qr.getData()
            elif self.qr_type == DecodePSBTQRType.URLEGACY:
                return self.legacy_ur.getData()
            elif self.qr_type == DecodePSBTQRType.BASE64:
                return self.base64_qr.getData()
        return None

    def getBase64Data(self):
        if self.complete:
            data = self.getData()
            b64_psbt = b2a_base64(data)

            if b64_psbt[-1:] == b"\n":
                b64_psbt = b64_psbt[:-1]

            return b64_psbt.decode("ascii")
        return None

    def getPercentComplete(self) -> int:
        if self.qr_type == DecodePSBTQRType.UR2:
            return int(self.ur_decoder.estimated_percent_complete() * 100)
        elif self.qr_type == DecodePSBTQRType.SPECTER:
            if self.specter_qr.total_segments == None:
                return 0
            return int((self.specter_qr.collected_segments / self.specter_qr.total_segments) * 100)
        elif self.qr_type == DecodePSBTQRType.URLEGACY:
            if self.legacy_ur.total_segments == None:
                return 0
            return int((self.legacy_ur.collected_segments / self.legacy_ur.total_segments) * 100)
        elif self.qr_type == DecodePSBTQRType.BASE64:
            if self.base64_qr.complete:
                return 100
            else:
                return 0
        else:
            return 0

    def is_complete(self) -> bool:
        return self.complete

    def qrType(self):
        return self.qr_type

    @staticmethod
    def QR2Str(image) -> str:

        barcodes = pyzbar.decode(frame, symbols=[ZBarSymbol.QRCODE])

        for barcode in barcodes:
            # Only pull and return the first barcode
            return barcode.data.decode("utf-8")

    @staticmethod
    def SegmentType(s):

        if re.search("^UR\:CRYPTO-PSBT\/", s, re.IGNORECASE):
            return DecodePSBTQRType.UR2
        elif re.search("^p(\d+)of(\d+) ", s, re.IGNORECASE):
            return DecodePSBTQRType.SPECTER
        elif re.search("^UR\:BYTES\/", s, re.IGNORECASE):
            return DecodePSBTQRType.URLEGACY
        elif QRPSBT.isBase64(s):
            return DecodePSBTQRType.BASE64
        else:
            return DecodePSBTQRType.INVALID

    @staticmethod   
    def isBase64(s):
        try:
            return base64.b64encode(base64.b64decode(s)) == s
        except Exception:
            return False

###
### SpecterPSBTQR Class
### Purpose: used in DecodePSBTQR to decode Specter Desktop Animated QR PSBT encoding
###

class SpecterPSBTQR:

    def __init__(self):
        self.total_segments = None
        self.collected_segments = 0
        self.complete = False
        self.segments = []

    def add(self, segment):
        if self.total_segments == None:
            self.total_segments = SpecterPSBTQR.totalSegmentNum(segment)
            self.segments = [None] * self.total_segments
        elif self.total_segments != SpecterPSBTQR.totalSegmentNum(segment):
            raise Exception('Specter Desktop segment total changed unexpectedly')

        if self.segments[SpecterPSBTQR.currentSegmentNum(segment) - 1] == None:
            self.segments[SpecterPSBTQR.currentSegmentNum(segment) - 1] = SpecterPSBTQR.parseSegment(segment)
            self.collected_segments += 1
            if self.total_segments == self.collected_segments:
                self.complete = True
            return DecodePSBTQRAddStatus.SUCCESS # new segment added

        return DecodePSBTQRAddStatus.EXISTING # segment not added because it's already been added

    def getBase64Data(self) -> str:
        base64 = "".join(self.segments)
        if self.complete and DecodePSBTQR.isBase64(base64):
            return base64

        return None

    def getData(self):
        base64 = self.getBase64Data(self.segments)
        if base64 != None:
            return a2b_base64(base64)

        return None

    def is_complete(self) -> bool:
        return self.complete

    @staticmethod
    def currentSegmentNum(segment) -> int:
        if DecodePSBTQR.SegmentType(segment) == DecodePSBTQRType.SPECTER:
            if re.search("^p(\d+)of(\d+) ", segment, re.IGNORECASE) != None:
                return int(re.search("^p(\d+)of(\d+) ", segment, re.IGNORECASE).group(1))
        raise Exception('Unable to parse Specter Desktop segment')

    @staticmethod
    def totalSegmentNum(segment) -> int:
        if DecodePSBTQR.SegmentType(segment) == DecodePSBTQRType.SPECTER:
            if re.search("^p(\d+)of(\d+) ", segment, re.IGNORECASE) != None:
                return int(re.search("^p(\d+)of(\d+) ", segment, re.IGNORECASE).group(2))
        raise Exception('Unable to parse Specter Desktop segment')

    @staticmethod
    def parseSegment(segment) -> str:
        return segment.split(" ")[-1].strip()

###
### LegacyURQR Class
### Purpose: used in DecodePSBTQR to decode Legacy UR animated qr encoding
###

class LegacyURQR:

    def __init__(self):
        self.total_segments = None
        self.collected_segments = 0
        self.complete = False
        self.segments = []

    def add(self, segment):
        if self.total_segments == None:
            self.total_segments = LegacyURQR.totalSegmentNum(segment)
            self.segments = [None] * self.total_segments
        elif self.total_segments != LegacyURQR.totalSegmentNum(segment):
            raise Exception('Specter Desktop segment total changed unexpectedly')

        if self.segments[LegacyURQR.currentSegmentNum(segment) - 1] == None:
            self.segments[LegacyURQR.currentSegmentNum(segment) - 1] = LegacyURQR.parseSegment(segment)
            self.collected_segments += 1
            if self.total_segments == self.collected_segments:
                self.complete = True
            return DecodePSBTQRAddStatus.SUCCESS # new segment added

        return DecodePSBTQRAddStatus.EXISTING # segment not added because it's already been added

    def getBase64Data(self) -> str:
        bc32_cbor = "".join(self.segments)
        raw = cbor_decode(bc32decode(bc32_cbor))
        base64 = b2a_base64(raw)

        if self.complete and DecodePSBTQR.isBase64(base64):
            return base64

        return None

    def getData(self):
        base64 = self.getBase64Data(self.segments)
        if base64 != None:
            return a2b_base64(base64)

        return None

    def is_complete(self) -> bool:
        return self.complete

    @staticmethod
    def currentSegmentNum(segment) -> int:
        if DecodePSBTQR.SegmentType(segment) == DecodePSBTQRType.URLEGACY:
            if re.search("^UR\:BYTES\/(\d+)OF(\d+)", segment, re.IGNORECASE) != None:
                return int(re.search("^UR\:BYTES\/(\d+)OF(\d+)", segment, re.IGNORECASE).group(1))
            else:
                raise Exception('Unexpected Legacy UR Error')
        raise Exception('Unable to parse Legacy UR segment')

    @staticmethod
    def totalSegmentNum(segment) -> int:
        if DecodePSBTQR.SegmentType(segment) == DecodePSBTQRType.URLEGACY:
            if re.search("^UR\:BYTES\/(\d+)OF(\d+)", segment, re.IGNORECASE) != None:
                return int(re.search("^UR\:BYTES\/(\d+)OF(\d+)", segment, re.IGNORECASE).group(2))
            else:
                return 1
        raise Exception('Unable to parse Legacy UR segment')

    @staticmethod
    def parseSegment(segment) -> str:
        return segment.split("/")[-1].strip()

###
### LegacyURQR Class
### Purpose: used in DecodePSBTQR to decode single frame base64 encoded qr image
###          does not support animated qr because no idicator or segments or thier order
###

class Base64QR:

    def __init__(self):
        self.total_segments = 1
        self.collected_segments = 0
        self.complete = False
        self.data = None

    def add(self, segment):
        if DecodePSBTQR.isBase64(segment):
            self.complete = True
            self.data = segment
            return DecodePSBTQRAddStatus.COMPLETE

        return DecodePSBTQRAddStatus.INVALID

    @staticmethod
    def currentSegmentNum(segment) -> int:
        return 1

    @staticmethod
    def totalSegmentNum(segment) -> int:
        return 1

    @staticmethod
    def parseSegment(segment) -> str:
        return segment

###
### DecodePSBTQRType Class IntEum
### Purpose: used in DecodePSBTQR to communicate qr encoding type
###

class DecodePSBTQRType(IntEnum):
    BASE64 = 1
    SPECTER = 2
    URLEGACY = 3
    UR2 = 5
    INVALID = 100

###
### DecodePSBTQRAddStatus Class IntEum
### Purpose: used in DecodePSBTQR to communicate status of adding qr frame/segment
###

class DecodePSBTQRAddStatus(IntEnum):
    SUCCESS = 1
    EXISTING = 2
    COMPLETE = 3
    FALSE = 4
    INVALID = 5