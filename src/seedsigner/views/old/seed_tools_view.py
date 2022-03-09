import math
import time
from PIL import ImageDraw, Image

from . import View

from seedsigner.helpers import QR, mnemonic_generation
from seedsigner.gui.components import Fonts
from seedsigner.models import DecodeQR, DecodeQRStatus, QRType, EncodeQR



class SeedToolsView(View):
    def __init__(self) -> None:
        super().__init__()

        # Gather words and seed display information
        self.words = []
        self.letters = []
        self.possible_alphabet = []
        self.possible_words = []
        self.selected_possible_words_index = 0
        self.seed_length = 12     # Default to 12, Valid values are 11, 12, 23 and 24
        self.seed_qr_image = None
        self.seed_entropy_image = None

        # Dice information
        self.roll_number = 1
        self.dice_selected = 0
        self.roll_data = ""
        self.dice_seed_phrase = []



    ###
    ### Display Seed from Dice
    ###
    def display_generate_seed_from_dice(self):
        self.roll_number = 1
        self.dice_selected = 5
        self.roll_data = ""

        self.draw_dice(self.dice_selected)
        time.sleep(1) # pause for 1 second before accepting input

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS, B.KEY_RIGHT, B.KEY_LEFT])
            if input == B.KEY_UP:
                ret_val = self.dice_arrow_up()
            elif input == B.KEY_DOWN:
                ret_val = self.dice_arrow_down()
            elif input == B.KEY_RIGHT:
                ret_val = self.dice_arrow_right()
            elif input == B.KEY_LEFT:
                ret_val = self.dice_arrow_left()
            elif input == B.KEY_PRESS:
                ret_val = self.dice_arrow_press()

            if ret_val == False:
                return []

            if self.roll_number >= 100:
                self.dice_seed_phrase = mnemonic_generation.generate_mnemonic_from_dice(self.roll_data)
                return self.dice_seed_phrase[:]


    def dice_arrow_up(self):
        new_selection = 0
        if self.dice_selected == 4:
            new_selection = 1
        elif self.dice_selected == 5:
            new_selection = 2
        elif self.dice_selected == 6:
            new_selection = 3

        if self.dice_selected != new_selection and new_selection != 0:
            self.draw_dice(new_selection)

        return True


    def dice_arrow_down(self):
        new_selection = 0
        if self.dice_selected == 1:
            new_selection = 4
        elif self.dice_selected == 2:
            new_selection = 5
        elif self.dice_selected == 3:
            new_selection = 6

        if self.dice_selected != new_selection and new_selection != 0:
            self.draw_dice(new_selection)

        return True


    def dice_arrow_right(self):
        new_selection = 0
        if self.dice_selected == 1:
            new_selection = 2
        elif self.dice_selected == 2:
            new_selection = 3
        elif self.dice_selected == 4:
            new_selection = 5
        elif self.dice_selected == 5:
            new_selection = 6

        if self.dice_selected != new_selection and new_selection != 0:
            self.draw_dice(new_selection)

        return True


    def dice_arrow_left(self):
        if self.dice_selected == 1:
            self.draw_prompt_custom("Undo ", "Cancel ", "Exit ", ["Action:  ", "", ""])
            input = self.buttons.wait_for([B.KEY1, B.KEY2, B.KEY3])
            if input == B.KEY1: #Undo
                self.roll_number = self.roll_number - 1
                self.roll_data = self.roll_data[:-1] # remove last character from string
                if self.roll_number >= 1:
                    self.draw_dice(self.dice_selected)
                    return True
                else:
                    return False
            elif input == B.KEY2: # Cancel
                self.draw_dice(self.dice_selected)
                return True
            elif input == B.KEY3: # Exit
                return False

        new_selection = 0
        if self.dice_selected == 3:
            new_selection = 2
        elif self.dice_selected == 2:
            new_selection = 1
        elif self.dice_selected == 6:
            new_selection = 5
        elif self.dice_selected == 5:
            new_selection = 4

        if self.dice_selected != new_selection and new_selection != 0:
            self.draw_dice(new_selection)

        return True


    def dice_arrow_press(self):
        self.roll_number += 1
        self.roll_data += str(self.dice_selected)

        # Reset for the next UI render
        if self.roll_number > 45:
            self.dice_selected = 5
        else:
            self.dice_selected = 2
            
        if self.roll_number < 100:
            self.draw_dice(self.dice_selected)

        return True


    def draw_dice(self, dice_selected):
        self.renderer.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)
        self.renderer.draw.text((45, 5), "Dice roll: " + str(self.roll_number) + "/99", fill=self.color, font=Fonts.get_font("Assistant-Medium", 26))

        # when dice is selected, rect fill will be orange and ellipse will be black, ellipse outline will be the black
        # when dice is not selected, rect will will be black and ellipse will be orange, ellipse outline will be orange

        # dice 1
        if dice_selected == 1:
            self.renderer.draw.rectangle((5, 50, 75, 120),   outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(34, 79), (46, 91)], outline="BLACK",  fill="BLACK")
        else:
            self.renderer.draw.rectangle((5, 50, 75, 120),   outline=self.color, fill="BLACK")
            self.renderer.draw.ellipse([(34, 79), (46, 91)], outline=self.color, fill=self.color)

        # dice 2
        if dice_selected == 2:
            self.renderer.draw.rectangle((85, 50, 155, 120), outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(100, 60), (112, 72)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(128, 98), (140, 110)], outline="BLACK", fill="BLACK")
        else:
            self.renderer.draw.rectangle((85, 50, 155, 120), outline=self.color, fill="BLACK")
            self.renderer.draw.ellipse([(100, 60), (112, 72)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(128, 98), (140, 110)], outline=self.color, fill=self.color)

        # dice 3
        if dice_selected == 3:
            self.renderer.draw.rectangle((165, 50, 235, 120), outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(180, 60), (192, 72)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(194, 79), (206, 91)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(208, 98), (220, 110)], outline="BLACK", fill="BLACK")
        else:
            self.renderer.draw.rectangle((165, 50, 235, 120), outline=self.color, fill="BLACK")
            self.renderer.draw.ellipse([(180, 60), (192, 72)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(194, 79), (206, 91)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(208, 98), (220, 110)], outline=self.color, fill=self.color)

        # dice 4
        if dice_selected == 4:
            self.renderer.draw.rectangle((5, 130, 75, 200), outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(20, 140), (32, 152)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(20, 174), (32, 186)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(48, 140), (60, 152)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(48, 174), (60, 186)], outline="BLACK", fill="BLACK")
        else:
            self.renderer.draw.rectangle((5, 130, 75, 200), outline=self.color, fill="BLACK")
            self.renderer.draw.ellipse([(20, 140), (32, 152)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(20, 174), (32, 186)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(48, 140), (60, 152)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(48, 174), (60, 186)], outline=self.color, fill=self.color)

        # dice 5
        if dice_selected == 5:
            self.renderer.draw.rectangle((85, 130, 155, 200), outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(100, 140), (112, 152)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(100, 178), (112, 190)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(114, 159), (126, 171)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(128, 140), (140, 152)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(128, 178), (140, 190)], outline="BLACK", fill="BLACK")
        else:
            self.renderer.draw.rectangle((85, 130, 155, 200), outline=self.color, fill="BLACK")
            self.renderer.draw.ellipse([(100, 140), (112, 152)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(100, 178), (112, 190)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(114, 159), (126, 171)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(128, 140), (140, 152)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(128, 178), (140, 190)], outline=self.color, fill=self.color)

        # dice 6
        if dice_selected == 6:
            self.renderer.draw.rectangle((165, 130, 235, 200), outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(180, 140), (192, 152)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(180, 157), (192, 169)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(180, 174), (192, 186)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(208, 140), (220, 152)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(208, 157), (220, 169)], outline="BLACK", fill="BLACK")
            self.renderer.draw.ellipse([(208, 174), (220, 186)], outline="BLACK", fill="BLACK")
        else:
            self.renderer.draw.rectangle((165, 130, 235, 200), outline=self.color, fill="BLACK")
            self.renderer.draw.ellipse([(180, 140), (192, 152)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(180, 157), (192, 169)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(180, 174), (192, 186)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(208, 140), (220, 152)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(208, 157), (220, 169)], outline=self.color, fill=self.color)
            self.renderer.draw.ellipse([(208, 174), (220, 186)], outline=self.color, fill=self.color)

        # bottom text
        self.renderer.draw.text((18, 210), "Press Control Stick to Select", fill=self.color, font=Fonts.get_font("Assistant-Medium", 18))
        self.renderer.show_image()

        self.dice_selected = dice_selected

    ###
    ### Display Seed Phrase
    ###

    def display_seed_qr_options(self, seed_phrase) -> int:
        if len(seed_phrase) == 24:
            standard = "29x29"
            compact = "25x25"
        else:
            standard = "25x25"
            compact = "21x21"
        r = self.controller.menu_view.display_generic_selection_menu(
            ["... [ Return to Seed Tools ]", f"Standard SeedQR: {standard}", f"Compact SeedQR: {compact}"],
            "Transcribe SeedQR"
        )
        if r == 2:
            return self.seed_phrase_as_qr(seed_phrase, is_compact_seedqr=False)
        elif r == 3:
            return self.seed_phrase_as_qr(seed_phrase, is_compact_seedqr=True)
        else:
            return None


    def seed_phrase_as_qr(self, seed_phrase, is_compact_seedqr=False):
        if is_compact_seedqr:
            e = EncodeQR(seed_phrase=seed_phrase, qr_type=QRType.SEED__COMPACTSEEDQR, wordlist=self.settings.wordlist)
        else:
            e = EncodeQR(seed_phrase=seed_phrase, qr_type=QRType.SEED__SEEDQR, wordlist=self.settings.wordlist)
        data = e.next_part()
        qr = QR()
        image = qr.qrimage(
            data=data,
            width=240,
            height=240,
            border=3,
            style=QR.STYLE__ROUNDED).convert("RGBA")
        View.DispShowImageWithText(image, "click to zoom, right to exit", font=View.ASSISTANT18, text_color="BLACK", text_background="ORANGE")

        input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_PRESS])
        if input == B.KEY_RIGHT:
            return

        elif input == B.KEY_PRESS:
            # Render an oversized QR code that we can view up close
            pixels_per_block = 24

            # Border must accommodate the 3 blocks outside the center 5x5 mask plus up to
            # 4 empty blocks inside the 5x5 mask (21x21 has a 1-block final col/row).
            qr_border = 7
            qr_blocks_per_zoom = 5
            if len(seed_phrase) == 24:
                if is_compact_seedqr:
                    num_modules = 25
                else:
                    num_modules = 29
            else:
                if is_compact_seedqr:
                    num_modules = 21

                    # Optimize for 21x21
                    qr_blocks_per_zoom = 7
                else:
                    num_modules = 25

            width = (qr_border + num_modules + qr_border) * pixels_per_block
            height = width
            data = e.next_part()
            qr = QR()
            image = qr.qrimage(
                data,
                width=width,
                height=height,
                border=qr_border,
                style=QR.STYLE__ROUNDED).convert("RGBA")

            # Render gridlines but leave the 1-block border as-is
            draw = ImageDraw.Draw(image)
            for i in range(qr_border, math.floor(width/pixels_per_block) - qr_border):
                draw.line((i * pixels_per_block, qr_border * pixels_per_block, i * pixels_per_block, height - qr_border * pixels_per_block), fill="#bbb")
                draw.line((qr_border * pixels_per_block, i * pixels_per_block, width - qr_border * pixels_per_block, i * pixels_per_block), fill="#bbb")

            # Prep the semi-transparent mask overlay
            # make a blank image for the overlay, initialized to transparent
            block_mask = Image.new("RGBA", (self.canvas_width, self.canvas_height), (255,255,255,0))
            draw = ImageDraw.Draw(block_mask)

            mask_width = int((self.canvas_width - qr_blocks_per_zoom * pixels_per_block)/2)
            mask_height = int((self.canvas_height - qr_blocks_per_zoom * pixels_per_block)/2)
            mask_rgba = (0, 0, 0, 226)
            draw.rectangle((0, 0, self.canvas_width, mask_height), fill=mask_rgba)
            draw.rectangle((0, self.canvas_height - mask_height - 1, self.canvas_width, self.canvas_height), fill=mask_rgba)
            draw.rectangle((0, mask_height, mask_width, self.canvas_height - mask_height), fill=mask_rgba)
            draw.rectangle((self.canvas_width - mask_width - 1, mask_height, self.canvas_width, self.canvas_height - mask_height), fill=mask_rgba)

            # Draw a box around the cutout portion of the mask for better visibility
            draw.line((mask_width, mask_height, mask_width, self.canvas_height - mask_height), fill=self.color)
            draw.line((self.canvas_width - mask_width, mask_height, self.canvas_width - mask_width, self.canvas_height - mask_height), fill=self.color)
            draw.line((mask_width, mask_height, self.canvas_width - mask_width, mask_height), fill=self.color)
            draw.line((mask_width, self.canvas_height - mask_height, self.canvas_width - mask_width, self.canvas_height - mask_height), fill=self.color)

            msg = "click to exit"
            tw, th = draw.textsize(msg, font=Fonts.get_font("Assistant-Medium", 18))
            draw.text(((self.canvas_width - tw) / 2, self.canvas_height - th - 2), msg, fill=self.color, font=Fonts.get_font("Assistant-Medium", 18))

            def draw_block_labels(cur_block_x, cur_block_y):
                # Create overlay for block labels (e.g. "D-5")
                block_labels_x = ["1", "2", "3", "4", "5", "6"]
                block_labels_y = ["A", "B", "C", "D", "E", "F"]

                block_labels = Image.new("RGBA", (self.canvas_width, self.canvas_height), (255,255,255,0))
                draw = ImageDraw.Draw(block_labels)
                draw.rectangle((mask_width, 0, self.canvas_width - mask_width, pixels_per_block), fill=self.color)
                draw.rectangle((0, mask_height, pixels_per_block, self.canvas_height - mask_height), fill=self.color)

                label_font = Fonts.get_font("Assistant-Medium", 26)
                x_label = block_labels_x[cur_block_x]
                tw, th = draw.textsize(x_label, font=label_font)

                # note: have to nudge the y-coord up (the extra "- 4") for some reason
                draw.text(((self.canvas_width - tw) / 2, ((pixels_per_block - th) / 2) - 4), x_label, fill="BLACK", font=label_font)

                y_label = block_labels_y[cur_block_y]
                tw, th = draw.textsize(y_label, font=label_font)
                draw.text(((pixels_per_block - tw) / 2, (self.canvas_height - th) / 2), y_label, fill="BLACK", font=label_font)

                return block_labels

            block_labels = draw_block_labels(0, 0)

            # Track our current coordinates for the upper left corner of our view
            cur_block_x = 0
            cur_block_y = 0
            cur_x = qr_border * pixels_per_block - mask_width
            cur_y = qr_border * pixels_per_block - mask_height
            next_x = cur_x
            next_y = cur_y

            self.renderer.show_image(
                image.crop((cur_x, cur_y, cur_x + self.canvas_width, cur_y + self.canvas_height)),
                alpha_overlay=Image.alpha_composite(block_mask, block_labels)
            )

            while True:
                input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT, B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS])
                if input == B.KEY_RIGHT:
                    next_x = cur_x + qr_blocks_per_zoom * pixels_per_block
                    cur_block_x += 1
                    if next_x > width - self.canvas_width:
                        next_x = cur_x
                        cur_block_x -= 1
                elif input == B.KEY_LEFT:
                    next_x = cur_x - qr_blocks_per_zoom * pixels_per_block
                    cur_block_x -= 1
                    if next_x < 0:
                        next_x = cur_x
                        cur_block_x += 1
                elif input == B.KEY_DOWN:
                    next_y = cur_y + qr_blocks_per_zoom * pixels_per_block
                    cur_block_y += 1
                    if next_y > height - self.canvas_height:
                        next_y = cur_y
                        cur_block_y -= 1
                elif input == B.KEY_UP:
                    next_y = cur_y - qr_blocks_per_zoom * pixels_per_block
                    cur_block_y -= 1
                    if next_y < 0:
                        next_y = cur_y
                        cur_block_y += 1
                elif input == B.KEY_PRESS:
                    return

                # Create overlay for block labels (e.g. "D-5")
                block_labels = draw_block_labels(cur_block_x, cur_block_y)

                if cur_x != next_x or cur_y != next_y:
                    self.renderer.show_image_pan(
                        image,
                        cur_x, cur_y, next_x, next_y,
                        rate=pixels_per_block,
                        alpha_overlay=Image.alpha_composite(block_mask, block_labels)
                    )
                    cur_x = next_x
                    cur_y = next_y

    def read_seed_phrase_qr(self):
        self.draw_modal(["Scanning..."], "Seed QR" ,"Right to Exit")
        try:
            self.controller.camera.start_video_stream_mode(resolution=(480, 480), framerate=12, format="rgb")
            decoder = DecodeQR(wordlist=self.settings.wordlist)
            while True:
                frame = self.controller.camera.read_video_stream(as_image=True)
                if frame is not None:
                    self.renderer.show_image_with_text(frame.resize((240,240)), "Scan Seed QR", font=Fonts.get_font("Assistant-Medium", 22), text_color=self.color, text_background=(0,0,0,225))
                    status = decoder.add_image(frame)

                    if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                        break
                    
                    if self.buttons.check_for_low(B.KEY_RIGHT) or self.buttons.check_for_low(B.KEY_LEFT):
                        self.controller.camera.stop_video_stream_mode()
                        self.words = []
                        return self.words[:]

            if decoder.is_complete and decoder.is_seed:
                self.words = decoder.get_seed_phrase()
            elif not decoder.is_psbt:
                self.draw_modal(["Not a valid Seed QR"], "", "Right to Exit")
                input = self.buttons.wait_for([B.KEY_RIGHT])
            else:
                self.draw_modal(["QR Parsing Failed"], "", "Right to Exit")
                input = self.buttons.wait_for([B.KEY_RIGHT])
                self.words = []

        finally:
            self.controller.camera.stop_video_stream_mode()

        return self.words[:]

