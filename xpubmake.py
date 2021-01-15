import ST7789
import spidev as SPI
import RPi.GPIO as GPIO
import time
import getwords

from embit import script
from embit import bip32
from embit import bip39
from embit.networks import NETWORKS
from embit import psbt
from binascii import unhexlify, hexlify

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import qrcode

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

# Raspberry Pi pin configuration:
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

impact18 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
impact22 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 22)

def showqrcodes(xpubstring):
    localxpubstring = xpubstring

    # draw.rectangle((0, 0, width, height), outline=0, fill=0)
    # draw.text((20, 110), "Creating Animated QR Code...", fill="ORANGE", font=impact18)
    # disp.ShowImage(image, 0, 0)

    qrdata = localxpubstring

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
            time.sleep(0.2)
            showingqrs = False
        else:
            time.sleep(0.3)

def make_xpub(runstate):
    localrunstate = getwords.gather_24_words(runstate)

    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((20, 110), "Creating Animated QR Code", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

    seed = bip39.mnemonic_to_seed(localrunstate[1])
    root = bip32.HDKey.from_seed(seed)  # removed: version=NETWORKS["main"]["xprv"]

    # first let's get the root fingerprint
    fingerprint = root.child(0).fingerprint
    hardened_derivation = "m/48h/0h/0h/2h"

    # derive account according to bip84
    bip48_xprv = root.derive(hardened_derivation)

    # corresponding master public key:
    bip48_xpub = bip48_xprv.to_public()

    xpubstring = "[%s%s]%s" % (
        hexlify(fingerprint).decode('utf-8'),
        hardened_derivation[1:],
        bip48_xpub.to_base58(NETWORKS["main"]["Zpub"]))

    print(xpubstring)

    showqrcodes(xpubstring)

    localrunstate[0] = 0
    localrunstate[1] = ""

    print(localrunstate)

    return localrunstate