"""
Legacy Encryption — Python port for SeedSigner (Raspberry Pi Zero)

Implements the same AES-256-GCM + PBKDF2 dual-key encryption scheme as
Legacy-offline.html, producing byte-identical ciphertext format so that
anything encrypted here can be decrypted in the browser and vice versa.

Dependencies: cryptography (pure-Python fallback works on Pi Zero)
Install:      pip install cryptography
"""

import os
import base64
import hashlib
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ---------------------------------------------------------------------------
# BIP-39 English wordlist (2 048 words) — loaded from file or embedded
# ---------------------------------------------------------------------------

_BIP39_WORDLIST: list[str] | None = None


def _load_wordlist() -> list[str]:
    """Load the BIP-39 English wordlist.

    Tries to read from a bundled `english.txt` (one word per line) first,
    then falls back to an embedded tuple.  SeedSigner already ships this
    file so we just reuse it.
    """
    global _BIP39_WORDLIST
    if _BIP39_WORDLIST is not None:
        return _BIP39_WORDLIST

    # Try SeedSigner's bundled wordlist location first
    search_paths = [
        os.path.join(os.path.dirname(__file__), "english.txt"),
        os.path.join(os.path.dirname(__file__), "..", "seedsigner", "resources", "english.txt"),
        os.path.join(os.path.dirname(__file__), "wordlist", "english.txt"),
    ]
    for path in search_paths:
        try:
            with open(path, "r") as f:
                words = [line.strip() for line in f if line.strip()]
            if len(words) == 2048:
                _BIP39_WORDLIST = words
                return _BIP39_WORDLIST
        except FileNotFoundError:
            continue

    raise FileNotFoundError(
        "BIP-39 english.txt not found. Place it next to this module or "
        "ensure SeedSigner's wordlist is accessible."
    )


def get_wordlist() -> list[str]:
    return _load_wordlist()


# ---------------------------------------------------------------------------
# Core cryptographic functions
# ---------------------------------------------------------------------------

PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16
IV_BYTES = 12
KEY_BITS = 256
KEY_BYTES = KEY_BITS // 8


def derive_key(password: str, salt: bytes) -> bytes:
    """PBKDF2-SHA256 key derivation — mirrors deriveKey() in the JS."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_BYTES,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_data(plaintext: str, password: str) -> dict:
    """Encrypt a plaintext string with AES-256-GCM.

    Returns a dict with base64-encoded salt, iv, ciphertext, and the
    integer paddingLength — the same structure as the JS encryptData().
    """
    # Random salt and IV
    salt = os.urandom(SALT_BYTES)
    iv = os.urandom(IV_BYTES)

    # Random padding (0–4 bytes) appended to plaintext before encoding
    padding_length = secrets.randbelow(5)  # 0..4
    padded = plaintext
    for _ in range(padding_length):
        padded += chr(secrets.randbelow(256))

    # Derive key and encrypt
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    # AES-GCM ciphertext includes the 16-byte auth tag appended by default
    ciphertext = aesgcm.encrypt(iv, padded.encode("utf-8"), None)

    # Encode to base64 (standard, with padding) — matches btoa() in browser
    salt_b64 = base64.b64encode(salt).decode("ascii")
    iv_b64 = base64.b64encode(iv).decode("ascii")
    ct_b64 = base64.b64encode(ciphertext).decode("ascii")

    return {
        "salt": salt_b64,
        "iv": iv_b64,
        "ciphertext": ct_b64,
        "paddingLength": padding_length,
    }


def decrypt_data(data: dict, password: str) -> str:
    """Decrypt a dict produced by encrypt_data (or the JS equivalent)."""
    salt = base64.b64decode(data["salt"])
    iv = base64.b64decode(data["iv"])
    ciphertext = base64.b64decode(data["ciphertext"])
    padding_length = int(data["paddingLength"])

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    decrypted_bytes = aesgcm.decrypt(iv, ciphertext, None)
    decrypted_text = decrypted_bytes.decode("utf-8", errors="replace")

    # Strip random padding
    if 0 < padding_length <= len(decrypted_text):
        decrypted_text = decrypted_text[:-padding_length]

    return decrypted_text


# ---------------------------------------------------------------------------
# Seed-phrase–level functions (dual-key wrapper)
# ---------------------------------------------------------------------------

def validate_seed_phrase(seed_phrase: str) -> bool:
    """Check that a seed phrase is 12 or 24 valid BIP-39 words."""
    words = seed_phrase.split(" ")
    if len(words) not in (12, 24):
        return False
    wordlist = get_wordlist()
    return all(w in wordlist for w in words)


def encrypt_seed_phrase(
    seed_phrase: str,
    benefactor_key: str,
    beneficiary_key: str,
) -> str:
    """Encrypt a BIP-39 seed phrase with the dual-key scheme.

    Returns a base64 string (trailing '=' stripped) that is fully
    compatible with Legacy-offline.html's decryptSeedPhrase().
    """
    if not validate_seed_phrase(seed_phrase):
        raise ValueError("Invalid seed phrase")

    combined_key = benefactor_key + beneficiary_key
    enc = encrypt_data(seed_phrase, combined_key)

    padding_str = str(enc["paddingLength"]).zfill(2)
    combined = f'{enc["salt"]}.{enc["iv"]}.{enc["ciphertext"]}.{padding_str}'

    # Outer base64 encode, strip trailing '='
    encoded = base64.b64encode(combined.encode("utf-8")).decode("ascii")
    encoded = encoded.rstrip("=")

    return encoded


def decrypt_seed_phrase(
    encrypted_seed_phrase: str,
    benefactor_key: str,
    beneficiary_key: str,
) -> str:
    """Decrypt an encrypted seed phrase produced by encrypt_seed_phrase()
    or by Legacy-offline.html's encryptSeedPhrase().
    """
    combined_key = benefactor_key + beneficiary_key

    # Re-pad base64 if needed and decode
    padded = encrypted_seed_phrase + "=" * (-len(encrypted_seed_phrase) % 4)
    decoded = base64.b64decode(padded).decode("utf-8")

    parts = decoded.split(".")
    if len(parts) != 4:
        raise ValueError("Invalid encrypted seed phrase format.")

    data = {
        "salt": parts[0],
        "iv": parts[1],
        "ciphertext": parts[2],
        "paddingLength": int(parts[3]),
    }

    return decrypt_data(data, combined_key)


# ---------------------------------------------------------------------------
# QR helpers for SeedSigner I/O
# ---------------------------------------------------------------------------

def encrypted_to_qr_data(encrypted: str) -> str:
    """Return the string that should be encoded into a QR code.

    For now this is just the raw base64 blob — compact enough for a
    Version-10 QR at medium ECC (~211 alphanumeric chars).
    """
    return encrypted


def qr_data_to_encrypted(qr_text: str) -> str:
    """Parse a scanned QR string back into the encrypted payload."""
    text = qr_text.strip()
    if text.startswith("LEGACY_ENC_V1:"):
        text = text[len("LEGACY_ENC_V1:"):]
    return text


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    # Use a tiny test wordlist for the CLI demo
    _BIP39_WORDLIST = [
        "abandon", "ability", "able", "about", "above", "absent", "absorb",
        "abstract", "absurd", "abuse", "access", "accident",
    ]

    seed = "abandon ability able about above absent absorb abstract absurd abuse access accident"
    bk = "benefactor-password-123"
    byk = "beneficiary-password-456"

    print(f"Seed phrase : {seed}")
    print(f"Benefactor  : {bk}")
    print(f"Beneficiary : {byk}")
    print()

    t0 = time.time()
    encrypted = encrypt_seed_phrase(seed, bk, byk)
    t1 = time.time()
    print(f"Encrypted   : {encrypted[:60]}...")
    print(f"Encrypt time: {t1 - t0:.2f}s")
    print()

    t0 = time.time()
    decrypted = decrypt_seed_phrase(encrypted, bk, byk)
    t1 = time.time()
    print(f"Decrypted   : {decrypted}")
    print(f"Decrypt time: {t1 - t0:.2f}s")
    print()

    assert decrypted == seed, "Round-trip FAILED"
    print("Round-trip OK")
