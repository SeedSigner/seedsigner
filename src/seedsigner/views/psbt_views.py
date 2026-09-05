from gettext import gettext as _

from seedsigner.models.psbt_parser import (PSBTInputOwnershipClaimError,
    PSBTMixedDerivationPathTypesError, PSBTOutputOwnershipClaimError,
    PSBTOutputOwnershipContradictionError, PSBTParser, PSBTSeedCannotSignError,
    PSBTSurplusDerivationPathsError)
from seedsigner.models.settings import SettingsConstants
from seedsigner.gui.components import FontAwesomeIconConstants, GUIConstants, SeedSignerIconConstants
from seedsigner.gui.screens.screen import (RET_CODE__BACK_BUTTON, ButtonListScreen, ButtonOption, LargeIconStatusScreen, WarningScreen, DireWarningScreen, QRDisplayScreen)
from seedsigner.views.view import BackStackView, MainMenuView, View, Destination



class PSBTSelectSeedView(View):
    SCAN_SEED = ButtonOption("Scan a seed", SeedSignerIconConstants.QRCODE)
    TYPE_12WORD = ButtonOption("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
    TYPE_24WORD = ButtonOption("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)
    TYPE_ELECTRUM = ButtonOption("Enter Electrum seed", FontAwesomeIconConstants.KEYBOARD)


    def run(self):
        from seedsigner.controller import Controller

        # Note: we can't just autoroute to the PSBT Overview because we might have a
        # multisig where we want to sign with more than one key on this device.
        if not self.controller.psbt:
            # Shouldn't be able to get here
            raise Exception("No transaction currently loaded")

        if self.controller.psbt_seed:
             if PSBTParser.has_matching_input_fingerprint(psbt=self.controller.psbt, seed=self.controller.psbt_seed, network=self.settings.get_value(SettingsConstants.SETTING__NETWORK)):
                 # skip the seed prompt if a seed was previously selected and has matching input fingerprint
                 return Destination(PSBTOverviewView)

        seeds = self.controller.storage.seeds
        button_data = []
        for seed in seeds:
            button_str = seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK))
            if not PSBTParser.has_matching_input_fingerprint(psbt=self.controller.psbt, seed=seed, network=self.settings.get_value(SettingsConstants.SETTING__NETWORK)):
                # Doesn't look like this seed can sign the current PSBT
                # TRANSLATOR_NOTE: Inserts fingerprint w/"?" to indicate that this seed can't sign the current PSBT
                button_str = _("{} (?)").format(button_str)

            button_data.append(ButtonOption(button_str, SeedSignerIconConstants.FINGERPRINT))

        button_data.append(self.SCAN_SEED)
        button_data.append(self.TYPE_12WORD)
        button_data.append(self.TYPE_24WORD)
        if self.settings.get_value(SettingsConstants.SETTING__ELECTRUM_SEEDS) == SettingsConstants.OPTION__ENABLED:
            button_data.append(self.TYPE_ELECTRUM)

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Select Signer"),
            is_button_text_centered=False,
            button_data=button_data
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if len(seeds) > 0 and selected_menu_num < len(seeds):
            # User selected one of the n seeds
            self.controller.psbt_seed = seeds[selected_menu_num]
            return Destination(PSBTOverviewView)
        
        # The remaining flows are a sub-flow; resume PSBT flow once the seed is loaded.
        self.controller.resume_main_flow = Controller.FLOW__PSBT

        if button_data[selected_menu_num] == self.SCAN_SEED:
            from seedsigner.views.scan_views import ScanSeedQRView
            return Destination(ScanSeedQRView)

        elif button_data[selected_menu_num] in [self.TYPE_12WORD, self.TYPE_24WORD]:
            from seedsigner.views.seed_views import SeedMnemonicEntryView
            if button_data[selected_menu_num] == self.TYPE_12WORD:
                self.controller.storage.init_pending_mnemonic(num_words=12)
            else:
                self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == self.TYPE_ELECTRUM:
            from seedsigner.views.seed_views import SeedElectrumMnemonicStartView
            return Destination(SeedElectrumMnemonicStartView)



class PSBTOverviewView(View):
    def __init__(self):
        super().__init__()

        self.loading_screen = None

        if not self.controller.psbt_parser or self.controller.psbt_parser.seed != self.controller.psbt_seed:
            # The PSBTParser takes a while to read the PSBT. Run the loading screen while
            # we wait.
            from seedsigner.gui.screens.screen import LoadingScreenThread
            self.loading_screen = LoadingScreenThread(text=_("Parsing PSBT..."))
            self.loading_screen.start()
                
            try:
                self.controller.psbt_parser = PSBTParser(
                    self.controller.psbt,
                    seed=self.controller.psbt_seed,
                    network=self.settings.get_value(SettingsConstants.SETTING__NETWORK)
                )

            # Note that in almost every exception case, we set clear_history to disable
            # returning via BACK button in the Destination.
            except PSBTInputOwnershipClaimError:
                self.set_redirect(Destination(PSBTInputOwnershipClaimFailedView, clear_history=True))
                return

            except PSBTOutputOwnershipClaimError:
                self.set_redirect(Destination(PSBTOutputOwnershipClaimFailedView, clear_history=True))
                return

            except PSBTSurplusDerivationPathsError:
                self.set_redirect(Destination(PSBTSurplusDerivationPathsView, clear_history=True))
                return

            except PSBTMixedDerivationPathTypesError:
                self.set_redirect(Destination(PSBTMixedDerivationPathTypesView, clear_history=True))
                return

            except PSBTOutputOwnershipContradictionError:
                self.set_redirect(Destination(PSBTOutputOwnershipContradictionView, clear_history=True))
                return

            except PSBTSeedCannotSignError:
                # Not a suspicious psbt, just the wrong seed for it. Send the user back to
                # pick another rather than clearing the flow.
                self.controller.psbt_parser = None
                self.controller.psbt_seed = None
                self.set_redirect(Destination(PSBTSeedCannotSignView))
                return

            finally:
                self.loading_screen.stop()


    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTOverviewScreen
        psbt_parser = self.controller.psbt_parser

        change_data = psbt_parser.change_data
        """
            change_data = [
                {
                    'output_index': 0,
                    'address': 'bc1q............', 
                    'amount': 397621401, 
                    'verified_derivation_path':
                        [2147483696, 2147483649, 2147483648, 2147483650, 1, 0],
                }, {},
            ]
        """
        num_change_outputs = 0
        num_self_transfer_outputs = 0
        for change_output in change_data:
            if PSBTParser.is_change_branch(change_output["verified_derivation_path"]):
                num_change_outputs += 1
            else:
                num_self_transfer_outputs += 1

        # Run the overview screen
        selected_menu_num = self.run_screen(
            PSBTOverviewScreen,
            spend_amount=psbt_parser.spend_amount,
            change_amount=psbt_parser.change_amount,
            fee_amount=psbt_parser.fee_amount,
            num_inputs=psbt_parser.num_inputs,
            num_self_transfer_outputs=num_self_transfer_outputs,
            num_change_outputs=num_change_outputs,
            destination_addresses=psbt_parser.destination_addresses,
            has_op_return=psbt_parser.op_return_data is not None,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            self.controller.psbt_seed = None
            return Destination(BackStackView)

        # expecting p2sh (legacy multisig) and p2pkh to have no policy set
        # skip change warning and psbt math view
        if psbt_parser.policy == None:
            return Destination(PSBTUnsupportedScriptTypeWarningView)
        
        elif psbt_parser.change_amount == 0:
            return Destination(PSBTNoChangeWarningView)

        else:
            return Destination(PSBTMathView)



class PSBTUnsupportedScriptTypeWarningView(View):
    def run(self):
        selected_menu_num = self.run_screen(
            WarningScreen,
            status_headline=_("Unsupported Script Type!"),
            text=_("Transaction has unsupported input script type, please verify your change addresses."),
            button_data=[ButtonOption("Continue")],
        )
        
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        # Only one exit point
        # skip PSBTMathView
        return Destination(
            PSBTAddressDetailsView, view_args={"address_num": 0},
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )



class PSBTNoChangeWarningView(View):
    def run(self):
        selected_menu_num = self.run_screen(
            WarningScreen,
            # TRANSLATOR_NOTE: User will receive no change back; the inputs to this transaction are fully spent
            status_headline=_("Full Spend!"),
            text=_("This transaction spends its entire input value. No change is coming back to your wallet."),
            button_data=[ButtonOption("Continue")],
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Only one exit point
        return Destination(
            PSBTMathView,
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )



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
        from seedsigner.gui.screens.psbt_screens import PSBTMathScreen
        psbt_parser: PSBTParser = self.controller.psbt_parser
        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)
        
        selected_menu_num = self.run_screen(
            PSBTMathScreen,
            input_amount=psbt_parser.input_amount,
            num_inputs=psbt_parser.num_inputs,
            spend_amount=psbt_parser.spend_amount,
            num_recipients=psbt_parser.num_destinations,
            fee_amount=psbt_parser.fee_amount,
            change_amount=psbt_parser.change_amount,
        )

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
    def __init__(self, address_num):
        super().__init__()
        self.address_num = address_num


    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTAddressDetailsScreen
        psbt_parser: PSBTParser = self.controller.psbt_parser

        if not psbt_parser:
            # Should not be able to get here
            raise Exception("Routing error")

        # TRANSLATOR_NOTE: Future-tense used to indicate that this transaction will send this amount, as opposed to "Send" on its own which could be misread as an instant command (e.g. "Send Now").
        title = _("Will Send")
        if psbt_parser.num_destinations > 1:
            title += f" (#{self.address_num + 1})"

        button_data = []
        if self.address_num < psbt_parser.num_destinations - 1:
            button_data.append(ButtonOption("Next recipient"))
        else:
            # TRANSLATOR_NOTE: Short for "Next step"
            button_data.append(ButtonOption("Next"))

        selected_menu_num = self.run_screen(
            PSBTAddressDetailsScreen,
            title=title,
            button_data=button_data,
            address=psbt_parser.destination_addresses[self.address_num],
            amount=psbt_parser.destination_amounts[self.address_num],
        )
        
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if self.address_num < len(psbt_parser.destination_addresses) - 1:
            # Show the next receive addr
            return Destination(PSBTAddressDetailsView, view_args={"address_num": self.address_num + 1})

        elif psbt_parser.change_amount > 0:
            # Move on to display change
            return Destination(PSBTChangeDetailsView, view_args={"change_address_num": 0})

        elif psbt_parser.op_return_data:
            return Destination(PSBTOpReturnView)

        else:
            # There's no change output to verify. Move on to sign the PSBT.
            return Destination(PSBTFinalizeView)



class PSBTChangeDetailsView(View):
    NEXT = ButtonOption("Next")
    SKIP_VERIFICATION = ButtonOption("Skip verification")
    VERIFY_MULTISIG = ButtonOption("Verify multisig change")

    def __init__(self, change_address_num):
        super().__init__()
        self.change_address_num = change_address_num


    def run(self):
        from embit import bip32
        from seedsigner.gui.screens.psbt_screens import PSBTChangeDetailsScreen
        psbt_parser: PSBTParser = self.controller.psbt_parser

        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)

        change_data = psbt_parser.get_change_data(change_num=self.change_address_num)
        """
            change_data:
            {
                'output_index': 0,
                'address': 'bc1q............', 
                'amount': 397621401, 
                'verified_derivation_path':
                    [2147483696, 2147483649, 2147483648, 2147483650, 1, 0],
            }
        """
        seed_fingerprint = self.controller.psbt_seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK))
        verified_derivation_path = change_data.get("verified_derivation_path")
        is_change_derivation_path = PSBTParser.is_change_branch(verified_derivation_path)

        # TODO: Refuse a path too short to carry a branch and an address index; until then
        # this can raise on a malformed psbt.
        derivation_path_addr_index = verified_derivation_path[-1]

        if is_change_derivation_path:
            # TRANSLATOR_NOTE: The amount you're receiving back from the transaction
            title = _("Your Change")
        else:
            title = _("Self-Transfer")
            self.VERIFY_MULTISIG.button_label = _("Verify multisig addr")
        # if psbt_parser.num_change_outputs > 1:
        #     title += f" (#{self.change_address_num + 1})"

        is_change_addr_verified = False
        if psbt_parser.is_multisig:
            # Multisig is verified here rather than during the initial parse because the
            # descriptor it needs to be checked against does not arrive until mid-flow.
            # TODO: Verify the multisig change as soon as the descriptor is loaded, rather
            # than waiting to do it here.

            # if the known-good multisig descriptor is already onboard:
            if self.controller.multisig_wallet_descriptor:
                is_change_addr_verified = psbt_parser.verify_multisig_output(self.controller.multisig_wallet_descriptor, change_num=self.change_address_num)
                button_data = [self.NEXT]

            else:
                # Nothing to check against yet. Have the Screen offer to load in the
                # multisig descriptor.
                button_data = [self.VERIFY_MULTISIG, self.SKIP_VERIFICATION]

        else:
            # The PSBTParser already proves that single sig change outputs are owned by
            # this seed.
            is_change_addr_verified = True
            button_data = [self.NEXT]

        # TODO: Will be unnecessary once the above update is made to verify multisig
        # change as soon as the descriptor is loaded.
        if not is_change_addr_verified and self.controller.multisig_wallet_descriptor is not None:
            # Verification failed, so this psbt is done.
            # Set clear_history to disable returning via BACK button.
            return Destination(PSBTAddressVerificationFailedView, view_args=dict(is_change=is_change_derivation_path), clear_history=True)

        selected_menu_num = self.run_screen(
            PSBTChangeDetailsScreen,
            title=title,
            button_data=button_data,
            address=change_data.get("address"),
            amount=change_data.get("amount"),
            is_multisig=psbt_parser.is_multisig,
            fingerprint=seed_fingerprint,
            derivation_path=bip32.path_to_str(verified_derivation_path),
            is_change_derivation_path=is_change_derivation_path,
            derivation_path_addr_index=derivation_path_addr_index,
            is_change_addr_verified=is_change_addr_verified,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == self.NEXT or button_data[selected_menu_num] == self.SKIP_VERIFICATION:
            if self.change_address_num < psbt_parser.num_change_outputs - 1:
                return Destination(PSBTChangeDetailsView, view_args={"change_address_num": self.change_address_num + 1})

            elif psbt_parser.op_return_data:
                return Destination(PSBTOpReturnView)

            else:
                # There's no more change to verify. Move on to sign the PSBT.
                return Destination(PSBTFinalizeView)
            
        elif button_data[selected_menu_num] == self.VERIFY_MULTISIG:
            from seedsigner.controller import Controller
            from seedsigner.views.seed_views import LoadMultisigWalletDescriptorView
            self.controller.resume_main_flow = Controller.FLOW__PSBT
            return Destination(LoadMultisigWalletDescriptorView)



class PSBTSeedCannotSignView(View):
    """
    Reached when parsing found this seed can't sign any of the psbt's inputs (see
    PSBTSeedCannotSignError).

    We do not view this as an attack; most likely the user simply selected the wrong seed.
    Routes back to seed selection rather than discarding the psbt.
    """
    SELECT_DIFFERENT_SEED = ButtonOption("Select a different seed")

    def run(self):
        # This is an informational mismatch, not a warning, so it uses the neutral info
        # icon and color rather than WarningScreen's alarming yellow edges.
        # TODO: give this its own InfoScreen (LargeIconStatusScreen with the INFO icon and
        # color baked in) rather than customizing the base screen at each call site.
        self.run_screen(
            LargeIconStatusScreen,
            title=_("Seed Can't Sign"),
            status_icon_name=SeedSignerIconConstants.INFO,
            status_color=GUIConstants.INFO_COLOR,
            text=_("None of the inputs in this transaction are controlled by this seed."),
            button_data=[self.SELECT_DIFFERENT_SEED],
            show_back_button=False,
        )

        # Set clear_history to disable returning via BACK button.
        return Destination(PSBTSelectSeedView, clear_history=True)



class PSBTOutputOwnershipClaimFailedView(View):
    """
    Reached when a false ownership claim on an output rejects the psbt (see
    PSBTOutputOwnershipClaimError). Claims on inputs route to
    PSBTInputOwnershipClaimFailedView instead.

    We view this as an attack. We do not allow the user to continue and give this the
    "Dire Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            DireWarningScreen,
            title=_("Suspicious Transaction"),
            status_headline=_("Likely an Attack!"),
            text=_("The transaction's change/self-transfer output is not going back to your wallet."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTInputOwnershipClaimFailedView(View):
    """
    Reached when a false ownership claim on an input rejects the psbt (see
    PSBTInputOwnershipClaimError).

    We do not view this as an attack; a forged input claim only renders the psbt
    unsignable. We do not allow the user to continue, but only give this the "Warning"
    level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            text=_("This transaction incorrectly claims that one of its inputs belongs to this seed."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTSurplusDerivationPathsView(View):
    """
    Reached when an output claims more derivation path entries than its script can use
    (see PSBTSurplusDerivationPathsError).

    The single sig case is a structural error. The multisig case could be an attempt to
    deceive but since we don't know for sure, it's sufficient to just use the "Warning"
    level and stop the user from continuing.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            # TRANSLATOR_NOTE: The transaction/psbt has an error but does not seem to be malicious.
            text=_("This transaction claims too many keys for one of its outputs."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTMixedDerivationPathTypesView(View):
    """
    Reached when an input or output describes its keys in both derivation path maps at
    once (PSBTMixedDerivationPathTypesError).

    We view this as a strange / buggy psbt and do not try to decide whether it is
    malicious. We do not allow the user to continue, but only give this the "Warning"
    level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            # TRANSLATOR_NOTE: The transaction/psbt has an error but does not seem to be malicious.
            text=_("This transaction claims taproot and non-taproot keys for the same script."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTOutputOwnershipContradictionView(View):
    """
    Reached when the psbt's account of who an output pays contradicts the script that
    output commits to (see PSBTOutputOwnershipContradictionError).

    We view this as an attack. We do not allow the user to continue and give this the
    "Dire Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            DireWarningScreen,
            title=_("Suspicious Transaction"),
            status_headline=_("Likely an Attack!"),
            # TRANSLATOR_NOTE: The transaction/psbt contains a deception that we consider an attack.
            text=_("This transaction misrepresents where one of its outputs pays."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTAddressVerificationFailedView(View):
    """
    Reached from PSBTChangeDetailsView when a multisig change or self-transfer output
    could not be verified against the descriptor the user supplied.

    We view this as suspicious but stop short of calling it an attack, since the user may
    have loaded the wrong wallet's descriptor. We do not allow the user to continue and
    give this the "Dire Warning" level.
    """
    def __init__(self, is_change: bool = True):
        super().__init__()
        self.is_change = is_change


    def run(self):
        # TRANSLATOR_NOTE: Variable is either "change" or "self-transfer".
        text = _("Transaction's {} address could not be verified from wallet descriptor.").format(_("change") if self.is_change else _("self-transfer"))

        self.run_screen(
            DireWarningScreen,
            title=_("Suspicious Transaction"),
            status_headline=_("Address Verification Failed"),
            text=text,
            button_data=[ButtonOption("Discard transaction")],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTOpReturnView(View):
    """
        Shows the OP_RETURN data
    """
    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTOpReturnScreen
        psbt_parser: PSBTParser = self.controller.psbt_parser

        if not psbt_parser:
            # Should not be able to get here
            raise Exception("Routing error")

        title = _("OP_RETURN")
        button_data = [ButtonOption("Next")]

        selected_menu_num = self.run_screen(
            PSBTOpReturnScreen,
            title=title,
            button_data=button_data,
            op_return_data=psbt_parser.op_return_data,
        )
        
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(PSBTFinalizeView)



class PSBTFinalizeView(View):
    """
    """
    APPROVE_PSBT = ButtonOption("Approve transaction")

    
    def run(self):
        from embit.psbt import PSBT
        from seedsigner.gui.screens.psbt_screens import PSBTFinalizeScreen

        psbt_parser: PSBTParser = self.controller.psbt_parser
        psbt: PSBT = self.controller.psbt

        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)
        
        selected_menu_num = self.run_screen(
            PSBTFinalizeScreen,
            button_data=[self.APPROVE_PSBT]
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        else:
            # Sign PSBT
            sig_cnt = PSBTParser.sig_count(psbt)
            psbt.sign_with(psbt_parser.root)
            trimmed_psbt = PSBTParser.trim(psbt)

            if sig_cnt == PSBTParser.sig_count(trimmed_psbt):
                # Signing failed / didn't do anything
                # TODO: Reserved for Nick. Are there different failure scenarios that we can detect?
                # Would be nice to alter the message on the next screen w/more detail.
                return Destination(PSBTSigningErrorView)
            
            else:
                self.controller.psbt = trimmed_psbt
                return Destination(PSBTSignedQRDisplayView)



class PSBTSignedQRDisplayView(View):
    def run(self):
        from seedsigner.models.encode_qr import UrPsbtQrEncoder

        qr_encoder = UrPsbtQrEncoder(
            psbt=self.controller.psbt,
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
        )
        self.run_screen(QRDisplayScreen, qr_encoder=qr_encoder)

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        return Destination(MainMenuView, clear_history=True)



class PSBTSigningErrorView(View):
    SELECT_DIFF_SEED = ButtonOption("Select different seed")
    
    def run(self):
        psbt_parser: PSBTParser = self.controller.psbt_parser
        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)

        # Just a WarningScreen here; only use DireWarningScreen for true security risks.
        selected_menu_num = self.run_screen(
            WarningScreen,
            title=_("Transaction Error"),
            status_icon_name=SeedSignerIconConstants.WARNING,
            status_headline=_("Signing Failed"),
            text=_("Signing with this seed did not add a valid signature."),
            button_data=[self.SELECT_DIFF_SEED]
        )

        if selected_menu_num == 0:
            # clear seed selected for psbt signing since it did not add a valid signature
            self.controller.psbt_seed = None
            return Destination(PSBTSelectSeedView, clear_history=True)

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
