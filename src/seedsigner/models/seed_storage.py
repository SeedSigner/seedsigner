from typing import List
from seedsigner.models import Seed
from seedsigner.models.seed import InvalidSeedException



class SeedStorage:
    def __init__(self) -> None:
        self.seeds: List[Seed] = []
        self.pending_seed: Seed = None
        self._pending_mnemonic: List[str] = []


    def set_pending_seed(self, seed: Seed):
        self.pending_seed = seed


    def get_pending_seed(self) -> Seed:
        return self.pending_seed


    def finalize_pending_seed(self) -> int:
        # Finally store the pending seed and return its index
        if self.pending_seed in self.seeds:
            index = self.seeds.index(self.pending_seed)
        else:
            self.seeds.append(self.pending_seed)
            index = len(self.seeds) - 1
        self.pending_seed = None
        return index


    def clear_pending_seed(self):
        self.pending_seed = None


    def validate_mnemonic(self, mnemonic: List[str]) -> bool:
        try:
            Seed(mnemonic=mnemonic)
        except InvalidSeedException as e:
            return False
        
        return True


    def num_seeds(self):
        return len(self.seeds)
    

    @property
    def pending_mnemonic(self) -> List[str]:
        # Always return a copy so that the internal List can't be altered
        return list(self._pending_mnemonic)
    

    def append_to_pending_mnemonic(self, word: str):
        self._pending_mnemonic.append(word)
    

    def update_pending_mnemonic(self, word: str, index: int):
        if len(self._pending_mnemonic) == index:
            # We're adding to the end
            self._pending_mnemonic.append(word)

        elif len(self._pending_mnemonic) > index:
            # We're replacing an existing value
            self._pending_mnemonic[index] = word

        else:
            raise Exception(f"index {index} is too high")
    

    def get_pending_mnemonic_word(self, index: int) -> str:
        if index < len(self._pending_mnemonic):
            return self._pending_mnemonic[index]
        return None


    def convert_pending_mnemonic_to_pending_seed(self):
        self.pending_seed = Seed(self._pending_mnemonic)
        self.discard_pending_mnemonic()
    

    def discard_pending_mnemonic(self):
        self._pending_mnemonic = []
