import logging
from seedsigner.gui.components import SeedSignerIconConstants
from seedsigner.hardware.microsd import MicroSD

from .view import View, Destination, MainMenuView

from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen, settings_screens)
from seedsigner.models.settings import Settings, SettingsConstants, SettingsDefinition

logger = logging.getLogger(__name__)



class SettingsMenuView(View):
    IO_TEST = "I/O test"
    NFC_TEST = "Test NFC Scan"
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
            title = "Settings"

            # Set up the next nested level of menuing
            button_data.append(("Advanced", None, None, None, SeedSignerIconConstants.CHEVRON_RIGHT))
            next_destination = Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__ADVANCED})

            button_data.append(self.IO_TEST)
            button_data.append(self.NFC_TEST)
            button_data.append(self.DONATE)

        elif self.visibility == SettingsConstants.VISIBILITY__ADVANCED:
            title = "Advanced"

            # So far there are no real Developer options; disabling for now
            # button_data.append(("Developer Options", None, None, None, SeedSignerIconConstants.CHEVRON_RIGHT))
            # next_destination = Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__DEVELOPER})
            next_destination = None
        
        elif self.visibility == SettingsConstants.VISIBILITY__DEVELOPER:
            title = "Dev Options"
            next_destination = None

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=title,
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
            return next_destination

        elif len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.IO_TEST:
            return Destination(IOTestView)
        
        elif button_data[selected_menu_num] == self.NFC_TEST:
            return Destination(NFCTestView)

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


    def run(self):
        initial_value = self.settings.get_value(self.settings_entry.attr_name)
        button_data = []
        checked_buttons = []
        for i, value in enumerate(self.settings_entry.selection_options):
            if type(value) == tuple:
                value, display_name = value
            else:
                display_name = value

            button_data.append(display_name)

            if (type(initial_value) == list and value in initial_value) or value == initial_value:
                checked_buttons.append(i)

                if self.selected_button is None:
                    # Highlight the selection (for multiselect highlight the first
                    # selected option).
                    self.selected_button = i
        
        if self.selected_button is None:
            self.selected_button = 0
            
        ret_value = self.run_screen(
            settings_screens.SettingsEntryUpdateSelectionScreen,
            display_name=self.settings_entry.display_name,
            help_text=self.settings_entry.help_text,
            button_data=button_data,
            selected_button=self.selected_button,
            checked_buttons=checked_buttons,
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
            updated_value = list(initial_value)
            if ret_value not in checked_buttons:
                # This is a new selection to add
                updated_value.append(value)
            else:
                # This is a de-select to remove
                updated_value.remove(value)

        else:
            # All other types are single selects (e.g. Enabled/Disabled, SELECT_1)
            if value == initial_value:
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



class SettingsIngestSettingsQRView(View):
    def __init__(self, data: str):
        super().__init__()

        # May raise an Exception which will bubble up to the Controller to display to the
        # user.
        self.config_name, settings_update_dict = Settings.parse_settingsqr(data)
            
        self.settings.update(settings_update_dict)

        if MicroSD.get_instance().is_inserted and self.settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS) == SettingsConstants.OPTION__ENABLED:
            self.status_message = "Persistent Settings enabled. Settings saved to SD card."
        else:
            self.status_message = "Settings updated in temporary memory"


    def run(self):
        from seedsigner.gui.screens.settings_screens import SettingsQRConfirmationScreen
        self.run_screen(
            SettingsQRConfirmationScreen,
            config_name=self.config_name,
            status_message=self.status_message,
        )

        # Only one exit point
        return Destination(MainMenuView)



"""****************************************************************************
    Misc
****************************************************************************"""
class IOTestView(View):
    def run(self):
        self.run_screen(settings_screens.IOTestScreen)

        return Destination(SettingsMenuView)

class NFCTestView(View):
    def run(self):
        
        from seedsigner.gui.screens.screen import LoadingScreenThread
        import os
        import time
        from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen, WarningScreen, DireWarningScreen, seed_screens, LargeIconStatusScreen)

        self.loading_screen = LoadingScreenThread(text="Scanning for NFC Tag")
        self.loading_screen.start()

        os.system("ifdnfc-activate no") # Need to disable IFD-NFC to be able to scan using libnfc-bindings...

        time.sleep(0.2) #Just give the loading screen a chance to load before moving on...

        import nfc
        import binascii

        context = nfc.init()
        nfcdevice = nfc.open(context)
        if nfcdevice is None:
            self.loading_screen.stop()
            print('ERROR: Unable to open NFC device.')
            self.run_screen(
                WarningScreen,
                title="NFC Failure",
                status_headline=None,
                text=f"ERROR: Unable to open NFC device. \n(May not be connected)",
                show_back_button=True,
            )
            return Destination(BackStackView)
            
        if nfc.initiator_init(nfcdevice) < 0:
            self.loading_screen.stop()
            print('ERROR: Unable to init NFC device.')
            self.run_screen(
                WarningScreen,
                title="NFC Failure",
                status_headline=None,
                text=f"ERROR: Unable to init NFC device.",
                show_back_button=True,
            )
            return Destination(BackStackView)

        print('NFC reader: %s opened' % nfc.device_get_name(nfcdevice))

        nfcmodulation = nfc.modulation()
        nfcmodulation.nmt = nfc.NMT_ISO14443A
        nfcmodulation.nbr = nfc.NBR_847 #Test at the highest baud rate for the best simulation of Smartcard operation

        nt = nfc.target()

        # Scan for 15 seconds
        ret = nfc.initiator_poll_target(nfcdevice, nfcmodulation, 1, 100, 1, nt)

        self.loading_screen.stop()

        if ret and nt.nti.nai.szUidLen:

            print('The following (NFC) ISO14443A tag was found:')
            print('    ATQA (SENS_RES): ', end='')
            nfc.print_hex(nt.nti.nai.abtAtqa, 2)
            id = 1
            if nt.nti.nai.abtUid[0] == 8:
                id = 3
            print('       UID (NFCID%d): ' % id , end='')
            nfc.print_hex(nt.nti.nai.abtUid, nt.nti.nai.szUidLen)
            foundtext="UID:\n" + binascii.hexlify(nt.nti.nai.abtUid).decode()[:14]

            print('      SAK (SEL_RES): ', end='')
            print(nt.nti.nai.btSak)
            if nt.nti.nai.szAtsLen:
                print('          ATS (ATR): ', end='')
                nfc.print_hex(nt.nti.nai.abtAts, nt.nti.nai.szAtsLen)
                foundtext = foundtext + "\nATR:\n" + binascii.hexlify(nt.nti.nai.abtAts).decode()[:28]

            self.run_screen(
                LargeIconStatusScreen,
                title="Found NFC Tag",
                status_headline=None,
                text=foundtext,
                show_back_button=False,
            )
        elif ret:
            print('Warning: IFD-NFC Conflict.')
            self.run_screen(
                WarningScreen,
                title="NFC Conflict",
                status_headline=None,
                text=f"Can't scan when IFD-NFC Active",
                show_back_button=True,
            )
        else:
            print('Warning: No NFC Tag Detected.')
            self.run_screen(
                WarningScreen,
                title="Warning",
                status_headline=None,
                text=f"Warning: No NFC Tag Detected.",
                show_back_button=True,
            )

        nfc.close(nfcdevice)
        nfc.exit(context)

        scinterface = self.settings.get_value(SettingsConstants.SETTING__SMARTCARD_INTERFACES)

        if "pn532" in scinterface:
            os.system("ifdnfc-activate yes") # Need to re-enable IFD-NFC if required...
        
        return Destination(MainMenuView)


class DonateView(View):
    def run(self):
        self.run_screen(settings_screens.DonateScreen)

        return Destination(SettingsMenuView)
