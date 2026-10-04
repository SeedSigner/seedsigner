from binascii import a2b_base64
from itertools import product
from unittest.mock import patch

from embit import bip32, script
from embit.psbt import PSBT, DerivationPath

from base import BaseTest, FlowTest, FlowStep
from psbt_testing_util import (PSBTTestData, claim_seed_owns_key, create_op_return_output,
    create_op_return_psbt, create_output, foreign_public_key, root_for_seed)

from seedsigner.controller import Controller
from seedsigner.models.psbt_parser import OPCODES, PSBTParser
from seedsigner.views.view import MainMenuView
from seedsigner.views import scan_views, seed_views, psbt_views
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



class TestPSBTOwnershipClaimRouting(FlowTest):
    """
    A psbt whose own description of itself does not hold up is refused during parsing,
    before the user is shown anything about the transaction. These cover what the user
    meets when that happens: a warning screen that ends the flow, not a crash.
    """

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


class TestPSBTOpReturnPaging(BaseTest):
    """
    Which part of a payload reaches each screen. Tested directly rather than through a
    FlowTest, which can only count screens, not see what is on them.
    """
    V = psbt_views.PSBTOpReturnView

    def test_a_page_holds_what_it_has_room_for(self):
        for length in (0, 1, self.V.MAX_UNITS_PER_PAGE):
            assert self.V.paginate(b"a" * length) == ([("a" * length)], False, False)

        # One character more needs a second page
        assert len(self.V.paginate(b"a" * (self.V.MAX_UNITS_PER_PAGE + 1))[0]) == 2

        # And a screen that also has to warn about burned value has one line less
        assert len(self.V.paginate(b"a" * self.V.MAX_UNITS_PER_PAGE, has_warning=True)[0]) == 2
        assert len(self.V.paginate(b"a" * (self.V.MAX_UNITS_PER_PAGE - self.V.UNITS_PER_LINE), has_warning=True)[0]) == 1

        # Hex draws two characters per byte, so it is paged against its own figure
        payload = bytes(range(0x80, 0x80 + self.V.MAX_UNITS_PER_PAGE)) * 2
        pages, is_hex, _ = self.V.paginate(payload)
        assert is_hex and len(pages) == 2 and "".join(pages) == payload.hex()


    def test_truncation_begins_one_page_past_the_limit(self):
        """
            Up to the limit the user sees every byte; one byte past it they are told
            some were left out.
        """
        exactly_full = b"a" * (self.V.MAX_UNITS_PER_PAGE * self.V.MAX_PAGES)

        pages, _, is_truncated = self.V.paginate(exactly_full)
        assert not is_truncated and "".join(pages) == exactly_full.decode()

        assert self.V.paginate(exactly_full + b"a")[2] is True

        # However enormous the payload, the page count is what bounds the work done. The
        # last page is a line short, to make room for the "not shown" label.
        pages, _, is_truncated = self.V.paginate(b"a" * 100_000)
        assert len(pages) == self.V.MAX_PAGES and is_truncated
        assert len(pages[-1]) == self.V.MAX_UNITS_PER_PAGE - self.V.UNITS_PER_LINE


    def test_text_or_hex_is_decided_once_for_the_whole_payload(self):
        """
            Deciding per page could cut a multi-byte character in half. And a decode
            check alone would let control characters through to the text path, where
            they draw as empty boxes.
        """
        # Valid UTF-8, but nothing anyone can read
        assert self.V.paginate(bytes(range(0x01, 0x20)))[1] is True

        # A message split over lines is still text
        assert self.V.paginate(b"Chancellor on the brink\nof third bailout")[1] is False

        # Four bytes per character, so a byte-wise split would land inside one
        payload = ("\U0001F4B8" * self.V.MAX_UNITS_PER_PAGE * 2).encode()
        pages, is_hex, _ = self.V.paginate(payload)
        assert not is_hex and "".join(pages) == payload.decode()

        # A bare OP_RETURN has nothing to render either way, and is not hex
        assert self.V.paginate(b"") == ([""], False, False)


    def test_each_screen_receives_its_own_output_and_page(self):
        """
            The flow tests only count screens, so they would pass even if every screen
            showed the first payload. This checks what each screen is actually given.
        """
        # The first output burns, so its screens carry a warning line and are paged tighter
        per_page = self.V.MAX_UNITS_PER_PAGE - self.V.UNITS_PER_LINE
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
                self.V(op_return_num=op_return_num, page_num=page_num).run()

            kwargs = mock_run_screen.call_args.kwargs
            assert (kwargs["page_text"], kwargs["total_bytes"], kwargs["amount"],
                kwargs["page_num"]) == (page_text, total_bytes, amount, page_num)


    def test_bytes_not_shown_counts_bytes_not_characters(self):
        """
            A page of text holds a fixed number of characters, but the label counts
            bytes. With multi-byte characters those differ, and the label must not
            under-report what was left out.
        """
        # Four bytes per character; one page more than the limit, so it is truncated
        payload = ("\U0001F4B8" * self.V.MAX_UNITS_PER_PAGE * (self.V.MAX_PAGES + 1)).encode()
        self.controller.psbt_parser = PSBTParser(
            p=create_op_return_psbt([create_op_return_output(payload)]),
            seed=PSBTTestData.seed, network=SettingsConstants.REGTEST)

        with patch.object(psbt_views.View, "run_screen") as mock_run_screen:
            mock_run_screen.return_value = 0
            self.V().run()

        kwargs = mock_run_screen.call_args.kwargs
        assert kwargs["is_truncated"]
        chars_shown = self.V.MAX_UNITS_PER_PAGE * self.V.MAX_PAGES - self.V.UNITS_PER_LINE
        assert kwargs["bytes_shown"] == chars_shown * 4



class TestPSBTOverviewOpReturnRows(BaseTest):
    """
    Which rows the flow diagram draws for the OP_RETURN outputs, and which get the burn
    mark. Tries every combination of burning and non-burning outputs, since a mark on
    the wrong row is worse than none.
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
            Every arrangement of burning and non-burning outputs, up to six of them.

            Once the rows are collapsed only the first and last outputs have their own
            row, so a burn on any of the middle ones has to show on the ellipsis, or the
            diagram would show no burn at all.
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



class TestPSBTOpReturnFlows(FlowTest):
    """
    A transaction may have more than one OP_RETURN, and a payload may need more than one
    screen. These check the routing that walks the user through all of it.
    """

    def _load_psbt_for_signing(self, psbt: PSBT):
        """
        Stage the psbt in the Controller and load the signing seed into storage, as if
        both had just been scanned, so the sequence can start at seed selection.
        """
        self.settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)
        self.controller.psbt = psbt
        self.controller.storage.set_pending_seed(PSBTTestData.seed)
        self.controller.storage.finalize_pending_seed()


    def test_paging_walks_every_page_of_every_output(self):
        """
            Every page of the first output, then every page of the second.
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


    def test_a_bare_op_return_still_gets_a_screen(self):
        """
            An empty OP_RETURN is still an output, and may still carry sats, so the flow
            must not skip it.
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

