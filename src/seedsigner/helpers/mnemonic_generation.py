import hashlib
import random
import unicodedata

from embit import bip39
from embit.bip39 import mnemonic_to_bytes, mnemonic_from_bytes
from embit.wordlists.bip39 import WORDLIST as WORDLIST__ENGLISH

"""
    This is SeedSigner's internal mnemonic generation utility but is also meant to
    function as an independently-executable CLI to facilitate external verification of
    SeedSigner's mnemonic generation for a given input entropy.

    Therefore its module imports should be kept to the bare minimum.

    ## Running as a standalone script
    Install the `embit` library:
    ```
    pip3 install embit
    ```

    And then run:
    ```
    python3 mnemonic_generation.py -h
    ```
"""


# Hard-coded value from SettingsConstants to avoid dependencies
WORDLIST_LANGUAGE__ENGLISH = 'en'

DICE__NUM_ROLLS__12WORD = 50
DICE__NUM_ROLLS__24WORD = 99


def _get_wordlist(wordlist_language_code) -> list[str]:
    """
        Convenience method to fetch the wordlist for the given language code without
        requiring any SeedSigner module dependencies for when this is run as a
        standalone CLI.
    """
    if wordlist_language_code == WORDLIST_LANGUAGE__ENGLISH:
        return WORDLIST__ENGLISH
    else:
        # Nested import to avoid dependency on Seed model when running this script standalone
        from seedsigner.models import Seed
        return Seed.get_wordlist(wordlist_language_code)



def calculate_checksum(mnemonic: list | str, wordlist_language_code: str = WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Provide 12- or 24-word mnemonic, returns complete mnemonic w/checksum as a list.

        Mnemonic may be a list of words or a string of words separated by spaces or commas.

        If 11- or 23-words are provided, append word `0000` to end of list as temp final
        word.
    """
    if type(mnemonic) == str:
        import re
        # split on commas or spaces
        mnemonic = re.findall(r'[^,\s]+', mnemonic)

    if len(mnemonic) in [11, 23]:
        if wordlist_language_code == WORDLIST_LANGUAGE__ENGLISH:
            temp_final_word = "abandon"
        else:
            # Nested import to avoid dependency on Seed model when running this script standalone
            from seedsigner.models import Seed
            temp_final_word = Seed.get_wordlist(wordlist_language_code)[0]

        mnemonic.append(temp_final_word)

    if len(mnemonic) not in [12, 24]:
        raise Exception("Pass in a 12- or 24-word mnemonic")
    
    # Work on a copy of the input list
    mnemonic_copy = mnemonic.copy()

    # Convert the resulting mnemonic to bytes, but we `ignore_checksum` validation
    # because we assume it's incorrect since we either let the user select their own
    # final word OR we injected the 0000 word from the wordlist.
    mnemonic_bytes = bip39.mnemonic_to_bytes(unicodedata.normalize("NFKD", " ".join(mnemonic_copy)), ignore_checksum=True, wordlist=_get_wordlist(wordlist_language_code))

    # This function will convert the bytes back into a mnemonic, but it will also
    # calculate the proper checksum bits while doing so. For a 12-word seed it will just
    # overwrite the last 4 bits from the above result with the checksum; for a 24-word
    # seed it'll overwrite the last 8 bits.
    return bip39.mnemonic_from_bytes(mnemonic_bytes).split()



def generate_mnemonic_from_bytes(entropy_bytes, wordlist_language_code: str = WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=_get_wordlist(wordlist_language_code)).split()



def generate_mnemonic_from_dice(roll_data: str, wordlist_language_code: str = WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Takes a string of 50 or 99 dice rolls and returns a 12- or 24-word mnemonic.

        Uses the iancoleman.io/bip39 and bitcoiner.guide/seed "Base 10" or "Hex" mode approach:
        * dice rolls are treated as string data.
        * hashed via SHA256.

        Important note: This method is NOT compatible with iancoleman's "Dice" mode.
    """
    entropy_bytes = hashlib.sha256(roll_data.encode()).digest()

    if len(roll_data) == DICE__NUM_ROLLS__12WORD:
        # 12-word mnemonic; only use 128bits / 16 bytes
        entropy_bytes = entropy_bytes[:16]

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=_get_wordlist(wordlist_language_code)).split()



def generate_mnemonic_from_coin_flips(coin_flips: str, wordlist_language_code: str = WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Takes a string of 128 or 256 0s and 1s and returns a 12- or 24-word mnemonic.

        Uses the iancoleman.io/bip39 and bitcoiner.guide/seed "Binary" mode approach:
        * binary digit stream is treated as string data.
        * hashed via SHA256.
    """
    entropy_bytes = hashlib.sha256(coin_flips.encode()).digest()

    if len(coin_flips) == 128:
        # 12-word mnemonic; only use 128bits / 16 bytes
        entropy_bytes = entropy_bytes[:16]

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=_get_wordlist(wordlist_language_code)).split()



def get_partial_final_word(coin_flips: str, wordlist_language_code: str = WORDLIST_LANGUAGE__ENGLISH) -> str:
    """ Look up the partial final word for the given coin flips.
        7 coin flips: 0101010 + 0000 where the final 4 bits will be replaced with the checksum
        3 coin flips: 0101 + 0000000 where the final 8 bits will be replaced with the checksum
    """
    binary_string = coin_flips + "0" * (11 - len(coin_flips))
    wordlist_index = int(binary_string, 2)

    if wordlist_language_code == WORDLIST_LANGUAGE__ENGLISH:
        wordlist = WORDLIST__ENGLISH
    else:
        from seedsigner.models import Seed, SettingsConstants
        wordlist = Seed.get_wordlist(wordlist_language_code)

    return wordlist[wordlist_index]




# Note: This currently isn't being used since we're now chaining hashed bytes for the
#   image-based entropy and aren't just ingesting a single image.
def generate_mnemonic_from_image(image, wordlist_language_code: str = WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    import hashlib
    hash = hashlib.sha256(image.tobytes())

    # Return as a list
    return bip39.mnemonic_from_bytes(hash.digest(), wordlist=_get_wordlist(wordlist_language_code)).split()



if __name__ == "__main__":
    import argparse

    usage = f"""
    Verify SeedSigner's dice rolls and coin flip entropy-to-mnemonic conversion via this tool.

    Compare its results against iancoleman.io/bip39 and bitcoiner.guide/seed

    Usage:
        # {DICE__NUM_ROLLS__12WORD} dice rolls / 12-word mnemonic
        python3 mnemonic_generation.py dice 5624433434...
        
        # {DICE__NUM_ROLLS__24WORD} dice rolls / 24-word mnemonic
        python3 mnemonic_generation.py dice 6151463561...

        # {DICE__NUM_ROLLS__12WORD} dice rolls, entered as 0-5 / 12-word mnemonic
        python3 mnemonic_generation.py --zero-indexed-dice dice 5135535514...

        # 128 coin flips / 12-word mnemonic
        python3 mnemonic_generation.py coins 1111100111...

        # 256 coin flips / 24-word mnemonic
        python mnemonic_generation.py coins 0010111010...

        # GENERATE {DICE__NUM_ROLLS__12WORD} random dice rolls / 12-word mnemonic
        python3 mnemonic_generation.py dice rand12

        # GENERATE {DICE__NUM_ROLLS__24WORD} random dice rolls / 24-word mnemonic
        python3 mnemonic_generation.py dice rand24

        # GENERATE {DICE__NUM_ROLLS__24WORD} random dice rolls, entered as 0-5 / 24-word mnemonic
        python3 mnemonic_generation.py --zero-indexed-dice dice rand24

        # GENERATE 128 random coin flips / 12-word mnemonic
        python3 mnemonic_generation.py coins rand12

        # GENERATE 256 random coin flips / 24-word mnemonic
        python3 mnemonic_generation.py coins rand24
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
                entropy = ''.join([str(random.randint(0, 5)) for i in range(DICE__NUM_ROLLS__12WORD if mnemonic_length == 12 else DICE__NUM_ROLLS__24WORD)])
            else:
                entropy = ''.join([str(random.randint(1, 6)) for i in range(DICE__NUM_ROLLS__12WORD if mnemonic_length == 12 else DICE__NUM_ROLLS__24WORD)])

        elif method == 'coins':
            entropy = ''.join([str(random.randint(0, 1)) for i in range(128 if mnemonic_length == 12 else 256)])

        elif method == 'final_word':
            random_dice_rolls = ''.join([str(random.randint(0, 1)) for i in range(128 if mnemonic_length == 12 else 256)])
            entropy = " ".join(generate_mnemonic_from_coin_flips(random_dice_rolls)[:-1])
            print(len(entropy.split()), entropy)

    if method == 'dice':
        if not zero_indexed_dice and ('0' in entropy or '6' not in entropy):
            print("Dice entry must be 1-6 unless --zero-indexed-dice is specified")
            exit(1)
        if len(entropy) not in [DICE__NUM_ROLLS__12WORD, DICE__NUM_ROLLS__24WORD]:
            print(f"Dice entropy must be {DICE__NUM_ROLLS__12WORD} or {DICE__NUM_ROLLS__24WORD} rolls")
            exit(1)
        mnemonic = generate_mnemonic_from_dice(entropy)
    
    elif method == 'coins':
        if len(entropy) not in [128, 256]:
            print("Coin flip entropy must be 128 or 256 flips")
            exit(1)
        mnemonic = generate_mnemonic_from_coin_flips(entropy)
    
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
                final_word = get_partial_final_word(coin_flips)
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

        mnemonic = calculate_checksum(entropy)

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