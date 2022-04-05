from PIL import Image, ImageDraw, ImageFont
from threading import Lock

from seedsigner.gui.components import Fonts, GUIConstants
from seedsigner.hardware.ST7789 import ST7789
from seedsigner.models import ConfigurableSingleton



class Renderer(ConfigurableSingleton):
    buttons = None
    canvas_width = 0
    canvas_height = 0
    canvas: Image.Image = None
    draw: ImageDraw.ImageDraw = None
    disp = None
    lock = Lock()


    @classmethod
    def configure_instance(cls):
        from seedsigner.models.settings import Settings

        # Instantiate the one and only Renderer instance
        renderer = cls.__new__(cls)
        cls._instance = renderer

        # Eventually we'll be able to plug in other display controllers
        renderer.disp = ST7789()
        renderer.canvas_width = renderer.disp.width
        renderer.canvas_height = renderer.disp.height

        renderer.canvas = Image.new('RGB', (renderer.canvas_width, renderer.canvas_height))
        renderer.draw = ImageDraw.Draw(renderer.canvas)


    def show_image(self, image=None, alpha_overlay=None):
        if alpha_overlay:
            if image == None:
                image = self.canvas
            image = Image.alpha_composite(image, alpha_overlay)

        if image:
            # Always write to the current canvas, rather than trying to replace it
            self.canvas.paste(image)

        self.disp.ShowImage(self.canvas, 0, 0)


    def show_image_pan(self, image, start_x, start_y, end_x, end_y, rate, alpha_overlay=None):
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

            crop = image.crop((cur_x, cur_y, cur_x + self.canvas_width, cur_y + self.canvas_height))

            if alpha_overlay:
                crop = Image.alpha_composite(crop, alpha_overlay)

            # Always keep a copy of the current display in the canvas
            self.canvas.paste(crop)

            self.disp.ShowImage(crop, 0, 0)


    # TODO: Remove all references
    def show_image_with_text(self, image, text, font=None, text_color="GREY", text_background=None):
        image_copy = image.copy().convert("RGBA")

        text_overlay = Image.new("RGBA", (self.canvas_width, self.canvas_height), (255,255,255,0))
        text_overlay_draw = ImageDraw.Draw(text_overlay)
        if not font:
            font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BODY_FONT_SIZE)
        tw, th = text_overlay_draw.textsize(text, font=font)
        if text_background:
            text_overlay_draw.rectangle(((240 - tw) / 2 - 3, 240 - th, (240 - tw) / 2 + tw + 3, 240), fill=text_background)
        text_overlay_draw.text(((240 - tw) / 2, 240 - th - 1), text, fill=text_color, font=font)

        self.show_image(image_copy, alpha_overlay=text_overlay)


    # TODO: Should probably move this to screens.py
    def draw_modal(self, lines = [], title = "", bottom = "") -> None:
        self.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)

        if len(title) > 0:
            tw, th = self.draw.textsize(title, font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 2), title, fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))

        if len(bottom) > 0:
            tw, th = self.draw.textsize(bottom, font=Fonts.get_font("Assistant-Medium", 18))
            self.draw.text(((240 - tw) / 2, 210), bottom, fill=self.color, font=Fonts.get_font("Assistant-Medium", 18))

        if len(lines) == 1:
            tw, th = self.draw.textsize(lines[0], font=Fonts.get_font("Assistant-Medium", 26))
            self.draw.text(((240 - tw) / 2, 90), lines[0], fill=self.color, font=Fonts.get_font("Assistant-Medium", 26))
        elif len(lines) == 2:
            tw, th = self.draw.textsize(lines[0], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 90), lines[0], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[1], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 125), lines[1], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
        elif len(lines) == 3:
            tw, th = self.draw.textsize(lines[0], font=Fonts.get_font("Assistant-Medium", 26))
            self.draw.text(((240 - tw) / 2, 55), lines[0], fill=self.color, font=Fonts.get_font("Assistant-Medium", 26))
            tw, th = self.draw.textsize(lines[1], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 90), lines[1], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[2], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 125), lines[2], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
        elif len(lines) == 4:
            tw, th = self.draw.textsize(lines[0], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 55), lines[0], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[1], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 90), lines[1], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[2], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 125), lines[2], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[3], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 160), lines[3], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))

        self.show_image()

        return


    # TODO: Should probably move this to templates.py
    def draw_prompt_yes_no(self, lines = [], title = "", bottom = "") -> None:
        self.draw_prompt_custom("", "Yes ", "No ", lines, title, bottom)
        return


    # TODO: Should probably move this to templates.py
    def draw_prompt_custom(self, a_txt, b_txt, c_txt, lines = [], title = "", bottom = "") -> None:
        self.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)

        if len(title) > 0:
            tw, th = self.draw.textsize(title, font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 2), title, fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))

        if len(bottom) > 0:
            tw, th = self.draw.textsize(bottom, font=Fonts.get_font("Assistant-Medium", 18))
            self.draw.text(((240 - tw) / 2, 210), bottom, fill=self.color, font=Fonts.get_font("Assistant-Medium", 18))

        if len(lines) == 1:
            tw, th = self.draw.textsize(lines[0], font=Fonts.get_font("Assistant-Medium", 26))
            self.draw.text(((240 - tw) / 2, 90), lines[0], fill=self.color, font=Fonts.get_font("Assistant-Medium", 26))
        elif len(lines) == 2:
            tw, th = self.draw.textsize(lines[0], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 90), lines[0], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[1], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 125), lines[1], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
        elif len(lines) == 3:
            tw, th = self.draw.textsize(lines[0], font=Fonts.get_font("Assistant-Medium", 26))
            self.draw.text(((240 - tw) / 2, 20), lines[0], fill=self.color, font=Fonts.get_font("Assistant-Medium", 26))
            tw, th = self.draw.textsize(lines[1], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 90), lines[1], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[2], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 125), lines[2], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
        elif len(lines) == 4:
            tw, th = self.draw.textsize(lines[0], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 20), lines[0], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[1], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 90), lines[1], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[2], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 125), lines[2], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))
            tw, th = self.draw.textsize(lines[3], font=Fonts.get_font("Assistant-Medium", 22))
            self.draw.text(((240 - tw) / 2, 160), lines[3], fill=self.color, font=Fonts.get_font("Assistant-Medium", 22))

        a_x_offset = 240 - Fonts.get_font("Assistant-Medium", 25).getsize(a_txt)[0]
        self.draw.text((a_x_offset, 39 + 0), a_txt, fill=self.color, font=Fonts.get_font("Assistant-Medium", 25))

        b_x_offset = 240 - Fonts.get_font("Assistant-Medium", 25).getsize(b_txt)[0]
        self.draw.text((b_x_offset , 39 + 60), b_txt, fill=self.color, font=Fonts.get_font("Assistant-Medium", 25))

        c_x_offset = 240 - Fonts.get_font("Assistant-Medium", 25).getsize(c_txt)[0]
        self.draw.text((c_x_offset , 39 + 120), c_txt, fill=self.color, font=Fonts.get_font("Assistant-Medium", 25))

        self.show_image()

        return


    def display_blank_screen(self):
        self.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)
        self.show_image()




