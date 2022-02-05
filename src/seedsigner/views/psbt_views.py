import json
from threading import Thread
import time
from typing import Counter

from embit import psbt
from seedsigner.gui.components import TextArea
from seedsigner.gui.screens.seed_screens import SeedValidScreen
from seedsigner.helpers.threads import BaseThread, ThreadsafeCounter
from seedsigner.models import psbt_parser

from seedsigner.models.psbt_parser import PSBTParser

from seedsigner.models.settings import SettingsConstants

from .view import BackStackView, MainMenuView, View, Destination

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonListScreen, LoadingScreenThread
from seedsigner.models import DecodeQR, Seed
from seedsigner.models.qr_type import QRType



class PSBTSelectSeedView(View):
    def __init__(self):
        super().__init__()
        self.seeds = []
        for seed in self.controller.storage.seeds:
            self.seeds.append({
                "fingerprint": seed.get_fingerprint(self.settings.network),
                "has_passphrase": seed.passphrase is not None
            })


    def run(self):
        button_data = []
        for seed in self.seeds:
            button_data.append((seed["fingerprint"], "fingerprint_inline"))
        button_data.append(("Scan a seed", "scan_inline"))
        button_data.append("Enter 12/24 words")

        screen = ButtonListScreen(
            title="Select Signer",
            is_button_text_centered=False,
            button_data=button_data
        )
        selected_menu_num = screen.display()

        if len(self.seeds) > 0 and selected_menu_num < len(self.seeds):
            return Destination(PSBTOverviewView, view_args={"seed_num": selected_menu_num})

        elif selected_menu_num == len(button_data) - 2:
            from seedsigner.views.scan_views import ScanView
            return Destination(ScanView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(MainMenuView)



class PSBTOverviewView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)

        # The PSBTParser takes a while to read the PSBT. Run the loading screen while we
        # wait.
        self.loading_screen = LoadingScreenThread()
        self.loading_screen.start()

        psbt_parser = PSBTParser(
            self.controller.psbt,
            seed=self.seed,
            network=self.controller.settings.network
        )
        self.controller.psbt_parser = psbt_parser


    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTOverviewScreen

        psbt_parser = self.controller.psbt_parser
        screen = PSBTOverviewScreen(
            spend_amount=psbt_parser.spend_amount,
            change_amount=psbt_parser.change_amount,
            fee_amount=psbt_parser.fee_amount,
            num_inputs=psbt_parser.num_inputs,
            destination_addresses=psbt_parser.destination_addresses,
        )

        # Everything is set. Stop the loading screen
        self.loading_screen.stop()

        # Run the overview screen
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            return Destination(PSBTAmountDetailsView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class PSBTOverviewMockView(View):
    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTOverviewScreen
        screen = PSBTOverviewScreen(
            spend_amount=384734,
            change_amount=84783,
            fee_amount=1313,
            num_inputs=12,
            destination_addresses=[
                "bc1q3lg2qc933hd4ke9xjwm68e3rxz94525d5vchy75",
                "bc1qkf4jqc933hd4ke9xjwm68e3rxz94525d5vchy75",
                "bc1q9de6qc933hd4ke9xjwm68e3rxz94525d5vchy75",
                "hello"
            ],
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            return Destination(MainMenuView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class PSBTAmountDetailsView(View):
    """
        Follows the Overview pictogram. Shows:
        + total input value
        - recipients' value
        - fees
        -------------------
        + change value
    """
    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTAmountDetailsScreen

        psbt_parser: PSBTParser = self.controller.psbt_parser
        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)
        
        screen = PSBTAmountDetailsScreen(
            input_amount=psbt_parser.input_amount,
            num_inputs=psbt_parser.num_inputs,
            spend_amount=psbt_parser.spend_amount,
            num_recipients=psbt_parser.num_destinations,
            fee_amount=psbt_parser.fee_amount,
            change_amount=psbt_parser.change_amount,
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            return Destination(PSBTAddressDetailsView, view_args={"address_num": 0, "is_change": len(psbt_parser.destination_addresses) == 0})

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



# class PSBTScriptDetailsView(View):
#     """
#         Shows script type
#     """
#     pass

#             # return Destination(PSBTAddressDetailsView, view_args={"address_num": 0, "is_change": len(psbt_parser.destination_addresses) == 0})




class PSBTAddressDetailsView(View):
    """
        Shows the recipient's address and amount they will receive
    """
    def __init__(self, address_num, is_change=False):
        super().__init__()
        self.address_num = address_num
        self.is_change = is_change


    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTAddressDetailsScreen

        psbt_parser: PSBTParser = self.controller.psbt_parser

        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)

        if self.is_change:
            screen = PSBTAddressDetailsScreen(
                address=psbt_parser.change_addresses[self.address_num],
                amount=psbt_parser.change_amounts[self.address_num],
                address_number=self.address_num + 1,   # Screen title starts count at 1
                num_addresses=len(psbt_parser.change_addresses),
                is_change=self.is_change
            )
        else:
            screen = PSBTAddressDetailsScreen(
                address=psbt_parser.destination_addresses[self.address_num],
                amount=psbt_parser.destination_amounts[self.address_num],
                address_number=self.address_num + 1,   # Screen title starts count at 1
                num_addresses=len(psbt_parser.destination_addresses),
                is_change=self.is_change
            )


        # self.address = "bc1p2805rrtn627nvvmwlj89htyyxyg588lazc2ytef5ejyrwpfpsxnqca4eg7"
        # self.address = "bc1qhzp0n0vyv9lrzh27rxrc2wfu05jhzcz5626dylpgl4cjt2q9uq4s8359wx"
        # self.address = "bc1qj2k6cy7yx7490zn6y7dkg70lc8kdhruvdn36d8"
        # self.address = "3Ge7DUnW63PFpQh826HQeGMmdtyd4Cj3s9"
        # self.amount = 78942
        selected_menu_num = screen.display()

        if self.is_change:
            if selected_menu_num == 0:
                # Verify this change addr
                return Destination(PSBTSingleSigChangeVerificationView, view_args={"change_address_num": self.address_num})
            elif selected_menu_num == 1:
                # Skipping verification
                if self.address_num < len(psbt_parser.change_addresses) - 1:
                    return Destination(PSBTAddressDetailsView, view_args={"address_num": self.address_num + 1, "is_change": True})
                else:
                    # There's no more change to verify. Move on to sign the PSBT.
                    return Destination(MainMenuView, view_args={})

        elif selected_menu_num == 0:
            if self.address_num < len(psbt_parser.destination_addresses) - 1:
                # Show the next receive addr
                return Destination(PSBTAddressDetailsView, view_args={"address_num": self.address_num + 1, "is_change": False})

            elif psbt_parser.change_amount > 0:
                # Move on to display change
                return Destination(PSBTAddressDetailsView, view_args={"address_num": 0, "is_change": True})

            else:
                # There's no change output to verify. Move on to sign the PSBT.
                return Destination(MainMenuView, view_args={})

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class PSBTSingleSigChangeVerificationView(View):
    """
    """
    def __init__(self, change_address_num):
        super().__init__()
        self.change_address_num = change_address_num
    

    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTSingleSigChangeVerificationScreen

        psbt_parser: PSBTParser = self.controller.psbt_parser
        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)
        
        address = psbt_parser.change_addresses[self.change_address_num]
        threadsafe_counter = ThreadsafeCounter()

        change_verification_thread = ChangeVerificationThread(
            psbt_parser=psbt_parser,
            address=address,
            threadsafe_counter=threadsafe_counter
        )
        change_verification_thread.start()

        screen = PSBTSingleSigChangeVerificationScreen(
            change_address=psbt_parser.change_addresses[self.change_address_num],
            threadsafe_counter=threadsafe_counter,
        )
        selected_menu_num = screen.display()

        change_verification_thread.stop()

        if selected_menu_num == 0:
            if self.change_address_num < len(psbt_parser.change_addresses) - 1:
                # Show the next change addr
                return Destination(PSBTAddressDetailsView, view_args={"address_num": self.change_address_num + 1, "is_change": True})

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class ChangeVerificationThread(BaseThread):
    def __init__(self, psbt_parser: PSBTParser, address: str, threadsafe_counter: ThreadsafeCounter):
        super().__init__()
        self.psbt_parser = psbt_parser
        self.address = address
        self.threadsafe_counter = threadsafe_counter
        self.verified_index: int = 0
        self.verified_index_is_change: bool = None

        print("Instantiated verification thread")


    def run(self):
        while self.keep_running:
            # Do work to verify addr
            # ...

            # For now mocking that up with time consuming... sleep
            time.sleep(0.25)

            # Increment our index counter
            self.threadsafe_counter.increment()

            if self.threadsafe_counter.cur_count % 10 == 0:
                print(f"Incremented to {self.threadsafe_counter.cur_count}")

            # On successfully verifying addr, set:
            # self.verified_index = self.counter.cur_count
            # self.verified_index_is_change = True
            # break   # Will instance stick around if run() exits?

            # TODO: This should be in `Seed` or `PSBT` utility class
            # def verify_single_sig_addr(self, address:str):
            #     import embit
            #     network = embit.NETWORKS[self.settings.network]
            #     version = embit.bip32.detect_version(derivation, default="xpub", network=network)
            #     root = embit.bip32.HDKey.from_seed(seed.seed, version=network["xprv"])
            #     fingerprint = hexlify(root.child(0).fingerprint).decode('utf-8')
            #     xprv = root.derive(derivation)
            #     xpub = xprv.to_public()
            #     for i in range(500):
            #         r_pubkey = xpub.derive([0,i]).key
            #         c_pubkey = xpub.derive([1,i]).key
                    
            #         recieve_address = ""
            #         change_address = ""
                    
            #         if "P2PKH" in address_type:
            #             recieve_address = embit.script.p2pkh(r_pubkey).address(network=network)
            #             change_address = embit.script.p2pkh(c_pubkey).address(network=network)
            #         elif "Bech32" in address_type:
            #             recieve_address = embit.script.p2wpkh(r_pubkey).address(network=network)
            #             change_address = embit.script.p2wpkh(c_pubkey).address(network=network)
            #         elif "P2SH" in address_type:
            #             recieve_address = embit.script.p2sh(embit.script.p2wpkh(r_pubkey)).address(network=network)
            #             change_address = embit.script.p2sh(embit.script.p2wpkh(c_pubkey)).address(network=network)
                        
            #         if address == recieve_address:
            #             self.menu_view.draw_modal(["Receive Address "+str(i), "Verified"], "", "Right to Exit")
            #             input = self.buttons.wait_for([B.KEY_RIGHT])
            #             return Path.MAIN_MENU
            #         if address == change_address:
            #             self.menu_view.draw_modal(["Change Address "+str(i), "Verified"], "", "Right to Exit")
            #             input = self.buttons.wait_for([B.KEY_RIGHT])
            #             return Path.MAIN_MENU
            #         else:
            #             self.menu_view.draw_modal(["Checking Address "+str(i), "..."], "", "Right to Abort")
            #             if self.buttons.check_for_low(B.KEY_RIGHT) or self.buttons.check_for_low(B.KEY_LEFT):
            #                 return Path.MAIN_MENU
