import hashlib
import unicodedata

from embit import bip39
from embit.bip39 import mnemonic_to_bytes, mnemonic_from_bytes
from typing import List

from seedsigner.models.seed import Seed


def calculate_checksum(mnemonic: list, wordlist_language_code: str) -> List[str]:
    """
        Provide 12- or 24-word mnemonic, returns complete mnemonic w/checksum as a list.

        If 11- or 23-words are provided, append word `0000` to end of list as temp final
        word.
    """
    if len(mnemonic) in [11, 23]:
        mnemonic.append(Seed.get_wordlist(wordlist_language_code)[0])

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



def generate_mnemonic_from_bytes(entropy_bytes) -> List[str]:
    return bip39.mnemonic_from_bytes(entropy_bytes).split()



def generate_mnemonic_from_dice(roll_data: str) -> List[str]:
    entropy_bytes = hashlib.sha256(roll_data.encode()).digest()

    if len(roll_data) == 50:
        # 12-word mnemonic; only use 128bits / 16 bytes
        entropy_bytes = entropy_bytes[:16]

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes).split()



# Note: This currently isn't being used since we're now chaining hashed bytes for the
#   image-based entropy and aren't just ingesting a single image.
def generate_mnemonic_from_image(image) -> List[str]:
    import hashlib
    hash = hashlib.sha256(image.tobytes())

    # Return as a list
    return bip39.mnemonic_from_bytes(hash.digest()).split()
