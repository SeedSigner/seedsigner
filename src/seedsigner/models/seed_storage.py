# External Dependencies
from embit import bip39, bip32

class SeedStorage:

	SEEDWORDS = bip39.WORDLIST

	def __init__(self) -> None:
		self.seeds = []
		self.mnemonics = []
		self.passphrases = []
		
		# to be removed once the concepts of slots is removed
		# this is a list of 3 indexes to the actual seed/mnemonic/passphrase data
		# -1 means the slot is empty
		self.slots = [-1,-1,-1]
	
	# only adds a seed if it's valid and does not already exist
	def add_seed(self, seed_phrase, passphrase: str = "", slot_num = -1) -> bool:
		mnemonic = ""
		if isinstance(seed_phrase, list):
			mnemonic = " ".join(seed_phrase).strip()
		elif isinstance(seed_phrase, str):
			mnemonic = seed_phrase.strip()
		else:
			raise ValueError("Invalid mnemonic seed phrase format")
			
		if not isinstance(passphrase, str):
			raise ValueError("Invalid passphrase format")

		try:
			seed = bip39.mnemonic_to_seed(mnemonic, passphrase, wordlist=SeedStorage.SEEDWORDS)
			self.seeds.append(seed)
			self.mnemonics.append(mnemonic)
			self.passphrases.append(passphrase)
			
			# used to track virtual slot number, TODO: remove concept in UI of slots
			if slot_num > 0:
				self.slots[slot_num - 1] = len(self.seeds) - 1

			return True
		except Exception as e:
			return False # return false if there is an unexpected exception
			
	def delete_seed(self, seed) -> bool:
		if seed in self.seeds:
			idx = self.seeds.index(seed)
			self.seeds.pop(idx)
			self.mnemonics.pop(idx)
			self.passphrases.pop(idx)
			self.slots[self.slots.index(idx)] = -1
			return True
		else:
			return False
			
	def add_passphrase_to_seed(self, seed, passphrase: str = ""):
		if not isinstance(passphrase, str):
			raise ValueError("Invalid passphrase format")
		
		# find existing seed to add passphrase to
		if seed in self.seeds:
			idx = self.seeds.index(seed)
			new_seed = bip39.mnemonic_to_seed(self.mnemonics[idx], passphrase, wordlist=SeedStorage.SEEDWORDS)
			self.seeds[idx] = new_seed
			self.passphrases[idx] = passphrase
			return True
		else:
			return False
		
	def remove_passphrase_from_seed(self, seed):
		# find existing seed to add passphrase to
		if seed in self.seeds:
			idx = self.seeds.index(seed)
			new_seed = bip39.mnemonic_to_seed(self.mnemonics[idx], "", wordlist=SeedStorage.SEEDWORDS)
			self.seeds[idx] = new_seed
			self.passphrases[idx] = ""
			return True
		else:
			return False
	
	# validates mnemonic part of a seed in list or string format
	def validate_mnemonic(self, seed_phrase) -> bool:
		mnemonic = ""
		if isinstance(seed_phrase, list):
			mnemonic = " ".join(seed_phrase).strip()
		elif isinstance(seed_phrase, str):
			mnemonic = seed_phrase.strip()
		else:
			raise ValueError("Invalid mnemonic seed phrase format")
			
		return bip39.mnemonic_is_valid(mnemonic)

	def get_last_seed(self):
		if len(self.seeds) >= 1:
			return self.seeds[-1]
		else:
			return None

	def get_last_mnemonic(self):
		if len(self.mnemonics) >= 1:
			return self.mnemonics[-1]
		else:
			return None

	def get_last_passphrase(self):
		if len(self.passphrases) >= 1:
			return self.passphrases[-1]
		else:
			return None
		
	def seed_count(self):
		return len(self.seeds)

	#
	# Slot related methods to be removed once the concepts of slots is removed
	# TODO: remove concept in UI of slots
	#
	
	def get_mnemonic_from_slot(self, slot_num = 0):
		if self.slots[slot_num - 1] == -1:
			raise ValueError("Slot is unexpectedly empty")
			
		return self.mnemonics[self.slots[slot_num - 1]]

	def get_passphrase_from_slot(self, slot_num = 0):
		if self.slots[slot_num - 1] == -1:
			raise ValueError("Slot is unexpectedly empty")
			
		return self.passphrases[self.slots[slot_num - 1]]
		
	def add_passphrase_to_slot(self, passphrase: str = "", slot_num = -1):
		if self.slots[slot_num - 1] == -1:
			raise ValueError("Slot is unexpectedly empty")
			
		return self.add_passphrase_to_seed(self.seeds[self.slots[slot_num - 1]], passphrase)

	def remove_passphrase_from_slot(self, slot_num = -1):
		if self.slots[slot_num - 1] == -1:
			raise ValueError("Slot is unexpectedly empty")
			
		return self.remove_passphrase_from_seed(self.seeds[self.slots[slot_num - 1]])

	def get_first_seed_slot(self):
		if self.slots[0] != -1:
			return self.slots[0] + 1
		elif self.slots[1] != -1:
			return self.slots[1] + 1
		elif self.slots[2] != -1:
			return self.slots[2] + 1

	def check_slot_1(self) -> bool:
		if self.slots[0] != -1:
			return True
		else:
			return False
	
	def check_slot_2(self) -> bool:
		if self.slots[1] != -1:
			return True
		else:
			return False
	
	def check_slot_3(self) -> bool:
		if self.slots[2] != -1:
			return True
		else:
			return False

	def check_slot(self, slot_num) -> bool:
		if self.slots[slot_num-1] != -1:
			return True
		else:
			return False

	def check_slot_passphrase(self, slot_num) -> bool:
		if self.slots[slot_num-1] != -1:
			if self.passphrases[self.slots[slot_num-1]] != "":
				return True
		return False
	
	def slot_avaliable(self) -> bool:
		if self.slots[0] == -1 or self.slots[1] == -1 or self.slots[2] == -1:
			return True
		return True
		
	def num_of_saved_seeds(self) -> int:
		count = 0
		if self.slots[0] != -1:
			count += 1
		if self.slots[1] != -1:
			count += 1
		if self.slots[2] != -1:
			count += 1

		return count

	def num_of_free_slots(self) -> int:
		count = 0
		if self.slots[0] == -1:
			count += 1
		if self.slots[0] == -1:
			count += 1
		if self.slots[0] == -1:
			count += 1

		return count

	def save_seed_phrase(self, seed_phrase = [], slot_num = 0) -> bool:
		return self.add_seed(seed_phrase,slot_num=slot_num)

	def save_passphrase(self, passphrase, slot_num = 0) -> bool:
		return self.add_passphrase_to_slot(passphrase, slot_num=slot_num)

	def get_seed_phrase(self, slot_num) -> []:
		if self.slots[slot_num - 1] == -1:
			return []

		return self.mnemonics[self.slots[slot_num - 1]].split()

	def get_passphrase(self, slot_num) -> str:
		if self.slots[slot_num - 1] == -1:
			return ""

		return self.passphrases[self.slots[slot_num - 1]]

	def delete_passphrase(self, slot_num) -> bool:
		if self.slots[slot_num - 1] == -1:
			return False

		return self.remove_passphrase_from_seed(self.seeds[self.slots[slot_num - 1]])

	def check_if_seed_valid(self, seed_phrase) -> bool:
		return self.validate_mnemonic(seed_phrase)
	