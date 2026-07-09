from base import BaseTest, FlowTest, FlowStep

from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.seed import Seed
from sp_testing_util import build_sp_send_psbt, build_sp_spend_psbt, build_sp_send_psbt_realistic, build_sp_change_psbt, build_sp_send_psbt_taproot_input


SEED = Seed("obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())


def _decoder_for(psbt):
    """A completed DecodeQR whose raw bytes are the given PSBT."""
    from seedsigner.models.decode_qr import DecodeQR
    d = DecodeQR()
    d.complete = True
    d.get_data_psbt = lambda: psbt.serialize()
    return d


def _capture_screen_kwargs(view):
    """Replaces view.run_screen with a stub that records each call's kwargs
    into the returned dict and answers BACK."""
    from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
    captured = {}
    def capture(screen_cls, **kwargs):
        captured.update(kwargs)
        return RET_CODE__BACK_BUTTON
    view.run_screen = capture
    return captured


class TestSettingGatedParse(BaseTest):
    def test_get_psbt_always_preserves_sp_fields(self):
        # F11: DecodeQR.get_psbt() always parses via SilentPaymentsPSBT
        # (a drop-in superset of PSBT); the SP setting only decides how
        # ScanView routes, not how the PSBT is parsed.
        from embit.silent_payments import SilentPaymentsPSBT
        decoder = _decoder_for(build_sp_send_psbt(SEED))
        parsed = decoder.get_psbt()
        assert isinstance(parsed, SilentPaymentsPSBT)
        assert parsed.has_sp_content
        assert any(getattr(o, "sp_data", None) is not None for o in parsed.outputs)

    def test_get_psbt_non_sp_psbt_has_no_sp_content(self):
        from embit.psbt import PSBT, DerivationPath
        from embit.script import p2wpkh
        from embit.transaction import TransactionOutput
        from embit import bip32

        # A vanilla (non-SP) PSBT still parses cleanly (via SilentPaymentsPSBT,
        # a drop-in superset) and reports no SP content.
        root = bip32.HDKey.from_seed(SEED.seed_bytes)
        pub = root.derive([0, 0]).get_public_key()
        vanilla = PSBT.create_v2()
        inp = vanilla.PSBTIN_CLS()
        inp.txid = bytes([0xAA] * 32)
        inp.vout = 0
        inp.sequence = 0xFFFFFFFE
        inp.witness_utxo = TransactionOutput(value=100_000, script_pubkey=p2wpkh(pub))
        inp.bip32_derivations[pub] = DerivationPath(root.my_fingerprint, [0, 0])
        vanilla.add_input(inp)
        out = vanilla.PSBTOUT_CLS()
        out.value = 90_000
        out.script_pubkey = p2wpkh(pub)
        vanilla.add_output(out)

        decoder = _decoder_for(vanilla)
        parsed = decoder.get_psbt()
        assert not parsed.has_sp_content


class TestPSBTParserSPDetection(BaseTest):
    def _parser(self, psbt):
        from seedsigner.models.settings_definition import SettingsConstants
        return PSBTParser(psbt, seed=SEED, network=SettingsConstants.MAINNET)

    def test_send_psbt_detected_and_renders_sp_address(self):
        parser = self._parser(build_sp_send_psbt(SEED))
        assert parser.has_sp_outputs is True
        assert parser.has_sp_spend_inputs is False
        assert len(parser.destination_addresses) == 1
        assert parser.destination_addresses[0].startswith("sp1")
        assert parser.destination_is_sp == [True]

    def test_spend_psbt_detected_as_spend_input(self):
        parser = self._parser(build_sp_spend_psbt(SEED))
        assert parser.has_sp_spend_inputs is True
        assert parser.has_sp_outputs is False
        assert parser.destination_is_sp == [False]

    def test_sp_change_output_detected_as_change_not_recipient(self):
        # SP output paying back to our own SP address (m=0 change label) must be
        # detected as change, not listed as an external recipient.
        parser = self._parser(build_sp_change_psbt(SEED))
        assert parser.num_change_outputs == 1
        cd = parser.change_data[0]
        assert cd["is_sp"] is True
        assert cd["is_change"] is True
        assert cd["address"].startswith("sp1")
        assert parser.change_amount == 9_000
        # the external recipient is the only destination; SP change is excluded
        assert parser.destination_is_sp == [False]
        assert parser.spend_amount == 90_000
        assert all(not a.startswith("sp1") for a in parser.destination_addresses)


class TestSPOutputClassification(BaseTest):
    def test_classify_sp_output(self):
        from binascii import unhexlify
        from embit import ec
        from embit.silent_payments import SilentPaymentData
        from embit.silent_payments.sp import tagged_hash
        from embit.util import secp256k1
        from seedsigner.models.settings_definition import SettingsConstants
        from sp_testing_util import SCAN_HEX, SPEND_HEX

        scan_priv, spend_pub = SEED.get_bip352_scan_spend_keys(SettingsConstants.MAINNET)

        # Someone else's output entirely (scan key doesn't match ours) -> None,
        # regardless of label.
        external = SilentPaymentData(ec.PublicKey.parse(unhexlify(SCAN_HEX)), ec.PublicKey.parse(unhexlify(SPEND_HEX)))
        assert PSBTParser._classify_sp_output(external, None, scan_priv, spend_pub) is None

        # label omitted (None): raw spend key match -> "self".
        self_receive = SilentPaymentData(scan_priv.get_public_key(), spend_pub)
        assert PSBTParser._classify_sp_output(self_receive, None, scan_priv, spend_pub) == "self"

        # label == 0: m=0 change-tweaked spend key match -> "change".
        tweak = tagged_hash("BIP0352/Label", scan_priv.secret + (0).to_bytes(4, "big"))
        change_spend = ec.PublicKey(secp256k1.ec_pubkey_add(secp256k1.ec_pubkey_parse(spend_pub.sec()), tweak))
        change = SilentPaymentData(scan_priv.get_public_key(), change_spend)
        assert PSBTParser._classify_sp_output(change, 0, scan_priv, spend_pub) == "change"

        assert PSBTParser._classify_sp_output(None, None, scan_priv, spend_pub) is None

    def test_classify_sp_output_labeled_address_is_self(self):
        # label >= 1: a labeled address's tweaked spend key match -> "self"
        # (still ours, just not change -- change is specifically the m=0 label).
        from embit.silent_payments import SilentPaymentData
        from embit.silent_payments.sp import apply_label
        from seedsigner.models.settings_definition import SettingsConstants

        scan_priv, spend_pub = SEED.get_bip352_scan_spend_keys(SettingsConstants.MAINNET)

        labeled_spend = apply_label(spend_pub, scan_priv, 5)
        labeled = SilentPaymentData(scan_priv.get_public_key(), labeled_spend)
        assert PSBTParser._classify_sp_output(labeled, 5, scan_priv, spend_pub) == "self"

    def test_classify_sp_output_forged_label_is_not_ours(self):
        # label >= 1 present but the spend key does NOT match that label's
        # tweak (forged/wrong label claim) -> None; the label is never
        # trusted at face value, only the recomputed spend key match counts.
        from embit.silent_payments import SilentPaymentData
        from embit.silent_payments.sp import apply_label
        from seedsigner.models.settings_definition import SettingsConstants

        scan_priv, spend_pub = SEED.get_bip352_scan_spend_keys(SettingsConstants.MAINNET)

        labeled_spend = apply_label(spend_pub, scan_priv, 5)
        forged = SilentPaymentData(scan_priv.get_public_key(), labeled_spend)
        assert PSBTParser._classify_sp_output(forged, 6, scan_priv, spend_pub) is None


class TestSPTrim(BaseTest):
    def test_send_psbt_trim_preserves_sp_fields(self):
        from embit.silent_payments import SilentPaymentsPSBT
        from embit import bip32
        psbt = build_sp_send_psbt(SEED)
        root = bip32.HDKey.from_seed(SEED.seed_bytes)
        psbt.sign_with(root)
        trimmed = PSBTParser.trim(psbt)
        assert isinstance(trimmed, SilentPaymentsPSBT)
        assert any(getattr(o, "sp_data", None) is not None for o in trimmed.outputs)
        assert PSBTParser.sp_contribution_count(trimmed) >= 1

    def test_send_psbt_trim_strips_bulky_fields(self):
        from embit.silent_payments import SilentPaymentsPSBT
        from embit import bip32
        psbt = build_sp_send_psbt_realistic(SEED)
        assert psbt.inputs[0].non_witness_utxo is not None
        root = bip32.HDKey.from_seed(SEED.seed_bytes)
        psbt.sign_with(root)
        trimmed = PSBTParser.trim(psbt)
        assert trimmed.inputs[0].non_witness_utxo is None
        assert trimmed.inputs[0].witness_utxo is not None
        assert len(trimmed.inputs[0].bip32_derivations) == 0
        assert len(trimmed.outputs[1].bip32_derivations) == 1
        parsed = SilentPaymentsPSBT.parse(trimmed.serialize())
        assert len(parsed.sp_ecdh_shares) >= 1
        assert len(parsed.inputs[0].partial_sigs) >= 1

    def test_pure_spend_trim_stays_unfinalized(self):
        from embit import bip32
        psbt = build_sp_spend_psbt(SEED)
        root = bip32.HDKey.from_seed(SEED.seed_bytes)
        psbt.sign_with(root)
        assert psbt.inputs[0].taproot_key_sig is not None
        trimmed = PSBTParser.trim(psbt)
        # BIP-375/376: the Signer does not finalize; the sig stays in
        # taproot_key_sig and the coordinator builds the final witness.
        assert trimmed.inputs[0].final_scriptwitness is None
        assert trimmed.inputs[0].taproot_key_sig is not None
        assert PSBTParser.sp_contribution_count(trimmed) == 1

    def test_send_from_taproot_input_trim_exports_unfinalized(self):
        # The combination that regressed in krux: a finalized PSBT makes the
        # coordinator (Sparrow/drongo) take copyFinalizedFields() instead of
        # combine(), dropping the derived PSBT_OUT_SCRIPT plus the global
        # ECDH share / DLEQ proof it needs to verify and extract.
        from embit.silent_payments import SilentPaymentsPSBT
        from embit import bip32
        psbt = build_sp_send_psbt_taproot_input(SEED)
        root = bip32.HDKey.from_seed(SEED.seed_bytes)
        psbt.sign_with(root)
        # embit's sign_input_with_tapkey finalizes key-path spends at signing time
        assert psbt.inputs[0].final_scriptwitness is not None
        trimmed = PSBTParser.trim(psbt)
        parsed = SilentPaymentsPSBT.parse(trimmed.serialize())  # QR-real round trip
        assert parsed.inputs[0].final_scriptwitness is None
        assert parsed.inputs[0].final_scriptsig is None
        assert parsed.inputs[0].taproot_key_sig is not None
        out = next(o for o in parsed.outputs if getattr(o, "sp_data", None) is not None)
        assert out.script_pubkey.data[:2] == b"\x51\x20"
        assert out.script_pubkey.data != b"\x51\x20" + bytes(32)  # actually derived
        assert len(parsed.sp_ecdh_shares) == 1
        assert len(parsed.sp_dleq_proofs) == 1
        PSBTParser.validate_sp_export(parsed)

    def test_send_trim_does_not_corrupt_source_for_reentry(self):
        # F9 regression: trim() used to clear bip32_derivations on the same
        # object `psbt_parser.psbt` aliases and return it, so a back-nav +
        # re-finalize re-signed a derivation-stripped PSBT and raised "no
        # eligible input is controlled by this seed".
        from seedsigner.models.settings_definition import SettingsConstants
        from embit import bip32

        psbt = build_sp_send_psbt_realistic(SEED)
        parser = PSBTParser(psbt, seed=SEED, network=SettingsConstants.MAINNET)
        root = bip32.HDKey.from_seed(SEED.seed_bytes)

        psbt.sign_with(root)
        trimmed = PSBTParser.trim(psbt)

        assert trimmed is not parser.psbt
        assert len(parser.psbt.inputs[0].bip32_derivations) > 0

        # Simulated re-entry: PSBTFinalizeView re-signs the still-intact source PSBT.
        sig_result = parser.psbt.sign_with(root)
        assert sig_result >= 1


class TestSPFinalizeFlow(FlowTest):
    def _prime(self, psbt):
        from seedsigner.models.settings_definition import SettingsConstants
        self.controller.psbt = psbt
        self.controller.psbt_seed = SEED
        self.controller.psbt_parser = PSBTParser(psbt, seed=SEED, network=SettingsConstants.MAINNET)

    def test_spend_psbt_signs_and_reaches_signed_qr(self):
        from seedsigner.views import psbt_views
        self._prime(build_sp_spend_psbt(SEED))
        self.run_sequence([
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSignedQRDisplayView),
        ])
        assert self.controller.psbt.inputs[0].taproot_key_sig is not None
        assert self.controller.psbt.inputs[0].final_scriptwitness is None

    def test_send_psbt_signs_and_reaches_signed_qr(self):
        from seedsigner.views import psbt_views
        self._prime(build_sp_send_psbt(SEED))
        self.run_sequence([
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSignedQRDisplayView),
        ])
        assert PSBTParser.sp_contribution_count(self.controller.psbt) >= 1

    def test_sp_change_routes_through_change_details_to_signed_qr(self):
        from seedsigner.views import psbt_views
        self._prime(build_sp_change_psbt(SEED))
        # Overview -> Math -> external recipient -> SP change details -> finalize -> QR
        self.run_sequence([
            FlowStep(psbt_views.PSBTOverviewView, screen_return_value=0),
            FlowStep(psbt_views.PSBTMathView, screen_return_value=0),
            FlowStep(psbt_views.PSBTAddressDetailsView, screen_return_value=0),
            FlowStep(psbt_views.PSBTChangeDetailsView, screen_return_value=0),
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSignedQRDisplayView),
        ])
        assert PSBTParser.sp_contribution_count(self.controller.psbt) >= 1


class TestSPDisplayFlow(BaseTest):
    def test_sp_destination_address_details_title_has_no_sp_marker(self):
        from seedsigner.views import psbt_views
        from seedsigner.models.settings_definition import SettingsConstants

        parser = PSBTParser(build_sp_send_psbt(SEED), seed=SEED, network=SettingsConstants.MAINNET)
        self.controller.psbt_parser = parser
        view = psbt_views.PSBTAddressDetailsView(address_num=0)

        captured = _capture_screen_kwargs(view)
        view.run()

        # Single SP recipient: plain "Will Send", no "(SP)" marker or index.
        assert captured["title"] == "Will Send"
        # F4: PSBTParser.destination_is_sp is consumed explicitly (not sniffed
        # from the address string) so the screen can pick the right font size.
        assert captured["is_sp"] is True

    def test_sp_change_details_passes_sp_and_verified_to_screen(self):
        from seedsigner.views import psbt_views
        from seedsigner.models.settings_definition import SettingsConstants

        parser = PSBTParser(build_sp_change_psbt(SEED), seed=SEED, network=SettingsConstants.MAINNET)
        self.controller.psbt = parser.psbt
        self.controller.psbt_seed = SEED
        self.controller.psbt_parser = parser
        view = psbt_views.PSBTChangeDetailsView(change_address_num=0)

        captured = _capture_screen_kwargs(view)
        view.run()

        assert captured["is_sp"] is True
        assert captured["is_change_addr_verified"] is True
        assert captured["title"] == "Your Change"
        assert captured["address"].startswith("sp1")


class TestSPValidationGuard(FlowTest):
    # Same priming as the finalize-flow tests; the happy path itself is covered
    # there by test_send_psbt_signs_and_reaches_signed_qr.
    _prime = TestSPFinalizeFlow._prime

    def test_valid_realistic_send_reaches_signed_qr(self):
        from seedsigner.views import psbt_views
        self._prime(build_sp_send_psbt_realistic(SEED))
        self.run_sequence([
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSignedQRDisplayView),
        ])

    def test_incomplete_sp_send_routes_to_error_view(self):
        from seedsigner.views import psbt_views
        from unittest.mock import patch

        self._prime(build_sp_send_psbt(SEED))

        def mock_sign_with(root):
            from embit.silent_payments.psbt import SPValidationError
            raise SPValidationError("Simulated error")
    
        with patch.object(self.controller.psbt, "sign_with", side_effect=mock_sign_with):
            self.run_sequence([
                FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
                FlowStep(psbt_views.PSBTSPValidationErrorView, button_data_selection=psbt_views.PSBTSPValidationErrorView.SELECT_DIFF_SEED),
                FlowStep(psbt_views.PSBTSelectSeedView),
            ])

    def test_wrong_seed_routes_to_sp_error_view(self):
        from seedsigner.views import psbt_views
        from seedsigner.views.view import MainMenuView
        from seedsigner.models.settings_definition import SettingsConstants
        from embit import bip32

        psbt = build_sp_send_psbt_realistic(SEED)
        wrong_root = bip32.HDKey.from_seed(bytes([0x99] * 32))
        parser = PSBTParser(psbt, seed=SEED, network=SettingsConstants.MAINNET)
        parser.root = wrong_root  # make the parser sign with the wrong key

        self.controller.psbt = psbt
        self.controller.psbt_seed = SEED
        self.controller.psbt_parser = parser

        self.run_sequence([
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSPValidationErrorView, button_data_selection=psbt_views.PSBTSPValidationErrorView.CANCEL),
            FlowStep(MainMenuView),
        ])

    def test_invalid_export_routes_to_error_view(self):
        # Post-trim BIP-375 hand-off check: if the trimmed PSBT would leave the
        # device finalized or incomplete, route to the SP error view instead of
        # displaying the QR.
        from seedsigner.views import psbt_views
        from unittest.mock import patch
        from embit.silent_payments.psbt import SPValidationError

        self._prime(build_sp_send_psbt(SEED))
        with patch.object(PSBTParser, "validate_sp_export", side_effect=SPValidationError("Simulated export error")):
            self.run_sequence([
                FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
                FlowStep(psbt_views.PSBTSPValidationErrorView, button_data_selection=psbt_views.PSBTSPValidationErrorView.SELECT_DIFF_SEED),
                FlowStep(psbt_views.PSBTSelectSeedView),
            ])


class TestSPExportValidation(BaseTest):
    """validate_sp_export enforces the BIP-375 Signer hand-off shape on device."""

    def _signed_trimmed(self):
        from embit import bip32
        psbt = build_sp_send_psbt(SEED)
        root = bip32.HDKey.from_seed(SEED.seed_bytes)
        psbt.sign_with(root)
        return PSBTParser.trim(psbt)

    def test_valid_export_passes(self):
        PSBTParser.validate_sp_export(self._signed_trimmed())

    def test_rejects_finalized_input(self):
        import pytest
        from embit.script import Witness
        from embit.silent_payments.psbt import SPValidationError
        trimmed = self._signed_trimmed()
        trimmed.inputs[0].final_scriptwitness = Witness([bytes(64)])
        with pytest.raises(SPValidationError, match="finalized"):
            PSBTParser.validate_sp_export(trimmed)

    def test_rejects_non_taproot_sp_output_script(self):
        import pytest
        from embit import script
        from embit.silent_payments.psbt import SPValidationError
        from sp_testing_util import EXTERNAL_PUB
        trimmed = self._signed_trimmed()
        sp_out = next(o for o in trimmed.outputs if getattr(o, "sp_data", None) is not None)
        sp_out.script_pubkey = script.p2wpkh(EXTERNAL_PUB)
        with pytest.raises(SPValidationError, match="Taproot"):
            PSBTParser.validate_sp_export(trimmed)

    def test_rejects_missing_ecdh_share(self):
        import pytest
        from embit.silent_payments.psbt import SPValidationError
        trimmed = self._signed_trimmed()
        trimmed.sp_ecdh_shares.clear()
        with pytest.raises(SPValidationError, match="ECDH"):
            PSBTParser.validate_sp_export(trimmed)

    def test_rejects_missing_dleq_proof(self):
        import pytest
        from embit.silent_payments.psbt import SPValidationError
        trimmed = self._signed_trimmed()
        trimmed.sp_dleq_proofs.clear()
        with pytest.raises(SPValidationError, match="DLEQ"):
            PSBTParser.validate_sp_export(trimmed)


class TestSPInputEligibilityGuard(BaseTest):
    """PSBTOverviewView's __init__-time BIP-352 input-eligibility pre-check for SP
    sends -- bails out before any review screen renders instead of failing at
    PSBTFinalizeView after the user has walked through the whole flow."""

    def _run_and_capture(self, view, returns):
        """Drives view.run(), replaying `returns` in order for each run_screen call."""
        calls = []
        returns = list(returns)
        def fake_run_screen(screen_cls, **kwargs):
            calls.append((screen_cls, kwargs))
            return returns.pop(0)
        view.run_screen = fake_run_screen
        return calls, view.run()

    def test_ineligible_input_redirects_to_sp_error_view_before_any_screen(self):
        from seedsigner.views import psbt_views
        from sp_testing_util import build_sp_send_psbt_ineligible_input

        # Don't pre-populate psbt_parser: leave it to PSBTOverviewView.__init__ to do
        # the fresh parse (and spin up the loading screen) so we can confirm it gets
        # stopped before the redirect fires.
        self.controller.psbt = build_sp_send_psbt_ineligible_input()
        self.controller.psbt_seed = SEED

        view = psbt_views.PSBTOverviewView()

        assert view.has_redirect is True
        redirect = view.get_redirect()
        assert redirect.View_cls is psbt_views.PSBTSPValidationErrorView
        assert redirect.view_args["error"]
        assert "Silent Payments" in redirect.view_args["error"]

        # The parse itself succeeded (bad input eligibility isn't a parse failure);
        # the loading spinner started for that parse must have been stopped before
        # we handed off to the error view, or it'd spin forever on an unreachable screen.
        # (LoadingScreenThread is globally mocked in BaseTest.setUp, so we can't observe
        # real thread state -- but we can confirm .stop() was actually called on it.)
        assert self.controller.psbt_parser is not None
        assert view.loading_screen is not None
        view.loading_screen.stop.assert_called_once()

        # has_redirect being True means the Controller's real routing never calls
        # run() on this View at all, so PSBTOverviewScreen is never rendered.

    def test_eligible_input_reaches_overview_screen_normally(self):
        """Happy-path guard: an SP send with an eligible P2WPKH input must not be
        caught by the new pre-check and must still reach PSBTOverviewScreen."""
        from seedsigner.views import psbt_views
        from seedsigner.gui.screens.psbt_screens import PSBTOverviewScreen
        from seedsigner.models.settings_definition import SettingsConstants

        self.settings.set_value(SettingsConstants.SETTING__PRIVACY_WARNINGS, SettingsConstants.OPTION__DISABLED)
        self.controller.psbt = build_sp_send_psbt(SEED)
        self.controller.psbt_seed = SEED

        view = psbt_views.PSBTOverviewView()

        assert view.has_redirect is False
        calls, _ = self._run_and_capture(view, [0])
        assert [screen_cls for screen_cls, _ in calls] == [PSBTOverviewScreen]
