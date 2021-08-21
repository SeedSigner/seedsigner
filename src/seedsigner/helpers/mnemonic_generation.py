from embit import bip39
from embit.bip39 import mnemonic_to_bytes, mnemonic_from_bytes



def calculate_checksum(partial_mnemonic: list):
    # Provide 11- or 23-word mnemonic, returns complete mnemonic w/checksum
    if len(partial_mnemonic) not in [11, 23]:
        raise Exception("Pass in a 11- or 23-word mnemonic")

    # Work on a copy of the input list
    mnemonic_copy = partial_mnemonic.copy()
    mnemonic_copy.append("abandon")

    # Ignores the final checksum word and recalcs
    mnemonic_bytes = bip39.mnemonic_to_bytes(" ".join(mnemonic_copy), ignore_checksum=True)

    # Return as a list
    return bip39.mnemonic_from_bytes(mnemonic_bytes).split()



def generate_mnemonic_from_bytes(entropy_bytes):
    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes).split()



def generate_mnemonic_from_dice(roll_data: str):
    entropyinteger = int(roll_data, 6)
    entropy_bytes = entropyinteger.to_bytes(32, byteorder="little")

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes).split()



# Note: This currently isn't being used since we're now chaining hashed bytes for the
#   image-based entropy and aren't just ingesting a single image.
def generate_mnemonic_from_image(image):
    hash = hashlib.sha256(image.tobytes())

    # Return as a list
    return bip39.mnemonic_from_bytes(hash.digest()).split()
