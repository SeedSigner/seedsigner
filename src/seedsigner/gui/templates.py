
from .components import (EDGE_PADDING, COMPONENT_PADDING, Button, TopNav, 
    TextArea)

from PIL import ImageFont
from seedsigner.helpers import B
from seedsigner.views import View



class BaseScreen:
    def __init__(self,
                 title:str,
                 font: ImageFont = None):
        from seedsigner.gui import Renderer
        self.renderer = Renderer.get_instance()
        self.title = title
        self.top_nav = TopNav(
            text=self.title,
            width=self.renderer.canvas_width,
            height=(2 * EDGE_PADDING) + int(self.renderer.canvas_width * 2.0 / 15.0),     # 32px on a 240x240 screen
            font=font,
        )


    def render(self):
        self.renderer.draw.rectangle((0, 0, self.renderer.canvas_width, self.renderer.canvas_height), fill=0)
        self.top_nav.render()
        self.renderer.show_image()



class ButtonListScreen(BaseScreen):
    def __init__(self,
                 title: str,
                 button_data: list,                  # w/Python 3.9 we can be more specific: list[str]
                 is_button_text_centered: bool,
                 is_bottom_list: bool,
                 title_font: ImageFont = None,
                 button_font: ImageFont = None,
                 button_selected_color: str = "orange"):
        super().__init__(title, title_font)

        self.button_data = button_data
        self.is_bottom_list = is_bottom_list

        button_height = int(self.renderer.canvas_height * 3.0 / 20.0)    # 36px on a 240x240 screen
        if len(self.button_data) == 1:
            button_list_height = button_height
        else:
            button_list_height = (len(self.button_data) * button_height) + (COMPONENT_PADDING * (len(self.button_data) - 1))

        if is_bottom_list:
            button_list_y = self.renderer.canvas_height - (button_list_height + EDGE_PADDING)
        else:
            button_list_y = self.top_nav.height + int((self.renderer.canvas_height - self.top_nav.height - button_list_height) / 2)

        self.buttons = []
        for i, entry in enumerate(button_data):
            button = Button(
                text=entry["text"],
                screen_x=EDGE_PADDING,
                screen_y=button_list_y + i * (button_height + COMPONENT_PADDING),
                width=self.renderer.canvas_width - (2 * EDGE_PADDING),
                height=button_height,
                is_text_centered=is_button_text_centered,
                font=button_font,
                selected_color=button_selected_color
            )
            self.buttons.append(button)

        self.buttons[0].is_selected = True
        self.selected_button = 0


    def render(self):
        self.renderer.draw.rectangle((0, 0, self.renderer.canvas_width, self.renderer.canvas_height), fill=0)
        self.top_nav.render()
        for button in self.buttons:
            button.render()
        self.renderer.show_image()


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

        self.renderer.show_image()



class BottomButtonScreen(ButtonListScreen):
    def __init__(self,
                 title: str,
                 button_data: list,
                 is_button_text_centered: bool,
                 title_font: ImageFont = None,
                 body_text: str = None,
                 is_body_text_centered: bool = True,
                 body_font_color: str = None,
                 body_font_name: str = None,
                 body_font_size: int = None,
                 button_font: ImageFont = None,
                 supersampling_factor: int = None):
        super().__init__(
            title=title,
            button_data=button_data,
            is_button_text_centered=is_button_text_centered,
            is_bottom_list=True,
            title_font=title_font,
            button_font=button_font
        )

        self.body_textscreen = TextArea(
            text=body_text,
            screen_x=0,
            screen_y=self.top_nav.height,
            width=self.renderer.canvas_width,
            height=self.buttons[0].screen_y - self.top_nav.height,
            font_name=body_font_name,
            font_size=body_font_size,
            font_color=body_font_color,
            is_text_centered=is_body_text_centered,
            supersampling_factor=supersampling_factor
        )


    def render(self):
        self.renderer.draw.rectangle((0, 0, self.renderer.canvas_width, self.renderer.canvas_height), fill=0)
        self.top_nav.render()
        self.body_textscreen.render()
        for button in self.buttons:
            button.render()
        self.renderer.show_image()



class FontTesterScreen(ButtonListScreen):
    def __init__(self,
                 title: str,
                 button_data: list,
                 is_text_centered: bool,
                 is_bottom_list: bool,
                 font: ImageFont,
                 button_font: ImageFont):
        super().__init__(
            title=title,
            button_data=button_data,
            is_text_centered=is_text_centered,
            is_bottom_list=is_bottom_list,
            font=font,
            button_font=button_font
        )


