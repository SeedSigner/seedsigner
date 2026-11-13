import pytest

# Must import this before the Controller
from base import BaseTest

from seedsigner.controller import Controller
from seedsigner.models.seed import BIP85ChildSeed, Seed


class TestSeedStorage(BaseTest):

    @pytest.mark.parametrize("children_specs", [
        # Format: [(parent_idx, child_idx, num_words), ...]
        [(0, 0, 12)],  # Single child for first parent
        [(0, 8, 12), (0, 1, 12), (0, 5, 12), (0, 2, 12)],  # Multiple children with different child_index values
        [(0, 2, 24), (0, 1, 12), (0, 2, 12), (0, 1, 24)],  # Multiple children with same child_index but different num_words
        [(1, 3, 24)],  # Single child for second parent only
        [(1, 5, 12), (0, 1, 12), (0, 0, 24)],  # Both parents have children
        [(1, 1, 24), (0, 3, 12), (1, 1, 12), (0, 1, 12)],  # Interleaved insertion across both parents
        [],  # No children for either parent
    ])
    def test_finalize_pending_seed(self, children_specs):
        """
        Test that finalize_pending_seed properly orders seeds in storage.

        BIP-85 child seeds should be inserted adjacent to parent, sorted by:
        1. child_index (ascending)
        2. num_words (12 before 24) when child_index is the same
        """
        storage = Controller.get_instance().storage

        # Add 2 parent seeds
        parent_mnemonics = [["abandon"] * 11 + ["about"], ["baby"] * 11 + ["away"]]
        parent_seeds = []
        for mnemonic in parent_mnemonics:
            parent_seed = Seed(mnemonic=mnemonic)
            storage.set_pending_seed(parent_seed)
            storage.finalize_pending_seed()
            parent_seeds.append(parent_seed)

        # Create and add child seeds to storage
        child_seeds = {0: {}, 1: {}}

        for parent_idx, child_idx, num_words in children_specs:
            parent_seed = parent_seeds[parent_idx]

            child_seed = BIP85ChildSeed(
                parent_seed=parent_seed,
                child_index=child_idx,
                num_words=num_words,
                mnemonic=parent_seed.get_bip85_child_mnemonic(child_idx, num_words).split(),
            )
            child_seeds[parent_idx][(child_idx, num_words)] = child_seed
            storage.set_pending_seed(child_seed)
            storage.finalize_pending_seed()

        # Build expected order: parent0, sorted children0, parent1, sorted children1
        expected_seeds = []
        for parent_idx in [0, 1]:
            expected_seeds.append(parent_seeds[parent_idx])

            # Add this parent's children sorted by (child_index, num_words)
            parent_children = sorted(child_seeds[parent_idx].keys(), key=lambda x: (x[0], x[1]))

            for child_idx, num_words in parent_children:
                expected_seeds.append(child_seeds[parent_idx][(child_idx, num_words)])

        assert storage.seeds == expected_seeds


    @pytest.mark.parametrize("child_indices", [
        [],  # No child seeds
        [0],  # Single child
        [5, 1, 10, 3],  # Four children with various indices
    ])
    def test_discard_seed(self, child_indices):
        """
        Discarding a seed should remove it from storage along with any of its BIP-85 child seeds.
        """
        storage = Controller.get_instance().storage

        # Add a seed to storage
        parent_seed = Seed(mnemonic=["abandon"] * 11 + ["about"])
        storage.seeds.append(parent_seed)

        # Add a second seed to ensure only the intended seed is removed
        storage.seeds.append(Seed(mnemonic=["baby"] * 11 + ["away"]))

        # Add child seeds to storage
        for child_index in child_indices:
            child_seed = BIP85ChildSeed(
                parent_seed=parent_seed,
                child_index=child_index,
                num_words=12,
                mnemonic=parent_seed.get_bip85_child_mnemonic(child_index, 12).split(),
            )
            storage.seeds.append(child_seed)

        storage.discard_seed(parent_seed)
        assert len(storage.seeds) == 1  # Only the second seed should remain


    def test_child_seed_is_stored_alongside_the_same_seed_loaded_directly(self):
        """
        A BIP-85 child seed and the same mnemonic loaded directly as a normal Seed are
        distinct in-memory entries; both must be stored.
        """
        storage = Controller.get_instance().storage

        parent_seed = Seed(mnemonic=["abandon"] * 11 + ["about"])
        child_mnemonic = parent_seed.get_bip85_child_mnemonic(0, 12).split()

        # Load the child's mnemonic directly as a normal seed, before the parent exists
        standalone_seed = Seed(mnemonic=child_mnemonic)
        storage.set_pending_seed(standalone_seed)
        storage.finalize_pending_seed()

        storage.set_pending_seed(parent_seed)
        storage.finalize_pending_seed()

        # Now derive + load that same seed as a BIP-85 child
        child_seed = BIP85ChildSeed(
            parent_seed=parent_seed,
            child_index=0,
            num_words=12,
            mnemonic=child_mnemonic,
        )
        storage.set_pending_seed(child_seed)
        storage.finalize_pending_seed()

        # Both representations are present, with the child adjacent to its parent
        assert storage.seeds == [standalone_seed, parent_seed, child_seed]

        # Discarding the parent removes only the child; the standalone seed survives
        storage.discard_seed(parent_seed)
        assert storage.seeds == [standalone_seed]
