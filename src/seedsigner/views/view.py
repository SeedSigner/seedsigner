import time

from seedsigner.gui.components import Fonts
from seedsigner.gui.screens import ButtonListScreen, TextTopNavScreen


"""
    Views contain the biz logic to handle discrete tasks, exactly analogous to a Flask
    request/response function or a Django View. Each page/screen displayed to the user
    should be implemented in its own View.

    In a web context, the View would prepare data for the html/css/js presentation
    templates. We have to implement our own presentation layer (implemented as `Screen`
    objects). For the sake of code cleanliness and separation of concerns, the View code
    should not know anything about pixel-level rendering.

    Sequences that require multiple pages/screens can be should be implemented as a
    series of separate Views. Exceptions can be made for complex interactive sequences,
    but in general, if your View is instantiating multiple Screens, you're probably
    putting too much functionality in that View.

    As with http requests, Views can receive input vars to inform their behavior. Views
    can also prepare the next set of vars to set up the next View that should be
    displayed (akin to `return redirect(url, param1=x, param2=y))`).

"""
class View:
    # TODO: Obviated by seedsigner.gui.components.TopNav
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


    def run(self, **kwargs):
        raise Exception("Must implement in the child class")




    ###
    ### Reusable components
    ###
    # TODO: Obviated by seedsigner.gui.components.TopNav
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



#########################################################################################
#
# Root level Views don't have a sub-module home so they live at the top level here.
#
#########################################################################################
class MainMenuView(View):
    def run(self):
        from .menu_view import SeedToolsMenuView
        from seedsigner.gui.screens import LargeButtonScreen
        selected_menu_num = LargeButtonScreen(
            title="Home",
            title_font_size=26,
            button_data=[("Scan", "scan"),
                         ("Seeds", "seeds"),
                         ("Tools", "tools"),
                         ("Settings", "settings")],
            show_back_button=False,
        ).display()

        if selected_menu_num == 0:
            return SeedToolsMenuView
        elif selected_menu_num == 1:
            return None
            # ret_val = Path.SIGN_TRANSACTION
        elif selected_menu_num == 2:
            return None
            # return self.display_settings_menu
        elif selected_menu_num == 3:
            return PowerOffView



class PowerOffView(View):
    def run(self):
        from subprocess import call
        TextTopNavScreen(
            title="Powering Down",
            text="Please wait about 30 seconds before disconnecting power.",
            text_font_size=22
        ).display()

        # call("sudo shutdown --poweroff now", shell=True)
        time.sleep(10)

