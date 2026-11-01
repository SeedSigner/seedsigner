"""
SeedSigner XOR Seed Backup Tool

Split a BIP39 seed into multiple XOR parts or combine parts back into the
original phrase. This utility mirrors the structure of tools/mnemonic.py and
tools/seed_phrase_to_qr.py for a consistent CLI experience.

TL;DR:
    pip3 install -e .
    cd tools
    python3 seed_xor.py -h
"""
import argparse
import sys
from hashlib import sha256
from binascii import a2b_hex
from secrets import randbits
from typing import List
from embit.bip39 import mnemonic_to_bytes, WORDLIST as WORDLIST__ENGLISH
from seedsigner.helpers.mnemonic_generation import generate_mnemonic_from_bytes

# -----------------------------------------------------------------------------
# Formatted usage examples shown with `-h`
# -----------------------------------------------------------------------------
usage = f"""
Examples:

    # Split into 3 deterministic parts
    python3 seed_xor.py split "<seed phrase>" 3 --deterministic

    # Split into 4 random parts
    python3 seed_xor.py split "<seed phrase>" 4

    # Combine parts back
    python3 seed_xor.py combine "<part A>" "<part B>" "<part C>"
"""

# -----------------------------------------------------------------------------
# Banner printed at runtime
# -----------------------------------------------------------------------------
BANNER = """
*******************************************************************************
 SeedSigner XOR Seed Backup Tool

 This tool splits a seed into multiple XOR backups and can recombine them to
 recover the original seed. It relies on the BIP39 wordlist to convert between
 seed phrases and binary entropy. 
 
 FOR TESTING / EDUCATIONAL PURPOSES ONLY!
*******************************************************************************
"""

def seed_xor(seed: int, seed_nbits: int, n: int, is_deterministic: bool, outputs: List[int]) -> List[int]:
    if is_deterministic:
        hex_seed = hex(seed)[2:]
        hex_seed = hex_seed if len(hex_seed) % 2 == 0 else "0" + hex_seed
        new_entropy = int(sha256(a2b_hex(hex_seed)).hexdigest()[2:int(seed_nbits/4) + 2], 16)
    else:
        new_entropy = randbits(seed_nbits)
    
    outputs.append(new_entropy)
    seed = seed ^ new_entropy
    
    if n <= 2:
        outputs.append(seed)
        return outputs
    else:
        return seed_xor(seed, seed_nbits, n-1, is_deterministic, outputs)



def seed_combining(seeds: List[int]) -> int:
    result = seeds[0]
    for seed in seeds[1:]:
        result ^= seed
    return result



def print_xor_backups(outputs: List[int], wordlist: List[str] = WORDLIST__ENGLISH) -> None:
    print("\nXOR Backups:")
    for i, output in enumerate(outputs):
        # Determine byte length: 128 bits = 16 bytes, 256 bits = 32 bytes, etc.
        bit_length = output.bit_length()
        byte_length = (bit_length + 7) // 8
        if byte_length <= 16:
            byte_length = 16
        elif byte_length <= 20:
            byte_length = 20
        elif byte_length <= 24:
            byte_length = 24
        elif byte_length <= 28:
            byte_length = 28
        else:
            byte_length = 32
        
        entropy_bytes = output.to_bytes(byte_length, 'big')
        mnemonic_list = generate_mnemonic_from_bytes(entropy_bytes)
        print(f"{i+1}: {' '.join(mnemonic_list)}\n")



def main() -> None:
    parser = argparse.ArgumentParser(
        description=f'SeedSigner XOR Seed Backup Tool\n\n{usage}',
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    split_parser = subparsers.add_parser('split', help='Split a seed into multiple XOR backups')
    split_parser.add_argument('seed_phrase', type=str, help='BIP39 seed phrase to split')
    split_parser.add_argument('parts', type=int, help='Number of parts to split into (including original)')
    split_parser.add_argument('--is_deterministic', action='store_true', 
                             help='Use deterministic splitting (same output for same input)')
    
    combine_parser = subparsers.add_parser('combine', help='Combine multiple XOR backups to recover the original seed')
    combine_parser.add_argument('seed_phrases', type=str, nargs='+', 
                               help='Two or more XOR backup seed phrases to combine')
    
    args = parser.parse_args()
    
    if args.command == 'split':
        outputs = []
        entropy_bytes = mnemonic_to_bytes(args.seed_phrase, wordlist=WORDLIST__ENGLISH)
        entropy_int = int.from_bytes(entropy_bytes, 'big')
        seed_xor(entropy_int, len(entropy_bytes) * 8, args.parts, args.is_deterministic, outputs)
        print_xor_backups(outputs)
        
    elif args.command == 'combine':
        backups = []
        byte_length = 0
        for phrase in args.seed_phrases:
            entropy_bytes = mnemonic_to_bytes(phrase, wordlist=WORDLIST__ENGLISH)
            if byte_length == 0:
                byte_length = len(entropy_bytes)
            backups.append(int.from_bytes(entropy_bytes, 'big'))
        
        combined_int = seed_combining(backups)
        combined_bytes = combined_int.to_bytes(byte_length, 'big')
        mnemonic_list = generate_mnemonic_from_bytes(combined_bytes)
        print("\nRecovered seed phrase:")
        print(' '.join(mnemonic_list))
        
    else:
        parser.print_help()
        sys.exit(1)



if __name__ == "__main__":
    print(BANNER)
    main()