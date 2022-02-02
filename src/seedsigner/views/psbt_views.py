import json

from seedsigner.models.psbt_parser import PSBTParser

from seedsigner.models.settings import SettingsConstants

from .view import BackStackView, MainMenuView, View, Destination

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonListScreen
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

        self.controller.psbt_parser = PSBTParser(
            self.controller.psbt,
            seed=self.seed,
            network=self.controller.settings.network
        )


    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTOverviewScreen
        psbt_parser: PSBTParser = self.controller.psbt_parser
        screen = PSBTOverviewScreen(
            spend_amount=psbt_parser.spend_amount,
            change_amount=psbt_parser.change_amount,
            fee_amount=psbt_parser.fee_amount,
            num_inputs=psbt_parser.num_inputs,
            destination_addresses=psbt_parser.destination_addresses,
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            return Destination(PSBTAddressDetailsView, view_args={"address_num": 0, "is_change": len(psbt_parser.destination_addresses) == 0})

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
        from seedsigner.gui.screens.psbt_screens import PSBTAddressDetailsScreen

        psbt_parser: PSBTParser = self.controller.psbt_parser
        if not psbt_parser:
            # Should not be able to get here
            return Destination(MainMenuView)
        

class PSBTScriptDetailsView(View):
    """
        Shows script type
    """
    pass



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

        if selected_menu_num == 0:
            if not self.is_change:
                if self.address_num < len(psbt_parser.destination_addresses) - 1:
                    # Show the next receive addr
                    return Destination(PSBTAddressDetailsView, view_args={"address_num": self.address_num + 1, "is_change": False})
                else:
                    # Move on to display change
                    return Destination(PSBTAddressDetailsView, view_args={"address_num": 0, "is_change": True})
            else:
                if self.address_num < len(psbt_parser.change_addresses) - 1:
                    # Show the next change addr
                    return Destination(PSBTAddressDetailsView, view_args={"address_num": self.address_num + 1, "is_change": True})
                else:
                    # Move on to display fee and sign PSBT
                    # TODO
                    return Destination(MainMenuView, view_args={})
 
        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)


"""
15 bcrt1q6tymx7mgag7806c53j895lnr5ka0jm3ut2w3n2 
1.48 2MsUBEppWxXfBa6REz2gtTDCGZHcvi27X3q 
21000 bcrt1q3ydh4j6as3h4eld8sfeyg8gllqd2s3fp0au99r9mgzkalpr262zqvj40kf 
"""
