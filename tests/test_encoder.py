import base64

from lumensigner.models import EncodeQR, QRType


def test_encode_seedqr():
    mnemonic = "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash"

    e = EncodeQR(seed_phrase=mnemonic.split(), qr_type=QRType.SEED__SEEDQR)
    print(e.next_part())
    assert e.next_part() == "121802020768124106400009195602431595117715840445"


def test_encode_address():
    address = "GBMLPRFCZDZJPKUPHUSHCKA737GOZL7ERZLGGMJ6YGHBFJZ6ZKMKCZTM"
    e = EncodeQR(
        stellar_address=address,
        derivation="m/44'/148'/128'",
        qr_type=QRType.STELLAR_ADDRESS,
    )
    assert (
        e.next_part()
        == "address;m/44'/148'/128';GBMLPRFCZDZJPKUPHUSHCKA737GOZL7ERZLGGMJ6YGHBFJZ6ZKMKCZTM"
    )


def test_encode_address_no_prefix():
    address = "GBMLPRFCZDZJPKUPHUSHCKA737GOZL7ERZLGGMJ6YGHBFJZ6ZKMKCZTM"
    e = EncodeQR(stellar_address=address, qr_type=QRType.STELLAR_ADDRESS_NO_PREFIX)
    assert e.next_part() == "GBMLPRFCZDZJPKUPHUSHCKA737GOZL7ERZLGGMJ6YGHBFJZ6ZKMKCZTM"


def test_encode_signature():
    signature = b"w\x9f\xd3S\x15\x84\xb1\x80\x87\x07\xd73\x1e\xd3\xaf\xb6\xb4\xbb\xa5W\x81\x04\x97\xd8\xf0\x93\xa6L(\xca<\xeb\xca\xd3X\xc2\x04z\x92\xd2\xdf\x19\x1eK\xaf\x0e2\x89\xa3\rN\xa9FGT\xde\xa4S\xc8\xaei\x0b\x99\x03"
    e = EncodeQR(signature=signature, qr_type=QRType.STELLAR_SIGNATURE)
    assert e.next_part() == f"signature;{base64.b64encode(signature).decode('utf-8')}"
