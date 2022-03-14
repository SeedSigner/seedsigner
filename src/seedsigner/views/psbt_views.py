from embit.psbt import PSBT

from seedsigner.models.encode_qr import EncodeQR
from seedsigner.models.qr_type import QRType
from seedsigner.models.settings import SettingsConstants

from .view import BackStackView, MainMenuView, NotYetImplementedView, View, Destination

from seedsigner.gui.components import FontAwesomeIconConstants, SeedSignerCustomIconConstants
from seedsigner.gui.screens import psbt_screens
from seedsigner.gui.screens.screen import (RET_CODE__BACK_BUTTON, ButtonListScreen,
    LoadingScreenThread, QRDisplayScreen, WarningScreen)
from seedsigner.models.psbt_parser import PSBTParser



class PSBTSelectSeedView(View):
    def run(self):
        # Note: we can't just autoroute to the PSBT Overview because we might have a
        # multisig where we want to sign with more than one key on this device.
        if not self.controller.psbt:
            # Shouldn't be able to get here
            raise Exception("No PSBT currently loaded")
        
        seeds = self.controller.storage.seeds

        SCAN_SEED = ("Scan a seed", FontAwesomeIconConstants.QRCODE)
        ENTER_WORDS = "Enter 12/24 words"
        button_data = []
        for seed in seeds:
            button_str = seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK))
            if not PSBTParser.has_matching_input_fingerprint(psbt=self.controller.psbt, seed=seed, network=self.settings.get_value(SettingsConstants.SETTING__NETWORK)):
                # Doesn't look like this seed can sign the current PSBT
                button_str += " (?)"
            
            if seed.passphrase is not None:
                # TODO: Include lock icon on right side of button
                pass
            button_data.append((button_str, SeedSignerCustomIconConstants.FINGERPRINT, "blue"))
        button_data.append(SCAN_SEED)
        button_data.append(ENTER_WORDS)

        selected_menu_num = ButtonListScreen(
            title="Select Signer",
            is_button_text_centered=False,
            button_data=button_data
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if len(seeds) > 0 and selected_menu_num < len(seeds):
            # User selected one of the n seeds
            self.controller.psbt_seed = self.controller.get_seed(selected_menu_num)
            return Destination(PSBTOverviewView)

        elif button_data[selected_menu_num] == SCAN_SEED:
            from seedsigner.views.scan_views import ScanView
            return Destination(ScanView)

        elif button_data[selected_menu_num] == ENTER_WORDS:
            # TODO
            return None



class PSBTOverviewView(View):
    def __init__(self):
        super().__init__()

        # The PSBTParser takes a while to read the PSBT. Run the loading screen while we
        # wait.
        self.loading_screen = LoadingScreenThread(text="Parsing PSBT...")
        self.loading_screen.start()

        if not self.controller.psbt_parser or self.controller.psbt_parser.seed != self.controller.psbt_seed:
            # Must run the PSBTParser or re-parse
            self.controller.psbt_parser = PSBTParser(
                self.controller.psbt,
                seed=self.controller.psbt_seed,
                network=self.settings.get_value(SettingsConstants.SETTING__NETWORK)
            )


    def run(self):
        psbt_parser = self.controller.psbt_parser

        change_data = psbt_parser.change_data
        """
            change_data = [
                {
                    'address': 'bc1q............', 
                    'amount': 397621401, 
                    'fingerprint': ['22bde1a9', '73c5da0a'], 
                    'derivation_path': ['m/48h/1h/0h/2h/1/0', 'm/48h/1h/0h/2h/1/0']
                }, {},
            ]
        """
        num_change_outputs = 0
        num_self_transfer_outputs = 0
        for change_output in change_data:
            print(f"""{change_output["derivation_path"][0]}""")
            if change_output["derivation_path"][0].split("/")[-2] == "1":
                num_change_outputs += 1
            else:
                num_self_transfer_outputs += 1

        screen = psbt_screens.PSBTOverviewScreen(
            spend_amount=psbt_parser.spend_amount,
            change_amount=psbt_parser.change_amount,
            fee_amount=psbt_parser.fee_amount,
            num_inputs=psbt_parser.num_inputs,
            num_self_transfer_outputs=num_self_transfer_outputs,
            num_change_outputs=num_change_outputs,
            destination_addresses=psbt_parser.destination_addresses,
        )

        # Everything is set. Stop the loading screen
        self.loading_screen.stop()

        # Run the overview screen
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if psbt_parser.change_amount == 0:
            return Destination(PSBTNoChangeWarningView)

        else:
            return Destination(PSBTMathView)



class PSBTNoChangeWarningView(View):
    def run(self):
        selected_menu_num = WarningScreen(
            status_headline="Full Spend!",
            text="This PSBT spends its entire input value. No change is coming back to your wallet.",
            button_data=["Continue"],
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Only one exit point
        return Destination(PSBTMathView)



class PSBTMathView(View):
    """
        Follows the Overview pictogram. Shows:
        + total input value
        - recipients' value
        - fees
        -------------------
        + change value
    """
    def run(self):
        psbt_parser: PSBTParser = self.controller.psbt_parser
        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)
        
        selected_menu_num = psbt_screens.PSBTMathScreen(
            input_amount=psbt_parser.input_amount,
            num_inputs=psbt_parser.num_inputs,
            spend_amount=psbt_parser.spend_amount,
            num_recipients=psbt_parser.num_destinations,
            fee_amount=psbt_parser.fee_amount,
            change_amount=psbt_parser.change_amount,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if len(psbt_parser.destination_addresses) > 0:
            return Destination(PSBTAddressDetailsView, view_args={"address_num": 0})
        else:
            # This is a self-transfer
            return Destination(PSBTChangeDetailsView, view_args={"change_address_num": 0})



class PSBTAddressDetailsView(View):
    """
        Shows the recipient's address and amount they will receive
    """
    def __init__(self, address_num, is_change=False):
        super().__init__()
        self.address_num = address_num


    def run(self):
        psbt_parser: PSBTParser = self.controller.psbt_parser

        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)

        title = "Will Send"
        if psbt_parser.num_destinations > 1:
            title += f" (#{self.address_num + 1})"

        button_data = []
        if self.address_num < psbt_parser.num_destinations - 1:
            button_data.append("Next Recipient")
        else:
            button_data.append("Next")

        selected_menu_num = psbt_screens.PSBTAddressDetailsScreen(
            title=title,
            button_data=button_data,
            address=psbt_parser.destination_addresses[self.address_num],
            amount=psbt_parser.destination_amounts[self.address_num],
        ).display()

        if selected_menu_num == 0:
            if self.address_num < len(psbt_parser.destination_addresses) - 1:
                # Show the next receive addr
                return Destination(PSBTAddressDetailsView, view_args={"address_num": self.address_num + 1, "is_change": False})

            elif psbt_parser.change_amount > 0:
                # Move on to display change
                return Destination(PSBTChangeDetailsView, view_args={"change_address_num": 0})

            else:
                # There's no change output to verify. Move on to sign the PSBT.
                return Destination(PSBTFinalizeView)

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class PSBTChangeDetailsView(View):
    """
    """
    def __init__(self, change_address_num):
        super().__init__()
        self.change_address_num = change_address_num


    def run(self):
        psbt_parser: PSBTParser = self.controller.psbt_parser

        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)

        # Can we verify this change addr?
        change_data = psbt_parser.get_change_data(change_num=self.change_address_num)
        """
            change_data:
            {
                'address': 'bc1q............', 
                'amount': 397621401, 
                'fingerprint': ['22bde1a9', '73c5da0a'], 
                'derivation_path': ['m/48h/1h/0h/2h/1/0', 'm/48h/1h/0h/2h/1/0']
            }
        """

        # Single-sig verification is easy. We expect to find a single fingerprint
        # and derivation path.
        seed_fingerprint = self.controller.psbt_seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK))
        print(f"seed fingerprint: {seed_fingerprint}")
        print(change_data)

        if seed_fingerprint not in change_data.get("fingerprint"):
            # TODO: Something is wrong with this psbt(?). Reroute to warning?
            return Destination(NotYetImplementedView)

        i = change_data.get("fingerprint").index(seed_fingerprint)
        derivation_path = change_data.get("derivation_path")[i]

        # 'm/84h/1h/0h/1/0' would be a change addr while 'm/84h/1h/0h/0/0' is a self-receive
        is_change_derivation_path = int(derivation_path.split("/")[-2]) == 1
        derivation_path_addr_index = int(derivation_path.split("/")[-1])

        NEXT = "Next"

        if is_change_derivation_path:
            title = "Your Change"
            VERIFY_MULTISIG = "Verify Multisig Change"
        else:
            title = "Self-Transfer"
            VERIFY_MULTISIG = "Verify Multisig Addr"
        # if psbt_parser.num_change_outputs > 1:
        #     title += f" (#{self.change_address_num + 1})"

        is_change_addr_verified = False
        if psbt_parser.is_multisig:
            # TODO: 
            # if the known-good multisig descriptor is already onboard:
                # calc change addr...
                # is_change_addr_verified = True
                # button_data = [NEXT]

            # else:
                # Have the Screen offer to load in the multisig descriptor.            
                # button_data = [VERIFY_MULTISIG, NEXT]

            # Temp value while awaiting above
            button_data = [VERIFY_MULTISIG, NEXT]
        else:
            # Single sig
            # TODO: Generate address from seed at derivation_path and compare with
            # change_data["address"]
            # Save for Nick
            is_change_addr_verified = True
            button_data = [NEXT]

        selected_menu_num = psbt_screens.PSBTChangeDetailsScreen(
            title=title,
            button_data=button_data,
            address=change_data.get("address"),
            amount=change_data.get("amount"),
            is_multisig=psbt_parser.is_multisig,
            fingerprint=seed_fingerprint,
            derivation_path=derivation_path,
            is_change_derivation_path=is_change_derivation_path,
            derivation_path_addr_index=derivation_path_addr_index,
            is_change_addr_verified=is_change_addr_verified,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == NEXT:
            if self.change_address_num < psbt_parser.num_change_outputs - 1:
                return Destination(PSBTChangeDetailsView, view_args={"change_address_num": self.change_address_num + 1})
            else:
                # There's no more change to verify. Move on to sign the PSBT.
                return Destination(PSBTFinalizeView)
            
        elif button_data[selected_menu_num] == VERIFY_MULTISIG:
            return Destination(NotYetImplementedView)



class PSBTFinalizeView(View):
    """
    """
    def run(self):
        psbt_parser: PSBTParser = self.controller.psbt_parser
        psbt: PSBT = self.controller.psbt

        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)

        selected_menu_num = psbt_screens.PSBTFinalizeScreen(
            button_data=["Approve PSBT"]
        ).display()

        if selected_menu_num == 0:
            # Sign PSBT
            loading_screen = LoadingScreenThread(text="Signing PSBT...")
            loading_screen.start()

            sig_cnt = PSBTParser.sig_count(psbt)
            psbt.sign_with(psbt_parser.root)
            trimmed_psbt = PSBTParser.trim(psbt)

            loading_screen.stop()

            if sig_cnt == PSBTParser.sig_count(trimmed_psbt):
                # Signing failed / didn't do anything
                # TODO: Reserved for Nick. Are there different failure scenarios that we can detect?
                # Would be nice to alter the message on the next screen w/more detail.
                return Destination(PSBTSigningErrorView)
            
            else:
                self.controller.psbt = trimmed_psbt

                if len(self.settings.get_value(SettingsConstants.SETTING__COORDINATORS)) == 1:
                    return Destination(PSBTSignedQRDisplayView, view_args={"coordinator": self.settings.get_value(SettingsConstants.SETTING__COORDINATORS)[0]})
                else:
                    return Destination(PSBTSelectCoordinatorView)

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class PSBTSelectCoordinatorView(View):
    def run(self):
        button_data = self.settings.get_multiselect_value_display_names(SettingsConstants.SETTING__COORDINATORS)
        selected_menu_num = psbt_screens.PSBTSelectCoordinatorScreen(
            button_data=button_data
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(PSBTSignedQRDisplayView, view_args={"coordinator": button_data[selected_menu_num]})



class PSBTSignedQRDisplayView(View):
    def __init__(self, coordinator: str):
        super().__init__()
        self.coordinator = coordinator
    
    def run(self):
        qr_psbt_type = QRType.PSBT__UR2
        if self.coordinator == SettingsConstants.COORDINATOR__SPECTER_DESKTOP:
            qr_psbt_type = QRType.PSBT__SPECTER

        qr_encoder = EncodeQR(
            psbt=self.controller.psbt,
            qr_type=qr_psbt_type,
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
            wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE),
        )
        QRDisplayScreen(qr_encoder=qr_encoder).display()

        # We're done with this PSBT. Remove all related data
        self.controller.psbt = None
        self.controller.psbt_parser = None
        self.controller.psbt_seed = None

        return Destination(MainMenuView, clear_history=True)



class PSBTSigningErrorView(View):
    def run(self):
        psbt_parser: PSBTParser = self.controller.psbt_parser
        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)

        # Just a WarningScreen here; only use DireWarningScreen for true security risks.
        selected_menu_num = WarningScreen(
            title="PSBT Error",
            status_icon_name=SeedSignerCustomIconConstants.CIRCLE_EXCLAMATION,
            status_headline="Signing Failed",
            text="Signing with this seed did not add a valid signature.",
            button_data=["Select Diff Seed"],
        ).display()

        if selected_menu_num == 0:
            return Destination(PSBTSelectSeedView, clear_history=True)

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
