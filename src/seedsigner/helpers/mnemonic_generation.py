import hashlib
import unicodedata

from embit import bip39
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.models.seed import Seed

"""
    This is SeedSigner's internal mnemonic generation utility.
     
    It can also be run as an independently-executable CLI to facilitate external
    verification of SeedSigner's results for a given input entropy.

    see: docs/dice_verification.md (the "Command Line Tool" section).
"""

DICE__NUM_ROLLS__12WORD = 50
DICE__NUM_ROLLS__24WORD = 99



def calculate_checksum(mnemonic: list | str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
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
        temp_final_word = Seed.get_wordlist(wordlist_language_code)[0]
        mnemonic.append(temp_final_word)

    if len(mnemonic) not in [12, 24]:
        raise Exception("Pass in a 12- or 24-word mnemonic")
    
    # Work on a copy of the input list
    mnemonic_copy = mnemonic.copy()

    # Convert the resulting mnemonic to bytes, but we `ignore_checksum` validation
    # because we assume it's incorrect since we either let the user select their own
    # final word OR we injected the 0000 word from the wordlist.
    mnemonic_bytes = bip39.mnemonic_to_bytes(unicodedata.normalize("NFKD", " ".join(mnemonic_copy)), ignore_checksum=True, wordlist=Seed.get_wordlist(wordlist_language_code))

    # This function will convert the bytes back into a mnemonic, but it will also
    # calculate the proper checksum bits while doing so. For a 12-word seed it will just
    # overwrite the last 4 bits from the above result with the checksum; for a 24-word
    # seed it'll overwrite the last 8 bits.
    return bip39.mnemonic_from_bytes(mnemonic_bytes).split()



def generate_mnemonic_from_bytes(entropy_bytes, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def generate_mnemonic_from_dice(roll_data: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
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
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def generate_mnemonic_from_coin_flips(coin_flips: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
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
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def get_partial_final_word(coin_flips: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> str:
    """ Look up the partial final word for the given coin flips.
        7 coin flips: 0101010 + **** where the final 4 bits will be replaced with the checksum
        3 coin flips: 010 + ******** where the final 8 bits will be replaced with the checksum
    """
    binary_string = coin_flips + "0" * (11 - len(coin_flips))
    wordlist_index = int(binary_string, 2)

    return Seed.get_wordlist(wordlist_language_code)[wordlist_index]



# Note: This currently isn't being used since we're now chaining hashed bytes for the
#   image-based entropy and aren't just ingesting a single image.
def generate_mnemonic_from_image(image, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    import hashlib
    hash = hashlib.sha256(image.tobytes())

    # Return as a list
    return bip39.mnemonic_from_bytes(hash.digest(), wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def get_valid_final_mnemonic_words(partial_mnemonic: list, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
    Calculate all valid final words that would produce a valid checksum for the given partial mnemonic.

    For 12-word seeds (7 bit entropy + 4 bit checksum): exactly 128 valid words out of 2048
    For 24-word seeds (3 bit entropy + 8 bit checksum): exactly 8 valid words out of 2048
    """
    wordlist = Seed.get_wordlist(wordlist_language_code)
    total_bits = 128 if len(partial_mnemonic) == 11 else 256
    entropy_bits = 0

    # convert partial mnemonic words to entropy bits.
    # left shift the current entropy_bits by 11 and combine the shifted value with word index.
    # this helps us calculate the correct checksum
    for word in partial_mnemonic:
        entropy_bits = (entropy_bits << 11) | wordlist.index(word)

    final_entropy_bits = total_bits - len(partial_mnemonic) * 11 # each word has 11 bits of entropy
    valid_indices = []

    # brute force all possible final entropy values
    # 12-word seeds: 2^7 = 128 iterations
    # 24-word seeds: 2^3 = 8 iterations
    for i in range(1 << final_entropy_bits):
        # combine existing entropy with candidate final entropy bits
        full_entropy = (entropy_bits << final_entropy_bits) | i
        
        # convert to bytes for SHA256 (crypto functions need byte input, not integers)
        entropy_bytes = full_entropy.to_bytes(total_bits//8, 'big')
        
        # BIP-39 checksum: first byte of SHA256 hash contains the checksum bits
        checksum = hashlib.sha256(entropy_bytes).digest()[0]
        
        # construct final word index from entropy + checksum bits
        if len(partial_mnemonic) == 11:
            # 12-word seed: use top 4 bits of checksum byte (>> 4 extracts bits 7-4)
            checksum_bits = checksum >> 4
            final_index = (i << 4) | checksum_bits
        else:
            # 24-word seed: use all 8 bits of checksum byte
            # combine 3 entropy bits (shifted left) + 8 checksum bits
            final_index = (i << 8) | checksum

        valid_indices.append(final_index)

    return [wordlist[i] for i in sorted(valid_indices)]
