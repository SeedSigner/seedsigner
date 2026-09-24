# Must import test base before the Controller
from base import FlowTest, FlowStep

from seedsigner.controller import Controller
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonOption
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views.view import ErrorView, MainMenuView
from seedsigner.views import scan_views, seed_views, tools_views



class TestToolsFlows(FlowTest):

    def test__address_explorer__flow(self):
        """
            Test the simplest AddressExplorer flow when a seed is already loaded.
        """
        controller = Controller.get_instance()
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        controller.storage.set_pending_seed(seed)
        controller.storage.finalize_pending_seed()

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, screen_return_value=0),  # ret 1st onboard seed
            FlowStep(seed_views.SeedExportXpubScriptTypeView, button_data_selection=ButtonOption(SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__SCRIPT_TYPES).get_selection_option_display_name_by_value(SettingsConstants.NATIVE_SEGWIT), return_data=SettingsConstants.NATIVE_SEGWIT)),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, button_data_selection=tools_views.ToolsAddressExplorerAddressTypeView.RECEIVE),
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=10),  # ret NEXT page of addrs
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=4),  # ret a specific addr from the list
            FlowStep(tools_views.ToolsAddressExplorerAddressView),  # runs until dismissed; no ret value
            FlowStep(tools_views.ToolsAddressExplorerAddressListView),
        ])


    def test__address_explorer__loadseed__sideflow(self):
        """
            Finalizing a seed during the Address Explorer flow should return to the next
            Address Explorer step upon completion.
        """
        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("0000" * 11 + "0003")

        # Finalize the new seed w/out passphrase
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),  # simulate read SeedQR
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedExportXpubScriptTypeView),
        ])

        assert self.controller.resume_main_flow == Controller.FLOW__ADDRESS_EXPLORER

        # Reset
        self.controller.storage.seeds.clear()
        self.controller.storage.set_pending_seed(Seed(mnemonic=["abandon "* 11 + "about"]))

        # Finalize the new seed w/passphrase
        self.run_sequence(
            sequence=[
                FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.PASSPHRASE),
                FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="mypassphrase")),
                FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.DONE),
                FlowStep(seed_views.SeedOptionsView, is_redirect=True),
                FlowStep(seed_views.SeedExportXpubScriptTypeView),
            ]
        )


    def test__address_explorer__load_electrum_seed__sideflow(self):
        """
            Loading an Electrum seed during the Address Explorer flow should return to
            the Address Explorer flow upon completion, skip the script type selection,
            and successfully generate receive or change addresses.
        """
        self.settings.set_value(SettingsConstants.SETTING__ELECTRUM_SEEDS, SettingsConstants.OPTION__ENABLED)

        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.TYPE_ELECTRUM),
            FlowStep(seed_views.SeedElectrumMnemonicStartView),
        ]

        # Load an Electrum mnemonic during the flow (same one used in test_seed.py)
        for word in "regular reject rare profit once math fringe chase until ketchup century escape".split():
            sequence += [
                FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word),
            ]

        sequence += [
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, button_data_selection=tools_views.ToolsAddressExplorerAddressTypeView.RECEIVE),
            FlowStep(tools_views.ToolsAddressExplorerAddressListView),
        ]

        self.run_sequence(sequence)



    def test__address_explorer__scan_wrong_qrtype__flow(self):
        """
        Scanning the wrong type of QR code when a SeedQR is expected should route to ErrorView
        """
        def load_wrong_data_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")

        # Finalize the new seed w/out passphrase
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_wrong_data_into_decoder),  # simulate scanning the wrong QR type
            FlowStep(ErrorView),
        ])


    def test__address_explorer__back_button__flow(self):
        """
        Backing out of AddressExplorer behavior depends on current Settings:
        * Multiple script types enabled: BACK to SeedExportXpubScriptTypeView
        * One script type enabled: BACK to where we started:
            * SeedOptions
            * ToolsAddressExplorerSelectSourceView if seed was already onboard
            * MainMenu if no seed was onboard when we entered via ToolsMenu (loading a
                seed during the flow wipes out any history before the load so our only
                option is to return to MainMenu).
        """
        def load_seed_into_decoder(view: scan_views.ScanView):
            view.decoder.add_data("0000" * 11 + "0003")

        controller = Controller.get_instance()
        seed = Seed(mnemonic=["abandon "* 11 + "about"])
        controller.storage.set_pending_seed(seed)
        controller.storage.finalize_pending_seed()

        # Scenario 1: Seed already onboard, multiple script types enabled, BACK can still
        #  change script type selection.
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [SettingsConstants.NATIVE_SEGWIT, SettingsConstants.TAPROOT])
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, screen_return_value=0),  # select the first onboard seed
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPLORER),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, screen_return_value=0),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.SeedExportXpubScriptTypeView),
        ])

        # Scenario 2: Seed already onboard, one script type enabled, started from 
        # SeedOptionsView, BACK to SeedOptionsView.
        self.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [SettingsConstants.NATIVE_SEGWIT])
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, screen_return_value=0),  # select the first onboard seed
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPLORER),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.SeedOptionsView),
        ])

        # Scenario 3: Seed already onboard, one script type enabled, started from
        # ToolsMenu, BACK to ToolsAddressExplorerSelectSourceView.
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, screen_return_value=0),  # select the first onboard seed
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView),
        ])

        # Scenario 4: No seed onboard, one script type enabled, started from Tools, BACK
        # can only go to MainMenu because of mid-flow seed load.
        controller.discard_seed(seed)
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_SEED),
            FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),  # simulate read SeedQR
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedExportXpubScriptTypeView, is_redirect=True),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(MainMenuView),
        ])


    def test__address_explorer__legacy_multisig_p2sh__flow(self):
        """
            Address Explorer should be able to parse a legacy multisig p2sh (m/45')
            descriptor and generate addresses.
        """
        def load_descriptor_into_decoder(view: scan_views.ScanView):
            # descriptor from test_psbt_parser.py
            p2sh_descriptor = "sh(sortedmulti(2,[0f889044/45h]tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62/<0;1>/*,[03cd0a2b/45h]tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L/<0;1>/*,[769f695c/45h]tpubD98hRDKvtATTM8hy5Vvt5ZrvDXwJvrUZm1p1mTKDmd7FqUHY9Wj2k4X1CvxjjtTf3JoChWqYbnWjfkRJ65GQnpVJKbbMfjnGzCwoBUXafyM/<0;1>/*))#uardwtq4".replace("<0;1>", "{0,1}")
            view.decoder.add_data(p2sh_descriptor)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerSelectSourceView, button_data_selection=tools_views.ToolsAddressExplorerSelectSourceView.SCAN_DESCRIPTOR),
            FlowStep(scan_views.ScanWalletDescriptorView, before_run=load_descriptor_into_decoder),  # simulate read descriptor QR
            FlowStep(seed_views.MultisigWalletDescriptorView, button_data_selection=seed_views.MultisigWalletDescriptorView.ADDRESS_EXPLORER),
            FlowStep(tools_views.ToolsAddressExplorerAddressTypeView, button_data_selection=tools_views.ToolsAddressExplorerAddressTypeView.RECEIVE),
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=10),  # ret NEXT page of addrs
            FlowStep(tools_views.ToolsAddressExplorerAddressListView, screen_return_value=4),  # ret a specific addr from the list
            FlowStep(tools_views.ToolsAddressExplorerAddressView),  # runs until dismissed; no ret value
            FlowStep(tools_views.ToolsAddressExplorerAddressListView),
        ])


    def test__verify_address__legacy_multisig_p2sh__flow(self):
        """
            Address Explorer should be able to scan a legacy multisig p2sh address and
            verify it against its descriptor.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # Receive addr @ index 5 from test_psbt_parser.py
            view.decoder.add_data("2N5eN5vUpgsLHAGzKm2VfmYyvNwXmCug5dH")

        def load_descriptor_into_decoder(view: scan_views.ScanView):
            # descriptor from test_psbt_parser.py
            p2sh_descriptor = "sh(sortedmulti(2,[0f889044/45h]tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62/<0;1>/*,[03cd0a2b/45h]tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L/<0;1>/*,[769f695c/45h]tpubD98hRDKvtATTM8hy5Vvt5ZrvDXwJvrUZm1p1mTKDmd7FqUHY9Wj2k4X1CvxjjtTf3JoChWqYbnWjfkRJ65GQnpVJKbbMfjnGzCwoBUXafyM/<0;1>/*))#uardwtq4".replace("<0;1>", "{0,1}")
            view.decoder.add_data(p2sh_descriptor)
        
        settings = Controller.get_instance().settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),  # simulate read address QR
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            FlowStep(seed_views.AddressVerificationSigTypeView, button_data_selection=seed_views.AddressVerificationSigTypeView.MULTISIG),
            FlowStep(seed_views.LoadMultisigWalletDescriptorView, button_data_selection=seed_views.LoadMultisigWalletDescriptorView.SCAN),
            FlowStep(scan_views.ScanWalletDescriptorView, before_run=load_descriptor_into_decoder),  # simulate read descriptor QR
            FlowStep(seed_views.MultisigWalletDescriptorView, screen_return_value=0),
            FlowStep(seed_views.SeedAddressVerificationView),
            FlowStep(seed_views.SeedAddressVerificationSuccessView),
        ])


    def test__verify_address__singlesig__flow(self):
        """
            Address Explorer should be able to scan a singlesig address and
            verify it against a loaded key.
        """
        controller = Controller.get_instance()
        controller.storage.set_pending_seed(Seed(mnemonic=["abandon "* 11 + "about"]))
        controller.storage.finalize_pending_seed()        
        settings = controller.settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)

        addrs = [
            # Native segwit regtest receive addr @ index 6
            "bcrt1q4e9q5taxnsvc6m0uxv6h75mkzvnkxeqk6l90u2",

            # Taproot regtest change addr @ index 48
            "bcrt1pj5v8ean2hc5lh2djsgfx4j9uc0n67942ngv6q9r49qv88ex5mrwsn3u4f7",
        ]

        for test_addr in addrs:
            def load_address_into_decoder(view: scan_views.ScanView):
                # Native segwit regtest receive addr @ index 6
                view.decoder.add_data(test_addr)

            self.run_sequence([
                FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
                FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
                FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),  # simulate read address QR
                FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
                FlowStep(seed_views.SeedSelectSeedView, screen_return_value=0),
                FlowStep(seed_views.SeedAddressVerificationView),
                FlowStep(seed_views.SeedAddressVerificationSuccessView),
            ])


class TestToolsImageEntropyFlows(FlowTest):

    def test__image_entropy__incorrect_preview_frame_count_aborts(self):
        """
        If the live preview screen returns anything other than the required number of
        entropy frames, the View must raise rather than continue on to seed creation.
        """
        from unittest.mock import Mock
        from seedsigner.views.view import UnhandledExceptionView
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyLivePreviewScreen

        # Empty list (no frames)
        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=[]),
            FlowStep(UnhandledExceptionView),
        ])

        # Too few
        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=[Mock()] * 10),
            FlowStep(UnhandledExceptionView),
        ])

        # Too many
        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=[Mock()] * (ToolsImageEntropyLivePreviewScreen.PREVIEW_POOL_SIZE + 5)),
            FlowStep(UnhandledExceptionView),
        ])

        # Degenerate None
        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=None),
            FlowStep(UnhandledExceptionView),
        ])



    def test__image_entropy__screen_exception_does_not_advance(self):
        """
        There is no explicit handling for the live preview screen raising, but the flow
        must never continue on to seed creation when it does.
        """
        from seedsigner.views.view import UnhandledExceptionView

        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=Exception("Test exception")),
            FlowStep(UnhandledExceptionView),
        ])


    def test__image_entropy__full_preview_frames_advances(self):
        """ A full set of preview frames advances to the final image capture. """
        from unittest.mock import Mock
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyLivePreviewScreen

        self.run_sequence([
            FlowStep(tools_views.ToolsImageEntropyLivePreviewView, screen_return_value=[Mock()] * ToolsImageEntropyLivePreviewScreen.PREVIEW_POOL_SIZE),
            FlowStep(tools_views.ToolsImageEntropyFinalImageView),
        ])



class TestToolsDiceGridFlows(FlowTest):
    """
    The camera and the photo reader are mocked out; these tests cover routing, the
    review/correct loop, and that the seed comes from exactly the reviewed rolls.
    """
    ROLLS = [(i % 6) + 1 for i in range(100)]

    def setup_method(self):
        super().setup_method()
        from unittest.mock import patch
        from seedsigner.helpers import dice_grid_reader
        self.camera_patch = patch("seedsigner.hardware.camera.Camera")
        self.camera_patch.start()
        self.reading = dice_grid_reader.DiceGridReading(rolls=list(self.ROLLS), uncertain=[False] * 100)
        self.reader_patch = patch("seedsigner.helpers.dice_grid_reader.read_dice_grid", side_effect=self.read)
        self.reader_patch.start()


    def teardown_method(self):
        self.camera_patch.stop()
        self.reader_patch.stop()
        super().teardown_method()


    def read(self, image):
        """ Stands in for the photo reader: returns self.reading, or raises it. """
        if isinstance(self.reading, Exception):
            raise self.reading
        return self.reading


    def expected_mnemonic(self, rolls: list[int]) -> list[str]:
        from seedsigner.helpers import mnemonic_generation
        return mnemonic_generation.generate_mnemonic_from_dice("".join(str(r) for r in rolls[:99]))


    def test__dice_grid__review_correct_and_finalize(self):
        """ A corrected roll replaces the reading, and only the first 99 rolls count. """
        from seedsigner.gui.screens.tools_screens import ToolsDiceGridReviewScreen

        self.reading.uncertain[5] = True
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.DICE),
            FlowStep(tools_views.ToolsDiceEntropyMnemonicLengthView, screen_return_value=2),  # scan grid
            FlowStep(tools_views.ToolsDiceGridScanView, screen_return_value=None),              # take the photo
            FlowStep(tools_views.ToolsDiceGridReviewView, screen_return_value=5),               # click roll 6
            FlowStep(tools_views.ToolsDiceGridEditRollView, screen_return_value="4"),
            FlowStep(tools_views.ToolsDiceGridReviewView, screen_return_value=ToolsDiceGridReviewScreen.DONE),
            FlowStep(seed_views.SeedWordsWarningView),
        ])

        corrected = list(self.ROLLS)
        corrected[5] = 4
        assert self.controller.storage.pending_seed.mnemonic_list == self.expected_mnemonic(corrected)
        assert self.controller.storage.pending_seed.mnemonic_list != self.expected_mnemonic(self.ROLLS)

        # The 100th die never counts
        other = list(corrected)
        other[99] = 1 if corrected[99] != 1 else 2
        assert self.expected_mnemonic(other) == self.expected_mnemonic(corrected)

        # Nothing about the rolls is left behind
        assert self.controller.dice_grid_rolls is None
        assert self.controller.dice_grid_uncertain is None


    def test__dice_grid__review_starts_on_first_flagged_roll(self):
        self.reading.uncertain[37] = True
        self.reading.uncertain[80] = True
        self.run_sequence([
            FlowStep(tools_views.ToolsDiceGridScanView, screen_return_value=None),
            FlowStep(tools_views.ToolsDiceGridReviewView),
        ])
        assert self.controller.dice_grid_selected_index == 37


    def test__dice_grid__unread_roll_must_be_entered(self):
        """ A roll that couldn't be read blocks finishing until it is entered. """
        from seedsigner.gui.screens.tools_screens import ToolsDiceGridReviewScreen

        self.reading.rolls[12] = 0
        self.reading.uncertain[12] = True
        self.run_sequence([
            FlowStep(tools_views.ToolsDiceGridScanView, screen_return_value=None),
            FlowStep(tools_views.ToolsDiceGridReviewView, screen_return_value=ToolsDiceGridReviewScreen.DONE),
            FlowStep(tools_views.ToolsDiceGridUnreadRollView, screen_return_value=0),
            FlowStep(tools_views.ToolsDiceGridEditRollView, screen_return_value="6"),
            FlowStep(tools_views.ToolsDiceGridReviewView, screen_return_value=ToolsDiceGridReviewScreen.DONE),
            FlowStep(seed_views.SeedWordsWarningView),
        ])

        entered = list(self.ROLLS)
        entered[12] = 6
        assert self.controller.storage.pending_seed.mnemonic_list == self.expected_mnemonic(entered)


    def test__dice_grid__markers_not_found_retakes_photo(self):
        from seedsigner.helpers import dice_grid_reader
        self.reading = dice_grid_reader.MarkersNotFound("no markers")

        self.run_sequence([
            FlowStep(tools_views.ToolsDiceEntropyMnemonicLengthView, screen_return_value=2),
            FlowStep(tools_views.ToolsDiceGridScanView, screen_return_value=None),
            FlowStep(tools_views.ToolsDiceGridMarkersNotFoundView, screen_return_value=0),
            FlowStep(tools_views.ToolsDiceGridScanView),
        ])
        assert self.controller.dice_grid_rolls is None


    def test__dice_grid__back_from_review_discards_rolls(self):
        self.run_sequence([
            FlowStep(tools_views.ToolsDiceEntropyMnemonicLengthView, screen_return_value=2),
            FlowStep(tools_views.ToolsDiceGridScanView, screen_return_value=None),
            FlowStep(tools_views.ToolsDiceGridReviewView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(tools_views.ToolsDiceGridScanView),
        ])
        assert self.controller.dice_grid_rolls is None


    def test__dice_grid__back_from_edit_keeps_reading(self):
        self.run_sequence([
            FlowStep(tools_views.ToolsDiceGridScanView, screen_return_value=None),
            FlowStep(tools_views.ToolsDiceGridReviewView, screen_return_value=3),
            FlowStep(tools_views.ToolsDiceGridEditRollView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(tools_views.ToolsDiceGridReviewView),
        ])
        assert self.controller.dice_grid_rolls == self.ROLLS
