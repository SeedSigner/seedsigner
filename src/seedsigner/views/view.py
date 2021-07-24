# External Dependencies
from PIL import Image, ImageDraw, ImageFont
import os
import pathlib
import spidev as SPI
import time
from multiprocessing import Queue
from seedsigner.helpers import B, ST7789


### Generic View Class to Instatiate Display
### Static Class variables are used for display
### Designed to be inherited for other view classes, but not required

class View:

    WIDTH = 240
    HEIGHT = 240

    # Define necessary fonts
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
    COURIERNEW14 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/courbd.ttf', 14)
    COURIERNEW24 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/courbd.ttf', 24)
    COURIERNEW38 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/courbd.ttf', 38)
    COURIERNEW30 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/courbd.ttf', 30)
    COURIERNEW20 = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/courbd.ttf', 20)

    font_path = os.path.join(pathlib.Path(__file__).parent.resolve(), "..", "resources", "fonts")

    ROBOTOCONDENSED_BOLD_16 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 16)
    ROBOTOCONDENSED_BOLD_18 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 18)
    ROBOTOCONDENSED_BOLD_20 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 20)
    ROBOTOCONDENSED_BOLD_22 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 20)
    ROBOTOCONDENSED_BOLD_24 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 22)
    ROBOTOCONDENSED_BOLD_25 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 25)
    ROBOTOCONDENSED_BOLD_26 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 26)
    ROBOTOCONDENSED_BOLD_28 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Bold.ttf"), 28)
    ROBOTOCONDENSED_LIGHT_16 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Light.ttf"), 16)
    ROBOTOCONDENSED_LIGHT_24 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Light.ttf"), 24)
    ROBOTOCONDENSED_REGULAR_16 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 16)
    ROBOTOCONDENSED_REGULAR_20 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 20)
    ROBOTOCONDENSED_REGULAR_22 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 22)
    ROBOTOCONDENSED_REGULAR_24 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 24)
    ROBOTOCONDENSED_REGULAR_26 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 26)
    ROBOTOCONDENSED_REGULAR_28 = ImageFont.truetype(os.path.join(font_path, "RobotoCondensed-Regular.ttf"), 28)

    RST = 27
    DC = 25
    BL = 24

    buttons = None
    canvas_width = 0
    canvas_height = 0
    canvas = None
    draw = None
    bus = 0
    device = 0
    disp = None
    previous_button_width = None

    def __init__(self) -> None:
        # Import here to avoid circular imports
        from seedsigner.controller import Controller
        self.controller = Controller.get_instance()

        View.buttons = self.controller.buttons
        View.color = self.controller.color

        View.canvas_width = View.WIDTH
        View.canvas_height = View.HEIGHT
        View.canvas = Image.new('RGB', (View.canvas_width, View.canvas_height))
        View.draw = ImageDraw.Draw(View.canvas)

        # 240x240 display with hardware SPI:
        View.bus = 0
        View.device = 0
        View.disp = ST7789(SPI.SpiDev(View.bus, View.device),View.RST, View.DC, View.BL)
        View.disp.Init()

        self.queue = Queue()

    def DispShowImage(image=None, alpha_overlay=None):
        if image == None:
            image = View.canvas
        if alpha_overlay:
            image = Image.alpha_composite(image, alpha_overlay)
        View.disp.ShowImage(image, 0, 0)

    def disp_show_image_pan(image, start_x, start_y, end_x, end_y, rate, alpha_overlay=None):
        cur_x = start_x
        cur_y = start_y
        rate_x = rate
        rate_y = rate
        if end_x - start_x < 0:
            rate_x = rate_x * -1
        if end_y - start_y < 0:
            rate_y = rate_y * -1

        while (cur_x != end_x or cur_y != end_y) and (rate_x != 0 or rate_y != 0):
            cur_x += rate_x
            if (rate_x > 0 and cur_x > end_x) or (rate_x < 0 and cur_x < end_x):
                # We've moved too far; back up and undo that last move.
                cur_x -= rate_x
                rate_x = 0

            cur_y += rate_y
            if (rate_y > 0 and cur_y > end_y) or (rate_y < 0 and cur_y < end_y):
                # We've moved too far; back up and undo that last move.
                cur_y -= rate_y
                rate_y = 0

            crop = image.crop((cur_x, cur_y, cur_x + View.canvas_width, cur_y + View.canvas_height))

            if alpha_overlay:
                crop = Image.alpha_composite(crop, alpha_overlay)

            View.disp.ShowImage(crop, 0, 0)



    def DispShowImageWithText(image, text, font=None, text_color="GREY", text_background=None):
        image_copy = image.copy().convert("RGBA")
        draw = ImageDraw.Draw(image_copy)

        text_overlay = Image.new("RGBA", (View.canvas_width, View.canvas_height), (255,255,255,0))
        text_overlay_draw = ImageDraw.Draw(text_overlay)
        if not font:
            font = View.COURIERNEW14
        tw, th = text_overlay_draw.textsize(text, font=font)
        if text_background:
            text_overlay_draw.rectangle(((240 - tw) / 2 - 3, 240 - th, (240 - tw) / 2 + tw + 3, 240), fill=text_background)
        text_overlay_draw.text(((240 - tw) / 2, 240 - th - 1), text, fill=text_color, font=font)
        View.DispShowImage(image_copy, alpha_overlay=text_overlay)


    def draw_modal(self, lines = [], title = "", bottom = "") -> None:
        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

        if len(title) > 0:
            tw, th = View.draw.textsize(title, font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 2), title, fill=View.color, font=View.IMPACT22)

        if len(bottom) > 0:
            tw, th = View.draw.textsize(bottom, font=View.IMPACT18)
            View.draw.text(((240 - tw) / 2, 210), bottom, fill=View.color, font=View.IMPACT18)

        if len(lines) == 1:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT26)
            View.draw.text(((240 - tw) / 2, 90), lines[0], fill=View.color, font=View.IMPACT26)
        elif len(lines) == 2:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[0], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[1], fill=View.color, font=View.IMPACT22)
        elif len(lines) == 3:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT26)
            View.draw.text(((240 - tw) / 2, 55), lines[0], fill=View.color, font=View.IMPACT26)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[1], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[2], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[2], fill=View.color, font=View.IMPACT22)
        elif len(lines) == 4:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 55), lines[0], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[1], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[2], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[2], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[3], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 160), lines[3], fill=View.color, font=View.IMPACT22)

        View.DispShowImage()

        return

    def draw_prompt_yes_no(self, lines = [], title = "", bottom = "") -> None:

        self.draw_prompt_custom("", "Yes ", "No ", lines, title, bottom)
        return

    def draw_prompt_custom(self, a_txt, b_txt, c_txt, lines = [], title = "", bottom = "") -> None:

        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

        if len(title) > 0:
            tw, th = View.draw.textsize(title, font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 2), title, fill=View.color, font=View.IMPACT22)

        if len(bottom) > 0:
            tw, th = View.draw.textsize(bottom, font=View.IMPACT18)
            View.draw.text(((240 - tw) / 2, 210), bottom, fill=View.color, font=View.IMPACT18)

        if len(lines) == 1:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT26)
            View.draw.text(((240 - tw) / 2, 90), lines[0], fill=View.color, font=View.IMPACT26)
        elif len(lines) == 2:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[0], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[1], fill=View.color, font=View.IMPACT22)
        elif len(lines) == 3:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT26)
            View.draw.text(((240 - tw) / 2, 20), lines[0], fill=View.color, font=View.IMPACT26)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[1], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[2], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[2], fill=View.color, font=View.IMPACT22)
        elif len(lines) == 4:
            tw, th = View.draw.textsize(lines[0], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 20), lines[0], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[1], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 90), lines[1], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[2], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 125), lines[2], fill=View.color, font=View.IMPACT22)
            tw, th = View.draw.textsize(lines[3], font=View.IMPACT22)
            View.draw.text(((240 - tw) / 2, 160), lines[3], fill=View.color, font=View.IMPACT22)

        a_x_offset = 240 - View.IMPACT25.getsize(a_txt)[0]
        View.draw.text((a_x_offset, 39 + 0), a_txt, fill=View.color, font=View.IMPACT25)

        b_x_offset = 240 - View.IMPACT25.getsize(b_txt)[0]
        View.draw.text((b_x_offset , 39 + 60), b_txt, fill=View.color, font=View.IMPACT25)

        c_x_offset = 240 - View.IMPACT25.getsize(c_txt)[0]
        View.draw.text((c_x_offset , 39 + 120), c_txt, fill=View.color, font=View.IMPACT25)

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
        View.draw.text(((240-tw)/2, 45), line1, fill=View.color, font=View.IMPACT22)
        tw, th = View.draw.textsize(line2, font=View.IMPACT20)
        View.draw.text(((240-tw)/2, 100), line2, fill=View.color, font=View.IMPACT20)
        tw, th = View.draw.textsize(line3, font=View.IMPACT20)
        View.draw.text(((240-tw)/2, 130), line3, fill=View.color, font=View.IMPACT20)
        tw, th = View.draw.textsize(line4, font=View.IMPACT20)
        View.draw.text(((240-tw)/2, 160), line4, fill=View.color, font=View.IMPACT20)
        View.DispShowImage()


    def display_blank_screen(self):
        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        View.DispShowImage()


    ###
    ### Reusable components
    ###
    def render_previous_button(self, highlight=False):
        # Set up the "back" arrow in the upper left
        arrow = "<"
        word_font = View.ROBOTOCONDENSED_BOLD_26
        top_padding = -3
        bottom_padding = 3
        side_padding = 3
        tw, th = word_font.getsize(arrow)
        self.previous_button_width = tw + 2 * side_padding
        if highlight:
            font_color = "black"
            background_color = View.color
        else:
            font_color = View.color
            background_color = "black"
        View.draw.rectangle((0,0, self.previous_button_width, th + top_padding + bottom_padding), fill=background_color)
        View.draw.text((side_padding, top_padding), arrow, fill=font_color, font=word_font)



