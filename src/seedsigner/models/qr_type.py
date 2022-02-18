from enum import IntEnum

###
### QRType Class IntEum
### Purpose: used with DecodeQR and EncodeQR to communicate qr encoding type
###

class QRType(IntEnum):
    PSBTBASE64 = 1
    PSBTSPECTER = 2
    PSBTURLEGACY = 3
    PSBTBASE43 = 4
    PSBTUR2 = 5
    SEEDQR = 6
    COMPACTSEEDQR = 10
    SEEDUR2 = 7
    SEEDMNEMONIC = 8
    SEED4LETTERMNEMONIC = 9
    XPUBQR = 20
    SPECTERXPUBQR = 21
    URXPUBQR = 22
    BITCOINADDRESSQR = 30
    SPECTERWALLETQR = 40
    URWALLETQR = 41
    BLUEWALLETQR = 42
    INVALID = 100