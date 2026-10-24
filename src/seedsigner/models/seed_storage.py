from typing import List
from seedsigner.models.seed import Seed, ElectrumSeed, ShamirSeed, InvalidSeedException, IncompleteShamirShareSetException, DuplicateShamirShareException
from seedsigner.models.settings_definition import SettingsConstants


# TODO: Hide type-specific "pending" logic behind a small hierarchy (PendingSeed, PendingElectrumSeed, PendingShamirSeed)
# to encapsulate the build-and-validate process per seed type and simplify SeedStorage.
class SeedStorage:
    def __init__(self) -> None:
        # TODO: Consider modernizing type hints to use built-in `list[...]` (Python 3.9+)
        self.seeds: List[Seed] = []
        self.pending_seed: Seed = None
        self._pending_mnemonic: List[str] = []
        self._pending_is_electrum : bool = False
        self._pending_shamir_share_set: List[str] = []
        self._pending_shamir_num_words: int = None  # Track word count for consistency


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

    
    # Shamir shares

    def init_pending_shamir_share_set(self, num_words: int = 20):
        self._pending_mnemonic = [None] * num_words
        self._pending_shamir_share_set = []  # Start with empty list instead of fixed size
        self._pending_shamir_num_words = num_words
        self._pending_is_electrum = False


    def add_pending_shamir_share(self):
        """
        Add the current pending mnemonic as a new share in the share set.
        """
        if self._pending_mnemonic and None not in self._pending_mnemonic:
            from embit import slip39

            new_share = slip39.Share.parse(" ".join(self._pending_mnemonic))
            for words in self._pending_shamir_share_set:
                share = slip39.Share.parse(" ".join(words))
                if (share.id, share.group_index, share.member_index) == (
                    new_share.id, new_share.group_index, new_share.member_index
                ):
                    raise DuplicateShamirShareException("Share already entered")

            # Copy the current mnemonic as a completed share
            self._pending_shamir_share_set.append(list(self._pending_mnemonic))
            # Reset the pending mnemonic for the next share
            self.discard_pending_mnemonic()
            self.init_pending_mnemonic(self._pending_shamir_num_words)


    def update_pending_shamir_share_set(self, index: int):
        """
        Replaces the nth share in the pending shamir share.

        * may specify a negative `index` (e.g. -1 is the last word).
        """
        if index >= len(self._pending_shamir_share_set):
            raise Exception(f"Share index {index} is too high")
        self._pending_shamir_share_set[index] = self._pending_mnemonic    
        if index < len(self._pending_shamir_share_set) - 1:
            self.discard_pending_mnemonic()
            self.init_pending_mnemonic(self._pending_shamir_num_words)


    def get_pending_shamir_share_set_share(self, index: int) -> List[str]:
        if index < len(self._pending_shamir_share_set):
            return self._pending_shamir_share_set[index]
        return None
    
    @property
    def pending_shamir_share_set_length(self) -> int:
        return len(self._pending_shamir_share_set)

    @property
    def pending_shamir_num_words(self) -> int:
        return self._pending_shamir_num_words

    def discard_pending_shamir_share_set(self):
        self._pending_shamir_share_set = []
        self._pending_shamir_num_words = None

    def get_pending_shamir_progress(self) -> dict:
        """Return recovery progress using both SLIP-39 threshold levels."""
        if not self._pending_shamir_share_set:
            return {
                "group_threshold": None,
                "completed_groups": 0,
                "shares_entered": 0,
                "shares_remaining": None,
                "current_group_index": None,
                "current_group_shares": 0,
                "current_group_threshold": None,
            }

        from embit import slip39

        shares = [
            slip39.Share.parse(" ".join(words))
            for words in self._pending_shamir_share_set
        ]
        group_threshold = shares[0].group_threshold
        group_counts = {}
        group_member_thresholds = {}
        for share in shares:
            group_counts[share.group_index] = group_counts.get(share.group_index, 0) + 1
            group_member_thresholds[share.group_index] = share.member_threshold

        completed_groups = sum(
            count >= group_member_thresholds[index]
            for index, count in group_counts.items()
        )
        current_group_index = shares[-1].group_index
        current_group_threshold = group_member_thresholds[current_group_index]
        current_group_shares = min(
            group_counts[current_group_index], current_group_threshold
        )

        shares_remaining = None
        if group_threshold == 1 and len(group_counts) == 1:
            shares_remaining = max(current_group_threshold - current_group_shares, 0)

        return {
            "group_threshold": group_threshold,
            "completed_groups": completed_groups,
            "shares_entered": len(shares),
            "shares_remaining": shares_remaining,
            "current_group_index": current_group_index,
            "current_group_shares": current_group_shares,
            "current_group_threshold": current_group_threshold,
        }


    def can_finalize_pending_shamir_share_set(self, passphrase: str = "") -> bool:
        """Return True if the current share set can reconstruct a Shamir seed."""
        if not self._pending_shamir_share_set:
            return False
        
        try:
            ShamirSeed(self._pending_shamir_share_set, passphrase)
        except IncompleteShamirShareSetException:
            return False

        return True

    def convert_pending_shamir_share_set_to_pending_seed(self, passphrase: str = '', finalize: bool = True):
        self.pending_seed = ShamirSeed(self._pending_shamir_share_set, passphrase)
        self.pending_seed.set_passphrase(passphrase)
        if finalize:
            self.discard_pending_mnemonic()
            self.discard_pending_shamir_share_set()
