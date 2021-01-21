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

#initialize fonts
impact18 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
impact23 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 23)
impact50 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 50)

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

def displayfinalword(word24):
    finalwordwidth, finalwordheight = draw.textsize(word24, font=impact50)

    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((65, 60), "Word 24 is :", fill="ORANGE", font=impact23)
    draw.text(((240-finalwordwidth)/2, 90), word24, fill="ORANGE", font=impact50)

    draw.text((73, 210), "RIGHT to EXIT", fill="ORANGE", font=impact18)

    disp.ShowImage(image, 0, 0)

def get_word_24(runstate):
    localrunstate = runstate

    stringphrase = localrunstate[1] + " abandon"

    bytes = mnemonic_to_bytes(stringphrase, ignore_checksum=True)

    finalseed = mnemonic_from_bytes(bytes)

    splitseed = finalseed.split()

    word24 = splitseed[-1]

    displayword24runstate = 1
    while displayword24runstate == 1:
        displayfinalword(word24)
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            displayword24runstate = 0

    localrunstate[0] = 0
    localrunstate[1] = ""
    return localrunstate