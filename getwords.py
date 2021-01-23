import ST7789
import spidev as SPI
import RPi.GPIO as GPIO

import time
import subprocess
import string

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

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

#alphabet reference
alphabet = list(string.ascii_lowercase)

#seed reference
# Specify Language Here
wordlist = "english"
with open(f"wordlists/{wordlist}.txt", "r") as f:
    seedwords = f.read().rstrip("\n").split("\n")


#seedphrase placeholder variables
seedphrase = [f"word{i}" for i in range (0,24)]

wordcounter = 1

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

#Define FONTS
impact25 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 25)
impact18 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
impact35 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 35)
impact23 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 23)

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
            nextslot = 0
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
            nextslot = 0
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 0
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.2)
            nextslot = 0
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
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
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
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
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
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
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

    #defines the which letter is being currently gathered
    letterstate = 1
    allowedletterstates = [1 , 2, 3, 4]

    #manages the movement between the letter entry slots
    while letterstate in allowedletterstates:
        if letterstate == 1:
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

    letterslot1 = "a"
    letterslot2 = "a"
    letterslot3 = "a"
    letterslot4 = "a"

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
    draw.text((65, 210), "RIGHT to verify", fill="ORANGE", font=impact18)

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
    draw.text((65, 210), "RIGHT to verify", fill="ORANGE", font=impact18)

    disp.ShowImage(image, 0, 0)

def gather_24_words(runstate):
    global seedphrase
    global wordcounter

    seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10",
                  "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19", "word20",
                  "word21", "word22", "word23", "word24"]

    localrunstate = runstate

    allowedwordstates = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]

    while wordcounter in allowedwordstates:
        getword()
        letterslot1 = "a"
        letterslot2 = "a"
        letterslot3 = "a"
        letterslot4 = "a"
        #print(seedphrase)

    verify1runstate = 1
    while verify1runstate == 1:
        showverify_24_1()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            verify1runstate = 0

    verify2runstate = 1
    while verify2runstate == 1:
        showverify_24_2()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            verify2runstate = 0

    seedphrase.pop(0)
    localrunstate[1] = " ".join(seedphrase)

    localrunstate[0] = 0

    seedphrase = ["word0", "word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10",
                  "word11", "word12", "word13", "word14", "word15", "word16", "word17", "word18", "word19", "word20",
                  "word21", "word22", "word23"]
    wordcounter = 1

    print("End of Gather 24 Words")
    print(localrunstate)

    return localrunstate