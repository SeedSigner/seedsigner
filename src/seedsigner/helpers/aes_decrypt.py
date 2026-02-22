import base64
import hashlib
import struct


class DecryptionError(Exception):
    """Raised for any decryption failure (bad passphrase, corrupt data, padding error, etc.)."""
    pass


# ---------------------------------------------------------------------------
# Minimal pure-Python AES-256-CBC decryption (no external dependencies).
#
# Only decryption is implemented — encryption is not needed.  Lookup tables
# are precomputed at import time to avoid per-byte GF(2^8) multiplication
# in the hot loop (important on Pi Zero).
# ---------------------------------------------------------------------------

# AES S-box
_SBOX = (
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
)

# Inverse S-box (for decryption)
_INV_SBOX = tuple(_SBOX.index(i) for i in range(256))

# Round constants
_RCON = (0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36)


def _gmul(a, b):
    """Galois field multiplication in GF(2^8)."""
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xff
        if hi:
            a ^= 0x1b
        b >>= 1
    return p


# Precomputed multiplication tables for InvMixColumns constants.
# Each table maps byte value (0-255) to its product with the constant.
# This replaces per-byte _gmul calls in the hot loop with O(1) lookups.
_MUL9  = tuple(_gmul(i, 0x09) for i in range(256))
_MUL11 = tuple(_gmul(i, 0x0b) for i in range(256))
_MUL13 = tuple(_gmul(i, 0x0d) for i in range(256))
_MUL14 = tuple(_gmul(i, 0x0e) for i in range(256))


def _key_expansion(key: bytes) -> list:
    """Expand 256-bit key into 60 32-bit round key words."""
    nk = 8  # AES-256: 8 words in key
    nr = 14  # AES-256: 14 rounds
    w = list(struct.unpack('>8I', key))
    for i in range(nk, 4 * (nr + 1)):
        t = w[i - 1]
        if i % nk == 0:
            # RotWord + SubWord + Rcon
            t = ((t << 8) | (t >> 24)) & 0xffffffff
            t = (_SBOX[(t >> 24) & 0xff] << 24 |
                 _SBOX[(t >> 16) & 0xff] << 16 |
                 _SBOX[(t >> 8) & 0xff] << 8 |
                 _SBOX[t & 0xff])
            t ^= _RCON[i // nk - 1] << 24
        elif i % nk == 4:
            t = (_SBOX[(t >> 24) & 0xff] << 24 |
                 _SBOX[(t >> 16) & 0xff] << 16 |
                 _SBOX[(t >> 8) & 0xff] << 8 |
                 _SBOX[t & 0xff])
        w.append(w[i - nk] ^ t)
    return w


def _inv_cipher_block(block: bytes, rk: list) -> bytes:
    """Decrypt one 16-byte AES block (AES-256, 14 rounds)."""
    nr = 14
    s = list(block)

    # AddRoundKey (round nr)
    for c in range(4):
        w = rk[nr * 4 + c]
        s[c * 4 + 0] ^= (w >> 24) & 0xff
        s[c * 4 + 1] ^= (w >> 16) & 0xff
        s[c * 4 + 2] ^= (w >> 8) & 0xff
        s[c * 4 + 3] ^= w & 0xff

    for rnd in range(nr - 1, 0, -1):
        # InvShiftRows
        s[0*4+1], s[1*4+1], s[2*4+1], s[3*4+1] = s[3*4+1], s[0*4+1], s[1*4+1], s[2*4+1]
        s[0*4+2], s[1*4+2], s[2*4+2], s[3*4+2] = s[2*4+2], s[3*4+2], s[0*4+2], s[1*4+2]
        s[0*4+3], s[1*4+3], s[2*4+3], s[3*4+3] = s[1*4+3], s[2*4+3], s[3*4+3], s[0*4+3]

        # InvSubBytes
        s = [_INV_SBOX[b] for b in s]

        # AddRoundKey
        for c in range(4):
            w = rk[rnd * 4 + c]
            s[c * 4 + 0] ^= (w >> 24) & 0xff
            s[c * 4 + 1] ^= (w >> 16) & 0xff
            s[c * 4 + 2] ^= (w >> 8) & 0xff
            s[c * 4 + 3] ^= w & 0xff

        # InvMixColumns (using precomputed lookup tables)
        ns = list(s)
        for c in range(4):
            i = c * 4
            a0, a1, a2, a3 = s[i], s[i+1], s[i+2], s[i+3]
            ns[i]   = _MUL14[a0] ^ _MUL11[a1] ^ _MUL13[a2] ^ _MUL9[a3]
            ns[i+1] = _MUL9[a0]  ^ _MUL14[a1] ^ _MUL11[a2] ^ _MUL13[a3]
            ns[i+2] = _MUL13[a0] ^ _MUL9[a1]  ^ _MUL14[a2] ^ _MUL11[a3]
            ns[i+3] = _MUL11[a0] ^ _MUL13[a1] ^ _MUL9[a2]  ^ _MUL14[a3]
        s = ns

    # Final round (no InvMixColumns)
    # InvShiftRows
    s[0*4+1], s[1*4+1], s[2*4+1], s[3*4+1] = s[3*4+1], s[0*4+1], s[1*4+1], s[2*4+1]
    s[0*4+2], s[1*4+2], s[2*4+2], s[3*4+2] = s[2*4+2], s[3*4+2], s[0*4+2], s[1*4+2]
    s[0*4+3], s[1*4+3], s[2*4+3], s[3*4+3] = s[1*4+3], s[2*4+3], s[3*4+3], s[0*4+3]

    # InvSubBytes
    s = [_INV_SBOX[b] for b in s]

    # AddRoundKey (round 0)
    for c in range(4):
        w = rk[c]
        s[c * 4 + 0] ^= (w >> 24) & 0xff
        s[c * 4 + 1] ^= (w >> 16) & 0xff
        s[c * 4 + 2] ^= (w >> 8) & 0xff
        s[c * 4 + 3] ^= w & 0xff

    return bytes(s)


def _aes256_cbc_decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    """AES-256-CBC decryption with PKCS#7 unpadding."""
    rk = _key_expansion(key)
    blocks = [ciphertext[i:i+16] for i in range(0, len(ciphertext), 16)]
    plaintext = bytearray()
    prev = iv
    for block in blocks:
        decrypted = _inv_cipher_block(block, rk)
        plaintext.extend(b ^ p for b, p in zip(decrypted, prev))
        prev = block

    # PKCS#7 unpadding
    if not plaintext:
        raise DecryptionError("Empty plaintext")
    pad_len = plaintext[-1]
    if pad_len < 1 or pad_len > 16:
        raise DecryptionError("Invalid PKCS#7 padding")
    if plaintext[-pad_len:] != bytes([pad_len]) * pad_len:
        raise DecryptionError("Invalid PKCS#7 padding")
    return bytes(plaintext[:-pad_len])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def decrypt_openssl_aes256cbc(data_b64: str, passphrase: str) -> str:
    """
    Decrypts OpenSSL-compatible AES-256-CBC data (base64, starts with "U2FsdGVkX1").
    Matches: openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -base64
    Returns plaintext UTF-8 string (the mnemonic).
    Raises DecryptionError on any failure.
    """
    try:
        # 1. Base64-decode
        data = base64.b64decode(data_b64.strip())

        # 2. Verify magic header
        if len(data) < 16 or data[:8] != b'Salted__':
            raise DecryptionError("Invalid OpenSSL magic header (expected 'Salted__')")

        # 3. Extract salt + ciphertext
        salt = data[8:16]
        ciphertext = data[16:]

        if len(ciphertext) % 16 != 0:
            raise DecryptionError("Ciphertext length not multiple of AES block size (16)")

        # 4. PBKDF2 derivation (100,000 iterations, 48 bytes = 32 key + 16 IV)
        derived = hashlib.pbkdf2_hmac(
            'sha256', passphrase.encode('utf-8'), salt, 100000, dklen=48
        )
        key = derived[:32]
        iv = derived[32:48]

        # 5. Decrypt AES-256-CBC + strip PKCS#7 padding
        plaintext_bytes = _aes256_cbc_decrypt(key, iv, ciphertext)

        # 6. Return as UTF-8
        return plaintext_bytes.decode('utf-8')

    except Exception as e:
        if isinstance(e, DecryptionError):
            raise
        raise DecryptionError(f"Decryption failed: {str(e)}") from e
