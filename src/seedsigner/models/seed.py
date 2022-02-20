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



class InvalidSeedException(Exception):
    pass



class Seed:
    def __init__(self,
                 mnemonic: List[str] = None,
                 passphrase: str = "",
                 wordlist_language_code: str = SeedConstants.WORDLIST_LANGUAGE__ENGLISH) -> None:
        self.wordlist_language_code = wordlist_language_code

        if not mnemonic:
            raise Exception("Must initialize a Seed with a mnemonic List[str]")
        self._mnemonic: List[str] = unicodedata.normalize("NFKD", " ".join(mnemonic).strip()).split()

        self._passphrase: str = ""
        self.set_passphrase(passphrase, regenerate_seed=False)

        self.seed_bytes: bytes = None
        self._generate_seed()


    @staticmethod
    def get_wordlist(wordlist_language_code: str = SeedConstants.WORDLIST_LANGUAGE__ENGLISH) -> List[str]:
        # TODO: Support other bip-39 wordlist languages!
        if wordlist_language_code == SeedConstants.WORDLIST_LANGUAGE__ENGLISH:
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


    def get_fingerprint(self, network: str = SeedConstants.MAINNET) -> str:
        root = bip32.HDKey.from_seed(self.seed_bytes, version=NETWORKS[network]["xprv"])
        return hexlify(root.child(0).fingerprint).decode('utf-8')
        
    
    ### override operators    
    def __eq__(self, other):
        if isinstance(other, Seed):
            return self.seed_bytes == other.seed_bytes
        return False
