import unicodedata

from binascii import hexlify
from embit import bip39, bip32
from embit.networks import NETWORKS


class SeedConstants:
    MAINNET = "main"
    TESTNET = "test"
    
    SINGLE_SIG = "single_sig"
    MULTISIG = "multisig"

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



class Seed:
    def __init__(self, mnemonic = None, passphrase = "", wordlist=None) -> None:
        self._init_complete = False
        self._valid = False
        self.passphrase = passphrase
        self.mnemonic = mnemonic

        # TODO: Don't carry the wordlist around in each Seed instance. Just set it
        #   to a constant (e.g. WORDLIST__ENGLISH) that references the right list.
        self._wordlist = wordlist
        
        if self._wordlist == None:
            raise Exception('Wordlist Required')
        
        self._valid = self._generate_seed()
        self._init_complete = True
    
    def _generate_seed(self) -> bool:
        self.seed = None
        try:
            self.seed = bip39.mnemonic_to_seed(self.mnemonic, password=self.passphrase, wordlist=self._wordlist)
            return True
        except Exception as e:
            return False


    ### getters and setters
    
    @property
    def mnemonic(self):
        return self._mnemonic
    
    @property
    def mnemonic_list(self):
        return self._mnemonic.split()
    
    @property
    def mnemonic_display(self):
        return unicodedata.normalize("NFC", self._mnemonic)
    
    @property
    def mnemonic_display_list(self):
        return unicodedata.normalize("NFC", self._mnemonic).split()

    @mnemonic.setter
    def mnemonic(self, value):
        if isinstance(value, list):
            self._mnemonic = unicodedata.normalize("NFKD", " ".join(value).strip())
        elif isinstance(value, str):
            self._mnemonic = unicodedata.normalize("NFKD", value.strip())
            
        if self._init_complete:
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

        if self._init_complete:
            self._valid = self._generate_seed()

    @property
    def wordlist(self):
        return self._wordlist

    @wordlist.setter
    def wordlist(self, value):
        previous_wordlist = self._wordlist
        
        if isinstance(value, list):
            if len(value) == 2048:
                self._wordlist = value
            else:
                raise Exception('Invalid Wordlist')
        else:
            raise Exception('Wordlist Must be List Type')
        
        if self.mnemonic != None:
            # if has mnemonic, convert to new wordlist
            previous_mnemonic_str = self._mnemonic
            previous_mnemonic_list = previous_mnemonic_str.split()
            new_mnemonic_list = []
            for word in previous_mnemonic_list:
                idx = previous_wordlist.index(word)
                new_mnemonic_list.append(self._wordlist[idx])
            
            self._mnemonic = " ".join(new_mnemonic_list)

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