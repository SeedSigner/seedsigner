import logging

from gettext import gettext as _

from seedsigner.models.psbt_parser import (PSBTChangeDerivationPathError,
    PSBTExtraneousInputScriptError, PSBTInputAmountVerificationError,
    PSBTInputOwnershipClaimError, PSBTInputOwnershipContradictionError,
    PSBTInputScriptMismatchError, PSBTMalformedOpReturnError, PSBTMissingInputScriptError,
    PSBTMissingInputUtxoError, PSBTMixedDerivationPathTypesError, PSBTNegativeFeeError,
    PSBTOutputOwnershipClaimError, PSBTOutputOwnershipContradictionError, PSBTParser,
    PSBTSeedCannotSignError, PSBTSurplusDerivationPathsError,
    PSBTUnsortedMultisigKeysError, PSBTUnsupportedDerivationPathError,
    PSBTUnsupportedScriptPathError, PSBTUnverifiableMixedInputBasePathsError)
from seedsigner.models.settings import SettingsConstants
from seedsigner.gui.components import FontAwesomeIconConstants, GUIConstants, SeedSignerIconConstants
from seedsigner.gui.screens.screen import (RET_CODE__BACK_BUTTON, ButtonListScreen, ButtonOption, LargeIconStatusScreen, WarningScreen, DireWarningScreen, QRDisplayScreen)
from seedsigner.views.view import BackStackView, MainMenuView, View, Destination

logger = logging.getLogger(__name__)



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
            #
            # TODO: Most of these except clauses route to a View of their own whose only
            # job is to show a WarningScreen or DireWarningScreen and discard the psbt.
            # Replace them with a dict that maps each error type to its warning level and
            # user-facing message, shown by one generic View (as PSBTWarningView does for
            # the non-fatal warnings).
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

            except PSBTMalformedOpReturnError:
                self.set_redirect(Destination(PSBTMalformedOpReturnView, clear_history=True))
                return

            except PSBTUnsupportedDerivationPathError:
                self.set_redirect(Destination(PSBTUnsupportedDerivationPathView, clear_history=True))
                return

            except PSBTMissingInputScriptError:
                self.set_redirect(Destination(PSBTMissingInputScriptView, clear_history=True))
                return

            except PSBTInputScriptMismatchError:
                self.set_redirect(Destination(PSBTInputScriptMismatchView, clear_history=True))
                return

            except PSBTExtraneousInputScriptError:
                self.set_redirect(Destination(PSBTExtraneousInputScriptView, clear_history=True))
                return

            except PSBTOutputOwnershipContradictionError:
                self.set_redirect(Destination(PSBTOutputOwnershipContradictionView, clear_history=True))
                return

            except PSBTInputOwnershipContradictionError:
                self.set_redirect(Destination(PSBTInputOwnershipContradictionView, clear_history=True))
                return

            except PSBTUnsupportedScriptPathError:
                self.set_redirect(Destination(PSBTUnsupportedScriptPathView, clear_history=True))
                return

            except PSBTNegativeFeeError:
                self.set_redirect(Destination(PSBTNegativeFeeView, clear_history=True))
                return

            except PSBTChangeDerivationPathError as e:
                self.set_redirect(Destination(
                    PSBTUnexpectedChangeDerivationPathView,
                    view_args=dict(derivation_path=e.derivation_path),
                    clear_history=True,
                ))
                return

            except PSBTUnverifiableMixedInputBasePathsError:
                self.set_redirect(Destination(PSBTUnverifiableMixedInputBasePathsView, clear_history=True))
                return

            except PSBTUnsortedMultisigKeysError:
                self.set_redirect(Destination(PSBTUnsortedMultisigKeysView, clear_history=True))
                return

            except PSBTSeedCannotSignError:
                # Not a suspicious psbt, just the wrong seed for it. Send the user back to
                # pick another rather than clearing the flow.
                self.controller.psbt_parser = None
                self.controller.psbt_seed = None
                self.set_redirect(Destination(PSBTSeedCannotSignView))
                return

            except PSBTMissingInputUtxoError:
                self.set_redirect(Destination(PSBTMissingInputUtxoView, clear_history=True))
                return

            except PSBTInputAmountVerificationError as e:
                # The declared input amounts could not be verified, so the fee we would show is unproven
                # Set clear_history to disable returning via BACK button.
                logger.error(f"PSBT input amount verification failed: {e}")
                self.set_redirect(Destination(PSBTInputAmountVerificationFailedView, clear_history=True))
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
                    'address_index_beyond_window': False,
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
            op_return_amounts=psbt_parser.op_return_amounts,
            is_high_fee_tx=psbt_parser.is_high_fee,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            self.controller.psbt_seed = None
            return Destination(BackStackView)

        if len(psbt_parser.warnings) > 0:
            return Destination(PSBTWarningView)

        else:
            return Destination(PSBTMathView)



class PSBTWarningView(View):
    """
    Shows the psbt's warning at warning_index and then moves on to the next one. Once
    every warning has been shown, redirects to PSBTMathView instead.
    """
    CONTINUE = ButtonOption("Continue")

    def __init__(self, warning_index: int = 0):
        super().__init__()
        self.warning_index = warning_index

        if warning_index >= len(self.controller.psbt_parser.warnings):
            self.set_redirect(Destination(PSBTMathView))
            return


    def run(self):
        psbt_parser: PSBTParser = self.controller.psbt_parser
        warning = psbt_parser.warnings[self.warning_index]
        if warning == PSBTParser.WARNING__OP_RETURN_BURN:
            Screen_cls = DireWarningScreen
            # TRANSLATOR_NOTE: Total sats destroyed by this transaction's OP_RETURN outputs (e.g. "10,000 sats")
            status_headline = _("{} sats").format(f"{psbt_parser.burn_amount:,}")
            # TRANSLATOR_NOTE: "Burns" means the sats are destroyed: sent to OP_RETURN outputs, which can never be spent. "OP_RETURN" is a technical term, should probably NOT be translated in most languages
            text = _("This transaction burns these sats in OP_RETURN outputs. They can never be spent.")

        elif warning == PSBTParser.WARNING__HIGH_FEE:
            Screen_cls = DireWarningScreen
            status_headline = _("High Fee!")
            # TRANSLATOR_NOTE: Variable is the percentage of the total output value (excluding change) that the fee exceeds. (e.g. "This transaction has a fee higher than 25% of the total output value (excluding change).")
            text = _("This transaction has a fee higher than {}% of the total output value (excluding change).").format(PSBTParser.HIGH_FEES_WARNING_THRESHOLD)

        elif warning == PSBTParser.WARNING__NO_CHANGE:
            Screen_cls = WarningScreen
            # TRANSLATOR_NOTE: User will receive no change back; the inputs to this transaction are fully spent
            status_headline = _("Full Spend!")
            text = _("This transaction spends its entire input value. No change is coming back to your wallet.")

        elif warning == PSBTParser.WARNING__CHANGE_ADDRESS_INDEX_BEYOND_WINDOW:
            # Change or a self-transfer comes back to a derivation path this wallet does
            # use, but at an address index further along than the coins being spent
            # suggest it has reached.
            #
            # We warn and let the user continue rather than discarding the psbt. We are
            # offline and cannot see how far the coordinator has handed out addresses, so
            # the address index is the one change rule we can only guess at. An ordinary
            # transaction from an active wallet can trip it.
            Screen_cls = WarningScreen
            # TRANSLATOR_NOTE: Warns that funds are coming back to the user's own wallet (as change or a self-transfer) at an address far beyond the ones this transaction spends from, which their wallet may not look far enough ahead to find.
            status_headline = _("Distant Address")
            text = _("Funds return to an address far beyond the ones being spent. Your wallet may not find them.")

        else:
            raise Exception(f"Unhandled psbt warning: {warning}")

        selected_menu_num = self.run_screen(
            Screen_cls,
            status_headline=status_headline,
            text=text,
            button_data=[self.CONTINUE],
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Only one exit point
        return Destination(
            PSBTWarningView,
            view_args=dict(warning_index=self.warning_index + 1),
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )



class PSBTMathView(View):
    """
        Follows the Overview pictogram. Shows:
        + total input value
        - recipients' value
        - burned by OP_RETURN outputs, if any
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
            input_amount=psbt_parser.verified_input_amount,
            num_inputs=psbt_parser.num_inputs,
            spend_amount=psbt_parser.spend_amount,
            num_recipients=psbt_parser.num_destinations,
            fee_amount=psbt_parser.fee_amount,
            change_amount=psbt_parser.change_amount,
            burn_amount=psbt_parser.burn_amount,
            is_high_fee_tx=psbt_parser.is_high_fee,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if len(psbt_parser.destination_addresses) > 0:
            return Destination(PSBTAddressDetailsView, view_args={"address_num": 0})

        elif psbt_parser.num_change_outputs > 0:
            # This is a self-transfer
            return Destination(PSBTChangeDetailsView, view_args={"change_address_num": 0})

        elif psbt_parser.num_op_returns > 0:
            # No recipient and no change, so every output is an OP_RETURN
            return Destination(PSBTOpReturnView)

        else:
            return Destination(PSBTFinalizeView)



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

        elif psbt_parser.num_op_returns > 0:
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
                'address_index_beyond_window': False,
            }
        """
        seed_fingerprint = self.controller.psbt_seed.get_fingerprint(self.settings.get_value(SettingsConstants.SETTING__NETWORK))
        verified_derivation_path = change_data.get("verified_derivation_path")
        is_change_derivation_path = PSBTParser.is_change_branch(verified_derivation_path)
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
            # Multisig change is verified against the user's descriptor, which arrives
            # mid-flow. Every change output is checked as soon as the descriptor
            # arrives. So once a verified descriptor is recorded, this output has already
            # passed.
            if psbt_parser.verified_multisig_descriptor is not None:
                is_change_addr_verified = True
                button_data = [self.NEXT]

            else:
                # Have the Screen offer to load in the multisig descriptor. When the
                # cosigners resolve, the parser has already verified this change output,
                # so the descriptor check is unnecessary. We still ask for it as a best
                # practice: it encourages the user to keep their descriptor accessible
                # and confirms that they haven't lost it.
                button_data = [self.VERIFY_MULTISIG, self.SKIP_VERIFICATION]

        else:
            # The PSBTParser already proves that single sig change outputs are owned by
            # this seed.
            is_change_addr_verified = True
            button_data = [self.NEXT]

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
            is_address_index_beyond_window=change_data["address_index_beyond_window"],
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == self.NEXT or button_data[selected_menu_num] == self.SKIP_VERIFICATION:
            if self.change_address_num < psbt_parser.num_change_outputs - 1:
                return Destination(PSBTChangeDetailsView, view_args={"change_address_num": self.change_address_num + 1})

            elif psbt_parser.num_op_returns > 0:
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



class PSBTMalformedOpReturnView(View):
    """
    Reached when an OP_RETURN output's script is not made of complete pushes (see
    PSBTMalformedOpReturnError).

    We view this as a malformed psbt and do not try to decide whether it is malicious. We
    do not allow the user to continue, but only give this the "Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            # TRANSLATOR_NOTE: The transaction/psbt has an error but does not seem to be malicious.
            text=_("This transaction's OP_RETURN data is malformed."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTUnsupportedDerivationPathView(View):
    """
    Reached when a psbt claims one of this seed's keys at a derivation path too short for
    any wallet to use, such as the seed's master key itself (see
    PSBTUnsupportedDerivationPathError).

    We do not try to decide whether this is an attack or a mistake; no standard wallet
    writes a claim at a path that short either way. We do not allow the user to continue,
    but only give this the "Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            # TRANSLATOR_NOTE: The transaction/psbt has an error but does not seem to be malicious.
            text=_("This transaction uses a key of yours that this device will not sign with."),
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



class PSBTInputOwnershipContradictionView(View):
    """
    Reached when the psbt claims one of this seed's keys on an input whose committed
    script does not use that key (see PSBTInputOwnershipContradictionError).

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
            text=_("This transaction misrepresents which keys own an input."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTNegativeFeeView(View):
    """
    Reached when a psbt's outputs spend more than its inputs bring in (see
    PSBTNegativeFeeError). Malformed rather than hostile, so it shows a plain (not dire)
    warning and discards the psbt to the main menu.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            # TRANSLATOR_NOTE: The transaction's outputs spend more than its inputs hold, which is impossible.
            text=_("This transaction's outputs send more than its inputs provide."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all ephemeral
        # data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTMissingInputScriptView(View):
    """
    Reached when an input commits to a script that the psbt did not supply (see
    PSBTMissingInputScriptError).

    We view this as a correctness problem rather than an attack. We do not allow the user
    to continue, but only give this the "Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            # TRANSLATOR_NOTE: The transaction/psbt has an error but does not seem to be malicious.
            text=_("This transaction left out a script that one of its inputs needs."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTInputScriptMismatchView(View):
    """
    Reached when an input supplies a script that hashes to something other than what the
    input commits to (see PSBTInputScriptMismatchError).

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
            text=_("This transaction supplied the wrong script for one of its inputs."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTExtraneousInputScriptView(View):
    """
    Reached when an input supplies a script beyond the ones its scriptPubKey commits to
    (see PSBTExtraneousInputScriptError).

    We do not try to decide whether this is an attack or a mistake. We do not allow the
    user to continue, but only give this the "Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            # TRANSLATOR_NOTE: The transaction/psbt has an error but does not seem to be malicious.
            text=_("This transaction supplied an extra script for one of its inputs."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTUnsupportedScriptPathView(View):
    """
    Reached when an input only lets this seed sign through a taproot script path spend
    (see PSBTUnsupportedScriptPathError).

    Script path spends are not yet supported, so this seed cannot sign the input. We do
    not allow the user to continue, but only give this the "Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Not Yet Implemented"),
            status_headline=None,
            text=_("This transaction needs a taproot script path signature."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTUnexpectedChangeDerivationPathView(View):
    """
    Reached when an output comes back to this seed at a derivation path the wallet this
    transaction spends from does not use (see PSBTChangeDerivationPathError). Single sig
    and multisig alike.

    The coins still belong to the user's seed, but their coordinator software will never
    scan that path to find them. We view this as an attack. We do not allow the user to
    continue and give this the "Dire Warning" level. The path is displayed and named as a
    derivation path, which gives the user a term to search for.
    """
    DISCARD = ButtonOption("Discard transaction")

    def __init__(self, derivation_path: list[int]):
        super().__init__()
        self.derivation_path = derivation_path


    def run(self):
        from embit import bip32

        self.run_screen(
            DireWarningScreen,
            title=_("Suspicious Transaction"),
            status_headline=_("Unsafe Derivation Path"),
            # TRANSLATOR_NOTE: Variable is a derivation path such as "m/84'/0'/0'/5/0", shown on its own line, where this transaction sends funds back to the user's seed. "Our" refers to SeedSigner.
            text=_("{}\nfailed our safety checks.").format(bip32.path_to_str(self.derivation_path).replace("h", "'")),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTUnverifiableMixedInputBasePathsView(View):
    """
    Reached by single sig segwit v0 transactions when the inputs this seed owns are at
    more than one base path and at least one input has no non_witness_utxo (the full
    transaction that created its utxo). See PSBTUnverifiableMixedInputBasePathsError.

    We do not allow the user to continue, but only give this the "Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            # TRANSLATOR_NOTE: This transaction includes inputs from multiple wallets (accounts) controlled by this seed. This can be allowed for some script types, but not this one.
            text=_("Inputs from multiple wallets: cannot complete verification for this script type."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTUnsortedMultisigKeysView(View):
    """
    Reached when a multisig output that holds this seed's key, with the inputs' script
    type and m-of-n, lists its keys out of sorted order (see
    PSBTUnsortedMultisigKeysError).

    We only support sortedmulti() wallets, but an honest multi() wallet can produce this.
    We do not allow the user to continue, but only give this the "Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            text=_("A multisig output to this seed does not properly sort its keys. SeedSigner only supports BIP-67 compliant wallets."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTInputDescriptorMismatchView(View):
    """
    Reached when the descriptor the user just loaded does not derive the address of an
    input this seed owns (see PSBTInputDescriptorMismatchError).

    The usual cause is the user loading the wrong descriptor, but a forged descriptor
    fails the same way. We give this the "Dire Warning" level. The back button returns to
    the prompt to load a descriptor, so the user can try another one. Every descriptor
    they load faces the same check.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        button_data = [self.DISCARD]
        selected_menu_num = self.run_screen(
            DireWarningScreen,
            title=_("Wrong Descriptor"),
            status_headline=_("Descriptor Mismatch"),
            text=_("This descriptor is not for the wallet this transaction spends from."),
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == self.DISCARD:
            # We're done with this PSBT. Route back to MainMenuView, which clears all
            # ephemeral data (except in-memory seeds).
            # Set clear_history to disable returning via BACK button.
            return Destination(MainMenuView, clear_history=True)



class PSBTAddressVerificationFailedView(View):
    """
    Reached when the descriptor the user just loaded does not derive the address of a
    multisig change or self-transfer output (see PSBTChangeDescriptorMismatchError). The
    descriptor did match the inputs, so this is not simply a case of loading the wrong
    descriptor.

    We view this as suspicious but stop short of calling it an attack: the user may be
    sending funds to a different multisig wallet that includes this seed. We do not allow
    the user to continue and give this the "Dire Warning" level.
    """
    def __init__(self, is_change: bool = True):
        super().__init__()
        self.is_change = is_change


    def run(self):
        # TRANSLATOR_NOTE: Variable is either "change" or "self-transfer".
        text = _("The descriptor matches the transaction's inputs, but not its {} address.").format(_("change") if self.is_change else _("self-transfer"))

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



class PSBTInputAmountVerificationFailedView(View):
    """
    Reached when an input's declared amount could not be verified (see
    PSBTInputAmountVerificationError). Shows a dire warning and discards the psbt to the
    main menu.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            DireWarningScreen,
            title=_("Suspicious Transaction"),
            status_headline=_("Likely an Attack!"),
            text=_("This transaction's input amounts cannot be verified, so its fee cannot be trusted."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all ephemeral
        # data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTMissingInputUtxoView(View):
    """
    Reached when an input is missing the utxo it spends (see PSBTMissingInputUtxoError).

    We view this as a correctness problem rather than an attack. We do not allow the user
    to continue, but only give this the "Warning" level.
    """
    DISCARD = ButtonOption("Discard transaction")

    def run(self):
        self.run_screen(
            WarningScreen,
            title=_("Transaction Problem"),
            status_headline=None,
            # TRANSLATOR_NOTE: The transaction/psbt has an error but does not seem to be malicious.
            text=_("This transaction is missing required data for one of its inputs."),
            button_data=[self.DISCARD],
            show_back_button=False,
        )

        # We're done with this PSBT. Route back to MainMenuView, which clears all
        # ephemeral data (except in-memory seeds).
        # Set clear_history to disable returning via BACK button.
        return Destination(MainMenuView, clear_history=True)



class PSBTOpReturnView(View):
    """
        Shows one OP_RETURN output's data. `op_return_num` picks the output.
    """
    def __init__(self, op_return_num: int = 0):
        super().__init__()
        self.op_return_num = op_return_num


    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTOpReturnScreen
        psbt_parser: PSBTParser = self.controller.psbt_parser

        if not psbt_parser:
            # Should not be able to get here
            raise Exception("Routing error")

        if psbt_parser.num_op_returns > 1:
            # TRANSLATOR_NOTE: Title for one of several OP_RETURN outputs (e.g. "OP_RETURN (#2)"). "OP_RETURN" is a technical term, should probably NOT be translated in most languages
            title = _("OP_RETURN (#{})").format(self.op_return_num + 1)
        else:
            # TRANSLATOR_NOTE: Technical term, should probably NOT be translated in most languages
            title = _("OP_RETURN")
        button_data = [ButtonOption("Next")]

        selected_menu_num = self.run_screen(
            PSBTOpReturnScreen,
            title=title,
            button_data=button_data,
            op_return_data=psbt_parser.op_return_data[self.op_return_num],
            burn_amount=psbt_parser.op_return_amounts[self.op_return_num],
        )
        
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if self.op_return_num < psbt_parser.num_op_returns - 1:
            return Destination(PSBTOpReturnView, view_args={"op_return_num": self.op_return_num + 1})

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
