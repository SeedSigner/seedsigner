# External Dependencies
from embit import bip39, bip32
import unicodedata

from seedsigner.models.settings import Settings 

class Seed:

	def __init__(self, mnemonic = None, passphrase = "", wordlist=None) -> None:
		self._init_complete = False
		self._valid = False
		self.passphrase = passphrase
		self.mnemonic = mnemonic
		if wordlist == None:
			self._wordlist = Settings.get_instance().wordlist
		else:
			self._wordlist = wordlist
		
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

	### override operators
	
	def __eq__(self, other):
		if isinstance(other, Seed):
			return self.seed == other.seed
		return False
		
	def __bool__(self):
		return self._valid