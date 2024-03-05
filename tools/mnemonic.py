import argparse
import random
from seedsigner.helpers import mnemonic_generation
from embit.wordlists.bip39 import WORDLIST as WORDLIST__ENGLISH

"""
see: docs/dice_verification.md (the "Command Line Tool" section) for full instructions.

tldr:
    pip3 install embit
    pip3 install -e .
    cd tools
    python3 mnemonic.py -h
"""


usage = f"""
Verify SeedSigner's dice rolls and coin flip entropy-to-mnemonic conversion via this tool.

Compare its results against iancoleman.io/bip39 and bitcoiner.guide/seed

Usage:
    # {mnemonic_generation.DICE__NUM_ROLLS__12WORD} dice rolls / 12-word mnemonic
    python3 mnemonic.py dice 5624433434...

    # {mnemonic_generation.DICE__NUM_ROLLS__24WORD} dice rolls / 24-word mnemonic
    python3 mnemonic.py dice 6151463561...

    # {mnemonic_generation.DICE__NUM_ROLLS__12WORD} dice rolls, entered as 0-5 / 12-word mnemonic
    python3 mnemonic.py --zero-indexed-dice dice 5135535514...

    # 128 coin flips / 12-word mnemonic
    python3 mnemonic.py coins 1111100111...

    # 256 coin flips / 24-word mnemonic
    python mnemonic.py coins 0010111010...

    # GENERATE {mnemonic_generation.DICE__NUM_ROLLS__12WORD} random dice rolls / 12-word mnemonic
    python3 mnemonic.py dice rand12

    # GENERATE {mnemonic_generation.DICE__NUM_ROLLS__24WORD} random dice rolls / 24-word mnemonic
    python3 mnemonic.py dice rand24

    # GENERATE {mnemonic_generation.DICE__NUM_ROLLS__24WORD} random dice rolls, entered as 0-5 / 24-word mnemonic
    python3 mnemonic.py --zero-indexed-dice dice rand24

    # GENERATE 128 random coin flips / 12-word mnemonic
    python3 mnemonic.py coins rand12

    # GENERATE 256 random coin flips / 24-word mnemonic
    python3 mnemonic.py coins rand24
"""
RAND_12 = "rand12"
RAND_24 = "rand24"
parser = argparse.ArgumentParser(description=f'SeedSigner entropy-to-mnemonic tool\n\n{usage}', formatter_class=argparse.RawTextHelpFormatter)

# Required positional arguments
parser.add_argument('method', type=str, choices=['dice', 'coins', 'final_word'], help="Input entropy method")
parser.add_argument('entropy', type=str, help=f"""Entropy data. Enter "{ RAND_12 }" or "{ RAND_24 }" to create a random (not-secure) example seed.""")

# Optional arguments
parser.add_argument('-z', '--zero-indexed-dice',
                    action="store_true",
                    default=False,
                    dest="zero_indexed_dice",
                    help="Enables dice entry as [0-5] instead of default [1-6]")

args = parser.parse_args()

method = args.method
entropy = args.entropy
zero_indexed_dice = args.zero_indexed_dice

is_rand_seed = 'rand' in entropy
if is_rand_seed:
    # Generate random data as our entropy
    if entropy not in [RAND_12, RAND_24]:
        print(f"""Invalid random entropy value: Must be either "{RAND_12}" or "{RAND_24}".""")
        exit(1)
    mnemonic_length = 12 if entropy == RAND_12 else 24

    if method == 'dice':
        if zero_indexed_dice:
            entropy = ''.join([str(random.randint(0, 5)) for i in range(mnemonic_generation.DICE__NUM_ROLLS__12WORD if mnemonic_length == 12 else mnemonic_generation.DICE__NUM_ROLLS__24WORD)])
        else:
            entropy = ''.join([str(random.randint(1, 6)) for i in range(mnemonic_generation.DICE__NUM_ROLLS__12WORD if mnemonic_length == 12 else mnemonic_generation.DICE__NUM_ROLLS__24WORD)])

    elif method == 'coins':
        entropy = ''.join([str(random.randint(0, 1)) for i in range(128 if mnemonic_length == 12 else 256)])

    elif method == 'final_word':
        random_dice_rolls = ''.join([str(random.randint(0, 1)) for i in range(128 if mnemonic_length == 12 else 256)])
        entropy = " ".join(mnemonic_generation.generate_mnemonic_from_coin_flips(random_dice_rolls)[:-1])
        print(len(entropy.split()), entropy)

if method == 'dice':
    if not zero_indexed_dice and ('0' in entropy or '6' not in entropy):
        print("Dice entry must be 1-6 unless --zero-indexed-dice is specified")
        exit(1)
    if len(entropy) not in [mnemonic_generation.DICE__NUM_ROLLS__12WORD, mnemonic_generation.DICE__NUM_ROLLS__24WORD]:
        print(f"Dice entropy must be {mnemonic_generation.DICE__NUM_ROLLS__12WORD} or {mnemonic_generation.DICE__NUM_ROLLS__24WORD} rolls")
        exit(1)
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(entropy)

elif method == 'coins':
    if len(entropy) not in [128, 256]:
        print("Coin flip entropy must be 128 or 256 flips")
        exit(1)
    mnemonic = mnemonic_generation.generate_mnemonic_from_coin_flips(entropy)

elif method == 'final_word':
    num_input_words = len(entropy.split())
    if num_input_words not in [11, 12, 23, 24]:
        print(f"Final word entropy must be 11, 12, 23, or 24 words ({num_input_words} provided)")
        exit(1)

    if num_input_words in [11, 23]:
        # We need to fill the last bits of entropy
        if num_input_words == 11:
            # 7 final bits of entropy in the 12th word (7 + 4-bit checksum)
            num_final_entropy_bits = 7
        else:
            # 3 final bits of entropy in the 24th word (3 + 8-bit checksum)
            num_final_entropy_bits = 3

        final_entropy_method = None
        while final_entropy_method not in ['1', '2', '3']:
            final_entropy_method = input(f"""
How would you like to fill the final {num_final_entropy_bits} bits of entropy?

1.) {num_final_entropy_bits} coin flips
2.) Select an additional word from the wordlist
3.) Fill with zeros

Type 1, 2, or 3: """)

        if final_entropy_method == '1':
            coin_flips = input(f"""    Enter {num_final_entropy_bits} coin flips as 0 or 1 (e.g. { "".join(str(random.randint(0,1)) for f in range(0, num_final_entropy_bits)) }): """)
            if len(coin_flips) != num_final_entropy_bits:
                print(f"Invalid number of coin flips: needed {num_final_entropy_bits}, got {len(coin_flips)}")
            final_word = mnemonic_generation.get_partial_final_word(coin_flips)
            entropy += f" {final_word}"

        elif final_entropy_method == '2':
            final_word = input(f"""    Enter the final word: """)
            if final_word not in WORDLIST__ENGLISH:
                print(f"Invalid word: {final_word}")
                exit(1)
            entropy += f" {final_word}"

        elif final_entropy_method == '3':
            # Nothing to do; just pass the 11 or 23 words straight to calculate_checksum
            pass

    mnemonic = mnemonic_generation.calculate_checksum(entropy)

print("\n")
if is_rand_seed:
    print("\t***** This is a demo seed. Do not use it to store funds!!! *****")

print(f"""\t{" ".join(mnemonic)}\n""")

if is_rand_seed:
    print(f"\tEntropy: {entropy}\n")

if method == "dice":
    print(f"""\tVerify at iancoleman.io/bip39 or bitcoiner.guide/seed using "Base 10" or "Hex" mode.\n""")
elif method == "coins":
    print(f"""\tVerify at iancoleman.io/bip39 or bitcoiner.guide/seed using "Binary" mode.\n""")
