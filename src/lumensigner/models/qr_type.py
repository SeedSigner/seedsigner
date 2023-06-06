QRTYPE_SPLITTER = ";"


class QRType:
    """
    Used with DecodeQR and EncodeQR to communicate qr encoding type
    """

    STELLAR_ADDRESS = "address"
    STELLAR_ADDRESS_NO_PREFIX = "address-no-prefix"
    STELLAR_SIGNATURE = "signature"
    SIGN_HASH = "sign-hash"
    SIGN_TX = "sign-transaction"
    REQUEST_ADDRESS = "request-address"

    SEED__SEEDQR = "seed__seedqr"
    SEED__COMPACTSEEDQR = "seed__compactseedqr"
    SEED__MNEMONIC = "seed__mnemonic"
    SEED__FOUR_LETTER_MNEMONIC = "seed__four_letter_mnemonic"

    INVALID = "invalid"
