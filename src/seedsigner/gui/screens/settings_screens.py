import time

from dataclasses import dataclass
from PIL.ImageOps import autocontrast
from typing import List
from seedsigner.gui.components import Button, CheckboxButton, CheckedSelectionButton, FontAwesomeIconConstants, Fonts, GUIConstants, Icon, IconButton, IconTextLine, TextArea
from seedsigner.gui.screens.scan_screens import ScanScreen

from seedsigner.gui.screens.screen import BaseScreen, BaseTopNavScreen, ButtonListScreen
from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.hardware.camera import Camera
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
class IOTestScreen(BaseTopNavScreen):
    def __post_init__(self):
        self.title = "I/O Test"
        self.show_back_button = False
        self.resolution = (96, 96)
        self.framerate = 10
        self.instructions_text = None
        super().__post_init__()

        # D-pad pictogram
        input_button_width = GUIConstants.BUTTON_HEIGHT + 2
        input_button_height = input_button_width + 2
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

        # Hardware keys UI
        font = Fonts.get_font(GUIConstants.BUTTON_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)
        (left, top, text_width, bottom) = font.getbbox(text="Clear", anchor="ls")
        icon = Icon(
            icon_name=FontAwesomeIconConstants.CAMERA, 
            icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
        )
        key_button_width = text_width + 2*GUIConstants.COMPONENT_PADDING + GUIConstants.EDGE_PADDING
        key_button_height = icon.height + int(1.5*GUIConstants.COMPONENT_PADDING)
        key2_y = int(self.canvas_height/2) - int(key_button_height/2)

        self.key2_button = Button(
            text="Clear",   # Initialize with text to set vertical centering
            width=key_button_width,
            height=key_button_height,
            screen_x=self.canvas_width - key_button_width + GUIConstants.EDGE_PADDING,
            screen_y=key2_y,
            outline_color=GUIConstants.ACCENT_COLOR,
        )
        self.key2_button.text = " "  # but default state is empty
        self.components.append(self.key2_button)

        self.key1_button = IconButton(
            icon_name=FontAwesomeIconConstants.CAMERA,
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
        msg_height = GUIConstants.ICON_LARGE_BUTTON_SIZE + 2*GUIConstants.COMPONENT_PADDING
        camera_message = TextArea(
            text="Capturing image...",
            font_size=GUIConstants.TOP_NAV_TITLE_FONT_SIZE,
            is_text_centered=True,
            height=msg_height,
            screen_y=int((self.canvas_height - msg_height)/ 2),
        )
        while True:
            input = self.hw_inputs.wait_for(keys=HardwareButtonsConstants.ALL_KEYS, check_release=False)

            if input == HardwareButtonsConstants.KEY1:
                cur_selected_button = self.key1_button

                with self.renderer.lock:
                    cur_selected_button.is_selected = True
                    cur_selected_button.render()
                    camera_message.render()
                    # Render edges around message box
                    self.image_draw.rectangle(
                        (
                            -1, int((self.canvas_height - msg_height)/ 2) - 1,
                            self.canvas_width + 1, int((self.canvas_height + msg_height)/ 2) + 1
                        ),
                        outline=GUIConstants.ACCENT_COLOR,
                        width=1,
                    )
                    self.renderer.show_image()

                # Snap a pic, render it as the background, re-render all onscreen elements
                camera = Camera.get_instance()
                try:
                    camera.start_single_frame_mode(resolution=(self.canvas_width, self.canvas_height))

                    # Reset the button state
                    with self.renderer.lock:
                        cur_selected_button.is_selected = False
                        cur_selected_button.render()
                        self.renderer.show_image()

                    time.sleep(0.25)
                    background_frame = camera.capture_frame()
                    display_version = autocontrast(
                        background_frame,
                        cutoff=2
                    )
                    with self.renderer.lock:
                        self.canvas.paste(display_version, (0, self.top_nav.height))
                        self.key2_button.text = "Clear"
                        for component in self.components:
                            component.render()
                        self.renderer.show_image()
                finally:
                    camera.stop_single_frame_mode()

                continue

            elif input == HardwareButtonsConstants.KEY2:
                cur_selected_button = self.key2_button

                # Clear the background
                with self.renderer.lock:
                    cur_selected_button.is_selected = True
                    self._render()
                    self.renderer.show_image()

                    # And then re-render Key2 in its initial state
                    self.key2_button.text = " "
                    cur_selected_button.is_selected = False
                    cur_selected_button.render()
                    self.renderer.show_image()
                
                continue

            elif input == HardwareButtonsConstants.KEY3:
                # Exit
                cur_selected_button = self.key3_button
                cur_selected_button.is_selected = True
                with self.renderer.lock:
                    cur_selected_button.render()
                    self.renderer.show_image()
                    return
            
            elif input == HardwareButtonsConstants.KEY_PRESS:
                cur_selected_button = self.joystick_click_button

            elif input == HardwareButtonsConstants.KEY_UP:
                cur_selected_button = self.joystick_up_button

            elif input == HardwareButtonsConstants.KEY_DOWN:
                cur_selected_button = self.joystick_down_button

            elif input == HardwareButtonsConstants.KEY_LEFT:
                cur_selected_button = self.joystick_left_button

            elif input == HardwareButtonsConstants.KEY_RIGHT:
                cur_selected_button = self.joystick_right_button

            with self.renderer.lock:
                cur_selected_button.is_selected = True
                cur_selected_button.render()
                self.renderer.show_image()

            with self.renderer.lock:
                cur_selected_button.is_selected = False
                cur_selected_button.render()
                self.renderer.show_image()

            time.sleep(0.1)



@dataclass
class DonateScreen(BaseTopNavScreen):
    def __post_init__(self):
        self.title = "Donate"
        super().__post_init__()

        self.components.append(TextArea(
            text="SeedSigner is 100% free & open source, funded solely by the Bitcoin community.\n\nDonate onchain or LN at:",
            screen_y=self.top_nav.height + 3*GUIConstants.COMPONENT_PADDING,
        ))

        self.components.append(TextArea(
            text="seedsigner.com",
            font_size=GUIConstants.TOP_NAV_TITLE_FONT_SIZE + 8,
            font_color=GUIConstants.ACCENT_COLOR,
            supersampling_factor=1,
            screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING
        ))
