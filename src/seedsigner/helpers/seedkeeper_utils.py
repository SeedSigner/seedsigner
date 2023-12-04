from pysatochip.CardConnector import CardConnector
from pysatochip.JCconstants import SEEDKEEPER_DIC_TYPE, SEEDKEEPER_DIC_ORIGIN, SEEDKEEPER_DIC_EXPORT_RIGHTS
from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen,
    WarningScreen, DireWarningScreen, seed_screens, LargeIconStatusScreen)

import os
import time
from os import urandom

def init_seedkeeper(parentObject):
    # os.system("ifdnfc-activate")
    # time.sleep(0.1)  # give some time to initialize reader...

    # Spam connecting for 10 seconds to give the user time to insert the card
    status = None
    time_end = time.time() + 10
    while time.time() < time_end:
        try:
            Satochip_Connector = CardConnector(card_filter="seedkeeper")
            time.sleep(0.1)  # give some time to initialize reader...
            status = Satochip_Connector.card_get_status()
            break
        except Exception as e:
            print(e)
            time.sleep(0.1) # Sleep for 100ms

    if not status:
        parentObject.run_screen(
            WarningScreen,
            title="Unable to Connect",
            status_headline=None,
            text=f"Unable to find SeedKeeper, missing card or missing reader",
            show_back_button=True,
        )
        return None

    status = Satochip_Connector.card_get_status()
    print("Found Card:")
    print(status[3])

    if (Satochip_Connector.needs_secure_channel):
        print("Initiating Secure Channel")
        Satochip_Connector.card_initiate_secure_channel()

    if status[3]['setup_done']:
        ret = seed_screens.SeedAddPassphraseScreen(title="Seedkeeper PIN").display()

        if ret == RET_CODE__BACK_BUTTON:
            return None
        
        Satochip_Connector.set_pin(0, list(bytes(ret, "utf-8")))

        try:
            print("Verifying PIN")
            (response, sw1, sw2) = Satochip_Connector.card_verify_PIN()
            print(response)
        except RuntimeError as e: #Incorrect PIN
            print(e) #
            status = Satochip_Connector.card_get_status()
            pin_tries_left = status[3]['PIN0_remaining_tries']
            if pin_tries_left == 0:
                parentObject.run_screen(
                    WarningScreen,
                    title="Card Blocked",
                    status_headline=None,
                    text=f"Incorrect-PIN entered too many times, card locked...",
                    show_back_button=True,
                )
            else:
                parentObject.run_screen(
                    WarningScreen,
                    title="Incorrect PIN",
                    status_headline=None,
                    text=f"Unable to unlock SeedKeeper, Incorrect PIN " + str(pin_tries_left) + " tries remain before card locks...",
                    show_back_button=True,
                )
            return None
    else:
        print("Seedkeeper Needs Initial Setup")
        parentObject.run_screen(
            WarningScreen,
            title="Seedkeeper Uninitialised",
            status_headline=None,
            text=f"Set a device PIN to complete Card Setup",
            show_back_button=True,
        )

        ret = seed_screens.SeedAddPassphraseScreen(title="Seedkeeper PIN").display()

        if ret == RET_CODE__BACK_BUTTON:
            return None
    
        """Run the initial card setup process"""
        pin_0 = list(ret.encode('utf8'))
        # Just stick with the defaults from SeedKeeper tool
        pin_tries_0 = 0x05
        ublk_tries_0 = 0x01
        # PUK code can be used when PIN is unknown and the card is locked
        # We use a random value as the PUK is not used currently and is not user friendly
        ublk_0 = list(urandom(16))
        pin_tries_1 = 0x01
        ublk_tries_1 = 0x01
        pin_1 = list(urandom(16))  # the second pin is not used currently
        ublk_1 = list(urandom(16))
        secmemsize = 32  # 0x0000 # => for satochip - TODO: hardcode value?
        memsize = 0x0000  # RFU
        create_object_ACL = 0x01  # RFU
        create_key_ACL = 0x01  # RFU
        create_pin_ACL = 0x01  # RFU

        (response, sw1, sw2) = Satochip_Connector.card_setup(pin_tries_0, ublk_tries_0, pin_0, ublk_0, pin_tries_1, ublk_tries_1, pin_1, ublk_1, secmemsize, memsize, create_object_ACL, create_key_ACL, create_pin_ACL, option_flags=0, hmacsha160_key=None, amount_limit=0)
        if sw1 != 0x90 or sw2 != 0x00:
            print("ERROR: Setup Failed")
            parentObject.run_screen(
                WarningScreen,
                title="Invalid PIN",
                status_headline=None,
                text=f"Invalid PIN entered, select another and try again.",
                show_back_button=True,
            )
            return None
        else:
            Satochip_Connector.set_pin(0, list(bytes(ret, "utf-8")))
            print("Setup Succeeded")
            parentObject.run_screen(
                LargeIconStatusScreen,
                title="Success",
                status_headline=None,
                text=f"Card Setup Complete",
                show_back_button=False,
            )

    return Satochip_Connector

                