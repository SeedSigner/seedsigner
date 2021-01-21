import ST7789
import spidev as SPI
import RPi.GPIO as GPIO

import time
import subprocess

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from subprocess import call

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

impact16 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 16)
impact18 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
impact20 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 20)
impact22 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 22)

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

def powering_down_notifier():
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

#MAIN MENU FUNCTIONS BELOW
#MAIN MENU FUNCTIONS BELOW
#MAIN MENU FUNCTIONS BELOW

def main_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((35, 2), "SeedSigner  v0.1.0", fill="ORANGE", font=impact22)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Seed Generation Tools", fill="BLACK", font=impact20)
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
    draw.text((35, 2), "SeedSigner  v0.1.0", fill="ORANGE", font=impact22)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Seed Generation Tools", fill="ORANGE", font=impact20)
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
    draw.text((35, 2), "SeedSigner  v0.1.0", fill="ORANGE", font=impact22)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Seed Generation Tools", fill="ORANGE", font=impact20)
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
    draw.text((35, 2), "SeedSigner  v0.1.0", fill="ORANGE", font=impact22)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Seed Generation Tools", fill="ORANGE", font=impact20)
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
                localrunstate[0] = 3
                powering_down_notifier()
                call("sudo shutdown --poweroff now", shell=True)


# SETTINGS MENU FUNCTIONS BELOW
# SETTINGS MENU FUNCTIONS BELOW
# SETTINGS MENU FUNCTIONS BELOW

def settings_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((85, 2), "Settings", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Input / Output Tests", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Version Info", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Donate to SeedSigner", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def settings_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((85, 2), "Settings", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Input / Output Tests", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Version Info", fill="BLACK", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Donate to SeedSigner", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def settings_option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((85, 2), "Settings", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Input / Output Tests", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Version Info", fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Donate to SeedSigner", fill="BLACK", font=impact20)
    # draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def settings_option4():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((85, 2), "Settings", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Input / Output Tests", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Version Info", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "Donate to SeedSigner", fill="ORANGE", font=impact20)
    draw.rectangle((5, 145, 210, 180), outline=0, fill="ORANGE")
    draw.text((15, 150), "... ( return to MAIN )", fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def settings_menu(runstate):
    localrunstate = runstate
    running = True
    optionselected = 1
    while running == True:
        optionselected = menu_elevator(optionselected, 4)
        if optionselected == 1:
            settings_option1()
        if optionselected == 2:
            settings_option2()
        if optionselected == 3:
            settings_option3()
        if optionselected == 4:
            settings_option4()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 50
                return localrunstate
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 57
                return localrunstate
            if optionselected == 3:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 56
                return localrunstate
            if optionselected == 4:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 0
                return localrunstate

#SEED GENERATION TOOLS MENU
#SEED GENERATION TOOLS MENU
#SEED GENERATION TOOLS MENU

def seedgen_menu_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((25, 2), "Seed Generation Tools", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Generate Word 24", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Create a Seed w/ Dice", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedgen_menu_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((25, 2), "Seed Generation Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Generate Word 24", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Create a Seed w/ Dice", fill="BLACK", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedgen_menu_option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((25, 2), "Seed Generation Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Generate Word 24", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Create a Seed w/ Dice", fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "... ( return to MAIN )", fill="BLACK", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def seedgen_menu(runstate):
    localrunstate = runstate
    running = True
    optionselected = 1
    while running == True:
        optionselected = menu_elevator(optionselected, 3)
        if optionselected == 1:
            seedgen_menu_option1()
        if optionselected == 2:
            seedgen_menu_option2()
        if optionselected == 3:
            seedgen_menu_option3()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if optionselected == 1:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 51
                return localrunstate
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 53
                return localrunstate
            if optionselected == 3:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 0
                return localrunstate

#SIGNING TOOLS MENU
#SIGNING TOOLS MENU
#SIGNING TOOLS MENU

def signing_menu_option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((60, 2), "Signing Tools", fill="ORANGE", font=impact20)
    draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Generate XPUB", fill="BLACK", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Sign a Transaction", fill="ORANGE", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def signing_menu_option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((60, 2), "Signing Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Generate XPUB", fill="ORANGE", font=impact20)
    draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Sign a Transaction", fill="BLACK", font=impact20)
    # draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "... ( return to MAIN )", fill="ORANGE", font=impact20)
    draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=impact18)
    disp.ShowImage(image, 0, 0)

def signing_menu_option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((60, 2), "Signing Tools", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 40, 210, 75), outline=0, fill="ORANGE")
    draw.text((15, 45), "Generate XPUB", fill="ORANGE", font=impact20)
    #draw.rectangle((5, 75, 210, 110), outline=0, fill="ORANGE")
    draw.text((15, 80), "Sign a Transaction", fill="ORANGE", font=impact20)
    draw.rectangle((5, 110, 210, 145), outline=0, fill="ORANGE")
    draw.text((15, 115), "... ( return to MAIN )", fill="BLACK", font=impact20)
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
                localrunstate[0] = 54
                return localrunstate
            if optionselected == 2:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 55
                return localrunstate
            if optionselected == 3:
                time.sleep(0.2)
                running = False
                localrunstate[0] = 0
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
        line2 = "Version 0.1.0"
        line3 = "built for use with"
        line4 = "Specter-desktop"
        line5 = "(Joystick RIGHT to EXIT)"

        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        textwidth, textheight = draw.textsize(line1, font=impact22)
        draw.text(((240 - textwidth) / 2, 20), line1, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line2, font=impact22)
        draw.text(((240 - textwidth) / 2, 55), line2, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line3, font=impact22)
        draw.text(((240 - textwidth) / 2, 90), line3, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line4, font=impact22)
        draw.text(((240 - textwidth) / 2, 125), line4, fill="ORANGE", font=impact22)
        textwidth, textheight = draw.textsize(line5, font=impact18)
        draw.text(((240 - textwidth) / 2, 210), line5, fill="ORANGE", font=impact18)
        disp.ShowImage(image, 0, 0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.4)
            running = False

    localrunstate[0] = 3

    return localrunstate