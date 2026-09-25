from typing import List
from seedsigner.models.seed import Seed, ElectrumSeed, InvalidSeedException
from seedsigner.models.settings_definition import SettingsConstants



class SeedStorage:
    def __init__(self) -> None:
        self.seeds: List[Seed] = []
        self.pending_seed: Seed = None
        self._pending_mnemonic: List[str] = []
        self._pending_is_electrum : bool = False
        self.rebuild_seedxor_parts: List[Seed] = []
        self.rebuild_seedxor_combined_seed: Seed = None


    def set_pending_seed(self, seed: Seed):
        self.pending_seed = seed


    def get_pending_seed(self) -> Seed:
        return self.pending_seed


    def finalize_pending_seed(self) -> Seed:
        # Store the pending seed and return it
        seed = self.pending_seed
        if seed not in self.seeds:
            self.seeds.append(seed)
        self.pending_seed = None
        return seed


    def clear_pending_seed(self):
        self.pending_seed = None


    def add_rebuild_seedxor_part(self, seed: Seed):
        self.rebuild_seedxor_parts.append(seed)
        self.clear_rebuild_seedxor_combined_seed()


    def clear_rebuild_seedxor_combined_seed(self):
        # Finalize stores the combined seed in both fields. Clear only this
        # flow's pending seed, never an equal-but-distinct seed from elsewhere.
        if self.pending_seed is self.rebuild_seedxor_combined_seed:
            self.clear_pending_seed()
        self.rebuild_seedxor_combined_seed = None


    def clear_rebuild_seedxor_data(self):
        self.clear_rebuild_seedxor_combined_seed()
        self.rebuild_seedxor_parts = []


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


    @property
    def pending_mnemonic_length(self) -> int:
        return len(self._pending_mnemonic)


    def init_pending_mnemonic(self, num_words:int = 12, is_electrum:bool = False):
        self._pending_mnemonic = [None] * num_words
        self._pending_is_electrum = is_electrum


    def update_pending_mnemonic(self, word: str, index: int):
        """
        Replaces the nth word in the pending mnemonic.

        * may specify a negative `index` (e.g. -1 is the last word).
        """
        if index >= len(self._pending_mnemonic):
            raise Exception(f"index {index} is too high")
        self._pending_mnemonic[index] = word
    

    def get_pending_mnemonic_word(self, index: int) -> str:
        if index < len(self._pending_mnemonic):
            return self._pending_mnemonic[index]
        return None
    

    def get_pending_mnemonic_fingerprint(self, network: str = SettingsConstants.MAINNET) -> str:
        try:
            if self._pending_is_electrum:
                seed = ElectrumSeed(self._pending_mnemonic)
            else:
                seed = Seed(self._pending_mnemonic)
            return seed.get_fingerprint(network)
        except InvalidSeedException:
            return None


    def convert_pending_mnemonic_to_pending_seed(self):
        if self._pending_is_electrum:
            self.pending_seed = ElectrumSeed(self._pending_mnemonic)
        else:
            self.pending_seed = Seed(self._pending_mnemonic)
        self.discard_pending_mnemonic()
    

    def discard_pending_mnemonic(self):
        self._pending_mnemonic = []
        self._pending_is_electrum = False
