class QRType:
    """
        Used with DecodeQR and EncodeQR to communicate qr encoding type
    """
    PSBT__BASE64 = "psbt__base64"
    PSBT__SPECTER = "psbt__specter"
    PSBT__BASE43 = "psbt__base43"
    PSBT__UR2 = "psbt__ur2"

    SEED__SEEDQR = "seed__seedqr"
    SEED__COMPACTSEEDQR = "seed__compactseedqr"
    SEED__UR2 = "seed__ur2"
    SEED__MNEMONIC = "seed__mnemonic"
    SEED__FOUR_LETTER_MNEMONIC = "seed__four_letter_mnemonic"

    SETTINGS = "settings"

    XPUB = "xpub"
    XPUB__SPECTER = "xpub__specter"
    XPUB__UR = "xpub__ur"

    BITCOIN_ADDRESS = "bitcoin_address"

    SIGN_MESSAGE = "sign_message"

    WALLET__SPECTER = "wallet__specter"
    WALLET__UR = "wallet__ur"
    WALLET__CONFIGFILE = "wallet__configfile"
    WALLET__GENERIC = "wallet__generic"
    OUTPUT__UR = "output__ur"
    ACCOUNT__UR = "account__ur"
    BYTES__UR = "bytes__ur"

    INVALID = "invalid"