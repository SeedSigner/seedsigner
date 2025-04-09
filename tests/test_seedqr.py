import os
from embit import bip39
from seedsigner.helpers.qr import QR
from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus
from seedsigner.models.encode_qr import SeedQrEncoder, CompactSeedQrEncoder
from seedsigner.models.qr_type import QRType



def run_encode_decode_test(entropy: bytes, mnemonic_length, qr_type):
    """ Helper method to re-run multiple variations of the same encode/decode test """
    mnemonic = bip39.mnemonic_from_bytes(entropy).split()
    assert len(mnemonic) == mnemonic_length

    if qr_type == QRType.SEED__SEEDQR:
        e = SeedQrEncoder(mnemonic=mnemonic)
    elif qr_type == QRType.SEED__COMPACTSEEDQR:
        e = CompactSeedQrEncoder(mnemonic=mnemonic)

    data = e.next_part()

    qr = QR()
    image = qr.qrimage(
        data=data,
        width=240,
        height=240,
        border=3
    )

    decoder = DecodeQR()
    status = decoder.add_image(image)
    assert status == DecodeQRStatus.COMPLETE

    decoded_seed_phrase = decoder.get_seed_phrase()
    assert mnemonic == decoded_seed_phrase



def test_standard_seedqr_encode_decode_():
    """ Should encode 24- and 12- word mnemonics to Standard SeedQR format and decode
        them back again to their original mnemonic seed phrase.
    """
    # 24-word seed
    run_encode_decode_test(os.urandom(32), mnemonic_length=24, qr_type=QRType.SEED__SEEDQR)

    # 12-word seed
    run_encode_decode_test(os.urandom(16), mnemonic_length=12, qr_type=QRType.SEED__SEEDQR)



def test_compact_seedqr_encode_decode():
    """ Should encode 24- and 12- word mnemonics to CompactSeedQR format and decode
        them back again to their original mnemonic seed phrase.
    """
    # 24-word seed
    run_encode_decode_test(os.urandom(32), mnemonic_length=24, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 12-word seed
    run_encode_decode_test(os.urandom(16), mnemonic_length=12, qr_type=QRType.SEED__COMPACTSEEDQR)



def test_compact_seedqr_handles_null_bytes():
    """ Should properly encode a CompactSeedQR with null bytes (b'\x00') in the input
        entropy and decode it back to the original mnemonic seed.
    """
    # 24-word seed, null bytes at the front
    entropy = b'\x00' + os.urandom(31)
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 24-word seed, null bytes in the middle
    entropy = os.urandom(10) + b'\x00' + os.urandom(21)
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 24-word seed, null bytes at the end
    entropy = os.urandom(31) + b'\x00'
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 24-word seed, multiple null bytes
    entropy = os.urandom(5) + b'\x00' + os.urandom(5) + b'\x00' + os.urandom(20)
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 24-word seed, multiple null bytes in a row
    entropy = os.urandom(10) + b'\x00\x00' + os.urandom(20)
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 12-word seed, null bytes at the beginning
    entropy = b'\x00' + os.urandom(15)
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 12-word seed, null bytes in the middle
    entropy = os.urandom(5) + b'\x00' + os.urandom(10)
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 12-word seed, null bytes at the end
    entropy = os.urandom(15) + b'\x00'
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 12-word seed, multiple null bytes
    entropy = os.urandom(5) + b'\x00' + os.urandom(5) + b'\x00' + os.urandom(4)
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QRType.SEED__COMPACTSEEDQR)

    # 12-word seed, multiple null bytes in a row
    entropy = os.urandom(10) + b'\x00\x00' + os.urandom(4)
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QRType.SEED__COMPACTSEEDQR)


def test_compact_seedqr_bytes_interpretable_as_str():
    """ 
    Should successfully decode a Compact SeedQR whose bytes can be interpreted as a valid
    string. Most Compact SeedQR byte data will raise a UnicodeDecodeError when attempting to
    interpret it as a string, but edge cases are possible.

    see: Issue #656
    """
    # Randomly generated to pass the str.decode() step; 12- and 24-word entropy.
    entropy_bytes_tests = [
        b'\x00' * 16,  # abandon * 11 + about
        b'\x12\x15\\1j`3\x0bkL}f\x00ZYK',
        b'tv\x1bZjmqN@t\x13\x1aK\\v)',
        b'|9\x05\x1aHF9j\xda\xb6v\x05\x08#\x12=',
        b"iHK`4\x1a5\xd3\xaf\xd3\xb47htJ.}<\xea\xbf\x88Xh\x01.?R2^\xc2\xb1'",
        b'|Z\x11\x1dt\xdd\x97~t&f &G$H|^[\xd3\x9d<q]z\x14.\x11`!\xd1\x91',
        b'0\xd4\xb3\\,\xcd\x8d7c/Rp\x0e\xc2\xbb\xe4\x99\xa3=j5,\xcc\x9a[>\x19Z{\ng^',
    ]

    for entropy_bytes in entropy_bytes_tests:
        entropy_bytes.decode()  # should not raise an exception
        mnemonic_length = 12 if len(entropy_bytes) == 16 else 24
        run_encode_decode_test(entropy_bytes, mnemonic_length=mnemonic_length, qr_type=QRType.SEED__COMPACTSEEDQR)
