from dataclasses import dataclass, field
from typing import Type

from seedsigner.gui.components import FontAwesomeIconConstants, SeedSignerIconConstants
from seedsigner.gui.screens import RET_CODE__POWER_BUTTON, RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.screen import BaseScreen, DireWarningScreen, LargeButtonScreen, PowerOffScreen, PowerOffNotRequiredScreen, ResetScreen, WarningScreen
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.settings_definition import SettingsDefinition
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
    def _initialize(self):
        """
        Whether the View is a regular class initialized by __init__() or a dataclass
        initialized by __post_init__(), this method will be called to set up the View's
        instance variables.
        """
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

        self._redirect: 'Destination' = None


    def __init__(self):
        self._initialize()


    def __post_init__(self):
        self._initialize()


    @property
    def has_redirect(self) -> bool:
        if not hasattr(self, '_redirect'):
            # Easy for a View to forget to call super().__init__()
            raise Exception(f"{self.__class__.__name__} did not call super().__init__()")
        return self._redirect is not None


    def set_redirect(self, destination: 'Destination'):
        """
        Enables early `__init__()` / `__post_init__()` logic to redirect away from the
        current View.

        Set a redirect Destination and then immediately `return` to exit `__init__()` or
        `__post_init__()`. When the `Destination.run()` is called, it will see the redirect
        and immediately return that new Destination to the Controller without running
        the View's `run()`.
        """
        # Always insure skip_current_view is set for a redirect
        destination.skip_current_view = True
        self._redirect = destination


    def get_redirect(self) -> 'Destination':
        return self._redirect


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
        if self.view.has_redirect:
            return self.view.get_redirect()
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
    SCAN = ("Scan", SeedSignerIconConstants.SCAN)
    SEEDS = ("Seeds", SeedSignerIconConstants.SEEDS)
    TOOLS = ("Tools", SeedSignerIconConstants.TOOLS)
    SETTINGS = ("Settings", SeedSignerIconConstants.SETTINGS)


    def run(self):
        from seedsigner.gui.screens.screen import MainMenuScreen
        button_data = [self.SCAN, self.SEEDS, self.TOOLS, self.SETTINGS]
        selected_menu_num = self.run_screen(
            MainMenuScreen,
            title="Home",
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__POWER_BUTTON:
            return Destination(PowerOptionsView)

        if button_data[selected_menu_num] == self.SCAN:
            from seedsigner.views.scan_views import ScanView
            return Destination(ScanView)
        
        elif button_data[selected_menu_num] == self.SEEDS:
            from seedsigner.views.seed_views import SeedsMenuView
            return Destination(SeedsMenuView)

        elif button_data[selected_menu_num] == self.TOOLS:
            from seedsigner.views.tools_views import ToolsMenuView
            return Destination(ToolsMenuView)

        elif button_data[selected_menu_num] == self.SETTINGS:
            from seedsigner.views.settings_views import SettingsMenuView
            return Destination(SettingsMenuView)



class PowerOptionsView(View):
    RESET = ("Restart", SeedSignerIconConstants.RESTART)
    POWER_OFF = ("Power Off", SeedSignerIconConstants.POWER)

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



@dataclass
class NotYetImplementedView(View):
    text: str = "This is still on our to-do list!"
    """
        Temporary View to use during dev.
    """
    def run(self):
        self.run_screen(
            WarningScreen,
            title="Work In Progress",
            status_headline="Not Yet Implemented",
            text=self.text,
            button_data=["Back to Main Menu"],
        )

        return Destination(MainMenuView)



@dataclass
class ErrorView(View):
    title: str = "Error"
    show_back_button: bool = True
    status_headline: str = None
    text: str = None
    button_text: str = None
    next_destination: Destination = field(default_factory=lambda: Destination(MainMenuView, clear_history=True))


    def run(self):
        self.run_screen(
            WarningScreen,
            title=self.title,
            status_headline=self.status_headline,
            text=self.text,
            button_data=[self.button_text],
            show_back_button=self.show_back_button,
        )

        return self.next_destination



@dataclass
class NetworkMismatchErrorView(ErrorView):
    title: str = "Network Mismatch"
    show_back_button: bool = False
    button_text: str = "Change Setting"
    next_destination: Destination = None


    def __post_init__(self):
        super().__post_init__()
        if not self.text:
            self.text = f"Current network setting ({self.settings.get_value_display_name(SettingsConstants.SETTING__NETWORK)}) doesn't match current action."

        if not self.next_destination:
            from seedsigner.views.settings_views import SettingsEntryUpdateSelectionView
            self.next_destination = Destination(SettingsEntryUpdateSelectionView, view_args=dict(attr_name=SettingsConstants.SETTING__NETWORK), clear_history=True)



@dataclass
class UnhandledExceptionView(View):
    error: list[str]


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



@dataclass
class OptionDisabledView(View):
    UPDATE_SETTING = "Update Setting"
    DONE = "Done"
    settings_attr: str

    def __post_init__(self):
        super().__post_init__()
        self.settings_entry = SettingsDefinition.get_settings_entry(self.settings_attr)
        self.error_msg = f"\"{self.settings_entry.display_name}\" is currently disabled in Settings."


    def run(self):
        button_data = [self.UPDATE_SETTING, self.DONE]
        selected_menu_num = self.run_screen(
            WarningScreen,
            title="Option Disabled",
            status_headline=None,
            text=self.error_msg,
            button_data=button_data,
            show_back_button=False,
            allow_text_overflow=True,  # Fit what we can, let the rest go off the edges
        )

        if button_data[selected_menu_num] == self.UPDATE_SETTING:
            from seedsigner.views.settings_views import SettingsEntryUpdateSelectionView
            return Destination(SettingsEntryUpdateSelectionView, view_args=dict(attr_name=self.settings_attr), clear_history=True)
        else:
            return Destination(MainMenuView, clear_history=True)



class RemoveMicroSDWarningView(View):
    """
        Warning to remove the microsd
    """
    def __init__(self, next_view: View):
        super().__init__()
        self.next_view = next_view

    def run(self):
        self.run_screen(
            WarningScreen,
            title="Security Tip",
            status_icon_name=FontAwesomeIconConstants.SDCARD,
            status_headline="",
            text="For maximum security,\nremove the MicroSD card\nbefore continuing.",
            show_back_button=False,
            button_data=["Continue"],
        )

        return Destination(self.next_view, clear_history=True)
