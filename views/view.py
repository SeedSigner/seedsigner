# External Dependencies
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import ST7789
import spidev as SPI
from multiprocessing import Queue

### Generic View Class to Instatiate Display
### Static Class variables are used for display
### Designed to be inherited for other view classes, but not required

class View:

    WIDTH = 240
    HEIGHT = 240

    # Define necessart fonts
    IMPACT16 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 16)
    IMPACT18 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
    IMPACT20 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 20)
    IMPACT21 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 21)
    IMPACT22 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 22)
    IMPACT23 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 23)
    IMPACT25 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 25)
    IMPACT26 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 26)
    IMPACT35 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 35)
    IMPACT50 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 50)
    COURIERNEW38 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/courbd.ttf', 38)
    COURIERNEW30 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/courbd.ttf', 30)

    RST = 27
    DC = 25
    BL = 24

    controller = None
    buttons = None
    canvas_width = 0
    canvas_height = 0
    canvas = None
    draw = None
    bus = 0
    device = 0
    disp = None

    def __init__(self, controller) -> None:

        # Global Singleton
        View.controller = controller
        View.buttons = View.controller.buttons

        View.canvas_width = View.WIDTH
        View.canvas_height = View.HEIGHT
        View.canvas = Image.new('RGB', (View.canvas_width, View.canvas_height))
        View.draw = ImageDraw.Draw(View.canvas)

        # 240x240 display with hardware SPI:
        View.bus = 0
        View.device = 0
        View.disp = ST7789.ST7789(SPI.SpiDev(View.bus, View.device),View.RST, View.DC, View.BL)
        View.disp.Init()

        self.queue = Queue()

    def DispShowImage(image = None):
        if image == None:
            image = View.canvas
        View.disp.ShowImage(image, 0, 0)

    def draw_modal(self, lines = [], title = "", bottom = "") -> None:

        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

        if len(title) > 0:
            tw, th = View.draw.textsize(title, font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 2), title, fill="ORANGE", font=View.IMPACT22)

        if len(bottom) > 0:
            tw, th = View.draw.textsize(bottom, font=View.IMPACT18)
            View.draw.text(((240 - tw) / 2, 210), bottom, fill="ORANGE", font=View.IMPACT18)

        if len(lines) == 1:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT26)
            View.draw.text(((240 - tw) / 2, 90), lines[0], fill="ORANGE", font=View.IMPACT26)
        elif len(lines) == 2:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[0], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[1], fill="ORANGE", font=View.IMPACT22)
        elif len(lines) == 3:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT26)
            View.draw.text(((240 - tw) / 2, 55), lines[0], fill="ORANGE", font=View.IMPACT26)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[1], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[2], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[2], fill="ORANGE", font=View.IMPACT22)
        elif len(lines) == 4:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 55), lines[0], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[1], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[2], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[2], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[3], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 160), lines[3], fill="ORANGE", font=View.IMPACT22)

        View.DispShowImage()

        return

    def draw_prompt_yes_no(self, lines = [], title = "", bottom = "") -> None:

        self.draw_prompt_custom("", "Yes ", "No ", lines, title, bottom)
        return

    def draw_prompt_custom(self, a_txt, b_txt, c_txt, lines = [], title = "", bottom = "") -> None:

        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

        if len(title) > 0:
            tw, th = View.draw.textsize(title, font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 2), title, fill="ORANGE", font=View.IMPACT22)

        if len(bottom) > 0:
            tw, th = View.draw.textsize(bottom, font=View.IMPACT18)
            View.draw.text(((240 - tw) / 2, 210), bottom, fill="ORANGE", font=View.IMPACT18)

        if len(lines) == 1:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT26)
            View.draw.text(((240 - tw) / 2, 90), lines[0], fill="ORANGE", font=View.IMPACT26)
        elif len(lines) == 2:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[0], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[1], fill="ORANGE", font=View.IMPACT22)
        elif len(lines) == 3:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT26)
            View.draw.text(((240 - tw) / 2, 20), lines[0], fill="ORANGE", font=View.IMPACT26)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[1], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[2], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[2], fill="ORANGE", font=View.IMPACT22)
        elif len(lines) == 4:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 20), lines[0], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[1], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[2], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[2], fill="ORANGE", font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[3], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 160), lines[3], fill="ORANGE", font=View.IMPACT22)

        a_x_offset = 240 - View.IMPACT25.getsize(a_txt)[0]
        View.draw.text((a_x_offset, 39 + 0), a_txt, fill="ORANGE", font=View.IMPACT25)

        b_x_offset = 240 - View.IMPACT25.getsize(b_txt)[0]
        View.draw.text((b_x_offset , 39 + 60), b_txt, fill="ORANGE", font=View.IMPACT25)

        c_x_offset = 240 - View.IMPACT25.getsize(c_txt)[0]
        View.draw.text((c_x_offset , 39 + 120), c_txt, fill="ORANGE", font=View.IMPACT25)

        View.DispShowImage()

        return

    ###
    ### Power Off Screen
    ###

    def display_power_off_screen(self):

        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

        line1 = "Powering Down..."
        line2 = "Please wait about"
        line3 = "30 seconds before"
        line4 = "disconnecting power."

        tw, th = View.draw.textsize(line1, font=View.IMPACT22)
        View.draw.text(((240-tw)/2, 45), line1, fill="ORANGE", font=View.IMPACT22)
        tw, th = View.draw.textsize(line2, font=View.IMPACT20)
        View.draw.text(((240-tw)/2, 100), line2, fill="ORANGE", font=View.IMPACT20)
        tw, th = View.draw.textsize(line3, font=View.IMPACT20)
        View.draw.text(((240-tw)/2, 130), line3, fill="ORANGE", font=View.IMPACT20)
        tw, th = View.draw.textsize(line4, font=View.IMPACT20)
        View.draw.text(((240-tw)/2, 160), line4, fill="ORANGE", font=View.IMPACT20)
        View.DispShowImage()
