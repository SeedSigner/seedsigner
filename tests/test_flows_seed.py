from typing import Callable
import pytest

# Must import test base before the Controller
from base import BaseTest, FlowTest, FlowStep
from base import FlowTestInvalidButtonDataSelectionException

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.seed import ElectrumSeed, Seed
from seedsigner.views.view import ErrorView, MainMenuView, OptionDisabledView, View, NetworkMismatchErrorView
from seedsigner.views import seed_views, scan_views, settings_views


def load_seed_into_decoder(view: scan_views.ScanView):
    view.decoder.add_data("0000" * 11 + "0003")



class TestSeedFlows(FlowTest):

    def test_scan_seedqr_flow(self):
        """
            Selecting "Scan" from the MainMenuView and scanning a SeedQR should enter the
            Finalize Seed flow and end at the SeedOptionsView.
        """
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView),
        ])


    def test_passphrase_entry_flow(self):
        """
        Opting to add a bip39 passphrase on the Finalize Seed screen should enter the
        passphrase entry / review flow and end at the SeedOptionsView. 
        """
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=SettingsConstants.LABEL__BIP39_PASSPHRASE),
            FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="muhpassphrase", is_back_button=True)),
            FlowStep(seed_views.SeedAddPassphraseExitDialogView, button_data_selection=seed_views.SeedAddPassphraseExitDialogView.DISCARD),
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=SettingsConstants.LABEL__BIP39_PASSPHRASE),
            FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="muhpassphrase", is_back_button=True)),
            FlowStep(seed_views.SeedAddPassphraseExitDialogView, button_data_selection=seed_views.SeedAddPassphraseExitDialogView.EDIT),
            FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="muhpassphrase")),
            FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.EDIT),
            FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="muhpassphrase")),
            FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.DONE),
            FlowStep(seed_views.SeedOptionsView),
        ])


    def test_mnemonic_entry_flow(self):
        """
            Manually entering a mnemonic should land at the Finalize Seed flow and end at
            the SeedOptionsView.
        """
        def test_with_mnemonic(mnemonic):
            Settings.HOSTNAME = "not seedsigner-os"
            sequence = [
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                FlowStep(seed_views.SeedsMenuView, is_redirect=True),  # When no seeds are loaded it auto-redirects to LoadSeedView
                FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD if len(mnemonic) == 12 else seed_views.LoadSeedView.TYPE_24WORD),
            ]

            # Now add each manual word entry step
            for word in mnemonic:
                sequence.append(
                    FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word)
                )
            
            # With the mnemonic completely entered, we land on the SeedFinalizeView
            sequence += [
                FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
                FlowStep(seed_views.SeedOptionsView),
            ]

            self.run_sequence(sequence)

        # Test data from iancoleman.io; 12- and 24-word mnemonic
        test_with_mnemonic("tone flat shed cool census soul paddle boy flight fantasy stem social".split())

        BaseTest.reset_controller()

        test_with_mnemonic("cotton artefact spy mind wing there echo steak child oak awful host despair online bicycle divorce middle firm diamond rare execute chimney almost hollow".split())


    def test_invalid_mnemonic(self):
        """ Should be able to go back and edit or discard an invalid mnemonic """
        # Test data from iancoleman.io
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, is_redirect=True),  # When no seeds are loaded it auto-redirects to LoadSeedView
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD if len(mnemonic) == 12 else seed_views.LoadSeedView.TYPE_24WORD),
        ]
        for word in mnemonic[:-1]:
            sequence.append(FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word))

        sequence += [
            FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value="zoo"),  # But finish with an INVALID checksum word
            FlowStep(seed_views.SeedMnemonicInvalidView, button_data_selection=seed_views.SeedMnemonicInvalidView.EDIT),
        ]

        # Restarts from first word
        for word in mnemonic[:-1]:
            sequence.append(FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word))

        sequence += [
            FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value="zebra"),  # provide yet another invalid checksum word
            FlowStep(seed_views.SeedMnemonicInvalidView, button_data_selection=seed_views.SeedMnemonicInvalidView.DISCARD),
            FlowStep(MainMenuView),
        ]

        self.run_sequence(sequence)


    def test_electrum_mnemonic_entry_flow(self):
        """
            Manually entering an Electrum mnemonic should land at the Finalize Seed flow and end at
            the SeedOptionsView.

            Most BIP-39 mnemonics should generate an error if entered as Electrum seeds.
        """
        def test_with_mnemonic(mnemonic: list[str], custom_extension: str = None, expects_electrum_seed_is_valid: bool = True):
            Settings.HOSTNAME = "not seedsigner-os"
            settings = Settings.get_instance()
            settings.set_value(SettingsConstants.SETTING__ELECTRUM_SEEDS, SettingsConstants.OPTION__ENABLED)

            sequence = [
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                FlowStep(seed_views.SeedsMenuView, is_redirect=True),  # When no seeds are loaded it auto-redirects to LoadSeedView
                FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_ELECTRUM),
                FlowStep(seed_views.SeedElectrumMnemonicStartView),  # Warning screen; no relevant button data selection.
            ]

            # Now add each manual word entry step
            for word in mnemonic:
                sequence.append(
                    FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word)
                )

            if expects_electrum_seed_is_valid:
                # With the mnemonic completely entered, we land on the SeedFinalizeView
                if custom_extension:
                    sequence += [
                        FlowStep(seed_views.SeedFinalizeView, screen_return_value=1),  # The passphrase / custom extension button is dynamic so there's no constant to refer to here
                        FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase=custom_extension)),  # This is a one-off oddity where the Screen returns dict instead of int | str
                        FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.DONE),
                        FlowStep(seed_views.SeedOptionsView),
                    ]
                else:
                    sequence += [
                        FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
                        FlowStep(seed_views.SeedOptionsView),
                    ]

            else:
                # Or we bomb out if the mnemonic is invalid for Electrum
                sequence.append(FlowStep(seed_views.SeedMnemonicInvalidView, button_data_selection=seed_views.SeedMnemonicInvalidView.DISCARD))

            self.run_sequence(sequence)

            BaseTest.reset_controller()


        # Test seeds generated by Electrum v4.5.5
        test_with_mnemonic("bomb congress scorpion mutual word stamp tongue valid permit salmon yellow spy".split())
        test_with_mnemonic("morning pretty hobby click extend color wait joke define sausage boost salmon".split())
        test_with_mnemonic("basket print toy noodle betray weird filter ticket insect copy force machine".split())
        test_with_mnemonic("basket print toy noodle betray weird filter ticket insect copy force machine".split(), custom_extension="test")
        test_with_mnemonic("basket print toy noodle betray weird filter ticket insect copy force machine".split(), custom_extension="monkey fling orange coin good")

        # Most BIP-39 seeds should fail; test seed generated by bitcoiner.guide
        test_with_mnemonic("pioneer divide volcano art victory family grow novel mandate bicycle senior adjust".split(), expects_electrum_seed_is_valid=False)


    def test_export_xpub_standard_flow(self):
        """
            Selecting "Export XPUB" from the SeedOptionsView should enter the Export XPUB flow and end at the MainMenuView
        """

        def flowtest_standard_xpub(sig_tuple, script_tuple, coord_tuple):
            self.run_sequence(
                initial_destination_view_args=dict(seed_num=0),
                sequence=[
                    FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_XPUB),
                    FlowStep(seed_views.SeedExportXpubSigTypeView, button_data_selection=sig_tuple[1]),
                    FlowStep(seed_views.SeedExportXpubScriptTypeView, button_data_selection=script_tuple[1]),
                    FlowStep(seed_views.SeedExportXpubCoordinatorView, button_data_selection=coord_tuple[1]),
                    FlowStep(seed_views.SeedExportXpubWarningView, screen_return_value=0),
                    FlowStep(seed_views.SeedExportXpubDetailsView, screen_return_value=0),
                    FlowStep(seed_views.SeedExportXpubQRDisplayView, screen_return_value=0),
                    FlowStep(MainMenuView),
                ]
        )
            
        # Load a finalized Seed into the Controller
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        self.controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
        self.controller.storage.finalize_pending_seed()

        # these are lists of (constant_value, display_name) tuples
        sig_types: list[tuple[str, str]] = SettingsConstants.ALL_SIG_TYPES
        script_types: list[tuple[str, str]] = SettingsConstants.ALL_SCRIPT_TYPES
        coordinators: list[tuple[str, str]] = SettingsConstants.ALL_COORDINATORS

        # enable non-defaults so they're available in views
        self.settings.set_value(SettingsConstants.SETTING__SIG_TYPES, [x for x,y in sig_types])
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [x for x,y in script_types])
        self.settings.set_value(SettingsConstants.SETTING__COORDINATORS, [x for x,y in coordinators])

        # exhaustively test flows thru standard sig_types, script_types, and coordinators
        for sig_tuple in sig_types:
            for script_tuple in script_types:
                for coord_tuple in coordinators:
                    # skip custom derivation
                    if script_tuple[0] == SettingsConstants.CUSTOM_DERIVATION:
                        continue 
                    # skip multisig taproot
                    elif sig_tuple[0] == SettingsConstants.MULTISIG and script_tuple[0] == SettingsConstants.TAPROOT:
                        continue
                    else:
                        print('\n\ntest_standard_xpubs(%s, %s, %s)' % (sig_tuple, script_tuple, coord_tuple))
                        flowtest_standard_xpub(sig_tuple, script_tuple, coord_tuple)


    def test_export_xpub_disabled_not_available_flow(self):
        """
            If sig_type/script_type/coordinator disabled, then these options are not available
        """
        # Load a finalized Seed into the Controller
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        self.controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
        self.controller.storage.finalize_pending_seed()

        # these are lists of (constant_value, display_name) tuples
        sig_types: list[tuple[str, str]] = SettingsConstants.ALL_SIG_TYPES
        script_types: list[tuple[str, str]] = SettingsConstants.ALL_SCRIPT_TYPES
        coordinators: list[tuple[str, str]] = SettingsConstants.ALL_COORDINATORS

        # these are the disabled types that we will be testing
        disabled_sig = SettingsConstants.MULTISIG
        disabled_script = SettingsConstants.TAPROOT
        disabled_coord = SettingsConstants.COORDINATOR__NUNCHUK

        # enable all but our target disabled type
        self.settings.set_value(SettingsConstants.SETTING__SIG_TYPES, [x for x,y in sig_types if x!=disabled_sig])
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [x for x,y in script_types if x!=disabled_script])
        self.settings.set_value(SettingsConstants.SETTING__COORDINATORS, [x for x,y in coordinators if x!=disabled_coord])

        # If multisig isn't an option, then the sig type selection is skipped altogether
        self.run_sequence(
            initial_destination_view_args=dict(seed_num=0),
            sequence=[
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_XPUB),
                FlowStep(seed_views.SeedExportXpubSigTypeView, is_redirect=True),
                FlowStep(seed_views.SeedExportXpubScriptTypeView),
            ]
        )

        # test that taproot is not an option via exception raised when choice is taproot
        with pytest.raises(FlowTestInvalidButtonDataSelectionException) as e:
            self.run_sequence(
                initial_destination_view_args=dict(seed_num=0),
                sequence=[
                    FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_XPUB),
                    FlowStep(seed_views.SeedExportXpubSigTypeView, is_redirect=True),
                    FlowStep(seed_views.SeedExportXpubScriptTypeView, button_data_selection=disabled_script),
                ]
            )

        # test that nunchuk is not an option via exception raised when choice is nunchuk
        with pytest.raises(FlowTestInvalidButtonDataSelectionException) as e:
            self.run_sequence(
                initial_destination_view_args=dict(seed_num=0),
                sequence=[
                    FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_XPUB),
                    FlowStep(seed_views.SeedExportXpubSigTypeView, is_redirect=True),
                    FlowStep(seed_views.SeedExportXpubScriptTypeView, screen_return_value=0),
                    FlowStep(seed_views.SeedExportXpubCoordinatorView, button_data_selection=disabled_coord),
                ]
            )


    def test_export_xpub_custom_derivation_flow(self):
        """
            Export XPUB flow for custom derivation finishes at MainMenuView
        """
        # Load a finalized Seed into the Controller
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        self.controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
        self.controller.storage.finalize_pending_seed()

        # enable custom derivation script_type setting (plus at least one more for a choice)
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [
            SettingsConstants.NATIVE_SEGWIT, 
            SettingsConstants.NESTED_SEGWIT,
            SettingsConstants.CUSTOM_DERIVATION
        ])

        # get display names to access button choices in the views (ugh: hardcoding, is there a better way?)
        sig_type = self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__SIG_TYPES)[0] # single sig
        script_type = self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__SCRIPT_TYPES)[2] # custom derivation
        coordinator = self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__COORDINATORS)[3] # specter

        self.run_sequence(
            initial_destination_view_args=dict(seed_num=0),
            sequence=[
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_XPUB),
                FlowStep(seed_views.SeedExportXpubSigTypeView, button_data_selection=sig_type),
                FlowStep(seed_views.SeedExportXpubScriptTypeView, button_data_selection=script_type),
                FlowStep(seed_views.SeedExportXpubCustomDerivationView, screen_return_value="m/0'/0'"),
                FlowStep(seed_views.SeedExportXpubCoordinatorView, button_data_selection=coordinator),
                FlowStep(seed_views.SeedExportXpubWarningView, screen_return_value=0),
                FlowStep(seed_views.SeedExportXpubDetailsView, screen_return_value=0),
                FlowStep(seed_views.SeedExportXpubQRDisplayView, screen_return_value=0),
                FlowStep(MainMenuView),
            ]
        )


    def test_export_xpub_skip_non_option_flow(self):
        """
            Export XPUB flows w/o user choices when no other options for sig_types, script_types, and/or coordinators
        """
        # Load a finalized Seed into the Controller
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        self.controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
        self.controller.storage.finalize_pending_seed()

        # exclusively set only one choice for each of sig_types, script_types and coordinators
        self.settings.update({
            SettingsConstants.SETTING__SIG_TYPES: SettingsConstants.MULTISIG,
            SettingsConstants.SETTING__SCRIPT_TYPES: SettingsConstants.NESTED_SEGWIT,
            SettingsConstants.SETTING__COORDINATORS: SettingsConstants.COORDINATOR__SPECTER_DESKTOP,
        })

        self.run_sequence(
            initial_destination_view_args=dict(seed_num=0),
            sequence=[
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_XPUB),
                FlowStep(seed_views.SeedExportXpubSigTypeView, is_redirect=True),
                FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
                FlowStep(seed_views.SeedExportXpubCoordinatorView, is_redirect=True),
                FlowStep(seed_views.SeedExportXpubWarningView, screen_return_value=0),
                FlowStep(seed_views.SeedExportXpubDetailsView, screen_return_value=0),
                FlowStep(seed_views.SeedExportXpubQRDisplayView, screen_return_value=0),
                FlowStep(MainMenuView),
            ]
        )


    def test_export_xpub_electrum_seed_flow(self):
        """
            Electrum seeds should skip script type selection
        """            
        # Load a finalized Seed into the Controller
        self.controller.storage.init_pending_mnemonic(num_words=12, is_electrum=True)
        self.controller.storage.set_pending_seed(ElectrumSeed("regular reject rare profit once math fringe chase until ketchup century escape".split()))
        self.controller.storage.finalize_pending_seed()

        # Make sure all options are enabled
        self.settings.set_value(SettingsConstants.SETTING__SIG_TYPES, [x for x,y in SettingsConstants.ALL_SIG_TYPES])
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [x for x,y in SettingsConstants.ALL_SCRIPT_TYPES])
        self.settings.set_value(SettingsConstants.SETTING__COORDINATORS, [x for x,y in SettingsConstants.ALL_COORDINATORS])

        self.run_sequence(
            initial_destination_view_args=dict(seed_num=0),
            sequence=[
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_XPUB),
                FlowStep(seed_views.SeedExportXpubSigTypeView, button_data_selection=seed_views.SeedExportXpubSigTypeView.SINGLE_SIG),

                # Skips past the script type options via redirect
                FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
                FlowStep(seed_views.SeedExportXpubCoordinatorView, button_data_selection=self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__COORDINATORS)[0]),
                FlowStep(seed_views.SeedExportXpubWarningView, screen_return_value=0),
                FlowStep(seed_views.SeedExportXpubDetailsView, screen_return_value=0),
                FlowStep(seed_views.SeedExportXpubQRDisplayView, screen_return_value=0),
                FlowStep(MainMenuView),
            ]
        )


    def test_discard_seed_flow(self):
        """
            Selecting "Discard Seed" from the SeedOptionsView should enter the Discard Seed flow and 
            remove the in-memory seed from the Controller.
        """
        # Load a finalized Seed into the Controller
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        self.controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
        self.controller.storage.finalize_pending_seed()

        self.run_sequence(
            initial_destination_view_args=dict(seed_num=0),
            sequence=[
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.DISCARD),
                FlowStep(seed_views.SeedDiscardView, button_data_selection=seed_views.SeedDiscardView.DISCARD),
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                FlowStep(seed_views.SeedsMenuView, is_redirect=True),  # When no seeds are loaded it auto-redirects to LoadSeedView
                FlowStep(seed_views.LoadSeedView),
            ]
        )



class TestMessageSigningFlows(FlowTest):
    MAINNET_DERIVATION_PATH = "m/84h/0h/0h/0/0"
    TESTNET_DERIVATION_PATH = "m/84h/1h/0h/0/0"
    CUSTOM_DERIVATION_PATH = "m/99h/0/0"
    SHORT_MESSAGE = "I attest that I control this bitcoin address blah blah blah"
    NO_WHITESPACE_MESSAGE = """{"height":841407,"lightning_bolt12":"lno1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}"""
    MULTIPAGE_MESSAGE = """Chancellor on brink of second bailout for banks

        Billions may be needed as lending squeeze tightens

        Alistair Darling has been forced to consider a second bailout for banks as the lending drought worsens.

        The Chancellor will decide within weeks whether to pump billions more into the economy as evidence mounts that the £37 billion part-nationalisation last year has failed to keep credit flowing. Options include cash injections, offering banks cheaper state guarantees to raise money privately or buying up “toxic assets”, The Times has learnt."""


    def load_seed_into_decoder(self, view: scan_views.ScanView):
        view.decoder.add_data("0000" * 11 + "0003")


    def load_signmessage_into_decoder(self, view:View, derivation_path: str, message: str):
        view.decoder.add_data(f"signmessage {derivation_path} ascii:{message}")


    def load_short_message_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.MAINNET_DERIVATION_PATH, self.SHORT_MESSAGE)


    def load_testnet_message_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.TESTNET_DERIVATION_PATH, self.SHORT_MESSAGE)


    def load_multipage_message_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.MAINNET_DERIVATION_PATH, self.MULTIPAGE_MESSAGE)


    def load_no_whitespace_message_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.MAINNET_DERIVATION_PATH, self.NO_WHITESPACE_MESSAGE)


    def load_custom_derivation_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.CUSTOM_DERIVATION_PATH, self.SHORT_MESSAGE)


    def inject_mesage_as_paged_message(self, view: View):
        # Because the Screen won't actually run, we have to do the Screen's work here
        from seedsigner.gui.components import reflow_text_into_pages, GUIConstants
        paged = reflow_text_into_pages(
            text=self.controller.sign_message_data["message"],
            width=240 - 2*GUIConstants.EDGE_PADDING,
            height=240 - GUIConstants.TOP_NAV_HEIGHT - 3*GUIConstants.EDGE_PADDING - GUIConstants.BUTTON_HEIGHT,
            allow_text_overflow=True,
        )
        self.controller.sign_message_data["paged_message"] = paged


    def test_sign_message_flow(self):
        """
        Should scan a `signmessage` QR and complete the message review, address review,
        and signing flow.
        """
        # Ensure message signing is enabled
        self.settings.set_value(SettingsConstants.SETTING__MESSAGE_SIGNING, SettingsConstants.OPTION__ENABLED)

        # Scenario 1: Load the mesage first, then the seed
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_short_message_into_decoder),  # simulate read message QR; ret val is ignored
            FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
            FlowStep(seed_views.SeedSelectSeedView, button_data_selection=seed_views.SeedSelectSeedView.SCAN_SEED),
            FlowStep(scan_views.ScanView, before_run=self.load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, before_run=self.inject_mesage_as_paged_message, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageConfirmAddressView, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageSignedMessageQRView, screen_return_value=0),
            FlowStep(MainMenuView),
        ])

        # Scenario 2: Scan the seed first, then select Sign Message
        self.controller.discard_seed(0)
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.SIGN_MESSAGE),
            FlowStep(scan_views.ScanView, before_run=self.load_short_message_into_decoder),  # simulate read message QR; ret val is ignored
            FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, before_run=self.inject_mesage_as_paged_message, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageConfirmAddressView, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageSignedMessageQRView, screen_return_value=0),
            FlowStep(MainMenuView),
        ])

        # Scenario 3: Load a long, multipage message
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_multipage_message_into_decoder),  # simulate read message QR; ret val is ignored
            FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
            FlowStep(seed_views.SeedSelectSeedView, button_data_selection=seed_views.SeedSelectSeedView.SCAN_SEED),
            FlowStep(scan_views.ScanView, before_run=self.load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, before_run=self.inject_mesage_as_paged_message, screen_return_value=0),  # page 1/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 2/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 3/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 4/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 5/5

            # Arrive at the address confirmation, then go backwards to re-review the paged message
            FlowStep(seed_views.SeedSignMessageConfirmAddressView, screen_return_value=RET_CODE__BACK_BUTTON),  # then back to page 5/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=RET_CODE__BACK_BUTTON),  # back to page 4/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=RET_CODE__BACK_BUTTON),  # back to page 3/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=RET_CODE__BACK_BUTTON),  # back to page 2/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=RET_CODE__BACK_BUTTON),  # back to page 1/5

            # Now proceed forward again to the end
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 1/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 2/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 3/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 4/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 5/5
            FlowStep(seed_views.SeedSignMessageConfirmAddressView, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageSignedMessageQRView, screen_return_value=0),
            FlowStep(MainMenuView),
        ])

        # Scenario 4: Load a long message without whitespace
        self.controller.discard_seed(0)
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.SIGN_MESSAGE),
            FlowStep(scan_views.ScanView, before_run=self.load_no_whitespace_message_into_decoder),  # simulate read message QR; ret val is ignored
            FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, before_run=self.inject_mesage_as_paged_message, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageConfirmAddressView, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageSignedMessageQRView, screen_return_value=0),
            FlowStep(MainMenuView),
        ])


    def test_sign_message_network_mismatch_flow(self):
        """
        Should redirect to NetworkMismatchErrorView if a message's derivation path network doesn't match the current network.

        The error view should then forward to the Network Settings update View.
        """
        # Ensure message signing is enabled
        self.settings.set_value(SettingsConstants.SETTING__MESSAGE_SIGNING, SettingsConstants.OPTION__ENABLED)

        def expect_network_mismatch_error(load_message: Callable):
            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
                FlowStep(scan_views.ScanView, before_run=load_message),  # simulate read message QR; ret val is ignored
                FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
                FlowStep(NetworkMismatchErrorView),
                FlowStep(settings_views.SettingsEntryUpdateSelectionView),
            ])

        # MAINNET settings vs TESTNET derivation path with the message
        self.settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.MAINNET)
        expect_network_mismatch_error(self.load_testnet_message_into_decoder)

        # TESTNET settings vs MAINNET derivation path with the message
        self.settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.TESTNET)
        expect_network_mismatch_error(self.load_short_message_into_decoder)

        # REGTEST settings vs MAINNET derivation path with the message
        self.settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)
        expect_network_mismatch_error(self.load_short_message_into_decoder)


    def test_sign_message_option_disabled(self):
        """
        Should redirect to OptionDisabledView if a `signmessage` QR is scanned with
        message signing disabled.

        Should offer the option to route directly to enable that settings or return to
        MainMenuView.
        """
        # Ensure message signing is disabled
        self.settings.set_value(SettingsConstants.SETTING__MESSAGE_SIGNING, SettingsConstants.OPTION__DISABLED)

        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_short_message_into_decoder),  # simulate read message QR; ret val is ignored
            FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
        ]

        # First test routing to update the setting
        self.run_sequence(
            sequence + [
                FlowStep(OptionDisabledView, button_data_selection=OptionDisabledView.UPDATE_SETTING),
                FlowStep(settings_views.SettingsEntryUpdateSelectionView),
            ]
        )

        # Now test exiting to Main Menu
        self.run_sequence(
            sequence + [
                FlowStep(OptionDisabledView, button_data_selection=OptionDisabledView.DONE),
                FlowStep(MainMenuView),
            ]
        )


    def test_sign_message_invalid_qr_flow(self):
        """
        Should clear `Controller.resume_main_flow` and redirect to ErrorView if an
        invalid signmessage QR is scanned.

        The error view should then forward to MainMenuView.
        """
        # Ensure message signing is enabled
        self.settings.set_value(SettingsConstants.SETTING__MESSAGE_SIGNING, SettingsConstants.OPTION__ENABLED)

        def load_invalid_signmessage_qr(view: scan_views.ScanView):
            view.decoder.add_data("this text will not make sense to the decoder")

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.SIGN_MESSAGE),
            FlowStep(scan_views.ScanView, before_run=load_invalid_signmessage_qr),  # simulate read message QR; ret val is ignored
            FlowStep(ErrorView),
            FlowStep(MainMenuView),
        ])

        assert self.controller.resume_main_flow is None


    def test_sign_message_unsupported_derivation_flow(self):
        """
        Should redirect to NotYetImplementedView if a message's derivation path isn't yet supported
        """
        # Ensure message signing is enabled
        self.settings.set_value(SettingsConstants.SETTING__MESSAGE_SIGNING, SettingsConstants.OPTION__ENABLED)

        def expect_unsupported_derivation(load_message: Callable):
            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
                FlowStep(scan_views.ScanView, before_run=self.load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
                FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.SIGN_MESSAGE),
                FlowStep(scan_views.ScanView, before_run=load_message),  # simulate read message QR; ret val is ignored
                FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
                FlowStep(seed_views.NotYetImplementedView),
                FlowStep(MainMenuView),
            ])

        self.settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.MAINNET)
        expect_unsupported_derivation(self.load_custom_derivation_into_decoder)

