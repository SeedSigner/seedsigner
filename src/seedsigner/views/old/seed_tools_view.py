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
