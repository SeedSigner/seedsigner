from typing import List, Tuple, Optional, Dict, Any
from embit import bip39
from seedsigner.models.seed import Seed


class SeedXORValidator:
    """Validates shards for SeedXOR operations."""

    @classmethod
    def validate_shard(cls, new_shard: Seed, existing_shards: List[Seed]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validates a new shard against existing shards.
        Returns (is_valid, error_dict)."""
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
                return False, {
                    "title": "Duplicate Shard",
                    "status_headline": "Duplicate Shard",
                    "message": "This shard is identical to shard #{}".format(i + 1),
                }
                
        # Check for inverse shards (which would cancel out)
        new_entropy = bip39.mnemonic_to_bytes(new_shard.mnemonic_str)
        for i, shard in enumerate(existing_shards):
            if len(new_shard.mnemonic_list) == len(shard.mnemonic_list):
                existing_entropy = bip39.mnemonic_to_bytes(shard.mnemonic_str)
                xored = bytes(a ^ b for a, b in zip(new_entropy, existing_entropy))
                if all(b == 0xFF for b in xored):
                    return False, {
                        "title": "Seed Inversion",
                        "status_headline": "Invalid Shard",
                        "message": "This shard is the binary inverse of shard #{} and would cancel it out.".format(i + 1),
                    }
               
        return True, None
