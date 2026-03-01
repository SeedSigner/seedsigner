from typing import List, Tuple, Optional, Dict, Any
from embit import bip39
from seedsigner.models.seed import Seed


class SeedXORValidator:
    """
    Handles validation logic for SeedXOR operations.
    Returns validation errors as dictionaries that can be used by Views.
    """

    @classmethod
    def validate_shard(cls, new_shard: Seed, existing_shards: List[Seed]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validates a new shard against existing shards.

        Args:
            new_shard: The new shard to validate
            existing_shards: List of already added shards

        Returns:
            Tuple of (is_valid, error_dict) where:
            - is_valid: bool indicating if validation passed
            - error_dict: dict with error details if validation failed, None otherwise
        """
        error_dict = None

        # Check for passphrase
        if new_shard.has_passphrase:
            return False, {
                "title": "Passphrase Not Allowed",
                "status_headline": "Invalid Shard",
                "message": "You may not XOR a seed that has passphrase.",
            }

        # Check mnemonic length consistency
        if existing_shards and len(new_shard.mnemonic_list) != len(existing_shards[0].mnemonic_list):
            return False, {
                "title": "Mnemonic Length Mismatch",
                "status_headline": "Invalid Shard",
                "message": "XOR requires seeds of similar mnemonic length!"
            }

        # Check for duplicate shards
        for i, shard in enumerate(existing_shards):
            if new_shard.mnemonic_str == shard.mnemonic_str:
                shard_num = i + 1
                error_dict = {
                    "title": "Duplicate Shard",
                    "status_headline": "Duplicate Shard",
                    "message": "This shard is identical to shard #{}".format(shard_num),
                }
                return False, error_dict

        # Check for inverse shards (which would cancel out)
        for i, shard in enumerate(existing_shards):
            if len(new_shard.mnemonic_list) == len(shard.mnemonic_list):
                # Use ignore_checksum=True to support Electrum seeds which
                # don't have valid BIP-39 checksums
                new_entropy = bip39.mnemonic_to_bytes(new_shard.mnemonic_str, ignore_checksum=True)
                existing_entropy = bip39.mnemonic_to_bytes(shard.mnemonic_str, ignore_checksum=True)

                # XOR the entropies and check if result is all 1s (binary inverse)
                inverse_entropy = bytes(a ^ b for a, b in zip(new_entropy, existing_entropy))
                if all(b == 0xFF for b in inverse_entropy):
                    shard_num = i + 1
                    error_dict = {
                        "title": "Seed Inversion",
                        "status_headline": "Invalid Shard",
                        "message": "This shard is the binary inverse of shard #{} and would cancel it out.".format(shard_num),
                    }
                    return False, error_dict

        return True, None
