import unicodedata

from binascii import hexlify
from embit import bip39, bip32
from embit.networks import NETWORKS
from typing import List


class SeedConstants:
    MAINNET = "main"
    TESTNET = "test"
    REGTEST = "regtest"
    ALL_NETWORKS = [
        (MAINNET, "Mainnet"),
        (TESTNET, "Testnet"),
        (REGTEST, "Regtest")
    ]
    
    SINGLE_SIG = "single_sig"
    MULTISIG = "multisig"
    ALL_SIG_TYPES = [
        (SINGLE_SIG, "Single Sig"),
        (MULTISIG, "Multisig"),
    ]

    NATIVE_SEGWIT = "native_segwit"
    NESTED_SEGWIT = "nested_segwit"
    TAPROOT = "taproot"
    CUSTOM_DERIVATION = "custom_derivation"
    ALL_SCRIPT_TYPES = [
        (NATIVE_SEGWIT, "Native Segwit"),
        (NESTED_SEGWIT, "Nested Segwit (legacy)"),
        (TAPROOT, "Taproot"),
        (CUSTOM_DERIVATION, "Custom Derivation"),
    ]

    WORDLIST_LANGUAGE__ENGLISH = "en"
    WORDLIST_LANGUAGE__CHINESE_SIMPLIFIED = "zh_Hans_CN"
    WORDLIST_LANGUAGE__CHINESE_TRADITIONAL = "zh_Hant_TW"
    WORDLIST_LANGUAGE__FRENCH = "fr"
    WORDLIST_LANGUAGE__ITALIAN = "it"
    WORDLIST_LANGUAGE__JAPANESE = "jp"
    WORDLIST_LANGUAGE__KOREAN = "kr"
    WORDLIST_LANGUAGE__PORTUGUESE = "pt"
    ALL_WORDLIST_LANGUAGES = [
        (WORDLIST_LANGUAGE__ENGLISH, "English"),
        # (WORDLIST_LANGUAGE__CHINESE_SIMPLIFIED, "简体中文"),
        # (WORDLIST_LANGUAGE__CHINESE_TRADITIONAL, "繁體中文"),
        # (WORDLIST_LANGUAGE__FRENCH, "Français"),
        # (WORDLIST_LANGUAGE__ITALIAN, "Italiano"),
        # (WORDLIST_LANGUAGE__JAPANESE, "日本語"),
        # (WORDLIST_LANGUAGE__KOREAN, "한국어"),
        # (WORDLIST_LANGUAGE__PORTUGUESE, "Português"),
    ]



class Seed:
    def __init__(self,
                 mnemonic = None,
                 passphrase = "",
                 wordlist_language_code = SeedConstants.WORDLIST_LANGUAGE__ENGLISH) -> None:
        self.wordlist_language_code = wordlist_language_code

        # The setters trigger a _generate_seed() call so we have to get the order right.
        self._passphrase = ""

        # First set the mnemonic go through its setter's filtering
        self.mnemonic = mnemonic

        if passphrase:
            # Now run the passphrase's setter filter to change the final seed
            self.passphrase = passphrase


    @staticmethod
    def get_wordlist(wordlist_language_code: str = SeedConstants.WORDLIST_LANGUAGE__ENGLISH):
        # TODO: Support other bip-39 wordlist languages!
        if wordlist_language_code == SeedConstants.WORDLIST_LANGUAGE__ENGLISH:
            return bip39.WORDLIST
        else:
            raise Exception(f"Unrecognized wordlist_language_code {wordlist_language_code}")


    def _generate_seed(self) -> bool:
        try:
            self.seed = bip39.mnemonic_to_seed(self.mnemonic, password=self.passphrase, wordlist=self.wordlist)
            return True
        except Exception as e:
            print(repr(e))
            return False


    @property
    def mnemonic(self) -> str:
        return self._mnemonic
    

    @property
    def mnemonic_list(self) -> List[str]:
        return self._mnemonic.split()
    

    @property
    def mnemonic_display(self) -> str:
        return unicodedata.normalize("NFC", self._mnemonic)
    

    @property
    def mnemonic_display_list(self) -> List[str]:
        return unicodedata.normalize("NFC", self._mnemonic).split()


    @mnemonic.setter
    def mnemonic(self, value):
        if isinstance(value, list):
            self._mnemonic = unicodedata.normalize("NFKD", " ".join(value).strip())
        elif isinstance(value, str):
            self._mnemonic = unicodedata.normalize("NFKD", value.strip())
            
        self._valid = self._generate_seed()


    @property
    def passphrase(self):
        return self._passphrase
        

    @property
    def passphrase_display(self):
        return unicodedata.normalize("NFC", self._passphrase)


    @passphrase.setter
    def passphrase(self, value):
        if isinstance(value, str):
            self._passphrase = unicodedata.normalize("NFKD", value)

        self._valid = self._generate_seed()


    @property
    def wordlist(self):
        return Seed.get_wordlist(self.wordlist_language_code)


    @wordlist.setter
    def wordlist(self, language_code: str):
        # TODO: Support other bip-39 wordlist languages!
        raise Exception("Not yet implemented!")


    def get_fingerprint(self, network: str = "main"):
        root = bip32.HDKey.from_seed(self.seed, version=NETWORKS[network]["xprv"])
        return hexlify(root.child(0).fingerprint).decode('utf-8')
        
    
    ### override operators    
    def __eq__(self, other):
        if isinstance(other, Seed):
            return self.seed == other.seed
        return False
        
    def __bool__(self):
        return self._valid