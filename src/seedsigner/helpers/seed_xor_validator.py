from typing import List, Tuple, Optional, Dict, Any
from embit import bip39
from seedsigner.models.seed import Seed


class SeedXORValidator:
    """Validates parts for SeedXOR operations."""

    @classmethod
    def validate_part(cls, new_part: Seed, existing_parts: List[Seed]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validates a new part against existing parts.
        Returns (is_valid, error_dict)."""
        if new_part.has_passphrase:
            return False, {
                "title": "Passphrase Not Allowed",
                "status_headline": "Invalid Part",
                "message": "You may not XOR a seed that has passphrase.",
            }

        # Check mnemonic length consistency
        if existing_parts and len(new_part.mnemonic_list) != len(existing_parts[0].mnemonic_list):
            return False, {
                "title": "Mnemonic Length Mismatch",
                "status_headline": "Invalid Part",
                "message": "XOR requires seeds of similar mnemonic length!"
            }

        # Check for duplicate parts
        for i, part in enumerate(existing_parts):
            if new_part.mnemonic_str == part.mnemonic_str:
                return False, {
                    "title": "Duplicate Part",
                    "status_headline": "Duplicate Part",
                    "message": "This part is identical to part #{}".format(i + 1),
                }

        # Check for inverse parts (which would cancel out)
        # Pass the Seed's wordlist explicitly — bip39.mnemonic_to_bytes defaults to
        #   English, which would fail on a non-English-wordlist Seed.  Wrap in
        #   try/except so a wordlist mismatch produces a clean error instead of an
        #   unhandled exception in the fingerprint view.
        try:
            new_entropy = bip39.mnemonic_to_bytes(new_part.mnemonic_str, wordlist=new_part.wordlist)
        except Exception:
            return False, {
                "title": "Invalid Part",
                "status_headline": "Invalid Part",
                "message": "Could not parse this seed's mnemonic.",
            }

        for i, part in enumerate(existing_parts):
            if len(new_part.mnemonic_list) == len(part.mnemonic_list):
                try:
                    existing_entropy = bip39.mnemonic_to_bytes(part.mnemonic_str, wordlist=part.wordlist)
                except Exception:
                    continue
                xored = bytes(a ^ b for a, b in zip(new_entropy, existing_entropy))
                if all(b == 0xFF for b in xored):
                    return False, {
                        "title": "Seed Inversion",
                        "status_headline": "Invalid Part",
                        "message": "This part is the binary inverse of part #{}. XORing them produces a known all-ones seed with no entropy.".format(i + 1),
                    }

        return True, None

    @classmethod
    def validate_combined_seed(cls, combined_seed: Seed) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validates the combined XOR result for degenerate cases.

        With 3+ colluding parts the XOR can produce all-zero or all-one entropy,
        which are known, worthless seeds that pass the BIP39 checksum.
        Returns (is_valid, error_dict).
        """
        try:
            entropy = bip39.mnemonic_to_bytes(combined_seed.mnemonic_str, wordlist=combined_seed.wordlist)
        except Exception:
            return False, {
                "title": "XOR Error",
                "status_headline": "Invalid Combined Seed",
                "message": "Could not parse the combined seed's mnemonic.",
            }

        if all(b == 0x00 for b in entropy):
            return False, {
                "title": "Zero Entropy Result",
                "status_headline": "Invalid Combined Seed",
                "message": "XORing these parts produces all-zero entropy (the 'abandon...about' seed). The result is a known, worthless seed.",
            }

        if all(b == 0xFF for b in entropy):
            return False, {
                "title": "Known Seed Result",
                "status_headline": "Invalid Combined Seed",
                "message": "XORing these parts produces a known all-ones seed with no entropy.",
            }

        return True, None
