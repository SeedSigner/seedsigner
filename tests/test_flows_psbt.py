from binascii import a2b_base64
from itertools import product
from unittest.mock import patch

from embit import bip32, script
from embit.psbt import PSBT, DerivationPath

from base import BaseTest, FlowTest, FlowStep
from psbt_testing_util import (PSBTTestData, claim_seed_owns_key, create_op_return_output,
    create_op_return_psbt, create_output, foreign_public_key, root_for_seed)

from seedsigner.controller import Controller
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.models.psbt_parser import OPCODES, PSBTParser
from seedsigner.views.view import MainMenuView
from seedsigner.views import scan_views, seed_views, psbt_views
from seedsigner.views.psbt_views import PSBTOpReturnView
from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants


class TestPSBTFlows(FlowTest):

    def test_scan_psbt_first_then_correct_seedqr_flow(self):
        """
            Selecting "Scan" from the MainMenuView and scanning a PSBT should enter the PSBTSelectSeedView flow
            when Scan a Seed is selected from PSBTSelectSeedView it should enter the ScanView flow
            when a SeedQR is scanned it should enter the PSBTOverviewView flow
            since the PSBT has change no warning is displayed and it should enter the PSBTMathView flow
            since the PSBT is not a self transfer it should enter the PSBTAddressDetailsView flow
        """
        def load_psbt_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_2_INPUTS)

        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("080115060387063104071857067618681125136207731354")
    
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
            FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(psbt_views.PSBTOverviewView),
            FlowStep(psbt_views.PSBTMathView),
            FlowStep(psbt_views.PSBTAddressDetailsView, button_data_selection=0),
            FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),
            FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),
            FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSignedQRDisplayView),
            FlowStep(MainMenuView)
        ])

        # Run the same PSBT flow again, this time selecting the seed that the
        # previous flow left loaded in memory.
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView),
        ])

        # Selecting the existing seed should have set it as the signing seed
        assert self.controller.psbt_seed is self.controller.storage.seeds[0]


    def test_tampered_input_amounts_routes_to_input_verification_failed(self):
        """
            A psbt whose non_witness_utxo doesn't verify can declare any input amounts it
            likes, which means it can display any fee it likes. It should be discarded
            outright with no option to proceed.
        """
        def load_tampered_psbt_into_decoder(view: scan_views.ScanView):
            # Editing the non_witness_utxo changes the txid it hashes to, so it no longer
            # matches the txid the input claims to spend.
            psbt = PSBT.parse(a2b_base64(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_2_INPUTS))
            psbt.inputs[0].non_witness_utxo.vout[0].value += 100_000
            view.decoder.add_data(str(psbt))

        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("080115060387063104071857067618681125136207731354")

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_tampered_psbt_into_decoder),
            FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),

            # Parsing fails, so the overview never renders; it redirects straight to the warning
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTInputAmountVerificationFailedView),
            FlowStep(MainMenuView),
        ])


    def test_scan_psbt_first_then_load_electrum_seed(self):
        """
            Should be able to load an Electrum mnemonic after first loading in a psbt.
        """
        def load_psbt_into_decoder(view: scan_views.ScanView):
            # Single sig psbt for the below Electrum mnemonic
            view.decoder.add_data("cHNidP8BAHECAAAAAX9/d6VyI7nvVTyhLBfqu05za2AJ2Z0dKMC0cUX+S2U7AQAAAAD9////AgeHAAAAAAAAFgAUOnNPuZMD1sQudt3+7LvHBUvGhyd//gAAAAAAABYAFGO9QLvu4V9/hz6ZjbIGMrqsEiIYAjQTAAABAR+ghgEAAAAAABYAFKawrgcT62jmIVQwyHPCV0thmJWbAQDBAQAAAAABAYeHL9UQlz/jEKUuNNY3LTeQRjudjBinsP2L0ppvgRt0AAAAAAD/////AnbP3rsPAAAAIlEgtgmCioGjfKwp6f8rOoI4OPb+ZV8db581J9IizZPskl2ghgEAAAAAABYAFKawrgcT62jmIVQwyHPCV0thmJWbAUDCBlMh9VjZN2NdU9Wabi0o3Ct1q9YHTsJRLAkLfUuIHB+BE+ucR4bdGAJG5nBhCWOmCXbpRwKP1INRYvkuQ2fHAAAAACIGA2+PEYHyVy6nhYwAx5SJKBIWXjsWgjhhf/2FEWqXgxnoEKNOC3gAAACAAAAAAAAAAAAAACICA0SBeeHxfHdny6rUnQJuteAnQ7shSydexjJCkSJarn3mEKNOC3gAAACAAQAAAAEAAAAA")

        self.settings.set_value(SettingsConstants.SETTING__ELECTRUM_SEEDS, SettingsConstants.OPTION__ENABLED)

        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
            FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.TYPE_ELECTRUM),
            FlowStep(seed_views.SeedElectrumMnemonicStartView),
        ]

        # Load the associated Electrum mnemonic during the flow
        for word in "apple drip silly junior language resource unaware whale snake copy gravity tank".split():
            sequence += [
                FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word),
            ]

        sequence += [
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(psbt_views.PSBTOverviewView),
            FlowStep(psbt_views.PSBTMathView),
        ]

        self.run_sequence(sequence)


    def test_scan_multisig_psbt_seed_already_signed_flow(self):
        
        def load_psbt_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("cHNidP8BAIkCAAAAAc9dCSh2RcRPfHaT5bNVBpbg0jAekRLqOK+bpN/QA0jeAAAAAAD9////AtAHAAAAAAAAIlEg24shYsV3IRCzlgmMKjAsR4Ad9tX896z7zDAi5q0TU9H3CgAAAAAAACIAIByGQg/VP2aRID62ty40E64HYZeRRsKRGLt8J/76R6stQ04FAE8BBDWHzwSLLGdzgAAAAq3q6nR20JnHR+vKrBQdWxN9C7xU8zNX942mVF7AQpl2ArrdLwVlkGxaatQJ4wwkvypNBKbwOq9hXGLNlKi7rZWAFDUxzXUwAACAAQAAgAAAAIACAACATwEENYfPBHOCZmWAAAACmH6KTXIny0vueRgQFBq4M6oMuG8f1QM0I/RzKQ03bCgCHrF0fyUtV0+FD2N34u/woqb8MAt/o+7Ed58RddhY8zYUCUjSaDAAAIABAACAAAAAgAIAAIAAAQEriBMAAAAAAAAiACBY4WsjDgJXLj3VW222jU1tkIIhT26ce/2efH73BWGGBiICAqyfkrdUO662QBrdvJcSOZMFxniD7M1awm9U0Kb5XCm5RzBEAiAPkQTY84YjFFkpD6MI2cc5rJySqws5fsTQA/8XEZFpbAIgTNVykbEH4Z7bqyzhhy6lty0K8rtCUDCaHNv+47NNIWgBAQMEAQAAAAEFR1IhApL4XO+VE1pPYn5wnRFyJQKVSc9TX2dO6KIBH6jwvgPaIQKsn5K3VDuutkAa3byXEjmTBcZ4g+zNWsJvVNCm+VwpuVKuIgYCkvhc75UTWk9ifnCdEXIlApVJz1NfZ07oogEfqPC+A9ocNTHNdTAAAIABAACAAAAAgAIAAIAAAAAAAAAAACIGAqyfkrdUO662QBrdvJcSOZMFxniD7M1awm9U0Kb5XCm5HAlI0mgwAACAAQAAgAAAAIACAACAAAAAAAAAAAAAAAEBR1IhApYXaczuYbBM/A+EH639Ir2yIB4PxL46dK/I1V1O9aHgIQLa02HCI/+EP+9gGpxHskjYWFN5hZzXY7RRvwV4UF42ylKuIgIClhdpzO5hsEz8D4Qfrf0ivbIgHg/Evjp0r8jVXU71oeAcNTHNdTAAAIABAACAAAAAgAIAAIABAAAAAAAAACICAtrTYcIj/4Q/72AanEeySNhYU3mFnNdjtFG/BXhQXjbKHAlI0mgwAACAAQAAgAAAAIACAACAAQAAAAAAAAAA")
        
        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("073318950739065415961602009907670428187212261116")
            
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
            FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(psbt_views.PSBTOverviewView),
            FlowStep(psbt_views.PSBTMathView),
            FlowStep(psbt_views.PSBTAddressDetailsView, button_data_selection=0),
            FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.SKIP_VERIFICATION),
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSigningErrorView, button_data_selection=psbt_views.PSBTSigningErrorView.SELECT_DIFF_SEED),
            FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.PASSPHRASE),
            FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="abc")),
            FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.DONE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(psbt_views.PSBTOverviewView),
            FlowStep(psbt_views.PSBTMathView),
            FlowStep(psbt_views.PSBTAddressDetailsView, button_data_selection=0),
            FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.SKIP_VERIFICATION),
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSignedQRDisplayView),
            FlowStep(MainMenuView),
        ])


    def test_parse_and_display_op_return_content(self):
        """
            PSBTs that include an OP_RETURN should be able to be parsed like any other
            PSBT and route to the dedicated OP_RETURN View to display the content
        """
        def load_psbt_into_decoder(view: scan_views.ScanView):
            """
                PSBT Tx and Wallet Details
                - Single Sig Wallet P2WPKH (Native Segwit) with no passphrase
                - Regtest 0fb882ff m/84'/1'/0' tpubDCfk37PqcQx6nFtFVuYHvRLJHxvYj33NjHkKRyRmWyCjyJ64sYBXyVjsTHaLBp5GLhM91VBgJ8nKDWDu52J2xVRy64c7ybEjjyWQJuQGLcg
                - 1 Input
                    - 99,992,460 sats
                - 2 Outputs
                    - 1 Output back to self (bcrt1qvwkhakqhz7m7kmz6332avatsmdy32m644g86vv) of 99,992,296 sats
                    - 1 OP_RETURN: "Chancellor on the brink of third bailout"
                - Fee 164 sats
            """
            view.decoder.add_data("cHNidP8BAIYCAAAAATpQ10o+gKdZ8ThpKsbfHiHYn3NhvUrQ5DvW0ZWX8jKLAAAAAAD9////AujC9QUAAAAAFgAUY61+2BcXt+tsWoxV1nVw20kVb1UAAAAAAAAAACtqTChDaGFuY2VsbG9yIG9uIHRoZSBicmluayBvZiB0aGlyZCBiYWlsb3V0aQAAAE8BBDWHzwNXmUmVgAAAANRFa7R5gYD84Wbha3d1QnjgfYPOBw87on6cXS32WoyqAsPFtPxB7PRTdbujUnBPUVDh9YUBtwrl4nc0OcRNGvIyEA+4gv9UAACAAQAAgAAAAIAAAQB0AgAAAAGNFK/1X0fP5q+nu5XX7Tk2VRa0EL+jkGI9CHiJvsjZCgAAAAAA/f///wKMw/UFAAAAABYAFIpZMNnUU6cQt8Q0YpZ0pnvsSA5fAAAAAAAAAAAZakwWYml0Y29pbiBpcyBmcmVlIHNwZWVjaGgAAAABAR+Mw/UFAAAAABYAFIpZMNnUU6cQt8Q0YpZ0pnvsSA5fAQMEAQAAACIGAvxDI0eNI1oQ2AU69R7A0jf+hUdilWCgrWHgdzkqlaXMGA+4gv9UAACAAQAAgAAAAIAAAAAAAQAAAAAiAgK9qKtzGWyiRrpmupdA99NVLriz3GQy6cENbyD19sfl/hgPuIL/VAAAgAEAAIAAAACAAAAAAAIAAAAAAA==")

        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("114006021552133507590698063102151531110102551496")

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
            FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(psbt_views.PSBTOverviewView),
            FlowStep(psbt_views.PSBTMathView),
            FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),

            # Should route to display OP_RETURN content
            FlowStep(psbt_views.PSBTOpReturnView, button_data_selection=0),

            # Should be able to sign the psbt
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSignedQRDisplayView),
            FlowStep(MainMenuView)
        ])



class PSBTSigningFlowTestBase(FlowTest):
    def _load_psbt_for_signing(self, psbt: PSBT, seed: Seed = None):
        """
        Stage the psbt in the Controller and load the signing seed into storage, as if
        both had just been scanned. Each test's sequence then starts at seed selection;
        the parse itself runs when PSBTOverviewView is instantiated.
        """
        self.settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)
        self.controller.psbt = psbt
        self.controller.storage.set_pending_seed(seed if seed is not None else PSBTTestData.seed)
        self.controller.storage.finalize_pending_seed()



class TestPSBTOwnershipClaimRouting(PSBTSigningFlowTestBase):
    """
    A psbt whose own description of itself does not hold up, or whose arithmetic is
    impossible, is refused during parsing, before the user is shown anything about the
    transaction. These cover what the user meets when that happens: a warning screen that
    ends the flow, not a crash.
    """

    def _psbt_with_change(self):
        psbt = PSBT.parse(a2b_base64(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_1_INPUT))
        psbt.outputs.append(create_output(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_CHANGE, 10_000))
        return psbt


    def test_forged_output_claim_terminates_signing_flow(self):
        """
        A forged ownership claim on an output is framed as a potential attack, so it
        routes to a warning that aborts the signing flow.
        """
        psbt = self._psbt_with_change()
        claim_seed_owns_key(psbt.outputs[0], "m/84h/1h/0h/1/0", foreign_public_key())
        self._load_psbt_for_signing(psbt)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTOutputOwnershipClaimFailedView, button_data_selection=psbt_views.PSBTOutputOwnershipClaimFailedView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_forged_input_claim_terminates_signing_flow(self):
        """
        A false claim on an input is framed as inconsistent data rather than as an attack,
        but also routes to its own information screen that aborts the signing flow.
        """
        psbt = self._psbt_with_change()
        claim_seed_owns_key(psbt.inputs[0], "m/84h/1h/0h/0/0", foreign_public_key())
        self._load_psbt_for_signing(psbt)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTInputOwnershipClaimFailedView, button_data_selection=psbt_views.PSBTInputOwnershipClaimFailedView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_surplus_derivation_paths_terminate_signing_flow(self):
        """
        When an output names more derivation paths than its script can use, nothing in
        the psbt says which key it actually pays, so parsing refuses it.

        The parser tests cover why that shape is refusable. This one covers what the user
        gets: a warning that ends the flow, rather than a crash, and without first being
        walked through the details of a transaction about to be discarded.
        """
        other_root = root_for_seed(PSBTTestData.recipient_seed)

        psbt = PSBT.parse(a2b_base64(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_2_INPUTS))

        # Output 2 pays a stranger and carries no derivation path entries of its own.
        # Give it two, so nothing in the psbt says which key it pays.
        for i in range(2):
            derivation_path = bip32.parse_path(f"m/84h/1h/0h/0/{i}")
            psbt.outputs[2].bip32_derivations[other_root.derive(derivation_path).get_public_key()] = \
                DerivationPath(other_root.my_fingerprint, derivation_path)

        self._load_psbt_for_signing(psbt, seed=PSBTTestData.two_input_seed)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTSurplusDerivationPathsView, button_data_selection=psbt_views.PSBTSurplusDerivationPathsView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_output_ownership_contradiction_terminates_signing_flow(self):
        """
        When a psbt marks an output as paying us while its script pays a stranger, the
        two cannot both be true, so parsing refuses it.

        The parser tests cover which shapes qualify. This one covers what the user gets:
        a warning that ends the flow, before any transaction detail is rendered.
        """
        psbt = PSBT.parse(a2b_base64(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_2_INPUTS))

        # Output 0 is the wallet's own change. Repoint its script at a stranger but leave
        # its derivation path entry in place, so the psbt still names a key this seed
        # owns on an output that no longer pays it. Note that psbt.tx is rebuilt on every
        # access, so the scriptPubKey has to be set on the output scope itself.
        psbt.outputs[0].script_pubkey = script.p2wpkh(foreign_public_key())

        self._load_psbt_for_signing(psbt, seed=PSBTTestData.two_input_seed)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTOutputOwnershipContradictionView, button_data_selection=psbt_views.PSBTOutputOwnershipContradictionView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_mixed_derivation_path_types_terminate_signing_flow(self):
        """
        An input or output filling both derivation path maps at once is refused on that
        shape alone. The check lives in the ownership scan, which runs over inputs as well
        as outputs, so this one plants the shape on an input, the side the parser tests do
        not cover.

        It ends the flow at its own warning before any transaction detail is rendered.
        """
        other_root = root_for_seed(PSBTTestData.recipient_seed)

        psbt = PSBT.parse(a2b_base64(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_2_INPUTS))

        # Input 0 already carries a segwit-v0 entry. Add a taproot one beside it, on a
        # stranger's key so nothing here claims this seed: the refusal is on the shape
        # alone, not on an ownership claim.
        derivation_path = bip32.parse_path("m/86h/1h/0h/0/0")
        psbt.inputs[0].taproot_bip32_derivations[foreign_public_key()] = (
            [], DerivationPath(other_root.my_fingerprint, derivation_path))

        self._load_psbt_for_signing(psbt, seed=PSBTTestData.two_input_seed)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTMixedDerivationPathTypesView, button_data_selection=psbt_views.PSBTMixedDerivationPathTypesView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_missing_input_utxo_terminates_signing_flow(self):
        """
        An input that carries no utxo data gives us no amount to verify, so parsing
        refuses the psbt.

        It ends the flow at its own warning before any transaction detail is rendered.
        """
        psbt = PSBT.parse(a2b_base64(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_2_INPUTS))

        # Input 0 is left intact, so the seed can still sign and the parse gets as far as
        # the amount check.
        psbt.inputs[1].witness_utxo = None
        psbt.inputs[1].non_witness_utxo = None

        self._load_psbt_for_signing(psbt, seed=PSBTTestData.two_input_seed)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTMissingInputUtxoView, button_data_selection=psbt_views.PSBTMissingInputUtxoView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_malformed_op_return_terminates_signing_flow(self):
        """
        An OP_RETURN push that claims more bytes than its script carries is malformed
        rather than hostile, but it is still refused during the parse and routes to a
        warning that aborts the signing flow.
        """
        psbt = self._psbt_with_change()
        truncated_push = script.Script(bytes([OPCODES.OP_RETURN, 10]) + b"abc")
        psbt.outputs.append(create_op_return_output(b"", script_pubkey=truncated_push))
        self._load_psbt_for_signing(psbt)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTMalformedOpReturnView, button_data_selection=psbt_views.PSBTMalformedOpReturnView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_missing_input_script_terminates_signing_flow(self):
        """
        The psbt leaves out the witness script that a p2wsh input commits to.

        The flow should stop at PSBTMissingInputScriptView, before any transaction detail
        is rendered.
        """
        psbt = PSBT.parse(a2b_base64(PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT))
        psbt.outputs.append(create_output(PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE, 10_000))
        psbt.inputs[0].witness_script = None

        self._load_psbt_for_signing(psbt)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTMissingInputScriptView, button_data_selection=psbt_views.PSBTMissingInputScriptView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_input_script_mismatch_terminates_signing_flow(self):
        """
        The psbt replaces a p2wsh input's witness script with a stranger's. The coin
        really is the user's, but the supplied script hashes to something other than what
        the input's scriptPubKey commits to.

        The flow should stop at PSBTInputScriptMismatchView, before any transaction detail
        is rendered.
        """
        psbt = PSBT.parse(a2b_base64(PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT))
        psbt.outputs.append(create_output(PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE, 10_000))
        foreign_multisig_keys = [foreign_public_key(f"m/48h/1h/0h/2h/0/{i}") for i in range(3)]
        psbt.inputs[0].witness_script = script.multisig(2, foreign_multisig_keys)

        self._load_psbt_for_signing(psbt)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTInputScriptMismatchView, button_data_selection=psbt_views.PSBTInputScriptMismatchView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_extraneous_input_script_terminates_signing_flow(self):
        """
        The psbt adds a witness script to a legacy multisig input, in addition to the
        input's own redeem script. The coin really is the user's and the redeem script
        still hashes to the scriptPubKey, but a legacy p2sh multisig input should never
        have a witness script.

        The flow should stop at PSBTExtraneousInputScriptView, before any transaction
        detail is rendered.
        """
        psbt = PSBT.parse(a2b_base64(PSBTTestData.MULTISIG_LEGACY_P2SH_1_INPUT))
        psbt.outputs.append(create_output(PSBTTestData.MULTISIG_LEGACY_P2SH_CHANGE, 10_000))

        # The extraneous script's content is irrelevant, so an arbitrary script will do
        psbt.inputs[0].witness_script = script.Script(b"\x51")  # OP_TRUE

        self._load_psbt_for_signing(psbt)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTExtraneousInputScriptView, button_data_selection=psbt_views.PSBTExtraneousInputScriptView.DISCARD),
            FlowStep(MainMenuView),
        ])


    def test_wrong_seed_routes_back_to_seed_selection_flow(self):
        """
        The wrong seed for a psbt redirects before any transaction detail is rendered and
        routes back to seed selection with the signing seed cleared so another can be
        picked.
        """
        self._load_psbt_for_signing(self._psbt_with_change(), seed=PSBTTestData.recipient_seed)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTSeedCannotSignView, button_data_selection=psbt_views.PSBTSeedCannotSignView.SELECT_DIFFERENT_SEED),
            FlowStep(psbt_views.PSBTSelectSeedView),
        ])

        assert self.controller.psbt_seed is None
        assert self.controller.psbt_parser is None

        # The psbt itself is kept: the user is choosing a different seed for it, not
        # starting over
        assert self.controller.psbt is not None


    def test_negative_fee_terminates_signing_flow(self):
        """
        A psbt whose outputs spend more than its inputs bring in is malformed rather than
        hostile, but it is still rejected during the parse and routes to a warning that
        aborts the signing flow.
        """
        psbt = self._psbt_with_change()
        psbt.outputs[0].value = sum(inp.utxo.value for inp in psbt.inputs) + 1
        self._load_psbt_for_signing(psbt)

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView, is_redirect=True),
            FlowStep(psbt_views.PSBTNegativeFeeView, button_data_selection=psbt_views.PSBTNegativeFeeView.DISCARD),
            FlowStep(MainMenuView),
        ])



class TestPSBTOpReturnPaging(BaseTest):
    """
    Which part of a payload reaches each screen.
    """

    def test_a_page_holds_what_it_has_room_for(self):
        per_page = PSBTOpReturnView.MAX_UNITS_PER_PAGE
        per_line = PSBTOpReturnView.UNITS_PER_LINE

        for length in (0, 1, per_page):
            assert PSBTOpReturnView.paginate(b"a" * length) == ([("a" * length)], False, False)

        # One character more needs a second page
        pages, _, _ = PSBTOpReturnView.paginate(b"a" * (per_page + 1))
        assert len(pages) == 2

        # And a screen that also has to warn about burned value has one line less
        pages, _, _ = PSBTOpReturnView.paginate(b"a" * per_page, has_warning=True)
        assert len(pages) == 2
        pages, _, _ = PSBTOpReturnView.paginate(b"a" * (per_page - per_line), has_warning=True)
        assert len(pages) == 1

        # Hex draws two characters per byte, so it is paged against its own figure
        payload = bytes(range(0x80, 0x80 + per_page)) * 2
        pages, is_hex, _ = PSBTOpReturnView.paginate(payload)
        assert is_hex is True
        assert len(pages) == 2
        assert "".join(pages) == payload.hex()


    def test_truncation_begins_one_page_past_the_limit(self):
        """
            Should show every byte up to the page limit, and mark the payload truncated
            one byte past it.
        """
        exactly_full = b"a" * (PSBTOpReturnView.MAX_UNITS_PER_PAGE * PSBTOpReturnView.MAX_PAGES)

        pages, _, is_truncated = PSBTOpReturnView.paginate(exactly_full)
        assert is_truncated is False
        assert "".join(pages) == exactly_full.decode()

        _, _, is_truncated = PSBTOpReturnView.paginate(exactly_full + b"a")
        assert is_truncated is True

        # However large the payload, it never gets more than MAX_PAGES pages, and each one
        # gives up a line to the truncation label
        pages, _, is_truncated = PSBTOpReturnView.paginate(b"a" * 100_000)
        assert is_truncated is True
        per_page = PSBTOpReturnView.MAX_UNITS_PER_PAGE - PSBTOpReturnView.UNITS_PER_LINE
        assert [len(page) for page in pages] == [per_page] * PSBTOpReturnView.MAX_PAGES


    def test_text_or_hex_is_decided_once_for_the_whole_payload(self):
        """
            Should send control characters to hex, and keep line breaks and multi-byte
            characters as text.
        """
        # Valid UTF-8, but nothing anyone can read
        _, is_hex, _ = PSBTOpReturnView.paginate(bytes(range(0x01, 0x20)))
        assert is_hex is True

        # A message split over lines is still text
        _, is_hex, _ = PSBTOpReturnView.paginate(b"Chancellor on the brink\nof third bailout")
        assert is_hex is False

        # Four bytes per character, so a byte-wise split would land inside one
        payload = ("\U0001F4B8" * PSBTOpReturnView.MAX_UNITS_PER_PAGE * 2).encode()
        pages, is_hex, _ = PSBTOpReturnView.paginate(payload)
        assert is_hex is False
        assert "".join(pages) == payload.decode()

        # A bare OP_RETURN has nothing to render either way, and is not hex
        assert PSBTOpReturnView.paginate(b"") == ([""], False, False)


    def test_each_screen_receives_its_own_output_and_page(self):
        """
            Should give each screen its own output's page, size and amount.
        """
        # The first output burns, so its pages are a line shorter
        per_page = PSBTOpReturnView.MAX_UNITS_PER_PAGE - PSBTOpReturnView.UNITS_PER_LINE
        first, second = b"a" * per_page + b"bbbb", b"second payload"

        self.controller.psbt_parser = PSBTParser(
            p=create_op_return_psbt([
                create_op_return_output(first, value=7_000),
                create_op_return_output(second),
            ]),
            seed=PSBTTestData.seed, network=SettingsConstants.REGTEST)

        expected = [
            (0, 0, "a" * per_page, len(first), 7_000),
            (0, 1, "bbbb", len(first), 7_000),
            (1, 0, "second payload", len(second), 0),
        ]

        for op_return_num, page_num, page_text, total_bytes, amount in expected:
            with patch.object(psbt_views.View, "run_screen") as mock_run_screen:
                mock_run_screen.return_value = 0
                PSBTOpReturnView(op_return_num=op_return_num, page_num=page_num).run()

            kwargs = mock_run_screen.call_args.kwargs
            assert (kwargs["page_text"], kwargs["total_bytes"], kwargs["amount"],
                kwargs["page_num"]) == (page_text, total_bytes, amount, page_num)


    def test_bytes_not_shown_counts_bytes_not_characters(self):
        """
            Should count the bytes left out, not characters, when the text has
            multi-byte characters.
        """
        # Four bytes per character; one page more than the limit, so it is truncated
        num_chars = PSBTOpReturnView.MAX_UNITS_PER_PAGE * (PSBTOpReturnView.MAX_PAGES + 1)
        payload = ("\U0001F4B8" * num_chars).encode()
        self.controller.psbt_parser = PSBTParser(
            p=create_op_return_psbt([create_op_return_output(payload)]),
            seed=PSBTTestData.seed, network=SettingsConstants.REGTEST)

        with patch.object(psbt_views.View, "run_screen") as mock_run_screen:
            mock_run_screen.return_value = 0
            PSBTOpReturnView().run()

        kwargs = mock_run_screen.call_args.kwargs
        assert kwargs["is_truncated"] is True
        per_page = PSBTOpReturnView.MAX_UNITS_PER_PAGE - PSBTOpReturnView.UNITS_PER_LINE
        assert kwargs["bytes_shown"] == per_page * PSBTOpReturnView.MAX_PAGES * 4



class TestPSBTOverviewOpReturnRows(BaseTest):
    """
    Which rows the flow diagram draws for the OP_RETURN outputs, and which get the burn
    mark.
    """
    MARK = " (!)"

    def _rows(self, amounts: list) -> list:
        from seedsigner.gui.screens.psbt_screens import PSBTOverviewScreen
        return PSBTOverviewScreen.op_return_rows(amounts)


    def test_a_row_each_up_to_three_then_elided(self):
        assert self._rows(None) == []

        for count in range(0, 4):
            assert len(self._rows([0] * count)) == count

        # Past three, always exactly three rows however many outputs there are
        for count in range(4, 12):
            rows = self._rows([0] * count)
            assert len(rows) == 3
            assert "1" in rows[0] and str(count) in rows[2]


    def test_only_the_outputs_that_burn_are_marked(self):
        """
            Should mark only the rows of outputs that burn, and the ellipsis when any
            output it hides burns, for every arrangement of up to six outputs.
        """
        for count in range(1, 7):
            for burns in product([False, True], repeat=count):
                rows = self._rows([10_000 if b else 0 for b in burns])
                marked = [row.endswith(self.MARK) for row in rows]

                if count <= 3:
                    assert marked == list(burns), f"{burns} -> {rows}"
                else:
                    assert marked == [burns[0], any(burns[1:-1]), burns[-1]], f"{burns} -> {rows}"

                # However the burns fall, a transaction that burns shows at least one mark
                assert any(marked) == any(burns)



class TestPSBTOpReturnFlows(PSBTSigningFlowTestBase):
    """
    Routing through every OP_RETURN output and every page of each.
    """

    def test_paging_walks_every_page_of_every_output(self):
        """
            Should walk every page of the first output, then every page of the second.
        """
        per_page = psbt_views.PSBTOpReturnView.MAX_UNITS_PER_PAGE

        self._load_psbt_for_signing(create_op_return_psbt([
            create_op_return_output(b"a" * (per_page + 1)),   # two pages
            create_op_return_output(b"b" * (per_page + 1)),   # two pages
        ]))

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView),
            FlowStep(psbt_views.PSBTMathView),
            FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),

            # Both pages of the first output, then both pages of the second
            FlowStep(psbt_views.PSBTOpReturnView, button_data_selection=0),
            FlowStep(psbt_views.PSBTOpReturnView, button_data_selection=0),
            FlowStep(psbt_views.PSBTOpReturnView, button_data_selection=0),
            FlowStep(psbt_views.PSBTOpReturnView, button_data_selection=0),

            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSignedQRDisplayView),
            FlowStep(MainMenuView),
        ])


    def test_a_burning_op_return_is_preceded_by_a_warning(self):
        """
            Should show the burn warning before the output that burns, and skip it on the
            way back from that output.
        """
        self._load_psbt_for_signing(create_op_return_psbt([
            create_op_return_output(b"first"),
            create_op_return_output(b"burns", value=100_000),
        ]))

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView),
            FlowStep(psbt_views.PSBTMathView),
            FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),
            FlowStep(psbt_views.PSBTOpReturnView, button_data_selection=0),
            FlowStep(psbt_views.PSBTOpReturnBurnWarningView, button_data_selection=0),
            FlowStep(psbt_views.PSBTOpReturnView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(psbt_views.PSBTOpReturnView),
        ])


    def test_a_bare_op_return_still_gets_a_screen(self):
        """
            Should give a bare OP_RETURN its own screen.
        """
        self._load_psbt_for_signing(create_op_return_psbt([
            create_op_return_output(b"", script_pubkey=script.Script(bytes([OPCODES.OP_RETURN])))
        ]))

        self.run_sequence([
            FlowStep(psbt_views.PSBTSelectSeedView, screen_return_value=0),
            FlowStep(psbt_views.PSBTOverviewView),
            FlowStep(psbt_views.PSBTMathView),
            FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),
            FlowStep(psbt_views.PSBTOpReturnView, button_data_selection=0),
            FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
            FlowStep(psbt_views.PSBTSignedQRDisplayView),
            FlowStep(MainMenuView),
        ])
