from seedsigner.gui.components import SeedSignerCustomIconConstants

from .view import View, Destination, MainMenuView

from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen, settings_screens)
from seedsigner.models.settings import SettingsConstants, SettingsDefinition



class SettingsMenuView(View):
    IO_TEST = "I/O test"
    DONATE = "Donate"

    def __init__(self, visibility: str = SettingsConstants.VISIBILITY__GENERAL, selected_attr: str = None, initial_scroll: int = 0):
        super().__init__()
        self.visibility = visibility
        self.selected_attr = selected_attr

        # Used to preserve the rendering position in the list
        self.initial_scroll = initial_scroll


    def run(self):
        settings_entries = SettingsDefinition.get_settings_entries(
            visibility=self.visibility
        )
        button_data=[e.display_name for e in settings_entries]

        selected_button = 0
        if self.selected_attr:
            for i, entry in enumerate(settings_entries):
                if entry.attr_name == self.selected_attr:
                    selected_button = i
                    break

        if self.visibility == SettingsConstants.VISIBILITY__GENERAL:
            self.title = "Settings"

            # Set up the next nested level of menuing
            button_data.append(("Advanced", None, None, None, SeedSignerCustomIconConstants.SMALL_CHEVRON_RIGHT))
            self.next_destination = Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__ADVANCED})

            button_data.append(self.IO_TEST)
            button_data.append(self.DONATE)

        elif self.visibility == SettingsConstants.VISIBILITY__ADVANCED:
            self.title = "Advanced"

            # So far there are no real Developer options; disabling for now
            # self.button_data.append(("Developer Options", None, None, None, SeedSignerCustomIconConstants.SMALL_CHEVRON_RIGHT))
            # self.next_destination = Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__DEVELOPER})
            self.next_destination = None
        
        elif self.visibility == SettingsConstants.VISIBILITY__DEVELOPER:
            self.title = "Dev Options"
            self.next_destination = None

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=self.title,
            is_button_text_centered=False,
            button_data=button_data,
            selected_button=selected_button,
            scroll_y_initial_offset=self.initial_scroll,
        )

        # Preserve our scroll position in this Screen so we can return
        initial_scroll = self.screen.buttons[0].scroll_y

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            if self.visibility == SettingsConstants.VISIBILITY__GENERAL:
                return Destination(MainMenuView)
            elif self.visibility == SettingsConstants.VISIBILITY__ADVANCED:
                return Destination(SettingsMenuView)
            else:
                return Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__ADVANCED})
        
        elif selected_menu_num == len(settings_entries):
            return self.next_destination

        elif len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.IO_TEST:
            return Destination(IOTestView)

        elif len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.DONATE:
            return Destination(DonateView)

        else:
            return Destination(SettingsEntryUpdateSelectionView, view_args=dict(attr_name=settings_entries[selected_menu_num].attr_name, parent_initial_scroll=initial_scroll))



class SettingsEntryUpdateSelectionView(View):
    """
        Handles changes to all selection-type settings (Multiselect, SELECT_1,
        Enabled/Disabled, etc).
    """
    def __init__(self, attr_name: str, parent_initial_scroll: int = 0, selected_button: int = None):
        super().__init__()
        self.settings_entry = SettingsDefinition.get_settings_entry(attr_name)
        self.selected_button = selected_button
        self.parent_initial_scroll = parent_initial_scroll

        self.button_data = []
        self.checked_buttons = []
        self.initial_value = self.settings.get_value(self.settings_entry.attr_name)
        for i, value in enumerate(self.settings_entry.selection_options):
            if type(value) == tuple:
                value, display_name = value
            else:
                display_name = value

            self.button_data.append(display_name)

            if (type(self.initial_value) == list and value in self.initial_value) or value == self.initial_value:
                self.checked_buttons.append(i)

                if self.selected_button is None:
                    # Highlight the selection (for multiselect highlight the first
                    # selected option).
                    self.selected_button = i
        
        if self.selected_button is None:
            self.selected_button = 0


    def run(self):
        ret_value = self.run_screen(
            settings_screens.SettingsEntryUpdateSelectionScreen,
            display_name=self.settings_entry.display_name,
            help_text=self.settings_entry.help_text,
            button_data=self.button_data,
            selected_button=self.selected_button,
            checked_buttons=self.checked_buttons,
            settings_entry_type=self.settings_entry.type,
        )

        destination = None
        settings_menu_view_destination = Destination(
            SettingsMenuView,
            view_args={
                "visibility": self.settings_entry.visibility,
                "selected_attr": self.settings_entry.attr_name,
                "initial_scroll": self.parent_initial_scroll,
            }
        )

        if ret_value == RET_CODE__BACK_BUTTON:
            return settings_menu_view_destination

        value = self.settings_entry.get_selection_option_value(ret_value)

        if self.settings_entry.type == SettingsConstants.TYPE__FREE_ENTRY:
            updated_value = ret_value
            destination = settings_menu_view_destination

        elif self.settings_entry.type == SettingsConstants.TYPE__MULTISELECT:
            updated_value = list(self.initial_value)
            if ret_value not in self.checked_buttons:
                # This is a new selection to add
                updated_value.append(value)
            else:
                # This is a de-select to remove
                updated_value.remove(value)

        else:
            # All other types are single selects (e.g. Enabled/Disabled, SELECT_1)
            if value == self.initial_value:
                # No change, return to menu
                return settings_menu_view_destination
            else:
                updated_value = value

        self.settings.set_value(
            attr_name=self.settings_entry.attr_name,
            value=updated_value
        )

        if destination:
            return destination

        # All selects stay in place; re-initialize where in the list we left off
        self.selected_button = ret_value

        return Destination(SettingsEntryUpdateSelectionView, view_args=dict(attr_name=self.settings_entry.attr_name, parent_initial_scroll=self.parent_initial_scroll, selected_button=self.selected_button), skip_current_view=True)



"""****************************************************************************
    Misc
****************************************************************************"""
class IOTestView(View):
    def run(self):
        self.run_screen(settings_screens.IOTestScreen)

        return Destination(SettingsMenuView)



class DonateView(View):
    def run(self):
        self.run_screen(settings_screens.DonateScreen)

        return Destination(SettingsMenuView)
