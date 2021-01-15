import ST7789
import spidev as SPI
import RPi.GPIO as GPIO

import time
import subprocess

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from imutils.video import VideoStream
from pyzbar import pyzbar
import argparse
import datetime
import imutils
import time
import cv2

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

impact18 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
impact22 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 22)

def iotestscreen(runstate):
    localrunstate = runstate

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

    scannedqrs = 0
    vs = VideoStream(usePiCamera=True).start()  # For Pi Camera
    time.sleep(2.0)

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