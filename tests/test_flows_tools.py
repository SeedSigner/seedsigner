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
            FlowStep(MainMenuView)
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
                FlowStep(MainMenuView),
            ])


    def test_verify_address_legacy_p2pkh_routes_to_seed_selection(self):
        """
            Legacy P2PKH addresses should route directly to SeedSelectSeedView, skipping
            AddressVerificationSigTypeView because P2PKH is always singlesig.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # Legacy P2PKH address
            view.decoder.add_data("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2")

        settings = Controller.get_instance().settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.MAINNET)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            FlowStep(seed_views.SeedSelectSeedView),
        ])

    def test_verify_address_native_multisig_with_loaded_descriptor_starts_verification(self):
        """
            Native segwit multisig addresses with a descriptor already loaded
            skip the descriptor loading view and goes directly to verification.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # 2-of-3 Native SegWit multisig address (Testnet)
            view.decoder.add_data("tb1q7tpecll8jhp77yqdeyt2t8q5swxmmqeh2v22cqpms5dxlp6p27dqlftet8")

        def load_descriptor_into_controller(view: tools_views.ToolsMenuView):
            from seedsigner.models.decode_qr import DecodeQR
            # Use testnet descriptor from test_embit_utils.py
            descriptor_str = "wsh(sortedmulti(2,[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*,[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/{0,1}/*))#zw6cnrlk".replace("{0,1}", "<0;1>")
            decoder = DecodeQR()
            decoder.add_data(descriptor_str)
            Controller.get_instance().multisig_wallet_descriptor = decoder.get_wallet_descriptor()

        settings = Controller.get_instance().settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.TESTNET)

        self.run_sequence([
            FlowStep(tools_views.ToolsMenuView, before_run=load_descriptor_into_controller, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            # Skips LoadMultisigWalletDescriptorView because descriptor is already loaded
            FlowStep(seed_views.SeedAddressVerificationView),
        ])

    def test_verify_address_native_multisig_loads_descriptor_and_resumes_verification(self):
        """
            Native segwit multisig addresses without a descriptor load the descriptor
            and then resume verification at SeedAddressVerificationView.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # Native segwit testnet receive addr
            view.decoder.add_data("tb1q7tpecll8jhp77yqdeyt2t8q5swxmmqeh2v22cqpms5dxlp6p27dqlftet8")

        def load_descriptor_into_decoder(view: scan_views.ScanView):
            descriptor_str = "wsh(sortedmulti(2,[8d55ff0d/48h/1h/0h/2h]tpubDDxNVWk924RTUhdkVB2uLHw1hGMPNMGufpZefhkkswjbZppVZcuMdjYKQN4ewUog9vbL6RBLFPRWcgTGT7kYP79N6thyJ43ELUs4N2szXMg/<0;1>/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/<0;1>/*,[0be174ee/48h/1h/0h/2h]tpubDEsePyLPkbxbrDiZSTTWdsviiNtiQjrvvzZnkLtG72QYLBygEsXePRsTdXi8DeMA7taCuuvoEBjUAfFrsNZeQJqfvG9fFoujYWbFPYUn7ux/<0;1>/*))#zw6cnrlk"
            view.decoder.add_data(descriptor_str)

        settings = Controller.get_instance().settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.TESTNET)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            # Skips SigTypeView because it's native multisig (length >= 62)
            FlowStep(seed_views.LoadMultisigWalletDescriptorView, button_data_selection=seed_views.LoadMultisigWalletDescriptorView.SCAN),
            FlowStep(scan_views.ScanWalletDescriptorView, before_run=load_descriptor_into_decoder),
            FlowStep(seed_views.MultisigWalletDescriptorView, screen_return_value=0),
            FlowStep(seed_views.SeedAddressVerificationView),
        ])

    def test_verify_address_nested_multisig_with_loaded_descriptor_starts_verification(self):
        """
            Nested segwit multisig addresses with a descriptor already loaded
            still require SigType selection, but then skip descriptor loading.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # 2-of-3 Nested SegWit multisig address (Testnet)
            view.decoder.add_data("2MtgJH28mZWNWU7VRU4ba6ciFbRRGYWZDt3")

        def load_descriptor_into_controller(view: tools_views.ToolsMenuView):
            from seedsigner.models.decode_qr import DecodeQR
            # Use testnet nested segwit descriptor from test_embit_utils.py
            descriptor_str = "sh(wsh(sortedmulti(2,[73c5da0a/48h/1h/1h/0h/1h]tpubDFH9dgzveyD8yHQb8VrpG8FYAuwcLMHMje2CCcbBo1FpaGzYVtJeYYxcYgRqSTta5utUFts8nPPHs9C2bqoxrey5jia6Dwf9mpwrPq7YvcJ/{0,1}/*,[0be174ee/48h/1h/0h/1h]tpubDEsePyLPkbxbnj6XuKvWwdERHaKkikZxaGJ9sJqmM7okbZXgkNSFiGU6GX6qEes6kD8f9Z9FosYB9UEnBSgBEyEwwJhj4uUcFE1WE8VtKoh/{0,1}/*,[8d55ff0d/48h/1h/0h/1h]tpubDDxNVWk924RTT3vyGLHdSDoZ2JUVX7jUsPcwCQ9MrKHAtJrW5zECTF9rFHCvqu526E4PjHp61hBknts2c5aGexvX7hvCZ8TGPvQFdzxxy59/{0,1}/*)))#2ujlfp73".replace("{0,1}", "<0;1>")
            decoder = DecodeQR()
            decoder.add_data(descriptor_str)
            Controller.get_instance().multisig_wallet_descriptor = decoder.get_wallet_descriptor()

        settings = Controller.get_instance().settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.TESTNET)

        self.run_sequence([
            FlowStep(tools_views.ToolsMenuView, before_run=load_descriptor_into_controller, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            FlowStep(seed_views.AddressVerificationSigTypeView, button_data_selection=seed_views.AddressVerificationSigTypeView.MULTISIG),
            # Skips LoadMultisigWalletDescriptorView because descriptor is already loaded
            FlowStep(seed_views.SeedAddressVerificationView),
        ])

    def test_verify_address_back_from_sig_type_returns_to_tools_menu(self):
        """
            Pressing back from AddressVerificationSigTypeView returns to ToolsMenuView
            and wipes the verification state.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # 2-of-3 Nested SegWit multisig address
            view.decoder.add_data("3Qzhs5zKVeSJUKTmECvvq3ZEuuZkZQcMYq")

        settings = Controller.get_instance().settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.MAINNET)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            FlowStep(seed_views.AddressVerificationSigTypeView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(tools_views.ToolsMenuView),
        ])

        controller = Controller.get_instance()
        assert controller.resume_main_flow is None
        assert controller.unverified_address is None

    def test_verify_address_back_from_sig_type_seed_selection_returns_to_sig_type_view(self):
        """
            Pressing back from SeedSelectSeedView when it was reached from
            AddressVerificationSigTypeView returns to AddressVerificationSigTypeView.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # Nested SegWit address
            view.decoder.add_data("3Qzhs5zKVeSJUKTmECvvq3ZEuuZkZQcMYq")

        settings = Controller.get_instance().settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.MAINNET)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            FlowStep(seed_views.AddressVerificationSigTypeView, button_data_selection=seed_views.AddressVerificationSigTypeView.SINGLE_SIG),
            FlowStep(seed_views.SeedSelectSeedView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(seed_views.AddressVerificationSigTypeView),
        ])

    def test_verify_address_back_from_direct_seed_selection_returns_to_tools_menu(self):
        """
            Pressing back from SeedSelectSeedView when it was reached directly
            (e.g. from Legacy P2PKH) returns to ToolsMenuView.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # Legacy P2PKH address
            view.decoder.add_data("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2")

        settings = Controller.get_instance().settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.MAINNET)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            FlowStep(seed_views.SeedSelectSeedView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(tools_views.ToolsMenuView),
        ])

        controller = Controller.get_instance()
        assert controller.resume_main_flow is None

    def test_verify_address_cancel_from_verification_returns_to_main_menu(self):
        """
            Pressing back from SeedAddressVerificationView cancels the verification
            and returns to MainMenuView.
        """
        def load_address_into_decoder(view: scan_views.ScanView):
            # Native segwit regtest receive addr
            view.decoder.add_data("bcrt1q4e9q5taxnsvc6m0uxv6h75mkzvnkxeqk6l90u2")

        controller = Controller.get_instance()
        controller.storage.set_pending_seed(Seed(mnemonic=["abandon "* 11 + "about"]))
        controller.storage.finalize_pending_seed()

        settings = controller.settings
        settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.TOOLS),
            FlowStep(tools_views.ToolsMenuView, button_data_selection=tools_views.ToolsMenuView.VERIFY_ADDRESS),
            FlowStep(scan_views.ScanAddressView, before_run=load_address_into_decoder),
            FlowStep(seed_views.AddressVerificationStartView, is_redirect=True),
            FlowStep(seed_views.SeedSelectSeedView, screen_return_value=0),
            FlowStep(seed_views.SeedAddressVerificationView, screen_return_value=RET_CODE__BACK_BUTTON),
            FlowStep(MainMenuView),
        ])

        controller = Controller.get_instance()
        assert controller.resume_main_flow is None
        assert controller.unverified_address is None

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
