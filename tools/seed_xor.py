import argparse
import sys
from hashlib import sha256
from binascii import a2b_hex
from secrets import randbits
from embit.wordlists.bip39 import WORDLIST as WORDLIST__ENGLISH


def get_wordnumber(word, wordlist=WORDLIST__ENGLISH):
    if word in wordlist:
        index = wordlist.index(word)
        return format(index, '011b') # 11-bit binary representation
    return "Error"

def mnemonic_to_entropy(phrase, wordlist=WORDLIST__ENGLISH):
    mnemonic = ""
    phrase = phrase.split()
    for word in phrase:
        mnemonic += get_wordnumber(word, wordlist)
    
    
    checksum_bits = len(mnemonic) // 32 #remove checksum bits
    return mnemonic[:-checksum_bits]

def resize_bin(bin_str, nbits):
    if nbits - len(bin_str) > 0:
        bin_str = "0" * (nbits - len(bin_str)) + bin_str
    return bin_str

def entropy_to_mnemonic(entropy, wordlist=WORDLIST__ENGLISH):
    #converts entropy to hex
    if isinstance(entropy, int):
        entropy_bin = bin(entropy)[2:]
    else:
        entropy_bin = entropy
    
    #it checks and adjust entropy size
    entropy_sizes = [128, 160, 192, 224, 256]
    entropy_size = next((size for size in entropy_sizes if len(entropy_bin) <= size), None)
    
    if not entropy_size:
        return "Error: Invalid entropy size"
    
    entropy_bin = resize_bin(entropy_bin, entropy_size)
    entropy_hex = hex(int(entropy_bin, 2))[2:]
    entropy_hex = entropy_hex if len(entropy_hex) % 2 == 0 else "0" + entropy_hex
    
    #calculating checksum
    entropy_bytes = a2b_hex(entropy_hex)
    hash_bytes = sha256(entropy_bytes).digest()
    checksum_bits = len(entropy_bin) // 32
    checksum = ''.join(format(b, '08b') for b in hash_bytes)[:checksum_bits]
    
    full_binary = entropy_bin + checksum
    
    words = []
    for i in range(0, len(full_binary), 11):
        idx = int(full_binary[i:i+11], 2)
        words.append(wordlist[idx])
    
    return " ".join(words)

def seed_xor(seed, seed_nbits, n, deterministic, outputs):
    if deterministic:
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
        return seed_xor(seed, seed_nbits, n-1, deterministic, outputs)

def seed_combining(seeds):
    result = seeds[0]
    for seed in seeds[1:]:
        result ^= seed
    return result

def print_xor_backups(outputs, wordlist=WORDLIST__ENGLISH):
    print("\nXOR Backups:")
    for i, output in enumerate(outputs):
        mnemonic = entropy_to_mnemonic(output, wordlist)
        print(f"{i+1}: {mnemonic}\n")

def main():
    parser = argparse.ArgumentParser(
        description='SeedSigner XOR Seed Backup Tool',
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    split_parser = subparsers.add_parser('split', help='Split a seed into multiple XOR backups')
    split_parser.add_argument('seed_phrase', type=str, help='BIP39 seed phrase to split')
    split_parser.add_argument('parts', type=int, help='Number of parts to split into (including original)')
    split_parser.add_argument('--deterministic', action='store_true', 
                             help='Use deterministic splitting (same output for same input)')
    
    combine_parser = subparsers.add_parser('combine', help='Combine multiple XOR backups to recover the original seed')
    combine_parser.add_argument('seed_phrases', type=str, nargs='+', 
                               help='Two or more XOR backup seed phrases to combine')
    
    args = parser.parse_args()
    
    if args.command == 'split':
        outputs = []
        entropy = mnemonic_to_entropy(args.seed_phrase)
        seed_xor(int(entropy, 2), len(entropy), args.parts, args.deterministic, outputs)
        print_xor_backups(outputs)
        
    elif args.command == 'combine':
        backups = []
        for phrase in args.seed_phrases:
            entropy = mnemonic_to_entropy(phrase)
            backups.append(int(entropy, 2))
        
        combined = seed_combining(backups)
        print("\nRecovered seed phrase:")
        print(entropy_to_mnemonic(combined))
        
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    print("""
*******************************************************************************

    SeedSigner xor seed backup tool
    
    This tool is designed to split a seed into multiple XOR backups and
    combine them back to recover the original seed. It uses the BIP39 wordlist
    to convert between seed phrases and binary entropy.
          
    Usage:
    1) for spliting into two seed phrase
        python3 seed_xor.py split "brother ride syrup domain absent sock dove unfair fever use morning absorb" 2
    2) for combining two seed phrases
        python3 seed_xor.py combine "<copy and paste the seed phrases A>" "<copy and paste the seed phrases B>" 
    
*******************************************************************************
""")
    main()