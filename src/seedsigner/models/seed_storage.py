# External Dependencies
from seedsigner.models import Seed


class SeedStorage:

	def __init__(self) -> None:
		self.seeds = []
		self.pending_seed = None
		
		# to be removed once the concepts of slots is removed
		# this is a list of 3 indexes to the actual seed/mnemonic/passphrase data
		# -1 means the slot is empty
		self.slots = [-1,-1,-1]

	def set_pending_seed(self, seed: Seed):
		self.pending_seed = seed

	def get_pending_seed(self) -> Seed:
		return self.pending_seed
	
	# only adds a seed if it's valid and does not already exist
	def add_mnemonic(self, mnemonic, passphrase: str = "", slot_num = -1) -> bool:
		self.seeds.append(Seed(mnemonic, passphrase))

		# used to track virtual slot number, TODO: remove concept in UI of slots
		if slot_num > 0:
			self.slots[slot_num - 1] = len(self.seeds) - 1
			
	def add_seed(self, seed: Seed, slot_num = -1):
		self.seeds.append(seed)
		
		# used to track virtual slot number, TODO: remove concept in UI of slots
		if slot_num > 0:
			self.slots[slot_num - 1] = len(self.seeds) - 1
			
	def add_passphrase_to_seed(self, seed, passphrase: str = ""):
		if not isinstance(passphrase, str):
			raise ValueError("Invalid passphrase format")
		
		# find existing seed to add passphrase to
		if seed in self.seeds:
			idx = self.seeds.index(seed)
			seed.passphrase = passphrase
			return True
		else:
			return False
		
	def remove_passphrase_from_seed(self, seed):
		return self.add_passphrase_to_seed(seed, "")
	
	# validates mnemonic part of a seed in list or string format
	def validate_mnemonic(self, seed_phrase) -> bool:
		try:
			seed = Seed(seed_phrase)
		except Exception as e:
			return False
		
		return True
		
	def seed_count(self):
		return len(self.seeds)

	#
	# Slot related methods to be removed once the concepts of slots is removed
	# TODO: remove concept in UI of slots
	#
	
	def get_mnemonic_from_slot(self, slot_num = 0):
		if self.slots[slot_num - 1] == -1:
			raise ValueError("Slot is unexpectedly empty")
			
		return self.seeds[self.slots[slot_num - 1]].mnemonic

	def get_passphrase_from_slot(self, slot_num = 0):
		if self.slots[slot_num - 1] == -1:
			raise ValueError("Slot is unexpectedly empty")
			
		return self.seeds[self.slots[slot_num - 1]].passphrase
		
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
			if self.seeds[self.slots[slot_num-1]].passphrase != "":
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
		if self.slots[1] == -1:
			count += 1
		if self.slots[2] == -1:
			count += 1

		return count

	def save_seed_phrase(self, seed_phrase = [], slot_num = 0) -> bool:
		return self.add_mnemonic(seed_phrase,slot_num=slot_num)

	def save_passphrase(self, passphrase, slot_num = 0) -> bool:
		return self.add_passphrase_to_slot(passphrase, slot_num=slot_num)

	def get_seed_phrase(self, slot_num) -> []:
		if self.slots[slot_num - 1] == -1:
			return []

		return self.seeds[self.slots[slot_num - 1]].mnemonic.split()

	def get_passphrase(self, slot_num) -> str:
		if self.slots[slot_num - 1] == -1:
			return ""

		return self.seeds[self.slots[slot_num - 1]].passphrase

	def get_seed(self, slot_num) -> Seed:
		if self.slots[slot_num - 1] == -1:
			return Seed()

		return self.seeds[self.slots[slot_num - 1]]

	def delete_passphrase(self, slot_num) -> bool:
		if self.slots[slot_num - 1] == -1:
			return False

		return self.remove_passphrase_from_seed(self.seeds[self.slots[slot_num - 1]])

	def check_if_seed_valid(self, seed_phrase) -> bool:
		return self.validate_mnemonic(seed_phrase)
	