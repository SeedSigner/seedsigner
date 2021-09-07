from enum import IntEnum

###
### QRType Class IntEum
### Purpose: used with DecodeQR and EncodeQR to communicate qr encoding type
###

class EncodeQRDensity(IntEnum):
	LOW = 1
	MEDIUM = 2
	HIGH = 3