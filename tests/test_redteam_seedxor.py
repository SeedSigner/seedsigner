"""Red-team regression tests for the SeedXOR rebuild flow.

Covers F1: resume_main_flow leaks that misrouted later normal seed loads
into the SeedXOR fingerprint view.
Covers F2: DISCARD_PARTS must delete parts by identity, never a pre-existing
user seed that merely shares a mnemonic with a typed/scanned part.
Covers F3: cancellation and part changes clear only the flow's pending
combined seed, preserving unrelated pending seeds and finalized seeds.
"""
import pytest

from base import FlowTest, FlowStep
from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.views.view import MainMenuView, ErrorView
from seedsigner.views import seed_views, scan_views
from seedsigner.views.seed_views import SeedsMenuView, SeedFinalizeView

from seedxor_test_vectors import EXAMPLE_12_A, EXAMPLE_12_B


def type_mnemonic(mnemonic: str):
    return [FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=w) for w in mnemonic.split()]


class TestResumeFlowLeak(FlowTest):
    def test_back_out_of_word0_then_normal_seed_load_not_misrouted(self):
        """Start SeedXOR typed entry, BACK out at word 0, back out to
        LoadSeedView, then type a normal seed -> must route to SeedFinalizeView,
        NOT RebuildSeedXORShowFingerprintView."""
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, is_redirect=True),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.REBUILD_SEED_XOR),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
            FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORLoadPartView),  # back-landing
        ]
        self.run_sequence(sequence)

        sequence = [
            FlowStep(seed_views.RebuildSeedXORLoadPartView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORManageView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_A)
        # Fixed behavior: normal seed load routes to SeedFinalizeView.
        sequence += [FlowStep(seed_views.SeedFinalizeView)]
        self.run_sequence(sequence)

    def test_scan_rejected_part_then_normal_seed_load_not_misrouted(self):
        """Scan a valid-but-rejected XOR part (duplicate). After the ErrorView,
        resume_main_flow must be cleared; a later normal seed load routes to
        SeedFinalizeView."""
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)

        # Load part 1 normally (typed)
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, is_redirect=True),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.REBUILD_SEED_XOR),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_A)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ]
        self.run_sequence(sequence)

        # Scan the SAME part again (duplicate -> rejected)
        def load_seed_qr(view: scan_views.ScanView):
            from seedsigner.models.seed import Seed
            wordlist = Seed.get_wordlist()
            indexes = [wordlist.index(word) for word in EXAMPLE_12_A.split()]
            numeric = "".join([str(i).zfill(4) for i in indexes])
            view.decoder.add_data(numeric)

        sequence = [
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.SCAN_PART),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_qr),
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(ErrorView, button_data_selection=0),   # duplicate part error
            FlowStep(seed_views.RebuildSeedXORLoadPartView),
        ]
        self.run_sequence(sequence)
        assert self.controller.resume_main_flow is None, "resume_main_flow must be cleared after validation error"

        # Back all the way out to LoadSeedView, then type a NORMAL new seed
        sequence = [
            FlowStep(seed_views.RebuildSeedXORLoadPartView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORManageView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_B)
        # Fixed behavior: normal seed load routes to SeedFinalizeView.
        sequence += [FlowStep(seed_views.SeedFinalizeView)]
        self.run_sequence(sequence)


class TestDiscardPartsByIdentity(FlowTest):
    """F2 regression: DISCARD_PARTS must not delete a pre-existing user seed
    that merely shares a mnemonic with a typed/scanned part."""

    def test_typed_duplicate_of_preexisting_seed_survives_discard(self):
        """Pre-load Seed(A) into storage. In the XOR flow, TYPE mnemonic A as
        part 1 (a DISTINCT object equal by value), B as part 2. FINALIZE ->
        DISCARD_PARTS. The pre-existing seed must survive; only the combined
        seed is added alongside it."""
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)
        preexisting = Seed(mnemonic=EXAMPLE_12_A.split())
        self.controller.storage.seeds.append(preexisting)

        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, button_data_selection=SeedsMenuView.LOAD),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.REBUILD_SEED_XOR),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_A)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_B)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.FINALIZE),
            FlowStep(seed_views.RebuildSeedXORFinalizeView, button_data_selection=0),
            FlowStep(seed_views.RebuildSeedXORFinalizeOptionsView,
                     button_data_selection=seed_views.RebuildSeedXORFinalizeOptionsView.DISCARD_PARTS),
            FlowStep(seed_views.SeedOptionsView),
        ]
        self.run_sequence(sequence)

        seeds = self.controller.storage.seeds
        assert any(s is preexisting for s in seeds), \
            "F2 regression: pre-existing seed deleted by DISCARD_PARTS"
        assert len(seeds) == 2, \
            f"expected pre-existing + combined seed, got {len(seeds)}"
        assert len(self.controller.storage.rebuild_seedxor_parts) == 0

    def test_use_loaded_seed_part_is_discarded(self):
        """A part loaded via 'Use loaded seed' IS the same object in storage,
        so DISCARD_PARTS legitimately removes it (user chose to consume it as
        a part). Combined seed survives; the other typed part never touches
        storage."""
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)
        preexisting = Seed(mnemonic=EXAMPLE_12_A.split())
        self.controller.storage.seeds.append(preexisting)

        # Part 1 via "Use loaded seed"
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(SeedsMenuView, button_data_selection=SeedsMenuView.LOAD),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.REBUILD_SEED_XOR),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.USE_LOADED_SEED),
            FlowStep(seed_views.RebuildSeedXORSelectExistingSeedView, screen_return_value=0),
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.LOAD_NEXT_PART),
            FlowStep(seed_views.RebuildSeedXORLoadPartView, button_data_selection=seed_views.RebuildSeedXORLoadPartView.TYPE_12WORD),
        ]
        sequence += type_mnemonic(EXAMPLE_12_B)
        sequence += [
            FlowStep(seed_views.RebuildSeedXORShowFingerprintView, button_data_selection=seed_views.RebuildSeedXORShowFingerprintView.CONTINUE),
            FlowStep(seed_views.RebuildSeedXORManageView, button_data_selection=seed_views.RebuildSeedXORManageView.FINALIZE),
            FlowStep(seed_views.RebuildSeedXORFinalizeView, button_data_selection=0),
            FlowStep(seed_views.RebuildSeedXORFinalizeOptionsView,
                     button_data_selection=seed_views.RebuildSeedXORFinalizeOptionsView.DISCARD_PARTS),
            FlowStep(seed_views.SeedOptionsView),
        ]
        self.run_sequence(sequence)

        seeds = self.controller.storage.seeds
        assert not any(s is preexisting for s in seeds), \
            "the 'Use loaded seed' part should have been discarded from storage"
        assert len(seeds) == 1, "only the combined seed should remain"

    def test_discard_seed_by_identity_only(self):
        """controller.discard_seed() must not remove an equal-but-distinct seed."""
        a = Seed(mnemonic=EXAMPLE_12_A.split())
        b = Seed(mnemonic=EXAMPLE_12_A.split())
        assert a == b and a is not b
        self.controller.storage.seeds.append(a)
        self.controller.discard_seed(b)
        assert a in self.controller.storage.seeds, \
            "discard_seed deleted an equal-but-distinct seed"
        self.controller.discard_seed(a)
        assert len(self.controller.storage.seeds) == 0
        # no-op on a seed not in storage
        self.controller.discard_seed(Seed(mnemonic=EXAMPLE_12_B.split()))


class TestCancelCombinedSeedCleanup(FlowTest):
    """F3: canceling a rebuild must not leave its combined seed pending."""

    @pytest.mark.parametrize("cleanup", ["cancel", "add", "remove"])
    @pytest.mark.parametrize("pending_kind", ["equal_distinct", "different", "none"])
    def test_cleanup_preserves_unrelated_pending_seed(self, cleanup, pending_kind):
        storage = self.controller.storage
        combined = Seed(mnemonic=EXAMPLE_12_A.split())
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_B.split()))
        storage.rebuild_seedxor_combined_seed = combined
        pending = None
        if pending_kind == "equal_distinct":
            pending = Seed(mnemonic=EXAMPLE_12_A.split())
            assert pending == combined and pending is not combined
        elif pending_kind == "different":
            pending = Seed(mnemonic=EXAMPLE_12_B.split())
        storage.set_pending_seed(pending)

        if cleanup == "cancel":
            self.run_sequence([
                FlowStep(seed_views.RebuildSeedXORCancelView,
                         button_data_selection=seed_views.RebuildSeedXORCancelView.CONFIRM),
                FlowStep(seed_views.LoadSeedView),
            ])
        elif cleanup == "add":
            storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_A.split()))
        else:
            self.controller.remove_rebuild_seedxor_part(0)

        assert storage.rebuild_seedxor_combined_seed is None
        assert storage.get_pending_seed() is pending

    @pytest.mark.parametrize("choice", [0, RET_CODE__BACK_BUTTON])
    def test_declining_cancel_preserves_combined_seed(self, choice):
        storage = self.controller.storage
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_A.split()))
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_B.split()))
        finalize = seed_views.RebuildSeedXORFinalizeView()
        assert finalize.error is None
        combined = storage.get_pending_seed()
        assert combined is not None

        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORCancelView, screen_return_value=choice),
            FlowStep(seed_views.RebuildSeedXORManageView),
        ])

        assert storage.get_pending_seed() is combined
        assert storage.rebuild_seedxor_combined_seed is combined
        assert len(storage.rebuild_seedxor_parts) == 2

    def test_cleanup_preserves_finalized_seed(self):
        storage = self.controller.storage
        combined = Seed(mnemonic=EXAMPLE_12_A.split())
        storage.rebuild_seedxor_combined_seed = combined
        storage.set_pending_seed(combined)
        storage.finalize_pending_seed()

        self.controller.clear_rebuild_seedxor_data()
        self.controller.clear_rebuild_seedxor_data()  # Idempotent cleanup.

        assert len(storage.seeds) == 1
        assert storage.seeds[0] is combined
        assert storage.get_pending_seed() is None
        assert storage.rebuild_seedxor_combined_seed is None

    def test_cancel_after_finalize_clears_pending_combined_seed(self):
        self.settings.set_value(SettingsConstants.SETTING__SEED_XOR, SettingsConstants.OPTION__ENABLED)
        storage = self.controller.storage
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_A.split()))
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_B.split()))

        def check_combined_is_pending(view):
            assert view.error is None
            assert storage.rebuild_seedxor_combined_seed is not None
            assert storage.get_pending_seed() is storage.rebuild_seedxor_combined_seed

        self.run_sequence([
            FlowStep(seed_views.RebuildSeedXORFinalizeView,
                     before_run=check_combined_is_pending,
                     screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.RebuildSeedXORManageView,
                     button_data_selection=seed_views.RebuildSeedXORManageView.CANCEL),
            FlowStep(seed_views.RebuildSeedXORCancelView,
                     button_data_selection=seed_views.RebuildSeedXORCancelView.CONFIRM),
            FlowStep(seed_views.LoadSeedView),
        ])

        assert storage.rebuild_seedxor_parts == []
        assert storage.rebuild_seedxor_combined_seed is None
        assert storage.get_pending_seed() is None
        assert storage.seeds == []

    def test_add_part_after_finalize_clears_pending_combined_seed(self):
        storage = self.controller.storage
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_A.split()))
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_B.split()))
        finalize = seed_views.RebuildSeedXORFinalizeView()
        assert finalize.error is None
        combined = storage.get_pending_seed()
        assert combined is not None

        # Exercise storage invalidation directly; validation belongs to controller.
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_A.split()))

        assert len(storage.rebuild_seedxor_parts) == 3
        assert storage.rebuild_seedxor_combined_seed is None
        assert storage.get_pending_seed() is None

    def test_remove_part_after_finalize_clears_pending_combined_seed(self):
        storage = self.controller.storage
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_A.split()))
        storage.add_rebuild_seedxor_part(Seed(mnemonic=EXAMPLE_12_B.split()))
        finalize = seed_views.RebuildSeedXORFinalizeView()
        assert finalize.error is None
        assert storage.get_pending_seed() is storage.rebuild_seedxor_combined_seed
        assert storage.get_pending_seed() is not None

        self.controller.remove_rebuild_seedxor_part(0)

        assert len(storage.rebuild_seedxor_parts) == 1
        assert storage.rebuild_seedxor_combined_seed is None
        assert storage.get_pending_seed() is None
