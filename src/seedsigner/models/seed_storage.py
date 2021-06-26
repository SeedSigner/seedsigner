# External Dependencies
from embit.bip39 import mnemonic_to_bytes, mnemonic_from_bytes
from embit import bip39

class SeedStorage:

    SEEDWORDS = bip39.WORDLIST

    def __init__(self) -> None:

        self.saved_seeds = [[],[],[]]

    ###
    ### Seed Related Methods
    ###

    def save_seed_phrase(self, seed_phrase = [], slot_num = 0) -> bool:
        slot_idx = slot_num - 1
        if slot_idx in (0,1,2):
            self.saved_seeds[slot_idx] = seed_phrase[:]
        else:
            return False

    def get_seed_phrase(self, slot_num) -> []:
        slot_idx = slot_num - 1
        if len(self.saved_seeds[slot_idx]) > 0:
            return self.saved_seeds[slot_idx]
        else:
            return []

    def valid_seed_structure(self, seed_phrase) -> bool:
        if isinstance(seed_phrase, list):
            if len(seed_phrase) in (12,24):
                if all(word in seed_phrase for word in SEEDWORDS):
                    return True
                else:
                    return False
            else:
                return False # Required to be 12 or 24 word seed phrase
        else:
            return False # Not list, not valid seed_phrase

    def valid_bip39_seed(self, seed_phrase) -> bool:
        if self.valid_seed_structure(seed_phrase):
            try:
                bip39.mnemonic_to_seed((" ".join(seed_phrase)).strip())
            except ValueError:
                return False
        else:
            return False

        return True

    def check_slot_1(self) -> bool:
        if len(self.saved_seeds[0]) > 0:
            return True
        else:
            return False

    def check_slot_2(self) -> bool:
        if len(self.saved_seeds[1]) > 0:
            return True
        else:
            return False

    def check_slot_3(self) -> bool:
        if len(self.saved_seeds[2]) > 0:
            return True
        else:
            return False

    def check_slot(self, slot_num) -> bool:
        if len(self.saved_seeds[slot_num-1]) > 0:
            return True
        else:
            return False

    def check_if_seed_valid(self, seed_phrase) -> bool:
        try:
            bip39.mnemonic_to_seed((" ".join(seed_phrase)).strip())
        except ValueError:
            return False

        return True

    def slot_avaliable(self) -> bool:
        if len(self.saved_seeds[0]) > 0 and len(self.saved_seeds[1]) > 0 and len(self.saved_seeds[2]) > 0:
            return False
        return True

    def num_of_saved_seeds(self) -> int:
        count = 0
        if len(self.saved_seeds[0]) > 0:
            count += 1
        if len(self.saved_seeds[1]) > 0:
            count += 1
        if len(self.saved_seeds[2]) > 0:
            count += 1

        return count

    def num_of_free_slots(self) -> int:
        count = 0
        if len(self.saved_seeds[0]) == 0:
            count += 1
        if len(self.saved_seeds[1]) == 0:
            count += 1
        if len(self.saved_seeds[2]) == 0:
            count += 1

        return count
