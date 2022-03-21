import time

from dataclasses import dataclass
from typing import List
from seedsigner.gui.components import Button, CheckboxButton, CheckedSelectionButton, FontAwesomeIconConstants, GUIConstants, IconButton, TextArea
from seedsigner.gui.screens.scan_screens import ScanScreen

from seedsigner.gui.screens.screen import ButtonListScreen, TextTopNavScreen
from seedsigner.hardware.buttons import HardwareButtons, HardwareButtonsConstants
from seedsigner.models.decode_qr import DecodeQRStatus
from seedsigner.models.settings import SettingsConstants


@dataclass
class SettingsEntryUpdateSelectionScreen(ButtonListScreen):
    display_name: str = None
    help_text: str = None
    checked_buttons: List[int] = None
    settings_entry_type: str = SettingsConstants.TYPE__ENABLED_DISABLED
    selected_button: int = 0

    def __post_init__(self):
        self.title = "Settings"
        self.is_bottom_list = True
        self.use_checked_selection_buttons = True
        if self.settings_entry_type == SettingsConstants.TYPE__MULTISELECT:
            self.Button_cls = CheckboxButton
        else:
            self.Button_cls = CheckedSelectionButton
        super().__post_init__()

        self.components.append(TextArea(
            text=self.display_name,
            font_size=GUIConstants.BODY_FONT_MAX_SIZE,
            is_text_centered=True,
            auto_line_break=False,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        ))

        if self.help_text:
            prev_component_bottom = self.components[-1].screen_y + self.components[-1].height
            self.components.append(TextArea(
                text=self.help_text,
                font_color=GUIConstants.LABEL_FONT_COLOR,
                is_text_centered=True,
                screen_y=prev_component_bottom + GUIConstants.COMPONENT_PADDING,
            ))



@dataclass
class IOTestScreen(ScanScreen):
    def __post_init__(self):
        super().__post_init__()

        # Pull the ScanScreen's live preview thread out before it can get started
        self.preview_thread = self.threads.pop()

        # D-pad pictogram
        input_button_width = GUIConstants.BUTTON_HEIGHT
        input_button_height = input_button_width

        dpad_center_x = GUIConstants.EDGE_PADDING + input_button_width + GUIConstants.COMPONENT_PADDING
        dpad_center_y = int((self.canvas_height - input_button_height)/2)

        self.joystick_click_button = IconButton(
            icon_name=FontAwesomeIconConstants.CIRCLE,
            icon_size=GUIConstants.ICON_INLINE_FONT_SIZE - 6,
            width=input_button_width,
            height=input_button_height,
            screen_x=dpad_center_x,
            screen_y=dpad_center_y,
            outline_color=GUIConstants.ACCENT_COLOR,
        )
        self.components.append(self.joystick_click_button)

        self.joystick_up_button = IconButton(
            icon_name=FontAwesomeIconConstants.ANGLE_UP,
            icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
            is_text_centered=True,
            width=input_button_width,
            height=input_button_height,
            screen_x=dpad_center_x,
            screen_y=dpad_center_y - input_button_height - GUIConstants.COMPONENT_PADDING,
            outline_color=GUIConstants.ACCENT_COLOR,
        )
        self.components.append(self.joystick_up_button)

        self.joystick_down_button = IconButton(
            icon_name=FontAwesomeIconConstants.ANGLE_DOWN,
            icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
            width=input_button_width,
            height=input_button_height,
            screen_x=dpad_center_x,
            screen_y=dpad_center_y + input_button_height + GUIConstants.COMPONENT_PADDING,
            outline_color=GUIConstants.ACCENT_COLOR,
        )
        self.components.append(self.joystick_down_button)

        self.joystick_left_button = IconButton(
            text=FontAwesomeIconConstants.ANGLE_LEFT,
            font_name=GUIConstants.ICON_FONT_NAME__FONT_AWESOME,
            font_size=GUIConstants.ICON_INLINE_FONT_SIZE,
            width=input_button_width,
            height=input_button_height,
            screen_x=dpad_center_x - input_button_width - GUIConstants.COMPONENT_PADDING,
            screen_y=dpad_center_y,
            outline_color=GUIConstants.ACCENT_COLOR,
        )
        self.components.append(self.joystick_left_button)

        self.joystick_right_button = IconButton(
            icon_name=FontAwesomeIconConstants.ANGLE_RIGHT,
            icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
            width=input_button_width,
            height=input_button_height,
            screen_x=dpad_center_x + input_button_width + GUIConstants.COMPONENT_PADDING,
            screen_y=dpad_center_y,
            outline_color=GUIConstants.ACCENT_COLOR,
        )
        self.components.append(self.joystick_right_button)

        key_button_width = int(1.75*GUIConstants.BUTTON_HEIGHT)
        key_button_height = int(0.85*GUIConstants.BUTTON_HEIGHT)
        key2_y = int(self.canvas_height/2) - int(key_button_height/2)

        self.key2_button = Button(
            text=" ",
            width=key_button_width,
            height=key_button_height,
            screen_x=self.canvas_width - key_button_width + GUIConstants.EDGE_PADDING,
            screen_y=key2_y,
            outline_color=GUIConstants.ACCENT_COLOR,
        )
        self.components.append(self.key2_button)

        self.key1_button = Button(
            text=" ",
            width=key_button_width,
            height=key_button_height,
            screen_x=self.canvas_width - key_button_width + GUIConstants.EDGE_PADDING,
            screen_y=key2_y - 3*GUIConstants.COMPONENT_PADDING - key_button_height,
            outline_color=GUIConstants.ACCENT_COLOR,
        )
        self.components.append(self.key1_button)

        self.key3_button = Button(
            text="Exit",
            width=key_button_width,
            height=key_button_height,
            screen_x=self.canvas_width - key_button_width + GUIConstants.EDGE_PADDING,
            screen_y=key2_y + 3*GUIConstants.COMPONENT_PADDING + key_button_height,
            outline_color=GUIConstants.ACCENT_COLOR,
        )
        self.components.append(self.key3_button)


    def _run(self):
        cur_selected_button = self.key1_button
        while True:
            input = self.hw_inputs.wait_for(keys=HardwareButtonsConstants.ALL_KEYS, check_release=False)

            if input == HardwareButtonsConstants.KEY_PRESS:
                cur_selected_button = self.joystick_click_button

            elif input == HardwareButtonsConstants.KEY_UP:
                cur_selected_button = self.joystick_up_button

            elif input == HardwareButtonsConstants.KEY_DOWN:
                cur_selected_button = self.joystick_down_button

            elif input == HardwareButtonsConstants.KEY_LEFT:
                cur_selected_button = self.joystick_left_button

            elif input == HardwareButtonsConstants.KEY_RIGHT:
                cur_selected_button = self.joystick_right_button

            elif input == HardwareButtonsConstants.KEY1:
                cur_selected_button = self.key1_button

            elif input == HardwareButtonsConstants.KEY2:
                cur_selected_button = self.key2_button

            elif input == HardwareButtonsConstants.KEY3:
                # Exit
                self.camera.stop_video_stream_mode()
                cur_selected_button = self.key3_button
                cur_selected_button.is_selected = True
                with self.renderer.lock:
                    cur_selected_button.render()
                    self.renderer.show_image()
                    return

            cur_selected_button.is_selected = True

            time.sleep(0.1)
