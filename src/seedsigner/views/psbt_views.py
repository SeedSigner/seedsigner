import json

from embit import psbt
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
            pass

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class PSBTOverviewMockView(View):
    def run(self):
        from seedsigner.gui.screens.psbt_screens import PSBTOverviewScreen
        screen = PSBTOverviewScreen(
            spend_amount=384734,
            change_amount=84783,
            fee_amount=1313,
            num_inputs=2,
            destination_addresses=[
                "bc1q3lg2qc933hd4ke9xjwm68e3rxz94525d5vchy75",
                "bc1qkf4jqc933hd4ke9xjwm68e3rxz94525d5vchy75",
                # "bc1q9de6qc933hd4ke9xjwm68e3rxz94525d5vchy75",
                # "hello"
            ],
        )
        selected_menu_num = screen.display()

        if selected_menu_num == 0:
            return Destination(MainMenuView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
