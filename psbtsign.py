import getwords
import ST7789
import spidev as SPI
import RPi.GPIO as GPIO

import time
import subprocess

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from embit.bip39 import mnemonic_to_bytes
from embit.bip39 import mnemonic_from_bytes

import qrcode

from imutils.video import VideoStream
from pyzbar import pyzbar
import argparse
import datetime
import imutils
import time
import cv2

from embit import script
from embit import bip32
from embit import bip39
from embit.networks import NETWORKS
from embit import psbt
from binascii import unhexlify, hexlify
# base64 encoding
from binascii import a2b_base64, b2a_base64

#GPIO define
RST_PIN        = 25
CS_PIN         = 8
DC_PIN         = 24

KEY_UP_PIN     = 6
KEY_DOWN_PIN   = 19
KEY_LEFT_PIN   = 5
KEY_RIGHT_PIN  = 26
KEY_PRESS_PIN  = 13

KEY1_PIN       = 21
KEY2_PIN       = 20
KEY3_PIN       = 16

RST = 27
DC = 25
BL = 24
bus = 0
device = 0

#init GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(KEY_UP_PIN,      GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Input with pull-up
GPIO.setup(KEY_DOWN_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(KEY_LEFT_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(KEY_RIGHT_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(KEY_PRESS_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(KEY1_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
GPIO.setup(KEY2_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
GPIO.setup(KEY3_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up

# 240x240 display with hardware SPI:
disp = ST7789.ST7789(SPI.SpiDev(bus, device),RST, DC, BL)
disp.Init()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = 240
height = 240
image = Image.new('RGB', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

#initialize fonts
impact18 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
impact20 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 20)
impact22 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 22)

def scananimatedqr():
    vs = VideoStream(usePiCamera=True).start()  # For Pi Camera
    time.sleep(2.0)

    listofstrings = ["empty"]
    gotlistlength = False
    camerarunning = True

    while camerarunning == True:
        frame = vs.read()
        frame = imutils.resize(frame, width=400)
        barcodes = pyzbar.decode(frame)
        for barcode in barcodes:
            barcodeData = barcode.data.decode("utf-8")
            string = barcodeData
            firstnumberstring = string[1]
            secondnumberstring = string[4]
            if gotlistlength == False:
                stringcounter = int(secondnumberstring) - 1
                while stringcounter >= 1:
                    listofstrings.append("empty")
                    stringcounter = stringcounter - 1
                gotlistlength = True
            length = len(string)
            spacelocation = string.find(" ") + 1
            trimmedstring = string[spacelocation:length]
            listofstrings[int(firstnumberstring) - 1] = trimmedstring
            if "empty" not in listofstrings:
                camerarunning = False
        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            print("joystick pressed left")
            time.sleep(0.3)
            vs.stop()
            return "abort"


    qrcodevalue = ""
    vs.stop()
    return qrcodevalue.join(listofstrings)

def signtransaction(seedphrase, psbtstring):
    localseedphrase = seedphrase
    localpsbtstring = psbtstring
    seed = bip39.mnemonic_to_seed(localseedphrase)
    root = bip32.HDKey.from_seed(seed)  # removed: version=NETWORKS["main"]["xprv"]

    # first let's get the root fingerprint
    fingerprint = root.child(0).fingerprint
    hardened_derivation = "m/48h/0h/0h/2h"
    # derive account according to bip84
    bip48_xprv = root.derive(hardened_derivation)
    # corresponding master public key:
    bip48_xpub = bip48_xprv.to_public()
    print("[%s%s]%s" % (
        hexlify(fingerprint).decode('utf-8'),
        hardened_derivation[1:],
        bip48_xpub.to_base58())
          )

    # parse psbt transaction
    b64_psbt = localpsbtstring
    print("took in psbt string")
    # first convert it to binary
    raw = a2b_base64(b64_psbt)
    print("converted to binary")
    # then parse
    tx = psbt.PSBT.parse(raw)

    # print how much we are spending and where
    total_in = 0
    for inp in tx.inputs:
        total_in += inp.witness_utxo.value
    print("Inputs:", total_in, "satoshi")
    totalinputs = total_in

    change_out = 0  # value that goes back to us
    send_outputs = []
    for i, out in enumerate(tx.outputs):
        # check if it is a change or not:
        change = False
        # should be one or zero for single-key addresses
        for pub in out.bip32_derivations:
            # check if it is our key
            if out.bip32_derivations[pub].fingerprint == fingerprint:
                hdkey = root.derive(out.bip32_derivations[pub].derivation)
                mypub = hdkey.key.get_public_key()
                if mypub != pub:
                    raise ValueError("Derivation path doesn't look right")
                # now check if provided scriptpubkey matches
                sc = script.p2wpkh(mypub)
                if sc == tx.tx.vout[i].script_pubkey:
                    change = True
                    continue
        if change:
            change_out += tx.tx.vout[i].value
        else:
            send_outputs.append(tx.tx.vout[i])
    print("Spending", total_in - change_out, "satoshi")
    totalspending = total_in - change_out

    fee = total_in - change_out
    for out in send_outputs:
        fee -= out.value
        print(out.value, "to", out.script_pubkey.address())  # removed: NETWORKS["main"]
    print("Fee:", fee, "satoshi")
    totalfee = fee
    destinationaddress = out.script_pubkey.address()

    #display transaction information
    sendingamount = totalspending - totalfee
    displaytransactioninfo = True
    while displaytransactioninfo == True:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        textwidth, textheight = draw.textsize("Confirm last 10 chars", font=impact22)
        draw.text(((240 - textwidth) / 2, 5), "Confirm last 10 chars", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize("of the receiving address:", font=impact22)
        draw.text(((240 - textwidth) / 2, 30), "of the receiving address:", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(destinationaddress[-10:], font=impact22)
        draw.text(((240 - textwidth) / 2, 55), destinationaddress[-10:], fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize("Amount Sending:", font=impact22)
        draw.text(((240 - textwidth) / 2, 90), "Amount Sending:", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(str(sendingamount) + " satoshis", font=impact22)
        draw.text(((240 - textwidth) / 2, 115), str(sendingamount) + " satoshis", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize("Plus a fee of:", font=impact22)
        draw.text(((240 - textwidth) / 2, 150), "Plus a fee of:", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(str(totalfee) + " satoshis", font=impact22)
        draw.text(((240 - textwidth) / 2, 175), str(totalfee) + " satoshis", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize("Joystick Right to CONTINUE", font=impact18)
        draw.text(((240 - textwidth) / 2, 215), "Joystick Right to CONTINUE", fill="ORANGE", font=impact18)
        disp.ShowImage(image, 0, 0)
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            displaytransactioninfo = False

    # sign the transaction
    tx.sign_with(root)
    raw = tx.serialize()
    # convert to base64
    b64_psbt = b2a_base64(raw)
    # somehow b2a ends with \n...
    if b64_psbt[-1:] == b"\n":
        b64_psbt = b64_psbt[:-1]
    # print
    print("\nSigned transaction:")
    print(b64_psbt.decode('utf-8'))
    return b64_psbt.decode('utf-8')

def showqrcodes(signedpsbt):
    localsignedpsbt = signedpsbt

    #disp.clear()
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((20, 110), "Creating Animated QR Code...", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

    qrdata = localsignedpsbt

    stringlength = len(qrdata)

    # print("The length of the string is: " + str(stringlength))
    numofchunks = (stringlength // 100) + 1
    staticnumofchunks = numofchunks
    listcounter = 1

    start = 0
    stop = 99
    chunklist = ["p" + str(listcounter) + "of" + str(staticnumofchunks) + " " + qrdata[start:stop]]
    # print("The start is: " + str(start) + " and the end is: " + str(stop))
    print(chunklist[0])
    qrimagelist = [qrcode.make(chunklist[0]).resize((240, 240)).convert('RGB')]

    while numofchunks > 1:
        #draw.rectangle((0, 0, width, height), outline=0, fill=0)
        #draw.text((20, 110), "Creating Animated QR Code", fill="ORANGE", font=impact18)
        #disp.ShowImage(image, 0, 0)
        start = start + 100
        stop = stop + 100
        if stop > stringlength:
            stop = stringlength  # - 1
        chunklist.append("p" + str(listcounter + 1) + "of" + str(staticnumofchunks) + " " + qrdata[start - 1:stop])
        print(chunklist[listcounter])
        qrimagelist.append(qrcode.make(chunklist[listcounter]).resize((240, 240)).convert('RGB'))
        listcounter = listcounter + 1
        numofchunks = numofchunks - 1

    showingqrs = True
    displayedqr = 0

    while showingqrs == True:
        disp.ShowImage(qrimagelist[displayedqr], 0, 0)
        time.sleep(0.3)
        if displayedqr < staticnumofchunks - 1:
            displayedqr = displayedqr + 1
            time.sleep(0.3)
        else:
            displayedqr = 0
            time.sleep(0.3)
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.4)
            showingqrs = False
        else:
            time.sleep(0.3)

def sign_psbt(runstate):
    localrunstate = runstate

    if localrunstate[1] == "":
        localrunstate = getwords.gather_24_words(localrunstate)

    print("The selected seed is:")
    print(localrunstate[1])
    print("")

    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((20, 110), "Scan the Animated QR Code", fill="ORANGE", font=impact18)
    textwidth, textheight = draw.textsize("Press joystick LEFT to ABORT", font=impact18)
    draw.text(((240 - textwidth) / 2, 215), "Press joystick LEFT to ABORT", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

    importedpbststring = scananimatedqr()

    if importedpbststring == "abort":
        localrunstate[0] = 0
        localrunstate[1] = ""
        return localrunstate

    print("The selected PSBT is:")
    print(importedpbststring)
    print("")

    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    disp.ShowImage(image, 0, 0)

    signedpsbtstring = signtransaction(runstate[1], importedpbststring)

    showqrcodes(signedpsbtstring)

    localrunstate[0] = 0
    localrunstate[1] = ""

    print("You reached the end of the sign_psbt function.")

    return localrunstate
