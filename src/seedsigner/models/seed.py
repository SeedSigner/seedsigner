import unicodedata

from binascii import hexlify
from embit import bip39, bip32
from embit.networks import NETWORKS
from typing import List


class SeedConstants:
    MAINNET = ("main", "Mainnet")
    TESTNET = ("test", "Testnet")
    REGTEST = ("regtest", "Regtest")
    ALL_NETWORKS = [MAINNET, TESTNET, REGTEST]
    
    SINGLE_SIG = "single_sig"
    MULTISIG = "multisig"
    ALL_SIG_TYPES = [
        SINGLE_SIG,
        MULTISIG,
    ]

    NATIVE_SEGWIT = "native_segwit"
    NESTED_SEGWIT = "nested_segwit"
    TAPROOT = "taproot"
    CUSTOM_DERIVATION = "custom_derivation"
    ALL_SCRIPT_TYPES = [
        {"type": NATIVE_SEGWIT, "display_name": "Native Segwit"},
        {"type": NESTED_SEGWIT, "display_name": "Nested Segwit (legacy)"},
        {"type": TAPROOT, "display_name": "Taproot"},
        {"type": CUSTOM_DERIVATION, "display_name": "Custom Derivation"},
    ]

    WORDLIST_LANGUAGE__ENGLISH = ("en", "English")
    WORDLIST_LANGUAGE__CHINESE_SIMPLIFIED = ("zh_Hans_CN", "简体中文")
    WORDLIST_LANGUAGE__CHINESE_TRADITIONAL = ("zh_Hant_TW", "繁體中文")
    WORDLIST_LANGUAGE__FRENCH = ("fr", "Français")
    WORDLIST_LANGUAGE__ITALIAN = ("it", "Italiano")
    WORDLIST_LANGUAGE__JAPANESE = ("jp", "日本語")
    WORDLIST_LANGUAGE__KOREAN = ("kr", "한국어")
    WORDLIST_LANGUAGE__PORTUGUESE = ("pt", "Português")
    ALL_WORDLIST_LANGUAGES = [
        WORDLIST_LANGUAGE__ENGLISH,
        # WORDLIST_LANGUAGE__CHINESE_SIMPLIFIED,
        # WORDLIST_LANGUAGE__CHINESE_TRADITIONAL,
        # WORDLIST_LANGUAGE__FRENCH,
        # WORDLIST_LANGUAGE__ITALIAN,
        # WORDLIST_LANGUAGE__JAPANESE,
        # WORDLIST_LANGUAGE__KOREAN,
        # WORDLIST_LANGUAGE__PORTUGUESE,
    ]



class Seed:
    def __init__(self,
                 mnemonic = None,
                 passphrase = "",
                 wordlist_language_code = SeedConstants.WORDLIST_LANGUAGE__ENGLISH[0]) -> None:
        self._mnemonic = mnemonic
        self.passphrase = passphrase
        self.wordlist_language_code = wordlist_language_code
        self._valid = self._generate_seed()


    @staticmethod
    def get_wordlist(wordlist_language_code: str = SeedConstants.WORDLIST_LANGUAGE__ENGLISH[0]):
        # TODO: Support other bip-39 wordlist languages!
        if wordlist_language_code == SeedConstants.WORDLIST_LANGUAGE__ENGLISH[0]:
            return bip39.WORDLIST


    def _generate_seed(self) -> bool:
        self.seed = None
        try:
            self.seed = bip39.mnemonic_to_seed(self._mnemonic, password=self.passphrase, wordlist=self.wordlist)
            return True
        except Exception as e:
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