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


def combine_mnemonics_with_xor(mnemonics: list[str], wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
    Combine multiple mnemonic seed phrases using XOR operation (SeedXOR).

    XORs the word indices (11 bits each) of each mnemonic, then converts the
    XOR'd entropy back to a mnemonic with a valid BIP-39 checksum.

    Supports both BIP-39 and Electrum seeds since both use the same 2048-word
    BIP-39 wordlist. The XOR is its own inverse: recombining all original parts
    will reproduce the original seed.

    For the entropy bits (first 128/256 bits), XOR is straightforward and
    reversible. The last word's checksum bits (4 bits for 12-word, 8 bits for
    24-word) are recomputed as a valid BIP-39 checksum from the XOR'd entropy.
    This means XOR parts are always valid BIP-39 seeds. When all parts are
    recombined, the entropy is perfectly restored; if the original was an
    Electrum seed, the HMAC check will pass since it depends on the entropy.

    Args:
        mnemonics: List of mnemonic seed phrases (as strings or lists of words)
        wordlist_language_code: Language code for the BIP39 wordlist (default: English)

    Returns:
        Combined mnemonic as a list of words

    Raises:
        ValueError: If mnemonics list is empty, contains invalid mnemonics,
                   or mnemonics have different word counts
    """
    if not mnemonics:
        raise ValueError("Mnemonic list cannot be empty")

    wordlist = Seed.get_wordlist(wordlist_language_code)

    # Convert mnemonics to lists of word indices
    try:
        index_lists = []
        for mnemonic in mnemonics:
            words = mnemonic.split() if isinstance(mnemonic, str) else mnemonic
            indices = []
            for word in words:
                if word not in wordlist:
                    raise ValueError(f"Word '{word}' is not in the dictionary")
                indices.append(wordlist.index(word))
            index_lists.append(indices)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Invalid mnemonic: {str(e)}")

    # Validate all mnemonics have the same word count
    word_counts = set(len(indices) for indices in index_lists)
    if len(word_counts) != 1:
        raise ValueError("All mnemonics must generate entropy of the same length")

    num_words = index_lists[0].__len__()
    if num_words not in (12, 24):
        raise ValueError("Mnemonics must be 12 or 24 words")

    # XOR all word indices together to get the combined 11-bit values
    combined_indices = index_lists[0][:]
    for indices in index_lists[1:]:
        combined_indices = [a ^ b for a, b in zip(combined_indices, indices)]

    # Convert combined indices to entropy bits (all 11 * num_words bits)
    all_bits = []
    for idx in combined_indices:
        for bit_pos in range(10, -1, -1):
            all_bits.append((idx >> bit_pos) & 1)

    # Extract entropy bits (strip the checksum bits from the last word)
    checksum_length = num_words // 3  # 4 for 12 words, 8 for 24 words
    entropy_bits = all_bits[:len(all_bits) - checksum_length]

    # Convert entropy bits to bytes
    entropy_bytes = bytearray()
    for i in range(0, len(entropy_bits), 8):
        byte = 0
        for bit in entropy_bits[i:i+8]:
            byte = (byte << 1) | bit
        entropy_bytes.append(byte)

    # Use mnemonic_from_bytes to produce a mnemonic with valid BIP-39 checksum
    return bip39.mnemonic_from_bytes(bytes(entropy_bytes), wordlist=wordlist).split()
