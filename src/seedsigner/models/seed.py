import unicodedata
import embit

from binascii import hexlify
from embit import bip39, bip32
from embit.networks import NETWORKS
from typing import List

from seedsigner.helpers.bip85 import hmac_sha512
from seedsigner.models.settings import SettingsConstants

class InvalidSeedException(Exception):
    pass

class Seed:
    def __init__(self,
                 mnemonic: List[str] = None,
                 bip85_seed: List[str] = None,
                 passphrase: str = "",
                 wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> None:
        self.wordlist_language_code = wordlist_language_code

        if not mnemonic:
            raise Exception("Must initialize a Seed with a mnemonic List[str]")
        self._mnemonic: List[str] = unicodedata.normalize("NFKD", " ".join(mnemonic).strip()).split()

        self._passphrase: str = ""
        self.set_passphrase(passphrase, regenerate_seed=False)

        self.seed_bytes: bytes = None
        self._generate_seed()
        self._bip85_seed: List[str] = ""
        self.bip85_index: int = 0
        self.bip85_num_words: int = 12


    @staticmethod
    def get_wordlist(wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> List[str]:
        # TODO: Support other bip-39 wordlist languages!
        if wordlist_language_code == SettingsConstants.WORDLIST_LANGUAGE__ENGLISH:
            return bip39.WORDLIST
        else:
            raise Exception(f"Unrecognized wordlist_language_code {wordlist_language_code}")


    def _generate_seed(self) -> bool:
        try:
            self.seed_bytes = bip39.mnemonic_to_seed(self.mnemonic_str, password=self._passphrase, wordlist=self.wordlist)
        except Exception as e:
            print(repr(e))
            raise InvalidSeedException(repr(e))


    @property
    def mnemonic_str(self) -> str:
        return " ".join(self._mnemonic)
    
    @property
    def mnemonic_list(self) -> List[str]:
        return self._mnemonic
    

    @property
    def mnemonic_display_str(self) -> str:
        return unicodedata.normalize("NFC", " ".join(self._mnemonic))
    

    @property
    def mnemonic_display_list(self) -> List[str]:
        return unicodedata.normalize("NFC", " ".join(self._mnemonic)).split()

    @property
    def bip85_seed_display_list(self) -> List[str]:
        return unicodedata.normalize("NFC", " ".join(self._bip85_seed)).split()
    
    #@property
    #def bip85_seed(self):
    #    return self._bip85_seed


    @property
    def passphrase(self):
        return self._passphrase
        

    @property
    def passphrase_display(self):
        return unicodedata.normalize("NFC", self._passphrase)


    def set_passphrase(self, passphrase: str, regenerate_seed: bool = True):
        if passphrase:
            self._passphrase = unicodedata.normalize("NFKD", passphrase)
        else:
            # Passphrase must always have a string value, even if it's just the empty
            # string.
            self._passphrase = ""

        if regenerate_seed:
            # Regenerate the internal seed since passphrase changes the result
            self._generate_seed()


    @property
    def wordlist(self) -> List[str]:
        return Seed.get_wordlist(self.wordlist_language_code)


    def set_wordlist_language_code(self, language_code: str):
        # TODO: Support other bip-39 wordlist languages!
        raise Exception("Not yet implemented!")


    def get_fingerprint(self, network: str = SettingsConstants.MAINNET) -> str:
        root = bip32.HDKey.from_seed(self.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(network)]["xprv"])
        return hexlify(root.child(0).fingerprint).decode('utf-8')
        
    def get_xpub(self, wallet_path: str = '/', network: str = SettingsConstants.MAINNET):
        root = bip32.HDKey.from_seed(self.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(network)]["xprv"])
        xprv = root.derive(wallet_path)
        xpub = xprv.to_public()
        return xpub

    # Derives a BIP85 mnemonic (seed word) from the master seed words using embit functions
    def get_bip85_child_mnemonic(self, bip85_index: int, bip85_num_words: int):
        passphrase = self._passphrase
        # language = 'english'
        # lang_code = 0
        # Need to add language later for path, defaults to English (0)
        path = "m/83696968'/39'/0'/{bip85_num_words}'/{bip85_index}'".format(bip85_num_words=bip85_num_words,
                                                                             bip85_index=bip85_index)
        #seed = bip39.mnemonic_to_seed(self.mnemonic_str, password=self._passphrase, wordlist=self.wordlist)
        # xprv = embit.bip32.HDKey.from_seed(seed)
        root = bip32.HDKey.from_seed(self.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(network)]["xprv"])

        # Derive k
        xprv = root.derive(path)
        entropy = hmac_sha512(xprv.secret)
        width = round(bip85_num_words / 12 * 16)
        return bip39.mnemonic_from_bytes(entropy[:width])

    ### override operators
    def __eq__(self, other):
        if isinstance(other, Seed):
            return self.seed_bytes == other.seed_bytes
        return False
