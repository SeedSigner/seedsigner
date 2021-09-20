
from .components import (EDGE_PADDING, COMPONENT_PADDING, Button, TopNav, 
    TextArea)

from PIL import ImageFont
from seedsigner.helpers import B
from seedsigner.views import View



class BaseScreen(View):
    def __init__(self, title:str, font=None):
        super().__init__()
        self.title = title
        self.top_nav = TopNav(
            text=self.title,
            width=self.canvas_width,
            height=(2 * EDGE_PADDING) + int(self.canvas_width * 2.0 / 15.0),     # 32px on a 240x240 screen
            draw=View.draw,
            font=font,
        )


    def render(self):
        View.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), fill=0)
        self.top_nav.render()
        View.DispShowImage()



class ButtonListScreen(BaseScreen):
    def __init__(self, title:str, button_data:list, is_button_text_centered:bool, is_bottom_list:bool, title_font=None, button_font=None):
        super().__init__(title, title_font)

        self.button_data = button_data
        self.is_bottom_list = is_bottom_list

        button_height = int(self.canvas_height * 3.0 / 20.0)    # 36px on a 240x240 screen
        if len(self.button_data) == 1:
            button_list_height = button_height
        else:
            button_list_height = (len(self.button_data) * button_height) + (COMPONENT_PADDING * (len(self.button_data) - 1))

        if is_bottom_list:
            button_list_y = self.canvas_height - (button_list_height + EDGE_PADDING)
        else:
            button_list_y = self.top_nav.height + int((self.canvas_height - self.top_nav.height - button_list_height) / 2)

        self.buttons = []
        for i, entry in enumerate(button_data):
            button = Button(
                text=entry["text"],
                screen_x=EDGE_PADDING,
                screen_y=button_list_y + i * (button_height + COMPONENT_PADDING),
                width=self.canvas_width - (2 * EDGE_PADDING),
                height=button_height,
                draw=View.draw,
                is_text_centered=is_button_text_centered,
                font=button_font,
            )
            self.buttons.append(button)

        self.buttons[0].is_selected = True
        self.selected_button = 0


    def render(self):
        View.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), fill=0)
        self.top_nav.render()
        for button in self.buttons:
            button.render()
        View.DispShowImage()


    def update_from_input(self, input):
        if input == B.KEY_UP:
            if self.selected_button == 0:
                # Move selection up to top_nav
                pass
            else:
                self.buttons[self.selected_button].is_selected = False
                self.buttons[self.selected_button].render()
                self.selected_button -= 1
                self.buttons[self.selected_button].is_selected = True
                self.buttons[self.selected_button].render()

        elif input == B.KEY_DOWN:
            if self.selected_button == len(self.buttons) - 1:
                # Trap selection at bottom?
                pass
            else:
                self.buttons[self.selected_button].is_selected = False
                self.buttons[self.selected_button].render()
                self.selected_button += 1
                self.buttons[self.selected_button].is_selected = True
                self.buttons[self.selected_button].render()

        else:
            return

        View.DispShowImage()



class BottomButtonScreen(ButtonListScreen):
    def __init__(self, title:str, button_data:list, is_button_text_centered:bool, title_font=None, body_text=None, is_body_text_centered=True, body_font_color=None, body_font=None, button_font=None):
        super().__init__(title=title, button_data=button_data, is_button_text_centered=is_button_text_centered, is_bottom_list=True, title_font=title_font, button_font=button_font)

        self.body_textscreen = TextArea(
            text=body_text,
            screen_x=0,
            screen_y=self.top_nav.height,
            width=self.canvas_width,
            height=self.buttons[0].screen_y - self.top_nav.height,
            draw=View.draw,
            font=body_font,
            font_color=body_font_color,
            is_text_centered=is_body_text_centered
        )


    def render(self):
        View.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), fill=0)
        self.top_nav.render()
        self.body_textscreen.render()
        for button in self.buttons:
            button.render()
        View.DispShowImage()



class FontTesterScreen(ButtonListScreen):
    def __init__(self, title:str, button_data:list, is_text_centered:bool, is_bottom_list:bool, font, button_font):
        super().__init__(title, button_data, is_text_centered, is_bottom_list, font, button_font)


