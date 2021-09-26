# External Dependencies
from PIL import Image, ImageDraw, ImageFont
import os
import pathlib
import time

from multiprocessing import Queue
from seedsigner.helpers import B
from seedsigner.gui.components import Fonts



class View:
    previous_button_width: int = None


    def __init__(self) -> None:
        # Import here to avoid circular imports
        from seedsigner.controller import Controller
        from seedsigner.gui import Renderer

        self.controller = Controller.get_instance()

        # TODO: Pull all rendering-related code out of Views and into GUI Templates?
        self.renderer = Renderer.get_instance()
        self.canvas_width = self.renderer.canvas_width
        self.canvas_height = self.renderer.canvas_height

        self.buttons = self.controller.buttons
        self.color = self.controller.color

        self.queue = Queue()



    ###
    ### Power Off Screen
    ###

    def display_power_off_screen(self):

        self.renderer.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)

        line1 = "Powering Down..."
        line2 = "Please wait about"
        line3 = "30 seconds before"
        line4 = "disconnecting power."

        tw, th = self.renderer.draw.textsize(line1, font=Fonts.get_font("Assistant-Medium", 22))
        self.renderer.draw.text(((240-tw)/2, 45), line1, fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
        tw, th = self.renderer.draw.textsize(line2, font=Fonts.get_font("Assistant-Medium", 20))
        self.renderer.draw.text(((240-tw)/2, 100), line2, fill=self.color, font=Fonts.get_font("Assistant-Medium", 20))
        tw, th = self.renderer.draw.textsize(line3, font=Fonts.get_font("Assistant-Medium", 20))
        self.renderer.draw.text(((240-tw)/2, 130), line3, fill=self.color, font=Fonts.get_font("Assistant-Medium", 20))
        tw, th = self.renderer.draw.textsize(line4, font=Fonts.get_font("Assistant-Medium", 20))
        self.renderer.draw.text(((240-tw)/2, 160), line4, fill=self.color, font=Fonts.get_font("Assistant-Medium", 20))
        self.renderer.show_image()


    def display_blank_screen(self):
        self.renderer.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)
        self.renderer.show_image()


    ###
    ### Reusable components
    ###
    def render_previous_button(self, highlight=False):
        # Set up the "back" arrow in the upper left
        arrow = "<"
        word_font = Fonts.get_font("RobotoCondensed-Bold", 26)
        top_padding = -3
        bottom_padding = 3
        side_padding = 3
        tw, th = word_font.getsize(arrow)
        self.previous_button_width = tw + 2 * side_padding
        if highlight:
            font_color = "black"
            background_color = self.color
        else:
            font_color = self.color
            background_color = "black"
        self.renderer.draw.rectangle((0,0, self.previous_button_width, th + top_padding + bottom_padding), fill=background_color)
        self.renderer.draw.text((side_padding, top_padding), arrow, fill=font_color, font=word_font)



