import ST7789
import spidev as SPI
import RPi.GPIO as GPIO

import subprocess

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from subprocess import call

from pyzbar import pyzbar
import argparse
import datetime
import time
import re

from embit.bip39 import mnemonic_to_bytes
from embit.bip39 import mnemonic_from_bytes
from embit import script
from embit import bip32
from embit import bip39
from embit.networks import NETWORKS
from embit import psbt
from embit import ec

from io import BytesIO

from binascii import unhexlify, hexlify, a2b_base64, b2a_base64
from bcur import bcur_decode, cbor_decode, bc32decode, bc32encode, cbor_encode, bcur_encode

import qrcode

import textwrap

import threading

# delayed import variables saved in global namespace
delayed_import_complete_ind = 0
imutils = None
cv2 = None
VideoStream = None

# delayed import funtion for long running imports
def delayed_import():
    global start_time
    global delayed_import_complete_ind
    global imutils, cv2, pyzbar, VideoStream
    import imutils
    import cv2
    from imutils.video import VideoStream
    delayed_import_complete_ind = 1
    return

# add delayed_import function to thread
delayed_import_thread = threading.Thread(target=delayed_import)

# USE CTL+F to locate the following "modules"
# MENU MODULE
# IO TEST MODULE
# GETWORDS MODULE
# GETLASTWORD MODULE
# DICE MODULE
# XPUBMAKE MODULE
# PSBTSIGN MODULE

version = "0.3.0"
currentnetwork = "main"
hardened_derivation = "m/48h/0h/0h/2h"
qrsize = 100

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

# Define necessart fonts
impact16 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 16)
impact18 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
impact20 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 20)
impact22 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 22)
impact23 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 23)
impact25 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 25)
impact26 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 26)
impact35 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 35)
impact50 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 50)
couriernew30 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/courbd.ttf', 30)

activeseedsaveslot = 0
savedseed1status = "[  ]"
savedseed2status = "[  ]"
savedseed3status = "[  ]"

qr_type_ur1_ind = 0
qr_type_specter_ind = 0

# BEGIN MENU MODULE
# BEGIN MENU MODULE
# BEGIN MENU MODULE

def menu_elevator(selected, numoptions):
    if GPIO.input(KEY_UP_PIN) == GPIO.LOW:
        if selected == 1:
            selected = numoptions
            time.sleep(0.2)
        else:
            selected = selected - 1
            time.sleep(0.2)
        print("The menu state is: " + str(selected))

    if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:
        if selected == numoptions:
            selected = 1
            time.sleep(0.2)
        else:
            selected = selected + 1
            time.sleep(0.2)
        print("The menu state is: " + str(selected))

    return selected

def powering_down_notifier(runstate):
    localrunstate = runstate

    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    line1 = "Powering Down..."
    line2 = "Please wait about"
    line3 = "30 seconds before"
    line4 = "disconnecting power."

    textwidth, textheight = draw.textsize(line1, font=impact22)
    draw.text(((240-textwidth)/2, 45), line1, fill="ORANGE", font=impact22)
    textwidth, textheight = draw.textsize(line2, font=impact20)
    draw.text(((240-textwidth)/2, 100), line2, fill="ORANGE", font=impact20)
    textwidth, textheight = draw.textsize(line3, font=impact20)
    draw.text(((240-textwidth)/2, 130), line3, fill="ORANGE", font=impact20)
    textwidth, textheight = draw.textsize(line4, font=impact20)
    draw.text(((240-textwidth)/2, 160), line4, fill="ORANGE", font=impact20)
    disp.ShowImage(image, 0, 0)

    call("sudo shutdown --poweroff now", shell=True)

#MAIN MENU FUNCTIONS BELOW
#MAIN MENU FUNCTIONS BELOW
#MAIN MENU FUNCTIONS BELOW

def main_loading():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((35, 2), "SeedSigner  v" + version, fill="ORANGE", font=impact22)
    draw.text((80, 100), "Starting ...", fill="ORANGE", font=impact20)
    disp.ShowImage(image, 0, 0)

def main_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((35, 2), "SeedSigner  v" + version, fill="ORANGE", font=impact22)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Seed Tools", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Signing Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Settings", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 145, 210, 170), outline=0, fill="ORANGE")
    draw.text((15, 150), "Power OFF Device", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def main_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((35, 2), "SeedSigner  v" + version, fill="ORANGE", font=impact22)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Seed Tools", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Signing Tools", fill="BLACK", font=impact20)
    #draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Settings", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 145, 210, 170), outline=0, fill="ORANGE")
    draw.text((15, 150), "Power OFF Device", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def main_option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((35, 2), "SeedSigner  v" + version, fill="ORANGE", font=impact22)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Seed Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Signing Tools", fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Settings", fill="BLACK", font=impact20)
    #draw.rectangle((5, 145, 210, 170), outline=0, fill="ORANGE")
    draw.text((15, 150), "Power OFF Device", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def main_option4():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((35, 2), "SeedSigner  v" + version, fill="ORANGE", font=impact22)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Seed Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Signing Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Settings", fill="ORANGE", font=impact20)
    draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Power OFF Device", fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def main_menu(runstate):
    localrunstate = runstate
    running = True
    optionselected = 1

    # only used the first time seedsigner starts
    while delayed_import_complete_ind == 0:
        main_loading()
        if delayed_import_thread.is_alive() == False and delayed_import_complete_ind == 0:
            # when delayed_import_thread is not alive and not complete, then start import
            delayed_import_thread.start()
        time.sleep(0.1)

    while running == True:
        optionselected = menu_elevator(optionselected, 4)
        if optionselected == 1:
            main_option1()
        if optionselected == 2:
            main_option2()
        if optionselected == 3:
            main_option3()
        if optionselected == 4:
            main_option4()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 1
                return localrunstate
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 2
                return localrunstate
            if optionselected == 3:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 3
                return localrunstate
            if optionselected == 4:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 58
                #powering_down_notifier()
                #call("sudo shutdown --poweroff now", shell=True)


# SETTINGS MENU FUNCTIONS BELOW
# SETTINGS MENU FUNCTIONS BELOW
# SETTINGS MENU FUNCTIONS BELOW

def settings_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Settings (1/2)", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Settings (1/2)", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Input / Output Tests", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 135, 210, 170), outline=0, fill="ORANGE")
    draw.text((15, 115), "Current Network: " + currentnetwork, fill="ORANGE", font=impact20)
    # draw.rectangle((5, 170, 210, 205), outline=0, fill="ORANGE")
    draw.text((15, 150), "Version Info", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 170, 210, 205), outline=0, fill="ORANGE")
    #draw.text((15, 175), "Donate to SeedSigner", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def settings_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Settings (1/2)", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Settings (1/2)", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Input / Output Tests", fill="BLACK", font=impact20)
    # draw.rectangle((5, 135, 210, 170), outline=0, fill="ORANGE")
    draw.text((15, 115), "Current Network: " + currentnetwork, fill="ORANGE", font=impact20)
    # draw.rectangle((5, 170, 210, 205), outline=0, fill="ORANGE")
    draw.text((15, 150), "Version Info", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 170, 210, 205), outline=0, fill="ORANGE")
    # draw.text((15, 175), "Donate to SeedSigner", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def settings_option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Settings (1/2)", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Settings (1/2)", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Input / Output Tests", fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Current Network: " + currentnetwork, fill="BLACK", font=impact20)
    # draw.rectangle((5, 170, 210, 205), outline=0, fill="ORANGE")
    draw.text((15, 150), "Version Info", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 170, 210, 205), outline=0, fill="ORANGE")
    # draw.text((15, 175), "Donate to SeedSigner", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def settings_option4():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Settings (1/2)", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Settings (1/2)", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Input / Output Tests", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 135, 210, 170), outline=0, fill="ORANGE")
    draw.text((15, 115), "Current Network: " + currentnetwork, fill="ORANGE", font=impact20)
    draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Version Info", fill="BLACK", font=impact20)
    # draw.rectangle((5, 170, 210, 205), outline=0, fill="ORANGE")
    # draw.text((15, 175), "Donate to SeedSigner", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def settings_option5():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Settings (2/2)", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Settings (2/2)", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    #draw.text((15, 45), "... ( return to MAIN )", fill="BLACK", font=impact20)
    # draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    #draw.text((15, 85), "Input / Output Tests", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 135, 210, 170), outline=0, fill="ORANGE")
    #draw.text((15, 120), "Current Network: " + currentnetwork, fill="ORANGE", font=impact20)
    # draw.rectangle((5, 170, 210, 205), outline=0, fill="ORANGE")
    #draw.text((15, 155), "Version Info", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Donate to SeedSigner", fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def settings_menu(runstate):
    localrunstate = runstate
    running = True
    optionselected = 1
    while running == True:
        optionselected = menu_elevator(optionselected, 5)
        if optionselected == 1:
            settings_option1()
        if optionselected == 2:
            settings_option2()
        if optionselected == 3:
            settings_option3()
        if optionselected == 4:
            settings_option4()
        if optionselected == 5:
            settings_option5()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 0
                return localrunstate
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 50
                return localrunstate
            if optionselected == 3:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 61
                return localrunstate
            if optionselected == 4:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 57
                return localrunstate
            if optionselected == 5:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 56
                return localrunstate

#SEED GENERATION TOOLS MENU
#SEED GENERATION TOOLS MENU
#SEED GENERATION TOOLS MENU

def seedselect_menu_option1():
    global savedseed1status, savedseed2status, savedseed3status
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Select a Seed Slot", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Select a Seed Slot", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="BLACK", font=impact20)
    # draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use Seed Slot #1 " + savedseed1status, fill="ORANGE", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use Seed Slot #2 " + savedseed2status, fill="ORANGE", font=impact20)
    # draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Use Seed Slot #3 " + savedseed3status, fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedselect_menu_option2():
    global savedseed1status, savedseed2status, savedseed3status
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Select a Seed Slot", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Select a Seed Slot", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use Seed Slot #1 " + savedseed1status, fill="BLACK", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use Seed Slot #2 " + savedseed2status, fill="ORANGE", font=impact20)
    # draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Use Seed Slot #3 " + savedseed3status, fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedselect_menu_option3():
    global savedseed1status, savedseed2status, savedseed3status
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Select a Seed Slot", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Select a Seed Slot", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use Seed Slot #1 " + savedseed1status, fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use Seed Slot #2 " + savedseed2status, fill="BLACK", font=impact20)
    # draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Use Seed Slot #3 " + savedseed3status, fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedselect_menu_option4():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Select a Seed Slot", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Select a Seed Slot", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use Seed Slot #1 " + savedseed1status, fill="ORANGE", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use Seed Slot #2" + savedseed2status, fill="ORANGE", font=impact20)
    draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Use Seed Slot #3" + savedseed3status, fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedselect_menu(runstate):
    global activeseedsaveslot
    global savedseed1status
    global savedseed2status
    global savedseed3status
    localrunstate = runstate
    running = True
    optionselected = 1
    if localrunstate[2][0] == "":
        savedseed1status = ""
    else:
        savedseed1status = "   +"
    if localrunstate[2][1] == "":
        savedseed2status = ""
    else:
        savedseed2status = "   +"
    if localrunstate[2][2] == "":
        savedseed3status = ""
    else:
        savedseed3status = "   +"
    while running == True:
        optionselected = menu_elevator(optionselected, 4)
        if optionselected == 1:
            seedselect_menu_option1()
        if optionselected == 2:
            seedselect_menu_option2()
        if optionselected == 3:
            seedselect_menu_option3()
        if optionselected == 4:
            seedselect_menu_option4()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 0
                return localrunstate
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                activeseedsaveslot = 1
                localrunstate[0] = 63
                return localrunstate
            if optionselected == 3:
                time.sleep(0.2)
                running = False
                activeseedsaveslot = 2
                localrunstate[0] = 63
                return localrunstate
            if optionselected == 4:
                time.sleep(0.2)
                running = False
                activeseedsaveslot = 3
                localrunstate[0] = 63
                return localrunstate

def seedgen_menu_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Seed Tools", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Seed Tools", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Generate Word 12 / 24", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Create a Seed w/ Dice", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Store a Seed (temp)", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedgen_menu_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Seed Tools", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Seed Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Generate Word 12 / 24", fill="BLACK", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Create a Seed w/ Dice", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Store a Seed (temp)", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedgen_menu_option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Seed Tools", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Seed Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Generate Word 12 / 24", fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Create a Seed w/ Dice", fill="BLACK", font=impact20)
    # draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Store a Seed (temp)", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedgen_menu_option4():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Seed Tools", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Seed Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Generate Word 12 / 24", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Create a Seed w/ Dice", fill="ORANGE", font=impact20)
    draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "Store a Seed (temp)", fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedgen_menu(runstate):
    localrunstate = runstate
    running = True
    optionselected = 1
    while running == True:
        optionselected = menu_elevator(optionselected, 4)
        if optionselected == 1:
            seedgen_menu_option1()
        if optionselected == 2:
            seedgen_menu_option2()
        if optionselected == 3:
            seedgen_menu_option3()
        if optionselected == 4:
            seedgen_menu_option4()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 0
                return localrunstate
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 51
                return localrunstate
            if optionselected == 3:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 53
                return localrunstate
            if optionselected == 4:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 62
                return localrunstate

def decideifusedsavedwords_menu_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Use a saved seed?", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Use a saved seed?", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Yes", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "No", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def decideifusedsavedwords_menu_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Use a saved seed?", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Use a saved seed?", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Yes", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "No", fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def decideifusesavedwords():
    running = True
    optionselected = 1
    while running == True:
        optionselected = menu_elevator(optionselected, 2)
        if optionselected == 1:
            decideifusedsavedwords_menu_option1()
        if optionselected == 2:
            decideifusedsavedwords_menu_option2()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                running = False
                return "yes"
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                return "no"

#SIGNING TOOLS MENU
#SIGNING TOOLS MENU
#SIGNING TOOLS MENU

def signing_menu_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((60, 2), "Signing Tools", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Generate XPUB", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Sign a Transaction", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def signing_menu_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((60, 2), "Signing Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Generate XPUB", fill="BLACK", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Sign a Transaction", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def signing_menu_option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((60, 2), "Signing Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Generate XPUB", fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Sign a Transaction", fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def signing_menu(runstate):
    localrunstate = runstate
    running = True
    optionselected = 1
    while running == True:
        optionselected = menu_elevator(optionselected, 3)
        if optionselected == 1:
            signing_menu_option1()
        if optionselected == 2:
            signing_menu_option2()
        if optionselected == 3:
            signing_menu_option3()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 0
                return localrunstate
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 54
                return localrunstate
            if optionselected == 3:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 55
                return localrunstate

#DONATE MENU
#DONATE MENU
#DONATE MENU

def donate(runstate):
    localrunstate = runstate

    running1 = True
    running2 = True
    while running1 == True:
        line1 = "You can support"
        line2 = "SeedSigner by donating"
        line3 = "any amount of BTC."
        line4 = "Thank You!!!"
        line5 = "(Press right for a QR code)"

        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        textwidth, textheight = draw.textsize(line1, font=impact22)
        draw.text(((240 - textwidth) / 2, 20), line1, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line2, font=impact22)
        draw.text(((240 - textwidth) / 2, 55), line2, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line3, font=impact22)
        draw.text(((240 - textwidth) / 2, 90), line3, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line4, font=impact22)
        draw.text(((240 - textwidth) / 2, 125), line4, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line5, font=impact22)
        draw.text(((240 - textwidth) / 2, 190), line5, fill="ORANGE", font=impact22)
        disp.ShowImage(image, 0, 0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.4)
            running1 = False

    donationqr = qrcode.make("bc1q8u3dyltlg6pu56fe7m58aqz9cwrfld0s03zlrjl0wvm9x4nfa60q2l0g97").resize(
        (240, 240)).convert('RGB')

    while running2 == True:
        disp.ShowImage(donationqr, 0, 0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.4)
            running2 = False

    localrunstate[0] = 3

    return localrunstate

#VERSTION MENU
#VERSTION MENU
#VERSTION MENU

def version_info(runstate):
    localrunstate = runstate

    running = True
    while running == True:
        line1 = "SeedSigner"
        line2 = "Version " + version
        line3 = "built for use with"
        line4 = "Specter-desktop"
        line5 = "v1.1.0 or higher"
        line6 = "(Joystick RIGHT to EXIT)"

        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        textwidth, textheight = draw.textsize(line1, font=impact22)
        draw.text(((240 - textwidth) / 2, 20), line1, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line2, font=impact22)
        draw.text(((240 - textwidth) / 2, 55), line2, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line3, font=impact22)
        draw.text(((240 - textwidth) / 2, 90), line3, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line4, font=impact22)
        draw.text(((240 - textwidth) / 2, 125), line4, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line5, font=impact22)
        draw.text(((240 - textwidth) / 2, 160), line5, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line6, font=impact18)
        draw.text(((240 - textwidth) / 2, 210), line6, fill="ORANGE", font=impact18)
        disp.ShowImage(image, 0, 0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.4)
            running = False

    localrunstate[0] = 3

    return localrunstate

#SELECT NUMBER OF WORDS MENU
#SELECT NUMBER OF WORDS MENU
#SELECT NUMBER OF WORDS MENU

def numofwords_menu_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("12 or 24 Word Seed?", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "12 or 24 Word Seed?", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use a 12 word seed", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use a 24 word seed", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def numofwords_menu_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("12 or 24 Word Seed?", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "12 or 24 Word Seed?", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use a 12 word seed", fill="BLACK", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use a 24 word seed", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def numofwords_menu_option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("12 or 24 Word Seed?", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "12 or 24 Word Seed?", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use a 12 word seed", fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use a 24 word seed", fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def numofwords_menu():
    running = True
    optionselected = 1
    while running == True:
        optionselected = menu_elevator(optionselected, 3)
        if optionselected == 1:
            numofwords_menu_option1()
        if optionselected == 2:
            numofwords_menu_option2()
        if optionselected == 3:
            numofwords_menu_option3()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                running = False
                return "abort"
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                return 12
            if optionselected == 3:
                time.sleep(0.2)
                running = False
                return 24

# SELECT NETWORK MENU
# SELECT NETWORK MENU
# SELECT NETWORK MENU

def network_menu_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Which Network?", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Which Network?", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to SETTINGS )", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use Mainnet", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use Testnet", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def network_menu_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Which Network?", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Which Network?", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to SETTINGS )", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use Mainnet", fill="BLACK", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use Testnet", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def network_menu_option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Which Network?", font=impact20)
    draw.text(((240 - textwidth) / 2, 2), "Which Network?", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "... ( return to SETTINGS )", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Use Mainnet", fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Use Testnet", fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def network_menu(runstate):
    localrunstate = runstate

    global currentnetwork
    global hardened_derivation

    running = True
    optionselected = 1
    while running == True:
        optionselected = menu_elevator(optionselected, 3)
        if optionselected == 1:
            network_menu_option1()
        if optionselected == 2:
            network_menu_option2()
        if optionselected == 3:
            network_menu_option3()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                localrunstate[0] = 3
                running = False
                return localrunstate
            if optionselected == 2:
                time.sleep(0.2)
                currentnetwork = "main"
                hardened_derivation = "m/48h/0h/0h/2h"
                localrunstate[0] = 3
                running = False
                return localrunstate
            if optionselected == 3:
                time.sleep(0.2)
                currentnetwork = "test"
                hardened_derivation = "m/48h/1h/0h/2h"
                localrunstate[0] = 3
                running = False
                return localrunstate

# BEGIN IO TEST MODULE
# BEGIN IO TEST MODULE
# BEGIN IO TEST MODULE

def iotestscreen(runstate):
    localrunstate = runstate

    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Initializing I/O Test", font=impact22)
    draw.text(((240 - textwidth) / 2, 100), "Initializing I/O Test", fill="ORANGE", font=impact22)
    disp.ShowImage(image, 0, 0)

    scannedqrs = 0
    vs = VideoStream(usePiCamera=True).start()  # For Pi Camera
    time.sleep(2.0)

    draw.rectangle((0,0,width,height), outline=0, fill=0)
    draw.text((45, 5), "Input/Output Check:", fill="ORANGE", font=impact18)
    draw.polygon([(61, 89), (80, 46), (99, 89)], outline="ORANGE", fill=0)
    draw.polygon([(51, 100), (8, 119), (51, 138)], outline="ORANGE", fill=0)
    draw.polygon([(109, 100), (152, 119), (109, 138)], outline="ORANGE", fill=0)
    draw.polygon([(61, 151), (80, 193), (99, 151)], outline="ORANGE", fill=0)
    draw.ellipse([(61, 99), (99, 141)], outline="ORANGE", fill=0)
    draw.ellipse([(198, 40), (238, 80)], outline="ORANGE", fill=0)
    draw.ellipse([(198, 95), (238, 135)], outline="ORANGE", fill=0)
    draw.text((200, 160), "EXIT", fill="ORANGE", font=impact18)
    prescantext = "Scan ANY QR Code"
    textwidth, textheight = draw.textsize(prescantext, font=impact22)
    draw.text(((240 - textwidth) / 2, 205), prescantext, fill="ORANGE", font=impact22)
    disp.ShowImage(image, 0, 0)

    running = True


    while running == True:
        frame = vs.read()
        frame = imutils.resize(frame, width=400)
        barcodes = pyzbar.decode(frame)
        for barcode in barcodes:
            scannedqrs += 1
            #time.sleep(0.1)
        #time.sleep(0.05)

        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((45, 5), "Input/Output Check:", fill="ORANGE", font=impact18)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            #time.sleep(0.1)
            draw.polygon([(61, 89), (80, 46), (99, 89)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(61, 89), (80, 46), (99, 89)], outline="ORANGE", fill=0)

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            #time.sleep(0.1)
            draw.polygon([(51, 100), (8, 119), (51, 138)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(51, 100), (8, 119), (51, 138)], outline="ORANGE", fill=0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            #time.sleep(0.1)
            draw.polygon([(109, 100), (152, 119), (109, 138)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(109, 100), (152, 119), (109, 138)], outline="ORANGE", fill=0)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            #time.sleep(0.1)
            draw.polygon([(61, 151), (80, 193), (99, 151)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(61, 151), (80, 193), (99, 151)], outline="ORANGE", fill=0)

        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:  # button is released
            #time.sleep(0.1)
            draw.ellipse([(61, 99), (99, 141)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.ellipse([(61, 99), (99, 141)], outline="ORANGE", fill=0)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            #time.sleep(0.1)
            draw.ellipse([(198, 40), (238, 80)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.ellipse([(198, 40), (238, 80)], outline="ORANGE", fill=0)

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            #time.sleep(0.1)
            draw.ellipse([(198, 95), (238, 135)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.ellipse([(198, 95), (238, 135)], outline="ORANGE", fill=0)

        draw.text((200, 160), "EXIT", fill="ORANGE", font=impact18)

        scansuccesstext = "QR code scanned!"
        if scannedqrs == 0:
            textwidth, textheight = draw.textsize(prescantext, font=impact22)
            draw.text(((240-textwidth)/2, 205), prescantext, fill="ORANGE", font=impact22)
        elif scannedqrs % 2 == 1:
            textwidth, textheight = draw.textsize(scansuccesstext, font=impact22)
            draw.rectangle((30, 205, 210, 235), outline="ORANGE", fill="ORANGE")
            draw.text(((240 - textwidth) / 2, 205), scansuccesstext, fill="BLACK", font=impact22)
        elif scannedqrs % 2 == 0:
            textwidth, textheight = draw.textsize(scansuccesstext, font=impact22)
            draw.rectangle((30, 205, 210, 235), outline="ORANGE", fill="BLACK")
            draw.text(((240 - textwidth) / 2, 205), scansuccesstext, fill="ORANGE", font=impact22)

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.4)
            vs.stop()
            running = False
            localrunstate[0] = 3
            return localrunstate

        disp.ShowImage(image,0,0)

    print("You exited the i o test module")

# GETWORDS MODULE
# GETWORDS MODULE
# GETWORDS MODULE

#alphabet reference
alphabet = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]

#seed reference
seedwords = ["abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual", "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance", "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent", "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol", "alert", "alien", "all", "alley", "allow", "almost", "alone", "alpha", "already", "also", "alter", "always", "amateur", "amazing", "among", "amount", "amused", "analyst", "anchor", "ancient", "anger", "angle", "angry", "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique", "anxiety", "any", "apart", "apology", "appear", "apple", "approve", "april", "arch", "arctic", "area", "arena", "argue", "arm", "armed", "armor", "army", "around", "arrange", "arrest", "arrive", "arrow", "art", "artefact", "artist", "artwork", "ask", "aspect", "assault", "asset", "assist", "assume", "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract", "auction", "audit", "august", "aunt", "author", "auto", "autumn", "average", "avocado", "avoid", "awake", "aware", "away", "awesome", "awful", "awkward", "axis", "baby", "bachelor", "bacon", "badge", "bag", "balance", "balcony", "ball", "bamboo", "banana", "banner", "bar", "barely", "bargain", "barrel", "base", "basic", "basket", "battle", "beach", "bean", "beauty", "because", "become", "beef", "before", "begin", "behave", "behind", "believe", "below", "belt", "bench", "benefit", "best", "betray", "better", "between", "beyond", "bicycle", "bid", "bike", "bind", "biology", "bird", "birth", "bitter", "black", "blade", "blame", "blanket", "blast", "bleak", "bless", "blind", "blood", "blossom", "blouse", "blue", "blur", "blush", "board", "boat", "body", "boil", "bomb", "bone", "bonus", "book", "boost", "border", "boring", "borrow", "boss", "bottom", "bounce", "box", "boy", "bracket", "brain", "brand", "brass", "brave", "bread", "breeze", "brick", "bridge", "brief", "bright", "bring", "brisk", "broccoli", "broken", "bronze", "broom", "brother", "brown", "brush", "bubble", "buddy", "budget", "buffalo", "build", "bulb", "bulk", "bullet", "bundle", "bunker", "burden", "burger", "burst", "bus", "business", "busy", "butter", "buyer", "buzz", "cabbage", "cabin", "cable", "cactus", "cage", "cake", "call", "calm", "camera", "camp", "can", "canal", "cancel", "candy", "cannon", "canoe", "canvas", "canyon", "capable", "capital", "captain", "car", "carbon", "card", "cargo", "carpet", "carry", "cart", "case", "cash", "casino", "castle", "casual", "cat", "catalog", "catch", "category", "cattle", "caught", "cause", "caution", "cave", "ceiling", "celery", "cement", "census", "century", "cereal", "certain", "chair", "chalk", "champion", "change", "chaos", "chapter", "charge", "chase", "chat", "cheap", "check", "cheese", "chef", "cherry", "chest", "chicken", "chief", "child", "chimney", "choice", "choose", "chronic", "chuckle", "chunk", "churn", "cigar", "cinnamon", "circle", "citizen", "city", "civil", "claim", "clap", "clarify", "claw", "clay", "clean", "clerk", "clever", "click", "client", "cliff", "climb", "clinic", "clip", "clock", "clog", "close", "cloth", "cloud", "clown", "club", "clump", "cluster", "clutch", "coach", "coast", "coconut", "code", "coffee", "coil", "coin", "collect", "color", "column", "combine", "come", "comfort", "comic", "common", "company", "concert", "conduct", "confirm", "congress", "connect", "consider", "control", "convince", "cook", "cool", "copper", "copy", "coral", "core", "corn", "correct", "cost", "cotton", "couch", "country", "couple", "course", "cousin", "cover", "coyote", "crack", "cradle", "craft", "cram", "crane", "crash", "crater", "crawl", "crazy", "cream", "credit", "creek", "crew", "cricket", "crime", "crisp", "critic", "crop", "cross", "crouch", "crowd", "crucial", "cruel", "cruise", "crumble", "crunch", "crush", "cry", "crystal", "cube", "culture", "cup", "cupboard", "curious", "current", "curtain", "curve", "cushion", "custom", "cute", "cycle", "dad", "damage", "damp", "dance", "danger", "daring", "dash", "daughter", "dawn", "day", "deal", "debate", "debris", "decade", "december", "decide", "decline", "decorate", "decrease", "deer", "defense", "define", "defy", "degree", "delay", "deliver", "demand", "demise", "denial", "dentist", "deny", "depart", "depend", "deposit", "depth", "deputy", "derive", "describe", "desert", "design", "desk", "despair", "destroy", "detail", "detect", "develop", "device", "devote", "diagram", "dial", "diamond", "diary", "dice", "diesel", "diet", "differ", "digital", "dignity", "dilemma", "dinner", "dinosaur", "direct", "dirt", "disagree", "discover", "disease", "dish", "dismiss", "disorder", "display", "distance", "divert", "divide", "divorce", "dizzy", "doctor", "document", "dog", "doll", "dolphin", "domain", "donate", "donkey", "donor", "door", "dose", "double", "dove", "draft", "dragon", "drama", "drastic", "draw", "dream", "dress", "drift", "drill", "drink", "drip", "drive", "drop", "drum", "dry", "duck", "dumb", "dune", "during", "dust", "dutch", "duty", "dwarf", "dynamic", "eager", "eagle", "early", "earn", "earth", "easily", "east", "easy", "echo", "ecology", "economy", "edge", "edit", "educate", "effort", "egg", "eight", "either", "elbow", "elder", "electric", "elegant", "element", "elephant", "elevator", "elite", "else", "embark", "embody", "embrace", "emerge", "emotion", "employ", "empower", "empty", "enable", "enact", "end", "endless", "endorse", "enemy", "energy", "enforce", "engage", "engine", "enhance", "enjoy", "enlist", "enough", "enrich", "enroll", "ensure", "enter", "entire", "entry", "envelope", "episode", "equal", "equip", "era", "erase", "erode", "erosion", "error", "erupt", "escape", "essay", "essence", "estate", "eternal", "ethics", "evidence", "evil", "evoke", "evolve", "exact", "example", "excess", "exchange", "excite", "exclude", "excuse", "execute", "exercise", "exhaust", "exhibit", "exile", "exist", "exit", "exotic", "expand", "expect", "expire", "explain", "expose", "express", "extend", "extra", "eye", "eyebrow", "fabric", "face", "faculty", "fade", "faint", "faith", "fall", "false", "fame", "family", "famous", "fan", "fancy", "fantasy", "farm", "fashion", "fat", "fatal", "father", "fatigue", "fault", "favorite", "feature", "february", "federal", "fee", "feed", "feel", "female", "fence", "festival", "fetch", "fever", "few", "fiber", "fiction", "field", "figure", "file", "film", "filter", "final", "find", "fine", "finger", "finish", "fire", "firm", "first", "fiscal", "fish", "fit", "fitness", "fix", "flag", "flame", "flash", "flat", "flavor", "flee", "flight", "flip", "float", "flock", "floor", "flower", "fluid", "flush", "fly", "foam", "focus", "fog", "foil", "fold", "follow", "food", "foot", "force", "forest", "forget", "fork", "fortune", "forum", "forward", "fossil", "foster", "found", "fox", "fragile", "frame", "frequent", "fresh", "friend", "fringe", "frog", "front", "frost", "frown", "frozen", "fruit", "fuel", "fun", "funny", "furnace", "fury", "future", "gadget", "gain", "galaxy", "gallery", "game", "gap", "garage", "garbage", "garden", "garlic", "garment", "gas", "gasp", "gate", "gather", "gauge", "gaze", "general", "genius", "genre", "gentle", "genuine", "gesture", "ghost", "giant", "gift", "giggle", "ginger", "giraffe", "girl", "give", "glad", "glance", "glare", "glass", "glide", "glimpse", "globe", "gloom", "glory", "glove", "glow", "glue", "goat", "goddess", "gold", "good", "goose", "gorilla", "gospel", "gossip", "govern", "gown", "grab", "grace", "grain", "grant", "grape", "grass", "gravity", "great", "green", "grid", "grief", "grit", "grocery", "group", "grow", "grunt", "guard", "guess", "guide", "guilt", "guitar", "gun", "gym", "habit", "hair", "half", "hammer", "hamster", "hand", "happy", "harbor", "hard", "harsh", "harvest", "hat", "have", "hawk", "hazard", "head", "health", "heart", "heavy", "hedgehog", "height", "hello", "helmet", "help", "hen", "hero", "hidden", "high", "hill", "hint", "hip", "hire", "history", "hobby", "hockey", "hold", "hole", "holiday", "hollow", "home", "honey", "hood", "hope", "horn", "horror", "horse", "hospital", "host", "hotel", "hour", "hover", "hub", "huge", "human", "humble", "humor", "hundred", "hungry", "hunt", "hurdle", "hurry", "hurt", "husband", "hybrid", "ice", "icon", "idea", "identify", "idle", "ignore", "ill", "illegal", "illness", "image", "imitate", "immense", "immune", "impact", "impose", "improve", "impulse", "inch", "include", "income", "increase", "index", "indicate", "indoor", "industry", "infant", "inflict", "inform", "inhale", "inherit", "initial", "inject", "injury", "inmate", "inner", "innocent", "input", "inquiry", "insane", "insect", "inside", "inspire", "install", "intact", "interest", "into", "invest", "invite", "involve", "iron", "island", "isolate", "issue", "item", "ivory", "jacket", "jaguar", "jar", "jazz", "jealous", "jeans", "jelly", "jewel", "job", "join", "joke", "journey", "joy", "judge", "juice", "jump", "jungle", "junior", "junk", "just", "kangaroo", "keen", "keep", "ketchup", "key", "kick", "kid", "kidney", "kind", "kingdom", "kiss", "kit", "kitchen", "kite", "kitten", "kiwi", "knee", "knife", "knock", "know", "lab", "label", "labor", "ladder", "lady", "lake", "lamp", "language", "laptop", "large", "later", "latin", "laugh", "laundry", "lava", "law", "lawn", "lawsuit", "layer", "lazy", "leader", "leaf", "learn", "leave", "lecture", "left", "leg", "legal", "legend", "leisure", "lemon", "lend", "length", "lens", "leopard", "lesson", "letter", "level", "liar", "liberty", "library", "license", "life", "lift", "light", "like", "limb", "limit", "link", "lion", "liquid", "list", "little", "live", "lizard", "load", "loan", "lobster", "local", "lock", "logic", "lonely", "long", "loop", "lottery", "loud", "lounge", "love", "loyal", "lucky", "luggage", "lumber", "lunar", "lunch", "luxury", "lyrics", "machine", "mad", "magic", "magnet", "maid", "mail", "main", "major", "make", "mammal", "man", "manage", "mandate", "mango", "mansion", "manual", "maple", "marble", "march", "margin", "marine", "market", "marriage", "mask", "mass", "master", "match", "material", "math", "matrix", "matter", "maximum", "maze", "meadow", "mean", "measure", "meat", "mechanic", "medal", "media", "melody", "melt", "member", "memory", "mention", "menu", "mercy", "merge", "merit", "merry", "mesh", "message", "metal", "method", "middle", "midnight", "milk", "million", "mimic", "mind", "minimum", "minor", "minute", "miracle", "mirror", "misery", "miss", "mistake", "mix", "mixed", "mixture", "mobile", "model", "modify", "mom", "moment", "monitor", "monkey", "monster", "month", "moon", "moral", "more", "morning", "mosquito", "mother", "motion", "motor", "mountain", "mouse", "move", "movie", "much", "muffin", "mule", "multiply", "muscle", "museum", "mushroom", "music", "must", "mutual", "myself", "mystery", "myth", "naive", "name", "napkin", "narrow", "nasty", "nation", "nature", "near", "neck", "need", "negative", "neglect", "neither", "nephew", "nerve", "nest", "net", "network", "neutral", "never", "news", "next", "nice", "night", "noble", "noise", "nominee", "noodle", "normal", "north", "nose", "notable", "note", "nothing", "notice", "novel", "now", "nuclear", "number", "nurse", "nut", "oak", "obey", "object", "oblige", "obscure", "observe", "obtain", "obvious", "occur", "ocean", "october", "odor", "off", "offer", "office", "often", "oil", "okay", "old", "olive", "olympic", "omit", "once", "one", "onion", "online", "only", "open", "opera", "opinion", "oppose", "option", "orange", "orbit", "orchard", "order", "ordinary", "organ", "orient", "original", "orphan", "ostrich", "other", "outdoor", "outer", "output", "outside", "oval", "oven", "over", "own", "owner", "oxygen", "oyster", "ozone", "pact", "paddle", "page", "pair", "palace", "palm", "panda", "panel", "panic", "panther", "paper", "parade", "parent", "park", "parrot", "party", "pass", "patch", "path", "patient", "patrol", "pattern", "pause", "pave", "payment", "peace", "peanut", "pear", "peasant", "pelican", "pen", "penalty", "pencil", "people", "pepper", "perfect", "permit", "person", "pet", "phone", "photo", "phrase", "physical", "piano", "picnic", "picture", "piece", "pig", "pigeon", "pill", "pilot", "pink", "pioneer", "pipe", "pistol", "pitch", "pizza", "place", "planet", "plastic", "plate", "play", "please", "pledge", "pluck", "plug", "plunge", "poem", "poet", "point", "polar", "pole", "police", "pond", "pony", "pool", "popular", "portion", "position", "possible", "post", "potato", "pottery", "poverty", "powder", "power", "practice", "praise", "predict", "prefer", "prepare", "present", "pretty", "prevent", "price", "pride", "primary", "print", "priority", "prison", "private", "prize", "problem", "process", "produce", "profit", "program", "project", "promote", "proof", "property", "prosper", "protect", "proud", "provide", "public", "pudding", "pull", "pulp", "pulse", "pumpkin", "punch", "pupil", "puppy", "purchase", "purity", "purpose", "purse", "push", "put", "puzzle", "pyramid", "quality", "quantum", "quarter", "question", "quick", "quit", "quiz", "quote", "rabbit", "raccoon", "race", "rack", "radar", "radio", "rail", "rain", "raise", "rally", "ramp", "ranch", "random", "range", "rapid", "rare", "rate", "rather", "raven", "raw", "razor", "ready", "real", "reason", "rebel", "rebuild", "recall", "receive", "recipe", "record", "recycle", "reduce", "reflect", "reform", "refuse", "region", "regret", "regular", "reject", "relax", "release", "relief", "rely", "remain", "remember", "remind", "remove", "render", "renew", "rent", "reopen", "repair", "repeat", "replace", "report", "require", "rescue", "resemble", "resist", "resource", "response", "result", "retire", "retreat", "return", "reunion", "reveal", "review", "reward", "rhythm", "rib", "ribbon", "rice", "rich", "ride", "ridge", "rifle", "right", "rigid", "ring", "riot", "ripple", "risk", "ritual", "rival", "river", "road", "roast", "robot", "robust", "rocket", "romance", "roof", "rookie", "room", "rose", "rotate", "rough", "round", "route", "royal", "rubber", "rude", "rug", "rule", "run", "runway", "rural", "sad", "saddle", "sadness", "safe", "sail", "salad", "salmon", "salon", "salt", "salute", "same", "sample", "sand", "satisfy", "satoshi", "sauce", "sausage", "save", "say", "scale", "scan", "scare", "scatter", "scene", "scheme", "school", "science", "scissors", "scorpion", "scout", "scrap", "screen", "script", "scrub", "sea", "search", "season", "seat", "second", "secret", "section", "security", "seed", "seek", "segment", "select", "sell", "seminar", "senior", "sense", "sentence", "series", "service", "session", "settle", "setup", "seven", "shadow", "shaft", "shallow", "share", "shed", "shell", "sheriff", "shield", "shift", "shine", "ship", "shiver", "shock", "shoe", "shoot", "shop", "short", "shoulder", "shove", "shrimp", "shrug", "shuffle", "shy", "sibling", "sick", "side", "siege", "sight", "sign", "silent", "silk", "silly", "silver", "similar", "simple", "since", "sing", "siren", "sister", "situate", "six", "size", "skate", "sketch", "ski", "skill", "skin", "skirt", "skull", "slab", "slam", "sleep", "slender", "slice", "slide", "slight", "slim", "slogan", "slot", "slow", "slush", "small", "smart", "smile", "smoke", "smooth", "snack", "snake", "snap", "sniff", "snow", "soap", "soccer", "social", "sock", "soda", "soft", "solar", "soldier", "solid", "solution", "solve", "someone", "song", "soon", "sorry", "sort", "soul", "sound", "soup", "source", "south", "space", "spare", "spatial", "spawn", "speak", "special", "speed", "spell", "spend", "sphere", "spice", "spider", "spike", "spin", "spirit", "split", "spoil", "sponsor", "spoon", "sport", "spot", "spray", "spread", "spring", "spy", "square", "squeeze", "squirrel", "stable", "stadium", "staff", "stage", "stairs", "stamp", "stand", "start", "state", "stay", "steak", "steel", "stem", "step", "stereo", "stick", "still", "sting", "stock", "stomach", "stone", "stool", "story", "stove", "strategy", "street", "strike", "strong", "struggle", "student", "stuff", "stumble", "style", "subject", "submit", "subway", "success", "such", "sudden", "suffer", "sugar", "suggest", "suit", "summer", "sun", "sunny", "sunset", "super", "supply", "supreme", "sure", "surface", "surge", "surprise", "surround", "survey", "suspect", "sustain", "swallow", "swamp", "swap", "swarm", "swear", "sweet", "swift", "swim", "swing", "switch", "sword", "symbol", "symptom", "syrup", "system", "table", "tackle", "tag", "tail", "talent", "talk", "tank", "tape", "target", "task", "taste", "tattoo", "taxi", "teach", "team", "tell", "ten", "tenant", "tennis", "tent", "term", "test", "text", "thank", "that", "theme", "then", "theory", "there", "they", "thing", "this", "thought", "three", "thrive", "throw", "thumb", "thunder", "ticket", "tide", "tiger", "tilt", "timber", "time", "tiny", "tip", "tired", "tissue", "title", "toast", "tobacco", "today", "toddler", "toe", "together", "toilet", "token", "tomato", "tomorrow", "tone", "tongue", "tonight", "tool", "tooth", "top", "topic", "topple", "torch", "tornado", "tortoise", "toss", "total", "tourist", "toward", "tower", "town", "toy", "track", "trade", "traffic", "tragic", "train", "transfer", "trap", "trash", "travel", "tray", "treat", "tree", "trend", "trial", "tribe", "trick", "trigger", "trim", "trip", "trophy", "trouble", "truck", "true", "truly", "trumpet", "trust", "truth", "try", "tube", "tuition", "tumble", "tuna", "tunnel", "turkey", "turn", "turtle", "twelve", "twenty", "twice", "twin", "twist", "two", "type", "typical", "ugly", "umbrella", "unable", "unaware", "uncle", "uncover", "under", "undo", "unfair", "unfold", "unhappy", "uniform", "unique", "unit", "universe", "unknown", "unlock", "until", "unusual", "unveil", "update", "upgrade", "uphold", "upon", "upper", "upset", "urban", "urge", "usage", "use", "used", "useful", "useless", "usual", "utility", "vacant", "vacuum", "vague", "valid", "valley", "valve", "van", "vanish", "vapor", "various", "vast", "vault", "vehicle", "velvet", "vendor", "venture", "venue", "verb", "verify", "version", "very", "vessel", "veteran", "viable", "vibrant", "vicious", "victory", "video", "view", "village", "vintage", "violin", "virtual", "virus", "visa", "visit", "visual", "vital", "vivid", "vocal", "voice", "void", "volcano", "volume", "vote", "voyage", "wage", "wagon", "wait", "walk", "wall", "walnut", "want", "warfare", "warm", "warrior", "wash", "wasp", "waste", "water", "wave", "way", "wealth", "weapon", "wear", "weasel", "weather", "web", "wedding", "weekend", "weird", "welcome", "west", "wet", "whale", "what", "wheat", "wheel", "when", "where", "whip", "whisper", "wide", "width", "wife", "wild", "will", "win", "window", "wine", "wing", "wink", "winner", "winter", "wire", "wisdom", "wise", "wish", "witness", "wolf", "woman", "wonder", "wood", "wool", "word", "work", "world", "worry", "worth", "wrap", "wreck", "wrestle", "wrist", "write", "wrong", "yard", "year", "ORANGE", "you", "young", "youth", "zebra", "zero", "zone", "zoo"]

#seedphrase variables
seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10", "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19", "word20", "word21", "word22", "word23"]
wordcounter = 1
letterstate = 1

# initialize letters
letterslot1 = "a"
letterslot2 = "a"
letterslot3 = "a"
letterslot4 = "a"

#accept the list output from each of the getletter functions
function1return = []
function2return = []
function3return = []
function4return = []

#function to get previous letter
def getPrevLetter(letter):
    number = alphabet.index(letter)
    number = number - 1
    if number == -1:
        number = 25
        return alphabet[number]
    else:
        return alphabet[number]

#function to get next letter
def getNextLetter(letter):
    number = alphabet.index(letter)
    number = number + 1
    if number == 26:
        number = 0
        return alphabet[number]
    else:
        return alphabet[number]

# function to get FIRST letter
def getletter1(inputletter):
    runstate = 1
    localletter = inputletter
    global wordcounter
    while runstate == 1:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((75, 2), "Seed Word: " + str(wordcounter), fill="ORANGE", font=impact18)
        draw.text((15, 210), "(choose from words on right)", fill="ORANGE", font=impact18)
        draw.text((5, 90), localletter, fill="ORANGE", font=impact35)
        #time.sleep(0.2)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(8, 85), (14, 69), (20, 85)], outline="ORANGE", fill="ORANGE")
            #localletter = getPrevLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(8, 85), (14, 69), (20, 85)], outline="ORANGE", fill=0)
            localletter = getNextLetter(localletter)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(8, 148), (14, 164), (20, 148)], outline="ORANGE", fill="ORANGE")
            #localletter = getNextLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(8, 148), (14, 164), (20, 148)], outline="ORANGE", fill=0)
            localletter = getPrevLetter(localletter)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW: # button is released
            time.sleep(0.2)
            nextslot = 2
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            if wordcounter == 1:
                nextslot = 0
                runstate = 0
                return [localletter, nextslot]
            else:
                wordcounter = wordcounter - 1
                nextslot = 1
                runstate = 0
                return [localletter, nextslot]

        possibles = [i for i in seedwords if i.startswith(localletter)]
        if len(possibles) == 1:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
        elif len(possibles) == 2:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
            word2width = impact25.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text((offset2, 97), possibles[1] + " -", fill="ORANGE", font=impact25)
        elif len(possibles) >= 3:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
            word2width = impact25.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text((offset2, 97), possibles[1] + " -", fill="ORANGE", font=impact25)
            word3width = impact25.getsize(possibles[2])
            offset3 = 223 - word3width[0]
            draw.text((offset3, 157), possibles[2] + " -", fill="ORANGE", font=impact25)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[2]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        disp.ShowImage(image,0,0)

#function to get SECOND letter
def getletter2(inputletter):
    runstate = 1  #just defines whether the current function is still running
    localletter = inputletter  #gathers the letter from the function input
    global wordcounter
    while runstate == 1:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((75, 2), "Seed Word: " + str(wordcounter), fill="ORANGE", font=impact18)
        draw.text((18, 210), "(choose from words on right)", fill="ORANGE", font=impact18)
        draw.text((5, 90), letterslot1, fill="ORANGE", font=impact35)
        draw.text((35, 90), localletter, fill="ORANGE", font=impact35)
        #time.sleep(0.1)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(38, 85), (44, 69), (50, 85)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(38, 85), (44, 69), (50, 85)], outline="ORANGE", fill=0)
            localletter = getNextLetter(localletter)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(38, 148), (44, 164), (50, 148)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(38, 148), (44, 164), (50, 148)], outline="ORANGE", fill=0)
            localletter = getPrevLetter(localletter)

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW: # button is released
            time.sleep(0.2)
            nextslot = 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 3
            runstate = 0
            return [localletter, nextslot]

        possibles = [i for i in seedwords if i.startswith(letterslot1 + localletter)]
        if len(possibles) == 1:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
        elif len(possibles) == 2:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
            word2width = impact25.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text((offset2, 97), possibles[1] + " -", fill="ORANGE", font=impact25)
        elif len(possibles) >= 3:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
            word2width = impact25.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text((offset2, 97), possibles[1] + " -", fill="ORANGE", font=impact25)
            word3width = impact25.getsize(possibles[2])
            offset3 = 223 - word3width[0]
            draw.text((offset3, 157), possibles[2] + " -", fill="ORANGE", font=impact25)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[2]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        disp.ShowImage(image,0,0)

#function to get THIRD letter
def getletter3(inputletter):
    runstate = 1
    localletter = inputletter
    global wordcounter
    while runstate == 1:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((75, 2), "Seed Word: " + str(wordcounter), fill="ORANGE", font=impact18)
        draw.text((18, 210), "(choose from words on right)", fill="ORANGE", font=impact18)
        draw.text((5, 90), letterslot1, fill="ORANGE", font=impact35)
        draw.text((35, 90), letterslot2, fill="ORANGE", font=impact35)
        draw.text((65, 90), localletter, fill="ORANGE", font=impact35)
        #time.sleep(0.1)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(68, 85), (74, 69), (80, 85)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(68, 85), (74, 69), (80, 85)], outline="ORANGE", fill=0)
            localletter = getNextLetter(localletter)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(68, 148), (74, 162), (80, 148)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(68, 148), (74, 162), (80, 148)], outline="ORANGE", fill=0)
            localletter = getPrevLetter(localletter)

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW: # button is released
            time.sleep(0.2)
            nextslot = 2
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 4
            runstate = 0
            return [localletter, nextslot]

        possibles = [i for i in seedwords if i.startswith(letterslot1 + letterslot2 + localletter)]
        if len(possibles) == 1:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
        elif len(possibles) == 2:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
            word2width = impact25.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text((offset2, 97), possibles[1] + " -", fill="ORANGE", font=impact25)
        elif len(possibles) >= 3:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
            word2width = impact25.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text((offset2, 97), possibles[1] + " -", fill="ORANGE", font=impact25)
            word3width = impact25.getsize(possibles[2])
            offset3 = 223 - word3width[0]
            draw.text((offset3, 157), possibles[2] + " -", fill="ORANGE", font=impact25)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[2]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        disp.ShowImage(image,0,0)

#function to get FOURTH letter
def getletter4(inputletter):
    runstate = 1
    localletter = inputletter
    global wordcounter
    while runstate == 1:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((75, 2), "Seed Word: " + str(wordcounter), fill="ORANGE", font=impact18)
        draw.text((18, 210), "(choose from words on right)", fill="ORANGE", font=impact18)
        draw.text((5, 90), letterslot1, fill="ORANGE", font=impact35)
        draw.text((35, 90), letterslot2, fill="ORANGE", font=impact35)
        draw.text((65, 90), letterslot3, fill="ORANGE", font=impact35)
        draw.text((95, 90), localletter, fill="ORANGE", font=impact35)
        #time.sleep(0.1)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(98, 85), (104, 69), (110, 85)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(98, 85), (104, 69), (110, 85)], outline="ORANGE", fill=0)
            localletter = getNextLetter(localletter)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(98, 148), (104, 162), (110, 148)], outline="ORANGE", fill="ORANGE")
        else:  # button is pressed:
            draw.polygon([(98, 148), (104, 162), (110, 148)], outline="ORANGE", fill=0)
            localletter = getPrevLetter(localletter)

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW: # button is released
            time.sleep(0.2)
            nextslot = 3
            runstate = 0
            return [localletter, nextslot]

        #nothing should happen if right is pressed on fourth letter
        #if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            #time.sleep(0.1)
            #nextslot = 0
            #runstate = 0
            #return [localletter, nextslot]

        possibles = [i for i in seedwords if i.startswith(letterslot1 + letterslot2 + letterslot3 + localletter)]
        if len(possibles) == 1:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
        elif len(possibles) == 2:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
            word2width = impact25.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text((offset2, 97), possibles[1] + " -", fill="ORANGE", font=impact25)
        elif len(possibles) >= 3:
            word1width = impact25.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text((offset1, 39), possibles[0] + " -", fill="ORANGE", font=impact25)
            word2width = impact25.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text((offset2, 97), possibles[1] + " -", fill="ORANGE", font=impact25)
            word3width = impact25.getsize(possibles[2])
            offset3 = 223 - word3width[0]
            draw.text((offset3, 157), possibles[2] + " -", fill="ORANGE", font=impact25)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 1
            selectedword = possibles[2]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        disp.ShowImage(image,0,0)

def getword():
    global letterslot1
    global letterslot2
    global letterslot3
    global letterslot4
    global wordcounter
    global letterstate
    print("the wordcounter is at: ", wordcounter)

    #defines the which letter is being currently gathered
    #letterstate = 1
    allowedletterstates = [0, 1, 2, 3, 4]

    #manages the movement between the letter entry slots
    print("the current letterstate is: ", letterstate)
    while letterstate in allowedletterstates:
        print("the current letterstate is: ", letterstate)
        if letterstate == 0:
            print("the letterstate was zero")
            wordcounter = 0
            letterslot1 = "a"
            letterslot2 = "a"
            letterslot3 = "a"
            letterslot4 = "a"
            letterstate = 1
            return
        if letterstate == 1:
            letterslot1 = "a"
            letterslot2 = "a"
            letterslot3 = "a"
            letterslot4 = "a"
            function1return = getletter1(letterslot1)
            letterslot1 = function1return[0]
            letterstate = function1return[1]
        elif letterstate == 2:
            function2return = getletter2(letterslot2)
            letterslot2 = function2return[0]
            letterstate = function2return[1]
        elif letterstate == 3:
            function3return = getletter3(letterslot3)
            letterslot3 = function3return[0]
            letterstate = function3return[1]
        elif letterstate == 4:
            function4return = getletter4(letterslot4)
            letterslot4 = function4return[0]
            letterstate = function4return[1]
        # letterslot1 = "a"
        # letterslot2 = "a"
        # letterslot3 = "a"
        # letterslot4 = "a"
        return

    letterslot1 = "a"
    letterslot2 = "a"
    letterslot3 = "a"
    letterslot4 = "a"
    letterstate = 1



def showverify_11():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    textwidth, textheight = draw.textsize("Selected Words", font=impact18)
    draw.text(((240 - textwidth) / 2, 2), "Selected Words", fill="ORANGE", font=impact18)
    draw.text((2, 40), "1: " + seedphrase[1], fill="ORANGE", font=impact23)
    draw.text((2, 65), "2: " + seedphrase[2], fill="ORANGE", font=impact23)
    draw.text((2, 90), "3: " + seedphrase[3], fill="ORANGE", font=impact23)
    draw.text((2, 115), "4: " + seedphrase[4], fill="ORANGE", font=impact23)
    draw.text((2, 140), "5: " + seedphrase[5], fill="ORANGE", font=impact23)
    draw.text((2, 165), "6: " + seedphrase[6], fill="ORANGE", font=impact23)
    draw.text((120, 40), "7: " + seedphrase[7], fill="ORANGE", font=impact23)
    draw.text((120, 65), "8: " + seedphrase[8], fill="ORANGE", font=impact23)
    draw.text((120, 90), "9: " + seedphrase[9], fill="ORANGE", font=impact23)
    draw.text((120, 115), "10: " + seedphrase[10], fill="ORANGE", font=impact23)
    draw.text((120, 140), "11: " + seedphrase[11], fill="ORANGE", font=impact23)
    draw.text((65, 210), "RIGHT to verify", fill="ORANGE", font=impact18)

    disp.ShowImage(image, 0, 0)

def gather_11_words(runstate):
    global seedphrase
    global wordcounter

    localrunstate = runstate

    allowedwordstates = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

    while wordcounter in allowedwordstates:
        print("according to gather_11_words, the wordcounter is at: ", wordcounter)
        getword()
        letterslot1 = "a"
        letterslot2 = "a"
        letterslot3 = "a"
        letterslot4 = "a"
        #print(seedphrase)

    if wordcounter == 0:
        localrunstate[0] = 0
        localrunstate[1] = ""
        seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9",
                      "word10",
                      "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19",
                      "word20",
                      "word21", "word22", "word23"]
        wordcounter = 1
        return localrunstate

    verify1runstate = 1
    while verify1runstate == 1:
        showverify_11()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            verify1runstate = 0

    seedphrase.pop(0)
    localrunstate[1] = " ".join(seedphrase[0:11:])

    localrunstate[0] = 52

    seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10",
                  "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19", "word20",
                  "word21", "word22", "word23"]
    wordcounter = 1

    print("End of Gather 11 Words")

    return localrunstate

def showverify_23_1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((40, 2), "Selected Words (1/2)", fill="ORANGE", font=impact18)
    draw.text((2, 40), "1: " + seedphrase[1], fill="ORANGE", font=impact23)
    draw.text((2, 65), "2: " + seedphrase[2], fill="ORANGE", font=impact23)
    draw.text((2, 90), "3: " + seedphrase[3], fill="ORANGE", font=impact23)
    draw.text((2, 115), "4: " + seedphrase[4], fill="ORANGE", font=impact23)
    draw.text((2, 140), "5: " + seedphrase[5], fill="ORANGE", font=impact23)
    draw.text((2, 165), "6: " + seedphrase[6], fill="ORANGE", font=impact23)
    draw.text((120, 40), " 7: " + seedphrase[7], fill="ORANGE", font=impact23)
    draw.text((120, 65), " 8: " + seedphrase[8], fill="ORANGE", font=impact23)
    draw.text((120, 90), " 9: " + seedphrase[9], fill="ORANGE", font=impact23)
    draw.text((120, 115), "10: " + seedphrase[10], fill="ORANGE", font=impact23)
    draw.text((120, 140), "11: " + seedphrase[11], fill="ORANGE", font=impact23)
    draw.text((120, 165), "12: " + seedphrase[12], fill="ORANGE", font=impact23)
    draw.text((65, 210), "RIGHT to verify", fill="ORANGE", font=impact18)

    disp.ShowImage(image,0,0)

def showverify_23_2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((40, 2), "Selected Words (2/2)", fill="ORANGE", font=impact18)
    draw.text((2, 40), "13: " + seedphrase[13], fill="ORANGE", font=impact23)
    draw.text((2, 65), "14: " + seedphrase[14], fill="ORANGE", font=impact23)
    draw.text((2, 90), "15: " + seedphrase[15], fill="ORANGE", font=impact23)
    draw.text((2, 115), "16: " + seedphrase[16], fill="ORANGE", font=impact23)
    draw.text((2, 140), "17: " + seedphrase[17], fill="ORANGE", font=impact23)
    draw.text((2, 165), "18: " + seedphrase[18], fill="ORANGE", font=impact23)
    draw.text((120, 40), "19: " + seedphrase[19], fill="ORANGE", font=impact23)
    draw.text((120, 65), "20: " + seedphrase[20], fill="ORANGE", font=impact23)
    draw.text((120, 90), "21: " + seedphrase[21], fill="ORANGE", font=impact23)
    draw.text((120, 115), "22: " + seedphrase[22], fill="ORANGE", font=impact23)
    draw.text((120, 140), "23: " + seedphrase[23], fill="ORANGE", font=impact23)
    draw.text((65, 210), "RIGHT to verify", fill="ORANGE", font=impact18)

    disp.ShowImage(image, 0, 0)

def gather_23_words(runstate):
    global seedphrase
    global wordcounter

    localrunstate = runstate

    allowedwordstates = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

    while wordcounter in allowedwordstates:
        getword()
        letterslot1 = "a"
        letterslot2 = "a"
        letterslot3 = "a"
        letterslot4 = "a"
        #print(seedphrase)

    if wordcounter == 0:
        localrunstate[0] = 0
        localrunstate[1] = ""
        seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9",
                      "word10",
                      "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19",
                      "word20",
                      "word21", "word22", "word23"]
        wordcounter = 1
        return localrunstate

    verify1runstate = 1
    while verify1runstate == 1:
        showverify_23_1()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            verify1runstate = 0

    verify2runstate = 1
    while verify2runstate == 1:
        showverify_23_2()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            verify2runstate = 0

    seedphrase.pop(0)
    localrunstate[1] = " ".join(seedphrase)

    localrunstate[0] = 52

    seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10",
                  "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19", "word20",
                  "word21", "word22", "word23"]
    wordcounter = 1

    print("End of Gather 23 Words")

    return localrunstate

def get_pre_calc_words(runstate):
    localrunstate = runstate

    seedsize = numofwords_menu()

    if seedsize == "abort":
        localrunstate[0] = 0
        localrunstate[1] = ""
        return localrunstate
    if seedsize == 12:
        localrunstate[0] = 60
        return localrunstate
    if seedsize == 24:
        localrunstate[0] = 59
        return localrunstate

def showverify_12():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    textwidth, textheight = draw.textsize("Selected Words", font=impact18)
    draw.text(((240 - textwidth) / 2, 2), "Selected Words", fill="ORANGE", font=impact18)
    draw.text((2, 40), "1: " + seedphrase[1], fill="ORANGE", font=impact23)
    draw.text((2, 65), "2: " + seedphrase[2], fill="ORANGE", font=impact23)
    draw.text((2, 90), "3: " + seedphrase[3], fill="ORANGE", font=impact23)
    draw.text((2, 115), "4: " + seedphrase[4], fill="ORANGE", font=impact23)
    draw.text((2, 140), "5: " + seedphrase[5], fill="ORANGE", font=impact23)
    draw.text((2, 165), "6: " + seedphrase[6], fill="ORANGE", font=impact23)
    draw.text((120, 40), " 7: " + seedphrase[7], fill="ORANGE", font=impact23)
    draw.text((120, 65), " 8: " + seedphrase[8], fill="ORANGE", font=impact23)
    draw.text((120, 90), " 9: " + seedphrase[9], fill="ORANGE", font=impact23)
    draw.text((120, 115), "10: " + seedphrase[10], fill="ORANGE", font=impact23)
    draw.text((120, 140), "11: " + seedphrase[11], fill="ORANGE", font=impact23)
    draw.text((120, 165), "12: " + seedphrase[12], fill="ORANGE", font=impact23)
    draw.text((25, 210), "LEFT to EXIT, RIGHT to VERIFY", fill="ORANGE", font=impact18)

    disp.ShowImage(image,0,0)

def showverify_24_1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((40, 2), "Selected Words (1/2)", fill="ORANGE", font=impact18)
    draw.text((2, 40), "1: " + seedphrase[1], fill="ORANGE", font=impact23)
    draw.text((2, 65), "2: " + seedphrase[2], fill="ORANGE", font=impact23)
    draw.text((2, 90), "3: " + seedphrase[3], fill="ORANGE", font=impact23)
    draw.text((2, 115), "4: " + seedphrase[4], fill="ORANGE", font=impact23)
    draw.text((2, 140), "5: " + seedphrase[5], fill="ORANGE", font=impact23)
    draw.text((2, 165), "6: " + seedphrase[6], fill="ORANGE", font=impact23)
    draw.text((120, 40), " 7: " + seedphrase[7], fill="ORANGE", font=impact23)
    draw.text((120, 65), " 8: " + seedphrase[8], fill="ORANGE", font=impact23)
    draw.text((120, 90), " 9: " + seedphrase[9], fill="ORANGE", font=impact23)
    draw.text((120, 115), "10: " + seedphrase[10], fill="ORANGE", font=impact23)
    draw.text((120, 140), "11: " + seedphrase[11], fill="ORANGE", font=impact23)
    draw.text((120, 165), "12: " + seedphrase[12], fill="ORANGE", font=impact23)
    draw.text((25, 210), "LEFT to EXIT, RIGHT to VERIFY", fill="ORANGE", font=impact18)

    disp.ShowImage(image,0,0)

def showverify_24_2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((40, 2), "Selected Words (2/2)", fill="ORANGE", font=impact18)
    draw.text((2, 40), "13: " + seedphrase[13], fill="ORANGE", font=impact23)
    draw.text((2, 65), "14: " + seedphrase[14], fill="ORANGE", font=impact23)
    draw.text((2, 90), "15: " + seedphrase[15], fill="ORANGE", font=impact23)
    draw.text((2, 115), "16: " + seedphrase[16], fill="ORANGE", font=impact23)
    draw.text((2, 140), "17: " + seedphrase[17], fill="ORANGE", font=impact23)
    draw.text((2, 165), "18: " + seedphrase[18], fill="ORANGE", font=impact23)
    draw.text((120, 40), "19: " + seedphrase[19], fill="ORANGE", font=impact23)
    draw.text((120, 65), "20: " + seedphrase[20], fill="ORANGE", font=impact23)
    draw.text((120, 90), "21: " + seedphrase[21], fill="ORANGE", font=impact23)
    draw.text((120, 115), "22: " + seedphrase[22], fill="ORANGE", font=impact23)
    draw.text((120, 140), "23: " + seedphrase[23], fill="ORANGE", font=impact23)
    draw.text((120, 165), "24: " + seedphrase[24], fill="ORANGE", font=impact23)
    draw.text((25, 210), "LEFT to EXIT, RIGHT to VERIFY", fill="ORANGE", font=impact18)

    disp.ShowImage(image, 0, 0)

def gather_12_words(runstate):
    global seedphrase
    global wordcounter

    seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10",
                  "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19", "word20",
                  "word21", "word22", "word23", "word24"]

    localrunstate = runstate

    print("Runstate at the begining of gather_24_words is:")
    print(localrunstate)

    allowedwordstates = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    while wordcounter in allowedwordstates:
        getword()
        letterslot1 = "a"
        letterslot2 = "a"
        letterslot3 = "a"
        letterslot4 = "a"
        #print(seedphrase)

    print("exited the wordcounter and the wordocunter is ", wordcounter)
    if wordcounter == 0:
        localrunstate[0] = 0
        localrunstate[1] = ""
        seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9",
                      "word10",
                      "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19",
                      "word20",
                      "word21", "word22", "word23"]
        wordcounter = 1
        print("reached the end of the wordcounter is zero if statement")
        print(localrunstate)
        return localrunstate

    print(" ".join(seedphrase[1:13:]))

    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Checking Seed Phrase...", font=impact22)
    draw.text(((240 - textwidth) / 2, 100), "Checking Seed Phrase...", fill="ORANGE", font=impact22)
    disp.ShowImage(image, 0, 0)

    try:
        seedtest = bip39.mnemonic_to_seed(" ".join(seedphrase[1:13:]))
    except ValueError:
        print("Now that was one bad seed...")

        errormessagedisplayed = True
        while errormessagedisplayed == True:
            line1 = "Seed Appears Invalid"
            line2 = "Check your seed"
            line3 = "And try again"
            line4 = "(Joystick RIGHT to EXIT)"

            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            textwidth, textheight = draw.textsize(line1, font=impact22)
            draw.text(((240 - textwidth) / 2, 20), line1, fill="ORANGE", font=impact22)
            textwidth, textheight = draw.textsize(line2, font=impact22)
            draw.text(((240 - textwidth) / 2, 90), line2, fill="ORANGE", font=impact22)
            textwidth, textheight = draw.textsize(line3, font=impact22)
            draw.text(((240 - textwidth) / 2, 125), line3, fill="ORANGE", font=impact22)
            textwidth, textheight = draw.textsize(line4, font=impact18)
            draw.text(((240 - textwidth) / 2, 210), line4, fill="ORANGE", font=impact18)
            disp.ShowImage(image, 0, 0)

            if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
                time.sleep(0.4)
                errormessagedisplayed = False

        wordcounter = 1
        localrunstate[0] = 0
        localrunstate[1] = ""

        print("Found an error in the seed and the runstate is:")
        print(runstate)

        return localrunstate

    verify1runstate = 1
    while verify1runstate == 1:
        showverify_12()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            verify1runstate = 0
        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            wordcounter = 1
            localrunstate[0] = 0
            localrunstate[1] = ""
            verify1runstate = 0
            return localrunstate

    seedphrase.pop(0)
    localrunstate[1] = " ".join(seedphrase[0:12:])

    #localrunstate[0] = 0

    seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10",
                  "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19", "word20",
                  "word21", "word22", "word23"]
    wordcounter = 1

    print("End of Gather 12 Words")
    print(localrunstate)

    return localrunstate

def gather_24_words(runstate):
    global seedphrase
    global wordcounter

    seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10",
                  "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19", "word20",
                  "word21", "word22", "word23", "word24"]

    localrunstate = runstate

    print("Runstate at the begining of gather_24_words is:")
    print(localrunstate)

    allowedwordstates = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]

    while wordcounter in allowedwordstates:
        getword()
        letterslot1 = "a"
        letterslot2 = "a"
        letterslot3 = "a"
        letterslot4 = "a"
        #print(seedphrase)

    if wordcounter == 0:
        localrunstate[0] = 0
        localrunstate[1] = ""
        seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9",
                      "word10",
                      "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19",
                      "word20",
                      "word21", "word22", "word23"]
        wordcounter = 1
        return localrunstate

    print(" ".join(seedphrase[1:]))

    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Checking Seed Phrase...", font=impact22)
    draw.text(((240 - textwidth) / 2, 100), "Checking Seed Phrase...", fill="ORANGE", font=impact22)
    disp.ShowImage(image, 0, 0)

    try:
        seedtest = bip39.mnemonic_to_seed(" ".join(seedphrase[1:]))
    except ValueError:
        print("Now that was one bad seed...")

        errormessagedisplayed = True
        while errormessagedisplayed == True:
            line1 = "Seed Appears Invalid"
            line2 = "Check your seed"
            line3 = "And try again"
            line4 = "(Joystick RIGHT to EXIT)"

            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            textwidth, textheight = draw.textsize(line1, font=impact22)
            draw.text(((240 - textwidth) / 2, 20), line1, fill="ORANGE", font=impact22)
            textwidth, textheight = draw.textsize(line2, font=impact22)
            draw.text(((240 - textwidth) / 2, 90), line2, fill="ORANGE", font=impact22)
            textwidth, textheight = draw.textsize(line3, font=impact22)
            draw.text(((240 - textwidth) / 2, 125), line3, fill="ORANGE", font=impact22)
            textwidth, textheight = draw.textsize(line4, font=impact18)
            draw.text(((240 - textwidth) / 2, 210), line4, fill="ORANGE", font=impact18)
            disp.ShowImage(image, 0, 0)

            if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
                time.sleep(0.4)
                errormessagedisplayed = False

        wordcounter = 1
        localrunstate[0] = 0
        localrunstate[1] = ""

        print("Found an error in the seed and the runstate is:")
        print(runstate)

        return localrunstate

    verify1runstate = 1
    while verify1runstate == 1:
        showverify_24_1()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            verify1runstate = 0
        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            wordcounter = 1
            localrunstate[0] = 0
            localrunstate[1] = ""
            verify1runstate = 0
            return localrunstate

    verify2runstate = 1
    while verify2runstate == 1:
        showverify_24_2()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            verify2runstate = 0
        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            wordcounter = 1
            localrunstate[0] = 0
            localrunstate[1] = ""
            verify1runstate = 0
            return localrunstate

    seedphrase.pop(0)
    localrunstate[1] = " ".join(seedphrase)

    #localrunstate[0] = 0

    seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10",
                  "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19", "word20",
                  "word21", "word22", "word23"]
    wordcounter = 1

    print("End of Gather 24 Words")
    print(localrunstate)

    return localrunstate

def get_pre_sign_words():

    seedsize = numofwords_menu()

    if seedsize == "abort":
        return "abort"
    if seedsize == 12:
        return 12
    if seedsize == 24:
        return 24

def confirmseedsaved():
    global activeseedsaveslot

    confirmationrunning = True
    while confirmationrunning == True:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        textwidth, textheight = draw.textsize("Seed Saved in Slot " + str(activeseedsaveslot), font=impact18)
        draw.text(((240 - textwidth) / 2, 110), "Seed Saved in Slot " + str(activeseedsaveslot), fill="ORANGE", font=impact18)
        textwidth, textheight = draw.textsize("Press joystick RIGHT to EXIT", font=impact18)
        draw.text(((240 - textwidth) / 2, 215), "Press joystick RIGHT to EXIT", fill="ORANGE", font=impact18)
        disp.ShowImage(image, 0, 0)
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.3)
            confirmationrunning = False

def tempsaveseed(runstate):
    localrunstate = runstate

    print("the active seedsaveslot is:", activeseedsaveslot)

    localseedsize = get_pre_sign_words()

    if localseedsize == "abort":
        localrunstate[0] = 0
        localrunstate[1] = ""
        return localrunstate
    if localseedsize == 12:
        localrunstate = gather_12_words(localrunstate)
        localrunstate[2][activeseedsaveslot - 1] = localrunstate[1]
        if localrunstate[2][activeseedsaveslot - 1] != "":
            confirmseedsaved()
        localrunstate[1] = ""
        localrunstate[0] = 0
        return localrunstate
    if localseedsize == 24:
        localrunstate = gather_24_words(localrunstate)
        localrunstate[2][activeseedsaveslot - 1] = localrunstate[1]
        if localrunstate[2][activeseedsaveslot - 1] != "":
            confirmseedsaved()
        localrunstate[1] = ""
        localrunstate[0] = 0
        return localrunstate

# GETLASTWORD MODULE
# GETLASTWORD MODULE
# GETLASTWORD MODULE

def displayfinalword(word24):
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    textwidth, textheight = draw.textsize("The final word is :", font=impact23)
    draw.text(((240 - textwidth) / 2, 60), "The final word is :", fill="ORANGE", font=impact23)
    textwidth, textheight = draw.textsize(word24, font=impact50)
    draw.text(((240 - textwidth) / 2, 90), word24, fill="ORANGE", font=impact50)

    draw.text((73, 210), "RIGHT to EXIT", fill="ORANGE", font=impact18)

    disp.ShowImage(image, 0, 0)

def get_final_word(runstate):
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

# BEGIN DICE MODULE
# BEGIN DICE MODULE
# BEGIN DICE MODULE

def drawdi1selected():
    draw.rectangle((5, 50, 75, 120), outline="ORANGE", fill="ORANGE")
    draw.ellipse([(34, 79), (46, 91)], outline="BLACK", fill="BLACK")
    draw.rectangle((85, 50, 155, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 98), (140, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 50, 235, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(194, 79), (206, 91)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 98), (220, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((5, 130, 75, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(20, 174), (32, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 140), (60, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 174), (60, 186)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 130, 155, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(100, 178), (112, 190)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(114, 159), (126, 171)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 140), (140, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 178), (140, 190)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 130, 235, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 157), (192, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 174), (192, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 140), (220, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 157), (220, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 174), (220, 186)], outline="ORANGE", fill="ORANGE")
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)

def drawdi2selected():
    draw.rectangle((5, 50, 75, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 50, 155, 120), outline="ORANGE", fill="ORANGE")
    draw.ellipse([(100, 60), (112, 72)], outline="BLACK", fill="BLACK")
    draw.ellipse([(128, 98), (140, 110)], outline="BLACK", fill="BLACK")
    draw.rectangle((165, 50, 235, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(194, 79), (206, 91)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 98), (220, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((5, 130, 75, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(20, 174), (32, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 140), (60, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 174), (60, 186)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 130, 155, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(100, 178), (112, 190)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(114, 159), (126, 171)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 140), (140, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 178), (140, 190)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 130, 235, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 157), (192, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 174), (192, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 140), (220, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 157), (220, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 174), (220, 186)], outline="ORANGE", fill="ORANGE")
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)

def drawdi3selected():
    draw.rectangle((5, 50, 75, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 50, 155, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 98), (140, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 50, 235, 120), outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 60), (192, 72)], outline="BLACK", fill="BLACK")
    draw.ellipse([(194, 79), (206, 91)], outline="BLACK", fill="BLACK")
    draw.ellipse([(208, 98), (220, 110)], outline="BLACK", fill="BLACK")
    draw.rectangle((5, 130, 75, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(20, 174), (32, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 140), (60, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 174), (60, 186)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 130, 155, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(100, 178), (112, 190)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(114, 159), (126, 171)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 140), (140, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 178), (140, 190)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 130, 235, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 157), (192, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 174), (192, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 140), (220, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 157), (220, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 174), (220, 186)], outline="ORANGE", fill="ORANGE")
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)

def drawdi4selected():
    draw.rectangle((5, 50, 75, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 50, 155, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 98), (140, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 50, 235, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(194, 79), (206, 91)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 98), (220, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((5, 130, 75, 200), outline="ORANGE", fill="ORANGE")
    draw.ellipse([(20, 140), (32, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(20, 174), (32, 186)], outline="BLACK", fill="BLACK")
    draw.ellipse([(48, 140), (60, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(48, 174), (60, 186)], outline="BLACK", fill="BLACK")
    draw.rectangle((85, 130, 155, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(100, 178), (112, 190)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(114, 159), (126, 171)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 140), (140, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 178), (140, 190)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 130, 235, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 157), (192, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 174), (192, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 140), (220, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 157), (220, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 174), (220, 186)], outline="ORANGE", fill="ORANGE")
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)

def drawdi5selected():
    draw.rectangle((5, 50, 75, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 50, 155, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 98), (140, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 50, 235, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(194, 79), (206, 91)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 98), (220, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((5, 130, 75, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(20, 174), (32, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 140), (60, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 174), (60, 186)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 130, 155, 200), outline="ORANGE", fill="ORANGE")
    draw.ellipse([(100, 140), (112, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(100, 178), (112, 190)], outline="BLACK", fill="BLACK")
    draw.ellipse([(114, 159), (126, 171)], outline="BLACK", fill="BLACK")
    draw.ellipse([(128, 140), (140, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(128, 178), (140, 190)], outline="BLACK", fill="BLACK")
    draw.rectangle((165, 130, 235, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 157), (192, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 174), (192, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 140), (220, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 157), (220, 169)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 174), (220, 186)], outline="ORANGE", fill="ORANGE")
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)

def drawdi6selected():
    draw.rectangle((5, 50, 75, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 50, 155, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 98), (140, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 50, 235, 120), outline="ORANGE", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(194, 79), (206, 91)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(208, 98), (220, 110)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((5, 130, 75, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(20, 174), (32, 186)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 140), (60, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(48, 174), (60, 186)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((85, 130, 155, 200), outline="ORANGE", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(100, 178), (112, 190)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(114, 159), (126, 171)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 140), (140, 152)], outline="ORANGE", fill="ORANGE")
    draw.ellipse([(128, 178), (140, 190)], outline="ORANGE", fill="ORANGE")
    draw.rectangle((165, 130, 235, 200), outline="ORANGE", fill="ORANGE")
    draw.ellipse([(180, 140), (192, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(180, 157), (192, 169)], outline="BLACK", fill="BLACK")
    draw.ellipse([(180, 174), (192, 186)], outline="BLACK", fill="BLACK")
    draw.ellipse([(208, 140), (220, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(208, 157), (220, 169)], outline="BLACK", fill="BLACK")
    draw.ellipse([(208, 174), (220, 186)], outline="BLACK", fill="BLACK")
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)

def rollsobtainer():

    rollnumber = 1
    rollcollectorstring = ""
    currentdiselected = 1
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((45, 5), "Dice roll: " + str(rollnumber) + "/99", fill="ORANGE", font=impact26)
    drawdi1selected()

    while rollnumber <= 99:
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.15)
            if currentdiselected == 2:
                currentdiselected = 3
                drawdi3selected()
            if currentdiselected == 1:
                currentdiselected = 2
                drawdi2selected()
            if currentdiselected == 5:
                currentdiselected = 6
                drawdi6selected()
            if currentdiselected == 4:
                currentdiselected = 5
                drawdi5selected()
        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:
            time.sleep(0.15)
            if currentdiselected == 2:
                currentdiselected = 1
                drawdi1selected()
            if currentdiselected == 3:
                currentdiselected = 2
                drawdi2selected()
            if currentdiselected == 5:
                currentdiselected = 4
                drawdi4selected()
            if currentdiselected == 6:
                currentdiselected = 5
                drawdi5selected()
        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:
            time.sleep(0.15)
            if currentdiselected == 1:
                currentdiselected = 4
                drawdi4selected()
            if currentdiselected == 2:
                currentdiselected = 5
                drawdi5selected()
            if currentdiselected == 3:
                currentdiselected = 6
                drawdi6selected()
        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:
            time.sleep(0.15)
            if currentdiselected == 4:
                currentdiselected = 1
                drawdi1selected()
            if currentdiselected == 5:
                currentdiselected = 2
                drawdi2selected()
            if currentdiselected == 6:
                currentdiselected = 3
                drawdi3selected()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            time.sleep(0.15)
            if currentdiselected == 6:
                rollcollectorstring = rollcollectorstring + "0"
            else:
                rollcollectorstring = rollcollectorstring + str(currentdiselected)
            print("The roll number is " + str(rollnumber) + " and the die selections are : " + rollcollectorstring)
            rollnumber = rollnumber + 1
            if currentdiselected == 1:
                drawdi1selected()
            if currentdiselected == 2:
                drawdi2selected()
            if currentdiselected == 3:
                drawdi3selected()
            if currentdiselected == 4:
                drawdi4selected()
            if currentdiselected == 5:
                drawdi5selected()
            if currentdiselected == 6:
                drawdi6selected()
        if rollnumber < 100:
            draw.text((45, 5), "Dice roll: " + str(rollnumber) + "/99", fill="ORANGE", font=impact26)
        disp.ShowImage(image, 0, 0)

    return rollcollectorstring


def getseedfromdice(runstate):
    localrunstate = runstate

    impact18 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
    impact23 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 23)

    collectedrolls = rollsobtainer()

    entropyinteger = int(collectedrolls, 6)

    rollsinbytes = entropyinteger.to_bytes(32, byteorder="little")

    baddicestring = mnemonic_from_bytes(rollsinbytes)

    wordarray = baddicestring.split()

    wordarray.pop(-1)

    laststring = " ".join(wordarray) + " abandon"

    lastbytes = mnemonic_to_bytes(laststring, ignore_checksum=True)

    correctedlaststring = mnemonic_from_bytes(lastbytes)

    displayarray = correctedlaststring.split()

    firstwordset = True
    while firstwordset is True:
        #Display the first 12 words
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((55, 2), "Your Seed Is (1/2):", fill="ORANGE", font=impact18)
        draw.text((2, 40), "1: " + displayarray[0], fill="ORANGE", font=impact23)
        draw.text((2, 65), "2: " + displayarray[1], fill="ORANGE", font=impact23)
        draw.text((2, 90), "3: " + displayarray[2], fill="ORANGE", font=impact23)
        draw.text((2, 115), "4: " + displayarray[3], fill="ORANGE", font=impact23)
        draw.text((2, 140), "5: " + displayarray[4], fill="ORANGE", font=impact23)
        draw.text((2, 165), "6: " + displayarray[5], fill="ORANGE", font=impact23)
        draw.text((120, 40), " 7: " + displayarray[6], fill="ORANGE", font=impact23)
        draw.text((120, 65), " 8: " + displayarray[7], fill="ORANGE", font=impact23)
        draw.text((120, 90), " 9: " + displayarray[8], fill="ORANGE", font=impact23)
        draw.text((120, 115), "10: " + displayarray[9], fill="ORANGE", font=impact23)
        draw.text((120, 140), "11: " + displayarray[10], fill="ORANGE", font=impact23)
        draw.text((120, 165), "12: " + displayarray[11], fill="ORANGE", font=impact23)
        draw.text((55, 210), "RIGHT to Continue", fill="ORANGE", font=impact18)
        disp.ShowImage(image, 0, 0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.25)
            firstwordset = False

    secondwordset = True
    while secondwordset is True:
        # Display the second 12 words
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((55, 2), "Your Seed Is (2/2):", fill="ORANGE", font=impact18)
        draw.text((2, 40), "13: " + displayarray[12], fill="ORANGE", font=impact23)
        draw.text((2, 65), "14: " + displayarray[13], fill="ORANGE", font=impact23)
        draw.text((2, 90), "15: " + displayarray[14], fill="ORANGE", font=impact23)
        draw.text((2, 115), "16: " + displayarray[15], fill="ORANGE", font=impact23)
        draw.text((2, 140), "17: " + displayarray[16], fill="ORANGE", font=impact23)
        draw.text((2, 165), "18: " + displayarray[17], fill="ORANGE", font=impact23)
        draw.text((120, 40), "19: " + displayarray[18], fill="ORANGE", font=impact23)
        draw.text((120, 65), "20: " + displayarray[19], fill="ORANGE", font=impact23)
        draw.text((120, 90), "21: " + displayarray[20], fill="ORANGE", font=impact23)
        draw.text((120, 115), "22: " + displayarray[21], fill="ORANGE", font=impact23)
        draw.text((120, 140), "23: " + displayarray[22], fill="ORANGE", font=impact23)
        draw.text((120, 165), "24: " + displayarray[23], fill="ORANGE", font=impact23)
        draw.text((70, 210), "RIGHT to EXIT", fill="ORANGE", font=impact18)
        disp.ShowImage(image, 0, 0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.25)
            secondwordset = False

    localrunstate[0] = 0
    localrunstate[1] = ""

    return localrunstate

# XPUBMAKE MODULE
# XPUBMAKE MODULE
# XPUBMAKE MODULE

def qrimage(data):
    qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_M,
    box_size=1,
    border=2
    )
    qr.add_data(data)
    qr.make(fit=True)
    return(qr.make_image(fill_color="black", back_color="white").resize((240,240)).convert('RGB'))

def make_xpub(runstate):
    localrunstate = runstate
    global hardened_derivation
    global currentnetwork
    global qrsize
    qrsize = 140

    decidedonwhichwords = False
    while decidedonwhichwords == False:
        if "" == localrunstate[2][0] and "" == localrunstate[2][1] and "" == localrunstate[2][2]:
            numwords = get_pre_sign_words()
            if numwords == "abort":
                localrunstate[0] = 0
                localrunstate[1] = ""
                return localrunstate
            if numwords == 12:
                localrunstate = gather_12_words(localrunstate)
                decidedonwhichwords = True
            if numwords == 24:
                localrunstate = gather_24_words(localrunstate)
                decidedonwhichwords = True
        else:
            print("saved words were detected")
            usesavedwords = decideifusesavedwords()
            if usesavedwords == "yes":
                localrunstate = seedselect_menu(localrunstate)
                if localrunstate[0] == 0:
                    localrunstate[1] = ""
                    return localrunstate
                localrunstate[1] = localrunstate[2][activeseedsaveslot - 1]
                localrunstate[0] = 54
                decidedonwhichwords = True
            if usesavedwords == "no":
                numwords = get_pre_sign_words()
                if numwords == "abort":
                    localrunstate[0] = 0
                    localrunstate[1] = ""
                    return localrunstate
                if numwords == 12:
                    localrunstate = gather_12_words(localrunstate)
                    decidedonwhichwords = True
                if numwords == 24:
                    localrunstate = gather_24_words(localrunstate)
                    decidedonwhichwords = True

    print("Made it back to the make_xpub function and the runstate is:")
    print(runstate)

    if localrunstate[0] == 0:
        localrunstate[1] = ""
        return localrunstate

    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((20, 110), "Creating Animated QR Code", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

    seed = bip39.mnemonic_to_seed(localrunstate[1])

    root = bip32.HDKey.from_seed(seed, version=NETWORKS[currentnetwork]["xprv"])

    # first let's get the root fingerprint
    fingerprint = root.child(0).fingerprint
    #hardened_derivation = "m/48h/0h/0h/2h"

    # derive account according to bip84
    bip48_xprv = root.derive(hardened_derivation)

    # corresponding master public key:
    bip48_xpub = bip48_xprv.to_public()

    xpubstring = "[%s%s]%s" % (
        hexlify(fingerprint).decode('utf-8'),
        hardened_derivation[1:],
        bip48_xpub.to_base58(NETWORKS[currentnetwork]["Zpub"]))

    print(xpubstring)

    global qr_type_ur1_ind, qr_type_specter_ind
    qr_type_ur1_ind = 0
    qr_type_specter_ind = 0

    showqrcodes(xpubstring)

    localrunstate[0] = 0
    localrunstate[1] = ""

    print(localrunstate)

    return localrunstate

# BEGIN PSBTSIGN MODULE
# BEGIN PSBTSIGN MODULE
# BEGIN PSBTSIGN MODULE

def scananimatedqr():
    vs = VideoStream(usePiCamera=True,resolution=(1024, 768),framerate=10).start()  # For Pi Camera
    time.sleep(2.0)

    listofstrings = ["empty"]
    framestatuslist = ["-"]
    framestatusstring = ""
    camerarunning = True
    gotnumofframes = False
    totalchunks = 0
    global qr_type_ur1_ind, qr_type_specter_ind
    qr_type_ur1_ind = 0
    qr_type_specter_ind = 0

    while gotnumofframes == False:
        frame = vs.read()
        th, frame = cv2.threshold(frame, 128, 255, cv2.THRESH_BINARY) #image binarization to improve decoding
        frame = imutils.resize(frame, width=550)
        barcodes = pyzbar.decode(frame)
        for barcode in barcodes:
            barcodeData = barcode.data.decode("utf-8")
            string = barcodeData
            print(string)

            if re.search("^UR\:BYTES\/(\d+)OF(\d+)", string, re.IGNORECASE) != None:
                # is UR 1.0 Encoding
                totalchunks = int(re.search("^UR\:BYTES\/(\d+)OF(\d+)", string, re.IGNORECASE).group(2))
                qr_type_ur1_ind = 1
            elif re.search("^p(\d+)of(\d+) ", string, re.IGNORECASE) != None:
                # is specter desktop encoding
                totalchunks = int(re.search("^p(\d+)of(\d+) ", string, re.IGNORECASE).group(2))
                qr_type_specter_ind = 1
            elif re.search("^UR\:.+\/(\d+)\-(\d+)\/", string, re.IGNORECASE) != None:
                # is UR 2.0 Encoding
                # not supported yet
                time.sleep(0.3)
                vs.stop()
                return "abort"
            else:
                totalchunks = 1

            gotnumofframes = True
        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            print("joystick pressed left")
            time.sleep(0.3)
            vs.stop()
            return "abort"

    chunkcounter = totalchunks - 1
    while chunkcounter >= 1:
        listofstrings.append("empty")
        framestatuslist.append("-")
        chunkcounter = chunkcounter - 1

    print(listofstrings)

    print(framestatuslist)

    while camerarunning == True:
        frame = vs.read()

        if qr_type_ur1_ind == 1:
            th, frame = cv2.threshold(frame, 128, 255, cv2.THRESH_BINARY)
            frame = imutils.resize(frame, width=550)
        else:
            frame = imutils.resize(frame, width=400)

        barcodes = pyzbar.decode(frame)
        for barcode in barcodes:
            barcodeData = barcode.data.decode("utf-8")
            string = barcodeData

            if qr_type_ur1_ind == 1:
                currentframe = int(re.search("^UR\:BYTES\/(\d+)OF(\d+)", string, re.IGNORECASE).group(1))
                trimmedstring = string.split("/")[-1].strip()
            else:
                currentframe = int(re.search("^p(\d+)of(\d+) ", string, re.IGNORECASE).group(1))
                trimmedstring = string.split(" ")[-1].strip()

            length = len(string)

            listofstrings[currentframe - 1] = trimmedstring
            framestatuslist[currentframe - 1] = "*"
            print(framestatusstring.join(framestatuslist))
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            textwidth, textheight = draw.textsize("Collecting QR Codes:", font=impact22)
            draw.text(((240 - textwidth) / 2, 15), "Collecting QR Codes:", fill="ORANGE", font=impact22)
            lines = textwrap.wrap(framestatusstring.join(framestatuslist), width=11)
            yheight = 60
            for line in lines:
                textwidth, textheight = draw.textsize(line, font=couriernew30)
                draw.text(((240 - textwidth) / 2, yheight), line, fill="ORANGE", font=couriernew30)
                yheight += 30
            textwidth, textheight = draw.textsize("Press joystick LEFT to ABORT", font=impact18)
            draw.text(((240 - textwidth) / 2, 215), "Press joystick LEFT to ABORT", fill="ORANGE", font=impact18)
            disp.ShowImage(image, 0, 0)
            if "empty" not in listofstrings:
                camerarunning = False
        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            print("joystick pressed left")
            time.sleep(0.3)
            vs.stop()
            return "abort"  ## need to uncomment for final insert

    qrcodevalue = ""
    vs.stop()
    print(qrcodevalue.join(listofstrings))
    return qrcodevalue.join(listofstrings) ## need to uncomment for final insert

def parse_multisig(sc):
    """Takes a script and extracts m,n and pubkeys from it"""
    # OP_m <len:pubkey> ... <len:pubkey> OP_n OP_CHECKMULTISIG
    # check min size
    if len(sc.data) < 37 or sc.data[-1] != 0xae:
        raise ValueError("Not a multisig script")
    m = sc.data[0] - 0x50
    if m < 1 or m > 16:
        raise ValueError("Invalid multisig script")
    n = sc.data[-2] - 0x50
    if n < m or n > 16:
        raise ValueError("Invalid multisig script")
    s = BytesIO(sc.data)
    # drop first byte
    s.read(1)
    # read pubkeys
    pubkeys = []
    for i in range(n):
        char = s.read(1)
        if char != b"\x21":
            raise ValueError("Invlid pubkey")
        pubkeys.append(ec.PublicKey.parse(s.read(33)))
    # check that nothing left
    if s.read() != sc.data[-2:]:
        raise ValueError("Invalid multisig script")
    return m, n, pubkeys

def get_cosigners(pubkeys, derivations, xpubs):
    """Returns xpubs used to derive pubkeys using global xpub field from psbt"""
    cosigners = []
    for i, pubkey in enumerate(pubkeys):
        if pubkey not in derivations:
            raise ValueError("Missing derivation")
        der = derivations[pubkey]
        for xpub in xpubs:
            origin_der = xpubs[xpub]
            # check fingerprint
            if origin_der.fingerprint == der.fingerprint:
                # check derivation - last two indexes give pub from xpub
                if origin_der.derivation == der.derivation[:-2]:
                    # check that it derives to pubkey actually
                    if xpub.derive(der.derivation[-2:]).key == pubkey:
                        # append strings so they can be sorted and compared
                        cosigners.append(xpub.to_base58())
                        break
    if len(cosigners) != len(pubkeys):
        raise RuntimeError("Can't get all cosigners")
    return sorted(cosigners)

def get_policy(scope, scriptpubkey, xpubs):
    """Parse scope and get policy"""
    # we don't know the policy yet, let's parse it
    script_type = scriptpubkey.script_type()
    # p2sh can be either legacy multisig, or nested segwit multisig
    # or nested segwit singlesig
    if script_type == "p2sh":
        if scope.witness_script is not None:
            script_type = "p2sh-p2wsh"
        elif scope.redeem_script is not None and scope.redeem_script.script_type() == "p2wpkh":
            script_type = "p2sh-p2wpkh"
    policy = { "type": script_type }
    # expected multisig
    if "p2wsh" in script_type and scope.witness_script is not None:
        m, n, pubkeys = parse_multisig(scope.witness_script)
        # check pubkeys are derived from cosigners
        #cosigners = get_cosigners(pubkeys, scope.bip32_derivations, xpubs)
        policy.update({
            "m": m, "n": n #, "cosigners": cosigners
        })
    return policy

def signtransaction(seedphrase, psbtstring):
    localseedphrase = seedphrase
    localpsbtstring = psbtstring
    destinationaddress = "self-transfer"
    global runstate
    global currentnetwork
    global hardened_derivation

    print("Current network settings are: " + currentnetwork + " " + hardened_derivation)

    seed = bip39.mnemonic_to_seed(localseedphrase)

    root = bip32.HDKey.from_seed(seed, version=NETWORKS[currentnetwork]["xprv"]) #was excluded before

    # first let's get the root fingerprint
    fingerprint = root.child(0).fingerprint
    #hardened_derivation = "m/48h/0h/0h/2h"
    # derive account according to bip84
    bip48_xprv = root.derive(hardened_derivation)
    # corresponding master public key:
    bip48_xpub = bip48_xprv.to_public()
    print("[%s%s]%s" % (
        hexlify(fingerprint).decode('utf-8'),
        hardened_derivation[1:],
        bip48_xpub.to_base58())
          )

    if qr_type_ur1_ind == 1:
        b64_psbt = b2a_base64(cbor_decode(bc32decode(localpsbtstring)))
    else:
        b64_psbt = localpsbtstring

    # parse psbt transaction
    print("took in psbt string")
    # first convert it to binary
    raw = a2b_base64(b64_psbt)
    print("converted to binary")
    # then parse
    tx = psbt.PSBT.parse(raw)

    # Check inputs of the transaction and check that they use the same script type
    # For multisig parsed policy will look like this:
    # { script_type: p2wsh, cosigners: [xpubs strings], m: 2, n: 3}
    policy = None
    inp_amount = 0
    for inp in tx.inputs:
        inp_amount += inp.witness_utxo.value
        # get policy of the input
        inp_policy = get_policy(inp, inp.witness_utxo.script_pubkey, tx.xpubs)
        # if policy is None - assign current
        if policy is None:
            policy = inp_policy
        # otherwise check that everything in the policy is the same
        else:
            # check policy is the same
            if policy != inp_policy:
                raise RuntimeError("Mixed inputs in the transaction")

    wallet = "Native Segwit "
    if "p2sh-" in policy["type"]:
        wallet = "Nested Segwit "
    if "m" in policy:
        wallet += "Multisig (%d of %d)" % (policy["m"], policy["n"])
    else:
        wallet += "Single sig"
    print("Spending from: %s" % wallet)
    print("Input amount: %d sat" % inp_amount)

    # now go through outputs and check if they are change
    spending = 0
    change = 0
    for i, out in enumerate(tx.outputs):
        out_policy = get_policy(out, tx.tx.vout[i].script_pubkey, tx.xpubs)
        is_change = False
        # if policy is the same - probably change
        if out_policy == policy:
            # double-check that it's change
            # we already checked in get_cosigners and parse_multisig
            # that pubkeys are generated from cosigners,
            # and witness script is corresponding multisig
            # so we only need to check that scriptpubkey is generated from
            # witness script

            # empty script by default
            sc = script.Script(b"")
            # multisig, we know witness script
            if policy["type"] == "p2wsh":
                sc = script.p2wsh(out.witness_script)
            elif policy["type"] == "p2sh-p2wsh":
                sc = script.p2sh(script.p2wsh(out.witness_script))
            # single-sig
            elif "pkh" in policy["type"]:
                if len(out.bip32_derivations.values()) > 0:
                    der = list(out.bip32_derivations.values())[0].derivation
                    my_pubkey = root.derive(der)
                if policy["type"] == "p2wpkh":
                    sc = script.p2wpkh(my_pubkey)
                elif policy["type"] == "p2sh-p2wpkh":
                    sc = script.p2sh(script.p2wpkh(my_pubkey))
            if sc.data == tx.tx.vout[i].script_pubkey.data:
                is_change = True
        if is_change:
            change += tx.tx.vout[i].value
            print("Change %d sats" % tx.tx.vout[i].value)
        else:
            spending += tx.tx.vout[i].value
            print("Spending %d sats to %s" % (tx.tx.vout[i].value, tx.tx.vout[i].script_pubkey.address(NETWORKS[currentnetwork])))
            destinationaddress = tx.tx.vout[i].script_pubkey.address(NETWORKS[currentnetwork])

    fee = inp_amount - change - spending

    print("Fee: %d sats" % fee)


    #destinationaddress = out.script_pubkey.address(NETWORKS[currentnetwork])

    #display transaction information
    #sendingamount = totalspending - totalfee  #my original code
    displaytransactioninfo = True
    while displaytransactioninfo == True:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        textwidth, textheight = draw.textsize("Confirm last 13 chars", font=impact22)
        draw.text(((240 - textwidth) / 2, 5), "Confirm last 13 chars", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize("of the receiving address:", font=impact22)
        draw.text(((240 - textwidth) / 2, 30), "of the receiving address:", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(destinationaddress[-13:], font=impact22)
        draw.text(((240 - textwidth) / 2, 55), destinationaddress[-13:], fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize("Amount Sending:", font=impact22)
        draw.text(((240 - textwidth) / 2, 90), "Amount Sending:", fill="ORANGE", font=impact22)
        if spending == 0:
            textwidth, textheight = draw.textsize("Self-Transfer (not parsed)", font=impact22)
            draw.text(((240 - textwidth) / 2, 115), "Self-Transfer (not parsed)", fill="ORANGE", font=impact22)
        else:
            textwidth, textheight = draw.textsize(str(spending) + " satoshis", font=impact22)
            draw.text(((240 - textwidth) / 2, 115), str(spending) + " satoshis", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize("Plus a fee of:", font=impact22)
        draw.text(((240 - textwidth) / 2, 150), "Plus a fee of:", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(str(fee) + " satoshis", font=impact22)
        draw.text(((240 - textwidth) / 2, 175), str(fee) + " satoshis", fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize("Left to EXIT, Right to CONTINUE", font=impact18)
        draw.text(((240 - textwidth) / 2, 215), "Left to EXIT, Right to CONTINUE", fill="ORANGE", font=impact18)
        disp.ShowImage(image, 0, 0)
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            displaytransactioninfo = False
        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            displaytransactioninfo = False
            return("abort")

    #update the status screen
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((20, 25), "Creating Animated QR Code...", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

    # sign the transaction
    tx.sign_with(root)

    #added section to trim psbt
    trimmed_psbt = psbt.PSBT(tx.tx)
    sigsEnd = 0
    for i, inp in enumerate(tx.inputs):
        sigsEnd += len(list(inp.partial_sigs.keys()))
        trimmed_psbt.inputs[i].partial_sigs = inp.partial_sigs

    #raw = tx.serialize()  #commented this out for the trim change
    raw = trimmed_psbt.serialize()

    if qr_type_ur1_ind == 1:
        return(raw)
    else:
        # convert to base64
        b64_psbt = b2a_base64(raw)
        # somehow b2a ends with \n...
        if b64_psbt[-1:] == b"\n":
            b64_psbt = b64_psbt[:-1]
        # print
        print("\nSigned transaction:")
        print(b64_psbt.decode('utf-8'))
        return b64_psbt.decode('utf-8')

def showqrcodes(qrdatain):
    localqrdatain = qrdatain

    if qr_type_ur1_ind == 1:
        bcur_raw = bcur_encode(localqrdatain)
        qrdata = bcur_raw[0].upper()
        qrhash = bcur_raw[1].upper()
    else:
        qrdata = localqrdatain

    stringlength = len(qrdata)

    # print("The length of the string is: " + str(stringlength))
    numofchunks = (stringlength // qrsize) + 1
    staticnumofchunks = numofchunks
    listcounter = 1

    start = 0
    stop = qrsize - 1
    if numofchunks == 1:
        if qr_type_ur1_ind == 1:
            chunklist = ["UR:BYTES/1OF1/" + qrhash + "/" + qrdata[start:stop]]
        else:
            chunklist = [qrdata[start:stop]]
    else:
        if qr_type_ur1_ind == 1:
            chunklist = ["UR:BYTES/" + str(listcounter) + "OF" + str(staticnumofchunks) + "/" + qrhash + "/" + qrdata[start:stop]]
        else:
            chunklist = ["p" + str(listcounter) + "of" + str(staticnumofchunks) + " " + qrdata[start:stop]]
    
    print(chunklist[0])
    qrimagelist = [qrimage(chunklist[0])]

    # draw.rectangle((0, 0, width, height), outline=0, fill=0)
    # draw.text((20, 25), "Creating Animated QR Code...", fill="ORANGE", font=impact18)
    generatingqrstatuslist = []
    generatingqrstatusstring = ""
    dashesneeded = numofchunks

    while dashesneeded > 0 and numofchunks > 1:
        if dashesneeded == numofchunks:
            generatingqrstatuslist.append("*")
        else:
            generatingqrstatuslist.append("-")
        dashesneeded = dashesneeded - 1
    # lines = textwrap.wrap(generatingqrstatusstring.join(generatingqrstatuslist), width=11)
    # yheight = 60
    # for line in lines:
    #     textwidth, textheight = draw.textsize(line, font=couriernew30)
    #     draw.text(((240 - textwidth) / 2, yheight), line, fill="ORANGE", font=couriernew30)
    #     yheight += 30
    # disp.ShowImage(image, 0, 0)
    print(generatingqrstatuslist)

    while numofchunks > 1:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((20, 25), "Creating Animated QR Code...", fill="ORANGE", font=impact18)
        start = start + qrsize
        stop = stop + qrsize
        if stop > stringlength:
            stop = stringlength  # - 1

        listcounter = listcounter + 1
        numofchunks = numofchunks - 1

        if qr_type_ur1_ind == 1:
            chunklist.append("UR:BYTES/" + str(listcounter) + "OF" + str(staticnumofchunks) + "/" + qrhash + "/" + qrdata[start - 1:stop])
        else:
            chunklist.append("p" + str(listcounter) + "of" + str(staticnumofchunks) + " " + qrdata[start - 1:stop])

        print(chunklist[listcounter-1])

        qrimagelist.append(qrimage(chunklist[listcounter-1]))

        generatingqrstatuslist[listcounter - 1] = "*"
        lines = textwrap.wrap(generatingqrstatusstring.join(generatingqrstatuslist), width=11)
        yheight = 60
        for line in lines:
            textwidth, textheight = draw.textsize(line, font=couriernew30)
            draw.text(((240 - textwidth) / 2, yheight), line, fill="ORANGE", font=couriernew30)
            yheight += 30
        disp.ShowImage(image, 0, 0)

    showingqrs = True
    displayedqr = 0

    while showingqrs == True:

        #Awkward structure is to allow for listening for joystick right
        disp.ShowImage(qrimagelist[displayedqr], 0, 0)
        time.sleep(0.1)
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            showingqrs = False
        else:
            time.sleep(0.1)

        disp.ShowImage(qrimagelist[displayedqr], 0, 0)
        time.sleep(0.1)
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            showingqrs = False
        else:
            time.sleep(0.1)

        disp.ShowImage(qrimagelist[displayedqr], 0, 0)
        time.sleep(0.1)
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            showingqrs = False
        else:
            time.sleep(0.1)


        if displayedqr < staticnumofchunks - 1:
            displayedqr = displayedqr + 1
            #time.sleep(0.3)
        else:
            displayedqr = 0
            #time.sleep(0.3)

def sign_psbt(runstate):
    localrunstate = runstate

    global qrsize
    qrsize = 100

    decidedonwhichwords = False
    while decidedonwhichwords == False:
        if "" == localrunstate[2][0] and "" == localrunstate[2][1] and "" == localrunstate[2][2]:
            numwords = get_pre_sign_words()
            if numwords == "abort":
                localrunstate[0] = 0
                localrunstate[1] = ""
                return localrunstate
            if numwords == 12:
                localrunstate = gather_12_words(localrunstate)
                decidedonwhichwords = True
                print("I hit the if statement")
                if localrunstate[0] == 0:
                    localrunstate[1] = ""
                    return localrunstate
            if numwords == 24:
                localrunstate = gather_24_words(localrunstate)
                decidedonwhichwords = True
                if localrunstate[0] == 0:
                    localrunstate[1] = ""
                    return localrunstate
        else:
            print("saved words were detected")
            usesavedwords = decideifusesavedwords()
            if usesavedwords == "yes":
                localrunstate = seedselect_menu(localrunstate)
                localrunstate[1] = localrunstate[2][activeseedsaveslot - 1]
                localrunstate[0] = 55
                decidedonwhichwords = True
            if usesavedwords == "no":
                numwords = get_pre_sign_words()
                if numwords == "abort":
                    localrunstate[0] = 0
                    localrunstate[1] = ""
                    return localrunstate
                if numwords == 12:
                    print("got to the magic point")
                    localrunstate = gather_12_words(localrunstate)
                    decidedonwhichwords = True
                    if localrunstate[0] == 0:
                        localrunstate[1] = ""
                        return localrunstate
                if numwords == 24:
                    localrunstate = gather_24_words(localrunstate)
                    decidedonwhichwords = True
                    if localrunstate[0] == 0:
                        localrunstate[1] = ""
                        return localrunstate

    if localrunstate[1] == "":
        numwords = get_pre_sign_words()

        if numwords == "abort":
            localrunstate[0] = 0
            localrunstate[1] = ""
            return localrunstate
        if numwords == 12:
            localrunstate = gather_12_words(localrunstate)
        if numwords == 24:
            localrunstate = gather_24_words(localrunstate)

    if localrunstate[0] == 0:
        localrunstate[1] = ""
        return localrunstate

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

    #parsing transaction info notification screen
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    textwidth, textheight = draw.textsize("Parsing txn data...", font=impact22)
    draw.text(((240 - textwidth) / 2, 100), "Parsing txn data...", fill="ORANGE", font=impact22)
    disp.ShowImage(image, 0, 0)

    print("The selected PSBT is:")
    print(importedpbststring)
    print("")

    # draw.rectangle((0, 0, width, height), outline=0, fill=0)
    # disp.ShowImage(image, 0, 0)

    signedpsbtstring = signtransaction(runstate[1], importedpbststring)

    if signedpsbtstring == "abort":
        localrunstate[0] = 0
        localrunstate[1] = ""
        return localrunstate

    showqrcodes(signedpsbtstring)

    localrunstate[0] = 0
    localrunstate[1] = ""

    print("You reached the end of the sign_psbt function.")

    return localrunstate
