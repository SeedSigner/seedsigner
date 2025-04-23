from binascii import hexlify
from embit import bip32, bech32
from embit import ec
# from seedsigner.helpers import bech32
from seedsigner.models.seed import Seed


NOSTR__PUBKEY_NPUB = "npub"
NOSTR__PUBKEY_HEX = "pubhex"
NOSTR__PRIVKEY_NSEC = "nsec"
NOSTR__PRIVKEY_HEX = "privhex"


def derive_nostr_key(seed: Seed) -> bip32.HDKey:
    """ Derive the NIP-06 Nostr key at m/44'/1237'/0'/0/0 """
    """
        Note: You could derive sibling seeds (e.g. m/44h/1237h/0h/0/1) from the same root
        Seed, but so far Nostr use cases & best practices are limited to just a single
        direct path from mnemonic to npub/nsec. No sibling or child Nostr keys.
    """
    root = bip32.HDKey.from_seed(seed.seed_bytes)
    return root.derive("m/44h/1237h/0h/0/0")



def get_nsec(seed: Seed) -> str:
    nostr_root = derive_nostr_key(seed=seed)
    converted_bits = bech32.convertbits(nostr_root.secret, 8, 5)
    return bech32.bech32_encode(encoding=bech32.Encoding.BECH32, hrp=NOSTR__PRIVKEY_NSEC, data=converted_bits)



def get_npub(seed: Seed) -> str:
    nostr_root = derive_nostr_key(seed=seed)
    privkey = ec.PrivateKey(secret=nostr_root.secret)
    pubkey = privkey.get_public_key().xonly()
    converted_bits = bech32.convertbits(pubkey, 8, 5)
    return bech32.bech32_encode(encoding=bech32.Encoding.BECH32, hrp=NOSTR__PUBKEY_NPUB, data=converted_bits)



def get_pubkey_hex(seed: Seed) -> str:
    nostr_root = derive_nostr_key(seed=seed)
    privkey = ec.PrivateKey(secret=nostr_root.secret)
    return hexlify(privkey.get_public_key().xonly()).decode()



def get_privkey_hex(seed: Seed) -> str:
    nostr_root = derive_nostr_key(seed=seed)
    return hexlify(nostr_root.secret).decode()



def get_nostr_key(seed: Seed, format: str = NOSTR__PUBKEY_NPUB) -> str:
    """
    Get the Nostr key in the requested format.
    :param seed: Seed object
    :param format: Format of the key (npub, pubhex, nsec, privhex)
    :return: Nostr key in the requested format
    """
    if format == NOSTR__PUBKEY_NPUB:
        return get_npub(seed)
    elif format == NOSTR__PUBKEY_HEX:
        return get_pubkey_hex(seed)
    elif format == NOSTR__PRIVKEY_NSEC:
        return get_nsec(seed)
    elif format == NOSTR__PRIVKEY_HEX:
        return get_privkey_hex(seed)
    else:
        raise ValueError(f"Invalid format: {format}")
