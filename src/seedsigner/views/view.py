from dataclasses import dataclass
from typing import Type

from seedsigner.gui.components import FontAwesomeIconConstants
from seedsigner.gui.screens import RET_CODE__POWER_BUTTON, RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.screen import BaseScreen, DireWarningScreen, LargeButtonScreen, PowerOffScreen, PowerOffNotRequiredScreen, ResetScreen, WarningScreen
from seedsigner.models.settings import Settings
from seedsigner.models.threads import BaseThread


class BackStackView:
    """
        Empty class that just signals to the Controller to pop the most recent View off
        the back_stack.
    """
    pass


"""
    Views contain the biz logic to handle discrete tasks, exactly analogous to a Flask
    request/response function or a Django View. Each page/screen displayed to the user
    should be implemented in its own View.

    In a web context, the View would prepare data for the html/css/js presentation
    templates. We have to implement our own presentation layer (implemented as `Screen`
    objects). For the sake of code cleanliness and separation of concerns, the View code
    should not know anything about pixel-level rendering.

    Sequences that require multiple pages/screens should be implemented as a series of
    separate Views. Exceptions can be made for complex interactive sequences, but in
    general, if your View is instantiating multiple Screens, you're probably putting too
    much functionality in that View.

    As with http requests, Views can receive input vars to inform their behavior. Views
    can also prepare the next set of vars to set up the next View that should be
    displayed (akin to Flask's `return redirect(url, param1=x, param2=y))`).

    Navigation guidance:
    "Next" - Continue to next step
    "Done" - End of flow, return to entry point (non-destructive)
    "OK/Close" - Exit current screen (non-destructive)
    "Cancel" - End task and return to entry point (destructive)
"""
class View:
    def __init__(self) -> None:
        # Import here to avoid circular imports
        from seedsigner.controller import Controller
        from seedsigner.gui import Renderer

        self.controller: Controller = Controller.get_instance()
        self.settings = Settings.get_instance()

        # TODO: Pull all rendering-related code out of Views and into gui.screens implementations
        self.renderer = Renderer.get_instance()
        self.canvas_width = self.renderer.canvas_width
        self.canvas_height = self.renderer.canvas_height

        self.screen = None
    

    def run_screen(self, Screen_cls: Type[BaseScreen], **kwargs) -> int | str:
        """
            Instantiates the provided Screen_cls and runs its interactive display.
            Returns the user's input upon completion.
        """
        self.screen = Screen_cls(**kwargs)
        return self.screen.display()


    def run(self, **kwargs) -> 'Destination':
        raise Exception("Must implement in the child class")



@dataclass
class Destination:
    """
        Basic struct to pass back to the Controller to tell it which View the user should
        be presented with next.
    """
    View_cls: Type[View]                # The target View to route to
    view_args: dict = None              # The input args required to instantiate the target View
    skip_current_view: bool = False     # The current View is just forwarding; omit current View from history
    clear_history: bool = False         # Optionally clears the back_stack to prevent "back"


    def __repr__(self):
        if self.View_cls is None:
            out = "None"
        else:
            out = self.View_cls.__name__
        if self.view_args:
            out += f"({self.view_args})"
        else:
            out += "()"
        if self.clear_history:
            out += f" | clear_history: {self.clear_history}"
        return out


    def _instantiate_view(self):
        if not self.view_args:
            # Can't unpack (**) None so we replace with an empty dict
            self.view_args = {}

        # Instantiate the `View_cls` with the `view_args` dict
        self.view = self.View_cls(**self.view_args)
    

    def _run_view(self):
        return self.view.run()


    def run(self):
        self._instantiate_view()
        return self._run_view()


    def __eq__(self, obj):
        """
            Equality test IGNORES the skip_current_view and clear_history options
        """
        return (isinstance(obj, Destination) and 
            obj.View_cls == self.View_cls and
            obj.view_args == self.view_args)
    

    def __ne__(self, obj):
        return not obj == self



#########################################################################################
#
# Root level Views don't have a sub-module home so they live at the top level here.
#
#########################################################################################
class MainMenuView(View):
    SCAN = ("Scan", FontAwesomeIconConstants.QRCODE)
    SEEDS = ("Seeds", FontAwesomeIconConstants.KEY)
    TOOLS = ("Tools", FontAwesomeIconConstants.SCREWDRIVER_WRENCH)
    SETTINGS = ("Settings", FontAwesomeIconConstants.GEAR)

    def run(self):
        button_data = [self.SCAN, self.SEEDS, self.TOOLS, self.SETTINGS]
        selected_menu_num = self.run_screen(
            LargeButtonScreen,
            title="Home",
            title_font_size=26,
            button_data=button_data,
            show_back_button=False,
            show_power_button=True,
        )

        if selected_menu_num == RET_CODE__POWER_BUTTON:
            return Destination(PowerOptionsView)

        if button_data[selected_menu_num] == self.SCAN:
            from .scan_views import ScanView
            return Destination(ScanView)
        
        elif button_data[selected_menu_num] == self.SEEDS:
            from .seed_views import SeedsMenuView
            return Destination(SeedsMenuView)

        elif button_data[selected_menu_num] == self.TOOLS:
            from .tools_views import ToolsMenuView
            return Destination(ToolsMenuView)

        elif button_data[selected_menu_num] == self.SETTINGS:
            from .settings_views import SettingsMenuView
            return Destination(SettingsMenuView)



class PowerOptionsView(View):
    RESET = ("Restart", FontAwesomeIconConstants.ROTATE_RIGHT)
    POWER_OFF = ("Power Off", FontAwesomeIconConstants.POWER_OFF)

    def run(self):
        button_data = [self.RESET, self.POWER_OFF]
        selected_menu_num = self.run_screen(
            LargeButtonScreen,
            title="Reset / Power",
            show_back_button=True,
            button_data=button_data
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        elif button_data[selected_menu_num] == self.RESET:
            return Destination(RestartView)
        
        elif button_data[selected_menu_num] == self.POWER_OFF:
            return Destination(PowerOffView)



class RestartView(View):
    def run(self):
        thread = RestartView.DoResetThread()
        thread.start()
        self.run_screen(ResetScreen)


    class DoResetThread(BaseThread):
        def run(self):
            import time
            from subprocess import call

            # Give the screen just enough time to display the reset message before
            # exiting.
            time.sleep(0.25)

            # Kill the SeedSigner process; Running the process again.
            # `.*` is a wildcard to detect either `python`` or `python3`.
            if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
                call("kill $(pidof python*) & python /opt/src/main.py", shell=True)
            else:
                call("kill $(ps aux | grep '[p]ython.*main.py' | awk '{print $2}')", shell=True)



class PowerOffView(View):
    def run(self):
        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
            self.run_screen(PowerOffNotRequiredScreen)
            return Destination(BackStackView)
        else:
            thread = PowerOffView.PowerOffThread()
            thread.start()
            self.run_screen(PowerOffScreen)


    class PowerOffThread(BaseThread):
        def run(self):
            import time
            from subprocess import call
            while self.keep_running:
                time.sleep(5)
                call("sudo shutdown --poweroff now", shell=True)



class NotYetImplementedView(View):
    """
        Temporary View to use during dev.
    """
    def run(self):
        self.run_screen(
            WarningScreen,
            title="Work In Progress",
            status_headline="Not Yet Implemented",
            text="This is still on our to-do list!",
            button_data=["Back to Main Menu"],
        )

        return Destination(MainMenuView)



@dataclass
class ErrorView(View):
    """
    """
    title: str = "Error"
    status_headline: str = None
    text: str = None
    button_text: str = None
    next_destination: Destination = Destination(MainMenuView, clear_history=True)

    def run(self):
        WarningScreen(
            title=self.title,
            status_headline=self.status_headline,
            text=self.text,
            button_data=[self.button_text],
        ).display()

        return self.next_destination



class UnhandledExceptionView(View):
    def __init__(self, error: list[str]):
        self.error = error


    def run(self):
        self.run_screen(
            DireWarningScreen,
            title="System Error",
            status_headline=self.error[0],
            text=self.error[1] + "\n" + self.error[2],
            button_data=["OK"],
            show_back_button=False,
            allow_text_overflow=True,  # Fit what we can, let the rest go off the edges
        )
        
        return Destination(MainMenuView, clear_history=True)
