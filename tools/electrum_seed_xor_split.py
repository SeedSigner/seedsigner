#!/usr/bin/env python3
"""
Electrum Seed XOR Splitter — Standalone CLI tool (Python 3.10+ standard library only)

Splits an Electrum native segwit seed into two XOR shares that recombine
to the original. Compatible with SeedSigner's Seed XOR rebuild flow.

SECURITY MODEL
==============
Share A is generated from os.urandom(), which draws from the OS CSPRNG:
  - macOS/Linux: /dev/urandom (ChaCha20 or ARC4 seeded from hardware entropy)
  - Windows: BCryptGenRandom (CNG)

This is the same source used by secrets.token_bytes(), GPG key generation,
and OpenSSL. It is cryptographically irreversible: knowing Share A reveals
zero information about the original seed without Share B, and vice versa.

WHY THIS IS SECURE
===================
Given an N-word seed (12 or 24 words), each word maps to an 11-bit index
(0..2047) from the BIP-39 wordlist. The entropy portion is 128 bits (12w)
or 256 bits (24w).

1. We generate Share A as random bytes from os.urandom() — a CSPRNG that
   produces output indistinguishable from true random to any computationally
   bounded adversary.

2. Share B = original_entropy XOR share_A_entropy.

3. Both shares get valid BIP-39 checksums appended (SHA-256 of entropy),
   making them valid standalone BIP-39 seed phrases.

4. Information-theoretic security: Share A is uniformly random and
   independent of the original seed. XOR with a uniformly random key is
   a one-time pad — each share alone is statistically independent of the
   secret. No amount of computation can recover the original from one share.

5. Recombination: XOR(Share_A, Share_B) = XOR(Share_A, original XOR Share_A)
                                        = original  (since X XOR X = 0)

COMPATIBILITY
=============
The two output shares are standard BIP-39 seeds. They can be loaded into
SeedSigner and recombined using the "Rebuild Seed XOR" flow, which will
auto-detect the result as an Electrum segwit seed.

Usage:
    python3 electrum_seed_xor_split.py
"""

import hashlib
import hmac
import os
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# BIP-39 English wordlist (2048 words)
# ---------------------------------------------------------------------------

# SHA-256 of the canonical wordlist (one word per line, trailing newline)
_WORDLIST_SHA256 = "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"
_WORDLIST_URL = "https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt"


def _load_wordlist() -> list[str]:
    """Load the BIP-39 English wordlist.

    Checks for a cached copy next to this script. If not found, downloads
    from the official bitcoin/bips GitHub repo and verifies the SHA-256
    hash before saving.
    """
    cache_path = Path(__file__).parent / "bip39_wordlist_english.txt"

    # Try cached file
    if cache_path.exists():
        data = cache_path.read_text(encoding="utf-8")
        if hashlib.sha256(data.encode("utf-8")).hexdigest() == _WORDLIST_SHA256:
            words = data.strip().splitlines()
            if len(words) == 2048:
                return words
        print(f"WARNING: Cached wordlist at {cache_path} failed hash check, re-downloading...")

    # Download
    print(f"Downloading BIP-39 wordlist from {_WORDLIST_URL} ...")
    try:
        with urllib.request.urlopen(_WORDLIST_URL, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as e:
        print(f"ERROR: Failed to download wordlist: {e}")
        print(f"Please manually download it and place at: {cache_path}")
        sys.exit(1)

    # Verify SHA-256
    actual_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if actual_hash != _WORDLIST_SHA256:
        print(f"ERROR: Downloaded wordlist SHA-256 mismatch!")
        print(f"  Expected: {_WORDLIST_SHA256}")
        print(f"  Got:      {actual_hash}")
        sys.exit(1)

    words = raw.strip().splitlines()
    if len(words) != 2048:
        print(f"ERROR: Wordlist has {len(words)} words, expected 2048")
        sys.exit(1)

    # Cache for next time
    cache_path.write_text(raw, encoding="utf-8")
    print(f"Wordlist cached to: {cache_path}")
    print()

    return words


WORDLIST: list[str] = []  # Populated at startup


# ---------------------------------------------------------------------------
# BIP-39 entropy <-> mnemonic conversion
# ---------------------------------------------------------------------------

def entropy_to_mnemonic(entropy: bytes) -> list[str]:
    """Convert raw entropy bytes to a BIP-39 mnemonic with valid checksum.

    Entropy must be 16 bytes (-> 12 words) or 32 bytes (-> 24 words).
    Checksum = first (entropy_bits / 32) bits of SHA-256(entropy).
    Total bits = entropy_bits + checksum_bits, split into 11-bit word indices.
    """
    if len(entropy) not in (16, 32):
        raise ValueError(f"Entropy must be 16 or 32 bytes, got {len(entropy)}")

    h = hashlib.sha256(entropy).digest()
    checksum_bits = len(entropy) * 8 // 32  # 4 for 128-bit, 8 for 256-bit

    # Build bit stream: entropy bits + checksum bits
    bits = []
    for byte in entropy:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    for i in range(7, 7 - checksum_bits, -1):
        bits.append((h[0] >> i) & 1)

    # Split into 11-bit groups -> word indices
    words = []
    for i in range(0, len(bits), 11):
        idx = 0
        for bit in bits[i:i + 11]:
            idx = (idx << 1) | bit
        words.append(WORDLIST[idx])

    return words


def mnemonic_to_entropy(mnemonic: list[str]) -> bytes:
    """Extract raw entropy bytes from a mnemonic (ignores checksum validity).

    This is necessary because Electrum seeds do NOT have valid BIP-39
    checksums — they use HMAC-SHA512 prefix validation instead. So we
    extract the entropy bits directly from the word indices.
    """
    indices = [WORDLIST.index(w) for w in mnemonic]

    # 11 bits per word
    all_bits = []
    for idx in indices:
        for bit_pos in range(10, -1, -1):
            all_bits.append((idx >> bit_pos) & 1)

    # Strip checksum bits (last word carries entropy + checksum)
    checksum_bits = len(mnemonic) // 3  # 4 for 12 words, 8 for 24 words
    entropy_bits = all_bits[:len(all_bits) - checksum_bits]

    # Convert to bytes
    entropy = bytearray()
    for i in range(0, len(entropy_bits), 8):
        byte = 0
        for bit in entropy_bits[i:i + 8]:
            byte = (byte << 1) | bit
        entropy.append(byte)

    return bytes(entropy)


# ---------------------------------------------------------------------------
# Electrum seed validation
# ---------------------------------------------------------------------------

def is_electrum_segwit(mnemonic_str: str) -> bool:
    """Check if a mnemonic is a valid Electrum native segwit seed.

    Electrum validates seeds by computing HMAC-SHA512 with key "Seed version"
    and checking the hex prefix:
      - "100" = native segwit (p2wpkh)
      - "101" = segwit 2FA
      - "01"  = standard (legacy)
    We only check "100" since that's what SeedSigner supports.
    """
    normalized = unicodedata.normalize("NFKD", mnemonic_str)
    h = hmac.digest(b"Seed version", normalized.encode("utf-8"), hashlib.sha512)
    return h.hex().startswith("100")


# ---------------------------------------------------------------------------
# XOR split
# ---------------------------------------------------------------------------

def xor_bytes(a: bytes, b: bytes) -> bytes:
    """XOR two equal-length byte strings."""
    return bytes(x ^ y for x, y in zip(a, b))


def split_seed(mnemonic: list[str]) -> tuple[list[str], list[str]]:
    """Split a seed mnemonic into two XOR shares.

    How it works:
      1. Extract the entropy bytes from the input seed (128 or 256 bits)
      2. Generate Share A entropy from os.urandom() (CSPRNG)
      3. Compute Share B entropy = original_entropy XOR share_A_entropy
      4. Convert both entropies to BIP-39 mnemonics (with valid checksums)

    Both shares are valid BIP-39 seed phrases. XOR(A, B) = original entropy.
    """
    original_entropy = mnemonic_to_entropy(mnemonic)
    entropy_len = len(original_entropy)  # 16 or 32 bytes

    # ---- THE KEY SECURITY STEP ----
    # os.urandom() is a CSPRNG — produces cryptographically secure random
    # bytes from the operating system's entropy pool. This makes Share A
    # statistically independent of the original seed.
    share_a_entropy = os.urandom(entropy_len)

    # Share B = original XOR Share A
    # Since Share A is uniformly random, Share B is also uniformly random
    # and independent of the original (one-time pad property).
    share_b_entropy = xor_bytes(original_entropy, share_a_entropy)

    # Convert to BIP-39 mnemonics (appends SHA-256 checksum to each)
    share_a = entropy_to_mnemonic(share_a_entropy)
    share_b = entropy_to_mnemonic(share_b_entropy)

    return share_a, share_b


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def validate_mnemonic_words(words: list[str]) -> list[str]:
    """Validate that all words are in the BIP-39 wordlist. Returns error list."""
    errors = []
    for i, word in enumerate(words):
        if word not in WORDLIST:
            errors.append(f"  Word {i + 1}: '{word}' is not in the BIP-39 wordlist")
    return errors


def main():
    global WORDLIST
    WORDLIST = _load_wordlist()

    print("=" * 64)
    print("  Electrum Seed XOR Splitter")
    print("  Splits an Electrum seed into 2 XOR shares")
    print("=" * 64)
    print()
    print("Enter your Electrum native segwit seed phrase below.")
    print("Supported: 12-word or 24-word seeds.")
    print()

    # --- Input seed ---
    while True:
        raw = input("Seed phrase: ").strip()
        if not raw:
            print("  No input. Try again.\n")
            continue

        words = raw.lower().split()
        if len(words) not in (12, 24):
            print(f"  Expected 12 or 24 words, got {len(words)}. Try again.\n")
            continue

        errors = validate_mnemonic_words(words)
        if errors:
            print("  Invalid words found:")
            for e in errors:
                print(e)
            print()
            continue

        mnemonic_str = " ".join(words)
        if not is_electrum_segwit(mnemonic_str):
            print("  WARNING: This does NOT validate as an Electrum native segwit seed.")
            resp = input("  Continue anyway? (y/n): ").strip().lower()
            if resp != "y":
                print()
                continue

        break

    # --- Split ---
    share_a, share_b = split_seed(words)

    # --- Verify recombination before writing ---
    a_entropy = mnemonic_to_entropy(share_a)
    b_entropy = mnemonic_to_entropy(share_b)
    recombined_entropy = xor_bytes(a_entropy, b_entropy)

    original_entropy = mnemonic_to_entropy(words)
    if recombined_entropy != original_entropy:
        print("\nFATAL: Recombination verification failed! Aborting.")
        sys.exit(1)

    # --- Write output ---
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"xor_shares_{timestamp}.txt"

    content_lines = [
        "=" * 64,
        "  Electrum Seed XOR Shares",
        f"  Generated: {datetime.now(timezone.utc).isoformat()}",
        "=" * 64,
        "",
        "SECURITY: Each share alone reveals ZERO information about your",
        "original seed. Store them in separate secure locations.",
        "",
        "RECOMBINATION: Load both shares into SeedSigner and use",
        "'Rebuild Seed XOR' to recover your original Electrum seed.",
        "",
        "-" * 64,
        "SHARE A (BIP-39):",
        " ".join(share_a),
        "",
        "-" * 64,
        "SHARE B (BIP-39):",
        " ".join(share_b),
        "",
        "-" * 64,
        f"Original seed word count: {len(words)}",
        f"Recombination verified:   YES",
        "=" * 64,
        "",
        "IMPORTANT: Delete this file after copying the shares to secure",
        "storage. Do NOT store both shares in the same location.",
    ]
    content = "\n".join(content_lines) + "\n"

    with open(filename, "w") as f:
        f.write(content)

    print()
    print(f"Shares written to: {filename}")
    print()
    print("Share A:", " ".join(share_a))
    print("Share B:", " ".join(share_b))
    print()
    print("Recombination verified: XOR(A, B) restores original entropy.")
    print()
    print("NEXT STEPS:")
    print("  1. Copy each share to separate secure storage")
    print("  2. Delete this file and clear your terminal history")
    print("  3. To recover: load both into SeedSigner -> Rebuild Seed XOR")


if __name__ == "__main__":
    main()
