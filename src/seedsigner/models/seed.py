import logging
import unicodedata
import hashlib
import hmac

from binascii import hexlify
from embit import bip39, bip32, bip85, ec
from embit.networks import NETWORKS
from typing import List, NamedTuple

from seedsigner.models.settings import SettingsConstants

logger = logging.getLogger(__name__)


class InvalidSeedException(Exception):
    pass


class SilentPaymentKeys(NamedTuple):
    """This seed's BIP-352 (scan_privkey, spend_pubkey) pair."""
    scan_privkey: ec.PrivateKey
    spend_pubkey: ec.PublicKey



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


    def _root(self, network: str = SettingsConstants.MAINNET) -> bip32.HDKey:
        """This seed's BIP-32 master key for `network`."""
        return bip32.HDKey.from_seed(self.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(network)]["xprv"])


    def get_fingerprint(self, network: str = SettingsConstants.MAINNET) -> str:
        return hexlify(self._root(network).child(0).fingerprint).decode('utf-8')


    def get_xpub(self, wallet_path: str = '/', network: str = SettingsConstants.MAINNET):
        # Import here to avoid slow startup times; takes 1.35s to import the first time
        from seedsigner.helpers import embit_utils
        return embit_utils.get_xpub(seed_bytes=self.seed_bytes, derivation_path=wallet_path, embit_network=SettingsConstants.map_network_to_embit(network))


    def get_bip85_child_mnemonic(self, bip85_index: int, bip85_num_words: int, network: str = SettingsConstants.MAINNET):
        """Derives the seed's nth BIP-85 child mnemonic"""
        root = self._root(network)

        # TODO: Support other BIP-39 wordlist languages!
        return bip85.derive_mnemonic(root, bip85_num_words, bip85_index)
        

    def get_bip352_wallet_derivation_path(self, network: str = SettingsConstants.MAINNET, account: int = 0) -> str:
        coin_type = 0 if network == SettingsConstants.MAINNET else 1
        return f"m/352'/{coin_type}'/{account}'"


    def get_bip352_scan_spend_keys(self, network: str = SettingsConstants.MAINNET, root: bip32.HDKey = None, account: int = 0) -> SilentPaymentKeys:
        """This seed's BIP-352 (scan_privkey, spend_pubkey) — the single derivation
        entry point; used to build the address/descriptor and to spot SP outputs
        that come back to us (change / self-transfer)."""
        root = root or self._root(network)
        # Derive the shared m/352'/coin'/account' prefix once, not per key
        wallet = root.derive(self.get_bip352_wallet_derivation_path(network, account))
        scan_privkey = wallet.derive("1h/0").key
        spend_pubkey = wallet.derive("0h/0").to_public().key
        return SilentPaymentKeys(scan_privkey, spend_pubkey)


    def generate_bip352_silent_payment_address(self, network: str = SettingsConstants.MAINNET, account: int = 0) -> str:
        from embit.silent_payments.sp import generate_silent_payment_address
        scan_privkey, spend_pubkey = self.get_bip352_scan_spend_keys(network, account=account)
        return generate_silent_payment_address(scan_privkey, spend_pubkey, network=SettingsConstants.map_network_to_embit(network))


    def generate_bip352_sp_descriptor(self, network: str = SettingsConstants.MAINNET, account: int = 0) -> str:
        from embit.descriptor.sp import SPScanKey, SilentPaymentDescriptor
        from embit.descriptor.arguments import KeyOrigin
        root = self._root(network)
        scan_privkey, spend_pubkey = self.get_bip352_scan_spend_keys(network, root=root, account=account)
        origin = KeyOrigin(root.my_fingerprint, bip32.parse_path(self.get_bip352_wallet_derivation_path(network, account)))
        # The spscan HRP only has a mainnet and a testnet form; embit maps "regtest" to
        # the mainnet HRP, so collapse it here the way the sp address encoder does.
        # BIP-352 doesn't define a regtest HRP, so this is the best we can do for now.
        sp_network = "main" if network == SettingsConstants.MAINNET else "test"
        sp_key = SPScanKey(scan_privkey, spend_pubkey, origin=origin, network=sp_network)
        return str(SilentPaymentDescriptor(sp_key))


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
