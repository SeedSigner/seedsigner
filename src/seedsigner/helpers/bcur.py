### bc-ur encoding stuff
from io import BytesIO
import hashlib

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def bech32_polymod(values):
    """Internal function that computes the Bech32 checksum."""
    generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def bech32_hrp_expand(hrp):
    """Expand the HRP into values for checksum computation."""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def bech32_verify_checksum(hrp, data):
    """Verify a checksum given HRP and converted data characters."""
    return bech32_polymod(bech32_hrp_expand(hrp) + data) == 1


def bech32_create_checksum(hrp, data):
    """Compute the checksum values given HRP and data."""
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def bech32_encode(hrp, data):
    """Compute a Bech32 string given HRP and data values."""
    combined = data + bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join([CHARSET[d] for d in combined])


def bech32_decode(bech):
    """Validate a Bech32 string, and determine HRP and data."""
    if (any(ord(x) < 33 or ord(x) > 126 for x in bech)) or (
        bech.lower() != bech and bech.upper() != bech
    ):
        return (None, None)
    bech = bech.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
        return (None, None)
    if not all(x in CHARSET for x in bech[pos + 1 :]):
        return (None, None)
    hrp = bech[:pos]
    data = [CHARSET.find(x) for x in bech[pos + 1 :]]
    if not bech32_verify_checksum(hrp, data):
        return (None, None)
    return (hrp, data[:-6])


def convertbits(data, frombits, tobits, pad=True):
    """General power-of-2 base conversion."""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def decode(hrp, addr):
    """Decode a segwit address."""
    hrpgot, data = bech32_decode(addr)
    if hrpgot != hrp:
        return (None, None)
    decoded = convertbits(data[1:], 5, 8, False)
    if decoded is None or len(decoded) < 2 or len(decoded) > 40:
        return (None, None)
    if data[0] > 16:
        return (None, None)
    if data[0] == 0 and len(decoded) != 20 and len(decoded) != 32:
        return (None, None)
    return (data[0], decoded)


def encode(hrp, witver, witprog):
    """Encode a segwit address."""
    ret = bech32_encode(hrp, [witver] + convertbits(witprog, 8, 5))
    if decode(hrp, ret) == (None, None):
        return None
    return ret


def bc32encode(data: bytes) -> str:
    """
    bc32 encoding
    see https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-004-bc32.md
    """
    dd = convertbits(data, 8, 5)
    polymod = bech32_polymod([0] + dd + [0, 0, 0, 0, 0, 0]) ^ 0x3FFFFFFF
    chk = [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]
    return "".join([CHARSET[d] for d in dd + chk])


def bc32decode(bc32: str) -> bytes:
    """
    bc32 decoding
    see https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-004-bc32.md
    """
    if bc32.lower() != bc32 and bc32.upper() != bc32:
        return None
    bc32 = bc32.lower()
    if not all([x in CHARSET for x in bc32]):
        return None
    res = [CHARSET.find(c) for c in bc32.lower()]
    if bech32_polymod([0] + res) != 0x3FFFFFFF:
        return None
    return bytes(convertbits(res[:-6], 5, 8, False))


def cbor_encode(data):
    l = len(data)
    if l <= 23:
        prefix = bytes([0x40 + l])
    elif l <= 255:
        prefix = bytes([0x58, l])
    elif l <= 65535:
        prefix = b"\x59" + l.to_bytes(2, "big")
    else:
        prefix = b"\x60" + l.to_bytes(4, "big")
    return prefix + data


def cbor_decode(data):
    s = BytesIO(data)
    b = s.read(1)[0]
    if b >= 0x40 and b < 0x58:
        l = b - 0x40
        return s.read(l)
    if b == 0x58:
        l = s.read(1)[0]
        return s.read(l)
    if b == 0x59:
        l = int.from_bytes(s.read(2), "big")
        return s.read(l)
    if b == 0x60:
        l = int.from_bytes(s.read(4), "big")
        return s.read(l)
    return None


def bcur_encode(data):
    """Returns bcur encoded string and hash digest"""
    cbor = cbor_encode(data)
    enc = bc32encode(cbor)
    h = hashlib.sha256(cbor).digest()
    enc_hash = bc32encode(h)
    return enc, enc_hash


def bcur_decode(data, checksum=None):
    """Returns decoded data, verifies hash digest if provided"""
    cbor = bc32decode(data)
    if checksum is not None:
        h = bc32decode(checksum)
        assert h == hashlib.sha256(cbor).digest()
    return cbor_decode(cbor)