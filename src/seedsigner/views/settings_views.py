from seedsigner.gui.components import FontAwesomeIconConstants

from .view import View, Destination, BackStackView, MainMenuView

from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen, settings_screens)
from seedsigner.models.settings import SettingsConstants, SettingsDefinition



class SettingsMenuView(View):
    def __init__(self, visibility: str = SettingsConstants.VISIBILITY__GENERAL, selected_attr: str = None):
        super().__init__()
        self.visibility = visibility
        self.selected_attr = selected_attr


    def run(self):
        settings_entries = SettingsDefinition.get_settings_entries(
            visibiilty=self.visibility
        )
        button_data=[e.display_name for e in settings_entries]

        selected_button = 0
        if self.selected_attr:
            for i, entry in enumerate(settings_entries):
                if entry.attr_name == self.selected_attr:
                    selected_button = i
                    break

        if self.visibility == SettingsConstants.VISIBILITY__GENERAL:
            title = "Settings"
            button_data.append(("Advanced", FontAwesomeIconConstants.CIRCLE_CHEVRON_RIGHT))
            next = Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__ADVANCED})

        elif self.visibility == SettingsConstants.VISIBILITY__ADVANCED:
            button_data.append(("Developer Options", FontAwesomeIconConstants.CIRCLE_CHEVRON_RIGHT))
            title = "Advanced"
            next = Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__DEVELOPER})
        
        elif self.visibility == SettingsConstants.VISIBILITY__DEVELOPER:
            title = "Dev Options"
            next = None

        screen = ButtonListScreen(
            title=title,
            is_button_text_centered=False,
            button_data=button_data,
            selected_button=selected_button,
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            if self.visibility == SettingsConstants.VISIBILITY__GENERAL:
                return Destination(MainMenuView)
            elif self.visibility == SettingsConstants.VISIBILITY__ADVANCED:
                return Destination(SettingsMenuView)
            else:
                return Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__ADVANCED})
        
        elif selected_menu_num == len(settings_entries):
            return next

        else:
            return Destination(SettingsEntryUpdateView, view_args={"attr_name": settings_entries[selected_menu_num].attr_name})



class SettingsEntryUpdateView(View):
    def __init__(self, attr_name: str):
        super().__init__()
        self.settings_entry = SettingsDefinition.get_settings_entry(attr_name)
        self.selected_button = 0


    def run(self):
        button_data = self.settings_entry.possible_values
        cur_value = self.settings.get_value(self.settings_entry.attr_name)
        checked_buttons = []
        for i, value in enumerate(button_data):
            if (type(cur_value) == list and value in cur_value) or value == cur_value:
                checked_buttons.append(i)

        screen = settings_screens.SettingsEntryUpdateScreen(
            display_name=self.settings_entry.display_name,
            help_text=self.settings_entry.help_text,
            button_data=button_data,
            selected_button=self.selected_button,
            checked_buttons=checked_buttons,
            settings_entry_type=self.settings_entry.type,
        )
        ret_value = screen.display()

        if self.settings_entry.type == SettingsConstants.TYPE__MULTISELECT:
            if ret_value == RET_CODE__BACK_BUTTON:
                return Destination(
                    SettingsMenuView,
                    view_args={
                        "visibility": self.settings_entry.visibility,
                        "selected_attr": self.settings_entry.attr_name
                    }
                )

            if ret_value not in checked_buttons:
                # This is a new selection to add
                cur_value.append(self.settings_entry.possible_values[ret_value])
            else:
                # This is a de-select to remove
                cur_value.remove(self.settings_entry.possible_values[ret_value])
            
            # Save the updated selections
            self.settings.set_value(
                attr_name=self.settings_entry.attr_name,
                value=cur_value
            )
            # Multiselects stay in place; re-initialize where in the list we left off
            # TODO: get Screen.scroll_y to pass in?
            self.selected_button = ret_value
            return self.run()

        elif ret_value == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        else:
            self.settings.set_value(
                attr_name=self.settings_entry.attr_name,
                value=self.settings_entry.possible_values[ret_value]
            )

            return Destination(
                SettingsMenuView,
                view_args={
                    "visibility": self.settings_entry.visibility,
                    "selected_attr": self.settings_entry.attr_name
                }
            )

