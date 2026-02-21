import base64
import hashlib

import pyaes


class DecryptionError(Exception):
    """Raised for any decryption failure (bad passphrase, corrupt data, padding error, etc.)."""
    pass


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

        # 5. Decrypt with pyaes (CBC) — pyaes handles PKCS#7 padding on final feed()
        decrypter = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(key, iv=iv))
        plaintext_bytes = decrypter.feed(ciphertext)
        plaintext_bytes += decrypter.feed()   # ← final call (handles padding)

        # 6. Return as UTF-8
        return plaintext_bytes.decode('utf-8')

    except Exception as e:
        if isinstance(e, DecryptionError):
            raise
        raise DecryptionError(f"Decryption failed: {str(e)}") from e
