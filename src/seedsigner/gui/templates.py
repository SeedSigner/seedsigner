
from .components import (EDGE_PADDING, COMPONENT_PADDING, Button, TopNav, 
    TextArea)

from dataclasses import dataclass
from PIL import ImageFont
from seedsigner.helpers import B, Buttons
from seedsigner.views import View



@dataclass
class BaseScreen:
    # Avoid setting defaults on parent dataclasses, otherwise you must have defaults on
    #   all child attrs. see: https://stackoverflow.com/a/53085935
    # No base attrs specified yet


    def __post_init__(self):
        from seedsigner.gui import Renderer
        self.renderer = Renderer.get_instance()
        self.hw_inputs = Buttons.get_instance()


    def render(self, show_image: bool = True):
        # Clear the whole canvas
        self.renderer.draw.rectangle((0, 0, self.renderer.canvas_width, self.renderer.canvas_height), fill=0)

        if show_image:
            # Will be false when called by child classes; they'll want to keep writing
            #   their own UI content before calling show_image() themselves.
            self.renderer.show_image()


    def run(self):
        """
            Screen can run on its own until it returns a final exit input from the user.

            For example: A basic menu screen where the user can key up and down. The
            Screen can handle the UI updates to light up the currently selected menu item
            on its own. Only when the user clicks to make a selection would run() exit
            and returns the selected option.

            But an alternate use case returns immediately after each user input so the
            View can update its controlling logic accordingly (e.g. as the user joysticks
            over different letters in the keyboard UI, we need to make matching changes
            to the list of mnemonic seed words that match the new letter).

            In this case, it would be called repeatedly in a loop:
            * run() and wait for it to handle user input
            * run() exits and returns the user input (e.g. KEY_UP)
            * View updates its state of the world accordingly
            * loop and call run() again
        """
        raise Exception("Must implement in a child class")



@dataclass
class BaseTopNavScreen(BaseScreen):
    title:str

    def __post_init__(self):
        super().__post_init__()
        self.top_nav = TopNav(
            text=self.title,
            width=self.renderer.canvas_width,
            height=(2 * EDGE_PADDING) + int(self.renderer.canvas_width * 2.0 / 15.0),     # 32px on a 240x240 screen
        )


    def render(self, show_image: bool = True):
        super().render(show_image=False)    # Child always tells parent to wait

        self.top_nav.render()

        if show_image:
            self.renderer.show_image()



@dataclass
class ButtonListScreen(BaseTopNavScreen):
    title: str      # Not necessary to include this since it's in parent; just here for clarity
    button_labels: list                  # w/Python 3.9 we can be more specific: list[str]
    selected_button: int = 0
    is_button_text_centered: bool = True
    is_bottom_list: bool = False
    button_font: ImageFont = None
    button_selected_color: str = "orange"

    def __post_init__(self):
        super().__post_init__()

        button_height = int(self.renderer.canvas_height * 3.0 / 20.0)    # 36px on a 240x240 screen
        if len(self.button_labels) == 1:
            button_list_height = button_height
        else:
            button_list_height = (len(self.button_labels) * button_height) + (COMPONENT_PADDING * (len(self.button_labels) - 1))

        if self.is_bottom_list:
            button_list_y = self.renderer.canvas_height - (button_list_height + EDGE_PADDING)
        else:
            button_list_y = self.top_nav.height + int((self.renderer.canvas_height - self.top_nav.height - button_list_height) / 2)

        self.buttons = []
        for i, button_label in enumerate(self.button_labels):
            button = Button(
                text=button_label,
                screen_x=EDGE_PADDING,
                screen_y=button_list_y + i * (button_height + COMPONENT_PADDING),
                width=self.renderer.canvas_width - (2 * EDGE_PADDING),
                height=button_height,
                is_text_centered=self.is_button_text_centered,
                font=self.button_font,
                selected_color=self.button_selected_color
            )
            self.buttons.append(button)

        self.buttons[0].is_selected = True
        self.selected_button = 0


    def render(self, show_image: bool = True):
        super().render(show_image=False)    # Child always tells parent to wait

        for button in self.buttons:
            button.render()

        self.renderer.show_image()


    def run(self):
        while True:
            user_input = self.hw_inputs.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            if user_input == B.KEY_UP:
                if self.selected_button == 0:
                    # TODO: Move selection up to top_nav
                    pass
                else:
                    self.buttons[self.selected_button].is_selected = False
                    self.buttons[self.selected_button].render()
                    self.selected_button -= 1
                    self.buttons[self.selected_button].is_selected = True
                    self.buttons[self.selected_button].render()

            elif user_input == B.KEY_DOWN:
                if self.selected_button == len(self.buttons) - 1:
                    # TODO: Trap selection at bottom?
                    pass
                else:
                    self.buttons[self.selected_button].is_selected = False
                    self.buttons[self.selected_button].render()
                    self.selected_button += 1
                    self.buttons[self.selected_button].is_selected = True
                    self.buttons[self.selected_button].render()

            elif user_input == B.KEY_PRESS:
                return self.selected_button

            # Write the screen updates
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
