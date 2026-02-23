import logging
import unicodedata
import hashlib
import hmac

from binascii import hexlify
from embit import bip39, bip32, bip85
from embit.networks import NETWORKS
from typing import List

from seedsigner.models.settings import SettingsConstants

logger = logging.getLogger(__name__)


class InvalidSeedException(Exception):
    pass



class Seed:
    def __init__(self,
                 mnemonic: List[str] = None,
                 passphrase: str = "",
                 wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> None:
        self._wordlist_language_code = wordlist_language_code

        if not mnemonic:
            raise Exception("Must initialize a Seed with a mnemonic List[str]")
        self._mnemonic: List[str] = unicodedata.normalize("NFKD", " ".join(mnemonic).strip()).split()

        self._passphrase: str = ""
        self.set_passphrase(passphrase, regenerate_seed=False)

        self.seed_bytes: bytes = None
        self._generate_seed()


    @staticmethod
    def get_wordlist(wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> List[str]:
        # TODO: Support other BIP-39 wordlist languages!
        if wordlist_language_code == SettingsConstants.WORDLIST_LANGUAGE__ENGLISH:
            return bip39.WORDLIST
        else:
            raise Exception(f"Unrecognized wordlist_language_code {wordlist_language_code}")


    def _generate_seed(self):
        try:
            self.seed_bytes = bip39.mnemonic_to_seed(self.mnemonic_str, password=self._passphrase, wordlist=self.wordlist)
        except Exception as e:
            logger.info(repr(e), exc_info=True)
            raise InvalidSeedException(repr(e))


    @property
    def mnemonic_str(self) -> str:
        return " ".join(self._mnemonic)
    

    @property
    def mnemonic_list(self) -> List[str]:
        return self._mnemonic


    @property 
    def wordlist_language_code(self) -> str:
        return self._wordlist_language_code


    @property
    def mnemonic_display_str(self) -> str:
        return unicodedata.normalize("NFC", " ".join(self._mnemonic))
    

    @property
    def mnemonic_display_list(self) -> List[str]:
        return unicodedata.normalize("NFC", " ".join(self._mnemonic)).split()


    @property
    def has_passphrase(self):
        return self._passphrase != ""


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
        # TODO: Support other BIP-39 wordlist languages!
        raise Exception("Not yet implemented!")


    @property
    def script_override(self) -> str:
        return None


    def derivation_override(self, sig_type: str = SettingsConstants.SINGLE_SIG) -> str:
        return None


    def detect_version(self, derivation_path: str, network: str = SettingsConstants.MAINNET, sig_type: str = SettingsConstants.SINGLE_SIG) -> str:
        embit_network = NETWORKS[SettingsConstants.map_network_to_embit(network)]
        return bip32.detect_version(derivation_path, default="xpub", network=embit_network)


    @property
    def passphrase_label(self) -> str:
        return SettingsConstants.LABEL__BIP39_PASSPHRASE


    @property
    def seedqr_supported(self) -> bool:
        return True


    @property
    def bip85_supported(self) -> bool:
        return True


    def get_fingerprint(self, network: str = SettingsConstants.MAINNET) -> str:
        root = bip32.HDKey.from_seed(self.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(network)]["xprv"])
        return hexlify(root.child(0).fingerprint).decode('utf-8')


    def get_xpub(self, wallet_path: str = '/', network: str = SettingsConstants.MAINNET):
        # Import here to avoid slow startup times; takes 1.35s to import the first time
        from seedsigner.helpers import embit_utils
        return embit_utils.get_xpub(seed_bytes=self.seed_bytes, derivation_path=wallet_path, embit_network=SettingsConstants.map_network_to_embit(network))


    def get_bip85_child_mnemonic(self, bip85_index: int, bip85_num_words: int, network: str = SettingsConstants.MAINNET):
        """Derives the seed's nth BIP-85 child mnemonic"""
        root = bip32.HDKey.from_seed(self.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(network)]["xprv"])

        # TODO: Support other BIP-39 wordlist languages!
        return bip85.derive_mnemonic(root, bip85_num_words, bip85_index)
        

    @staticmethod
    def _is_electrum_hmac(mnemonic_str: str) -> bool:
        """Check if a mnemonic string has a valid Electrum segwit HMAC prefix.

        Only checks for the segwit prefix ("100") since that is the only
        Electrum seed type SeedSigner supports.  The standard prefix ("01") is
        intentionally excluded because it is very short and causes false
        positives when brute-forcing last-word variants during XOR
        recombination (1-in-256 chance per candidate for 24-word seeds).
        """
        normalized = unicodedata.normalize("NFKD", mnemonic_str)
        h = hmac.digest(b"Seed version", normalized.encode('utf-8'), hashlib.sha512).hex()
        return h.startswith(SettingsConstants.ELECTRUM_SEED_SEGWIT)  # "100"


    @staticmethod
    def detect_mnemonic_type(mnemonic: list) -> str:
        """
        Detect whether a mnemonic is an Electrum seed or a standard BIP-39 seed.

        After XOR recombination, the resulting mnemonic has a valid BIP-39 checksum
        but the last word may differ from the original Electrum seed's last word
        (since Electrum doesn't use BIP-39 checksums). To handle this, we check
        all possible last words that share the same entropy bits — there are 16
        possibilities for 12-word seeds (4 checksum bits) and 256 for 24-word
        seeds (8 checksum bits).

        Returns: "electrum" if any candidate matches, otherwise "bip39"
        """
        if isinstance(mnemonic, str):
            mnemonic = mnemonic.split()

        # First, check the mnemonic as-is
        mnemonic_str = " ".join(mnemonic)
        if Seed._is_electrum_hmac(mnemonic_str):
            return "electrum"

        # The BIP-39 checksum may have changed the last word. Try all possible
        # last words that share the same entropy bits.
        wordlist = bip39.WORDLIST
        last_word = mnemonic[-1]
        last_index = wordlist.index(last_word)

        # For 12-word seeds: 4 checksum bits, so mask out bottom 4 bits
        # For 24-word seeds: 8 checksum bits, so mask out bottom 8 bits
        num_words = len(mnemonic)
        checksum_bits = num_words // 3  # 4 for 12 words, 8 for 24 words
        entropy_mask = ((1 << 11) - 1) ^ ((1 << checksum_bits) - 1)
        entropy_prefix = last_index & entropy_mask

        prefix_words = mnemonic[:-1]
        for i in range(1 << checksum_bits):
            candidate_index = entropy_prefix | i
            if candidate_index == last_index:
                continue  # Already checked
            if candidate_index >= len(wordlist):
                continue
            candidate_word = wordlist[candidate_index]
            candidate_str = " ".join(prefix_words + [candidate_word])
            if Seed._is_electrum_hmac(candidate_str):
                return "electrum"

        return "bip39"


    @staticmethod
    def get_electrum_mnemonic(mnemonic: list) -> list:
        """
        Given a mnemonic from XOR recombination (with BIP-39 checksum), find
        the exact last word that makes it a valid Electrum seed.

        Returns the corrected mnemonic list, or None if not an Electrum seed.
        """
        if isinstance(mnemonic, str):
            mnemonic = mnemonic.split()

        wordlist = bip39.WORDLIST

        # Check as-is first
        if Seed._is_electrum_hmac(" ".join(mnemonic)):
            return list(mnemonic)

        last_index = wordlist.index(mnemonic[-1])
        num_words = len(mnemonic)
        checksum_bits = num_words // 3
        entropy_mask = ((1 << 11) - 1) ^ ((1 << checksum_bits) - 1)
        entropy_prefix = last_index & entropy_mask

        prefix_words = mnemonic[:-1]
        for i in range(1 << checksum_bits):
            candidate_index = entropy_prefix | i
            if candidate_index >= len(wordlist):
                continue
            candidate_word = wordlist[candidate_index]
            candidate_mnemonic = prefix_words + [candidate_word]
            if Seed._is_electrum_hmac(" ".join(candidate_mnemonic)):
                return candidate_mnemonic

        return None


    ### override operators
    def __eq__(self, other):
        if isinstance(other, Seed):
            return self.seed_bytes == other.seed_bytes
        return False



class ElectrumSeed(Seed):

    def _generate_seed(self):
        if len(self._mnemonic) != 12:
            raise InvalidSeedException(f"Unsupported Electrum seed length: {len(self._mnemonic)}")

        s = hmac.digest(b"Seed version", self.mnemonic_str.encode('utf8'), hashlib.sha512).hex()
        prefix = s[0:3]

        # only support Electrum Segwit version for now
        if SettingsConstants.ELECTRUM_SEED_SEGWIT == prefix:
            self.seed_bytes=hashlib.pbkdf2_hmac('sha512', self.mnemonic_str.encode('utf-8'), b'electrum' + self._passphrase.encode('utf-8'), iterations = SettingsConstants.ELECTRUM_PBKDF2_ROUNDS)

        else:
            raise InvalidSeedException(f"Unsupported Electrum seed format: {prefix}")


    def set_passphrase(self, passphrase: str, regenerate_seed: bool = True):
        if passphrase:
            self._passphrase = ElectrumSeed.normalize_electrum_passphrase(passphrase)
        else:
            # Passphrase must always have a string value, even if it's just the empty
            # string.
            self._passphrase = ""

        if regenerate_seed:
            # Regenerate the internal seed since passphrase changes the result
            self._generate_seed()


    @staticmethod
    def normalize_electrum_passphrase(passphrase : str) -> str:
        passphrase = unicodedata.normalize('NFKD', passphrase)
        # lower
        passphrase = passphrase.lower()
        # normalize whitespaces
        passphrase = u' '.join(passphrase.split())
        return passphrase


    @property
    def script_override(self) -> str:
        return SettingsConstants.NATIVE_SEGWIT


    def derivation_override(self, sig_type: str = SettingsConstants.SINGLE_SIG) -> str:
        return "m/0h" if sig_type == SettingsConstants.SINGLE_SIG else "m/1h"


    def detect_version(self, derivation_path: str, network: str = SettingsConstants.MAINNET, sig_type: str = SettingsConstants.SINGLE_SIG) -> str:
        embit_network = NETWORKS[SettingsConstants.map_network_to_embit(network)]
        return embit_network["zpub"] if sig_type == SettingsConstants.SINGLE_SIG else embit_network["Zpub"]


    @property
    def passphrase_label(self) -> str:
        return SettingsConstants.LABEL__CUSTOM_EXTENSION


    @property
    def seedqr_supported(self) -> bool:
        return False


    @property
    def bip85_supported(self) -> bool:
        return False
