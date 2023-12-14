from pysatochip.CardConnector import CardConnector
from pysatochip.JCconstants import SEEDKEEPER_DIC_TYPE, SEEDKEEPER_DIC_ORIGIN, SEEDKEEPER_DIC_EXPORT_RIGHTS
from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen,
    WarningScreen, DireWarningScreen, seed_screens, LargeIconStatusScreen)
from seedsigner.gui.screens.screen import LoadingScreenThread


import os
import time
from os import urandom

def init_seedkeeper(parentObject):
    parentObject.loading_screen = LoadingScreenThread(text="Searching for SeedKeeper")
    parentObject.loading_screen.start()

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

    parentObject.loading_screen.stop()

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

def run_globalplatform(parentObject, command, loadingText = "Loading", successtext = "Success"):
    from subprocess import run

    parentObject.loading_screen = LoadingScreenThread(text=loadingText)
    parentObject.loading_screen.start()

    commandString = "java -jar /home/pi/Satochip-DIY/gp.jar " + command

    data = run(commandString, capture_output=True, shell=True, text=True)
    parentObject.loading_screen.stop()

    print("StdOut:", data.stdout)
    print("StdErr:", data.stderr)

    #data.stderr = data.stderr.replace("Warning: no keys given, defaulting to 404142434445464748494A4B4C4D4E4F", "")

    data.stderr = data.stderr.split('\n')

    errors_cleaned = []
    for errorLine in data.stderr:
        if "[INFO]" in errorLine: 
            continue
        elif "404142434445464748494A4B4C4D4E4F" in errorLine:
            continue
        elif len(errorLine) < 1:
            continue

        errors_cleaned.append(errorLine)

    print("StdErr (Cleaned):", errors_cleaned)

    errors_cleaned = " ".join(errors_cleaned)

    if len(errors_cleaned) > 1:
        # If it fails, report the error back (And make it more human readable for common errors)
        failureText = errors_cleaned
        if "is not present on card" in errors_cleaned:
            failureText = "Applet is not on the card, nothing to uninstall..."

        if "Multiple readers, must choose one" in errors_cleaned:
            failureText = "Multiple readers connected, please run with a single reader connected/activated..."

        if " Card cryptogram invalid" in errors_cleaned:
            failureText = "Card is locked with custom keys. Please refer to the Satochip-DIY documentation..."

        if "SCARD_E_NO_SMARTCARD" in errors_cleaned:
            failureText = "Unable to detect Card and/or Reader..."

        if "Applet loading not allowed" in errors_cleaned:
            failureText = "Applet is already installed..."

        if "0x6444" in errors_cleaned or "0x6F00" in errors_cleaned:
            failureText = "Incompatible Javacard..."

        if "Not enough memory space" in errors_cleaned:
            failureText = "Not enough space on Javacard for Applet..."

        if "SCARD_E_NO_SMARTCARD" in errors_cleaned:
            failureText = "Unable to detect Card and/or Reader..."

        parentObject.run_screen(
            WarningScreen,
            title="Failed",
            status_headline=None,
            text=failureText,
            show_back_button=False,
        )

        return None

    else:
        if successtext:
            print(successtext)
            parentObject.run_screen(
                LargeIconStatusScreen,
                title="Success",
                status_headline=None,
                text=successtext,
                show_back_button=False,
            )

        return data.stdout