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
impact26 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 26)

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