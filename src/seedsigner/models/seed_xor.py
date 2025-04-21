import logging
from binascii import hexlify
from typing import List
from seedsigner.models.seed import Seed, InvalidSeedException
from seedsigner.models.settings import SettingsConstants

logger = logging.getLogger(__name__)

class SeedXOR:
    @staticmethod
    def xor32(*args) -> bytes:
        """Bit-wise XOR between all args"""
        rv = bytearray(32)
        for i in range(32):
            for a in args:
                rv[i] ^= a[i]
        return bytes(rv)
    
    @staticmethod
    def xor_seed_bytes(seed_a_bytes: bytes, seed_b_bytes: bytes) -> bytes:
        """XOR two seed byte arrays together"""
        if len(seed_a_bytes) != len(seed_b_bytes):
            raise InvalidSeedException("Seeds must be the same length for XOR operations")
        
        return SeedXOR.xor32(seed_a_bytes, seed_b_bytes)
    
    @staticmethod
    def xor_seeds(seeds: List[Seed]) -> bytes:
        """XOR multiple seeds together, returning the resulting seed bytes"""
        if len(seeds) < 2:
            raise InvalidSeedException("At least two seeds are required for XOR operation")
        
        # Convert all seeds to bytes
        seed_bytes = [seed.seed_bytes for seed in seeds]
        
        # XOR all seeds together
        result = SeedXOR.xor32(*seed_bytes)
        
        # Verify the result is not all zeros
        if all(b == 0 for b in result):
            raise InvalidSeedException("Resulting seed is all zeros. This is invalid.")
        
        return result
    
    @staticmethod
    def create_seed_from_xor(seeds: List[Seed], wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> Seed:
        """Create a new seed by XORing multiple seeds together"""
        from seedsigner.helpers import mnemonic_generation
        
        # Get the XORed seed bytes
        xor_bytes = SeedXOR.xor_seeds(seeds)
        
        # Generate mnemonic from bytes
        mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(xor_bytes)
        
        # Create and return new seed
        return Seed(
            mnemonic=mnemonic,
            wordlist_language_code=wordlist_language_code
        )
    
    @staticmethod
    def get_fingerprint(seed: Seed, network: str = SettingsConstants.MAINNET) -> str:
        """Get the fingerprint of a seed for display purposes"""
        # Get the root key
        root = seed.get_root_key(network)
        
        # Get the fingerprint
        fingerprint = hexlify(root.fingerprint).decode('utf-8')
        
        return fingerprint
    
    @staticmethod
    def validate_seed(seed: Seed) -> bool:
        """Validate that a seed is properly formatted and checksummed"""
        try:
            # This will raise an exception if the seed is invalid
            seed.get_root_key()
            return True
        except Exception as e:
            logger.error(f"Invalid seed: {str(e)}")
            return False 