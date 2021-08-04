from enum import IntEnum

###
### QRType Class IntEum
### Purpose: used with DecodeQR and EncodeQR to communicate qr encoding type
###

class QRType(IntEnum):
    PSBTBASE64 = 1
    PSBTSPECTER = 2
    PSBTURLEGACY = 3
    PSBTUR2 = 5
    SEEDSSQR = 6
    SEEDUR2 = 7
    XPUBQR = 8
    SPECTERXPUBQR = 9
    INVALID = 100