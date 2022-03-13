import time

from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageColor
from typing import Any, List, Tuple
from seedsigner.gui.renderer import Renderer

from seedsigner.models.threads import BaseThread
from seedsigner.models.encode_qr import EncodeQR
from seedsigner.models.settings import SettingsConstants

from ..components import (GUIConstants, BaseComponent, Button, Icon, LargeIconButton, SeedSignerCustomIconConstants, TopNav,
    TextArea, load_image)

from seedsigner.hardware.buttons import HardwareButtonsConstants, HardwareButtons


# Must be huge numbers to avoid conflicting with the selected_button returned by the
#   screens with buttons.
RET_CODE__BACK_BUTTON = 1000
RET_CODE__POWER_BUTTON = 1001



@dataclass
class BaseScreen(BaseComponent):
    def __post_init__(self):
        super().__post_init__()
        
        self.hw_inputs = HardwareButtons.get_instance()

        # Implementation classes can add their own BaseThread to run in parallel with the
        # main execution thread.
        self.threads: List[BaseThread] = []

        # Implementation classes can add additional BaseComponent-derived objects to the
        # list. They'll be called to `render()` themselves in BaseScreen._render().
        self.components: List[BaseComponent] = []

        # Implementation classes can add PIL.Image objs here. Format is a tuple of the
        # Image and its (x,y) paste coords.
        self.paste_images: List[Tuple] = []

        # Tracks position on scrollable pages, determines which elements are visible.
        self.scroll_y = 0


    def display(self) -> Any:
        try:
            with self.renderer.lock:
                self._render()
                self.renderer.show_image()

            for t in self.threads:
                t.start()

            return self._run()
        except Exception as e:
            print(e)
            print("------")
            repr(e)
            raise e
        finally:
            for t in self.threads:
                t.stop()


    def clear_screen(self):
        # Clear the whole canvas
        self.image_draw.rectangle(
            (0, 0, self.canvas_width, self.canvas_height),
            fill=0,
        )


    def _render(self):
        self.clear_screen()

        # TODO: Check self.scroll_y and only render visible elements
        for component in self.components:
            component.render()

        for img, coords in self.paste_images:
            self.canvas.paste(img, coords)


    def _run(self):
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



class LoadingScreenThread(BaseThread):
    def __init__(self, text: str = None):
        super().__init__()
        self.text =text


    def run(self):
        renderer: Renderer = Renderer.get_instance()

        center_image = load_image("btc_logo_60x60.png")
        orbit_gap = 2*GUIConstants.COMPONENT_PADDING
        bounding_box = (
            int((renderer.canvas_width - center_image.width)/2 - orbit_gap),
            int((renderer.canvas_height - center_image.height)/2 - orbit_gap),
            int((renderer.canvas_width + center_image.width)/2 + orbit_gap),
            int((renderer.canvas_height + center_image.height)/2 + orbit_gap),
        )
        position = 0
        arc_sweep = 45
        arc_color = "#ff9416"
        arc_trailing_color = "#80490b"

        # Need to flush the screen
        with renderer.lock:
            renderer.draw.rectangle((0, 0, renderer.canvas_width, renderer.canvas_height), fill=GUIConstants.BACKGROUND_COLOR)
            renderer.canvas.paste(center_image, (bounding_box[0] + orbit_gap, bounding_box[1] + orbit_gap))

            if self.text:
                TextArea(
                    text=self.text,
                    font_size=GUIConstants.TOP_NAV_TITLE_FONT_SIZE,
                    screen_y=int((renderer.canvas_height - bounding_box[3])/2),
                ).render()

        while self.keep_running:
            with renderer.lock:
                # Render leading arc
                renderer.draw.arc(
                    bounding_box,
                    start=position,
                    end=position + arc_sweep,
                    fill=arc_color,
                    width=GUIConstants.COMPONENT_PADDING
                )

                # Render trailing arc
                renderer.draw.arc(
                    bounding_box,
                    start=position - arc_sweep,
                    end=position,
                    fill=arc_trailing_color,
                    width=GUIConstants.COMPONENT_PADDING
                )

                # Erase previous trailing arc leading arc
                renderer.draw.arc(
                    bounding_box,
                    start=position - 2*arc_sweep,
                    end=position - arc_sweep,
                    fill=GUIConstants.BACKGROUND_COLOR,
                    width=GUIConstants.COMPONENT_PADDING
                )

                renderer.show_image()
            position += arc_sweep



@dataclass
class BaseTopNavScreen(BaseScreen):
    top_nav_icon_name: str = None
    top_nav_icon_color: str = None
    title: str = "Screen Title"
    title_font_size: int = GUIConstants.TOP_NAV_TITLE_FONT_SIZE
    show_back_button: bool = True
    show_power_button: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.top_nav = TopNav(
            icon_name=self.top_nav_icon_name,
            icon_color=self.top_nav_icon_color,
            text=self.title,
            font_size=self.title_font_size,
            width=self.canvas_width,
            height=GUIConstants.TOP_NAV_HEIGHT,
            show_back_button=self.show_back_button,
            show_power_button=self.show_power_button,
        )
        self.is_input_in_top_nav = False

        self.components.append(self.top_nav)


    def _run(self):
        raise Exception("Must implement in a child class")



@dataclass
class TextTopNavScreen(BaseTopNavScreen):
    text: str = "Body text"
    is_text_centered: bool = True
    text_font_name: str = GUIConstants.BODY_FONT_NAME
    text_font_size: int = GUIConstants.BODY_FONT_SIZE

    def __post_init__(self):
        super().__post_init__()

        self.text_area = TextArea(
            text=self.text,
            screen_x=0,
            screen_y=self.top_nav.height,
            width=self.canvas_width,
            height=self.canvas_height - self.top_nav.height,
            font_name=self.text_font_name,
            font_size=self.text_font_size,
            is_text_centered=self.is_text_centered
        )
        self.components.append(self.text_area)


    def _run(self):
        while True:
            user_input = self.hw_inputs.wait_for(
                [
                    HardwareButtonsConstants.KEY_UP,
                    HardwareButtonsConstants.KEY_DOWN,
                    HardwareButtonsConstants.KEY_PRESS
                ],
                check_release=True,
                release_keys=[HardwareButtonsConstants.KEY_PRESS]
            )

            with self.renderer.lock:
                if user_input == HardwareButtonsConstants.KEY_UP:
                    if not self.top_nav.is_selected:
                        # Only move navigation up there if there's something to select
                        if self.top_nav.show_back_button or self.top_nav.show_power_button:
                            self.top_nav.is_selected = True
                            self.top_nav.render()

                elif user_input == HardwareButtonsConstants.KEY_DOWN:
                    if self.top_nav.is_selected:
                        self.top_nav.is_selected = False
                        self.top_nav.render()

                elif user_input == HardwareButtonsConstants.KEY_PRESS:
                    if self.top_nav.is_selected:
                        return self.top_nav.selected_button

                # Write the screen updates
                self.renderer.show_image()



@dataclass
class ButtonListScreen(BaseTopNavScreen):
    button_data: list = None                  # list can be a mix of str or tuple(label: str, icon_name: str)
    selected_button: int = 0
    is_button_text_centered: bool = True
    is_bottom_list: bool = False
    button_font_name: str = GUIConstants.BUTTON_FONT_NAME
    button_font_size: int = GUIConstants.BUTTON_FONT_SIZE
    button_selected_color: str = GUIConstants.ACCENT_COLOR

    # Params for version of list used for Settings
    Button_cls = Button
    checked_buttons: List[int] = None


    def __post_init__(self):
        super().__post_init__()
        button_height = GUIConstants.BUTTON_HEIGHT
        if len(self.button_data) == 1:
            button_list_height = button_height
        else:
            button_list_height = (len(self.button_data) * button_height) + (GUIConstants.COMPONENT_PADDING * (len(self.button_data) - 1))

        if self.is_bottom_list:
            button_list_y = self.canvas_height - (button_list_height + GUIConstants.EDGE_PADDING)
        else:
            button_list_y = self.top_nav.height + int((self.canvas_height - self.top_nav.height - button_list_height) / 2)

        self.has_scroll_arrows = False
        if button_list_y < self.top_nav.height:
            # The button list is too long; force it to run off the bottom of the screen.
            button_list_y = self.top_nav.height
            self.has_scroll_arrows = True

        self.buttons: List[Button] = []
        for i, button_label in enumerate(self.button_data):
            icon_name = None
            icon_color = None
            button_label_color = GUIConstants.BUTTON_FONT_COLOR
            if type(button_label) == tuple:
                if len(button_label) == 2:
                    (button_label, icon_name) = button_label
                    icon_color = GUIConstants.BUTTON_FONT_COLOR

                elif len(button_label) == 3:
                    (button_label, icon_name, icon_color) = button_label

                elif len(button_label) == 4:
                    (button_label, icon_name, icon_color, button_label_color) = button_label

            button_kwargs = dict(
                text=button_label,
                icon_name=icon_name,
                icon_color=icon_color,
                is_icon_inline=True,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=button_list_y + i * (button_height + GUIConstants.LIST_ITEM_PADDING),
                width=self.canvas_width - (2 * GUIConstants.EDGE_PADDING),
                height=button_height,
                is_text_centered=self.is_button_text_centered,
                font_name=self.button_font_name,
                font_size=self.button_font_size,
                font_color=button_label_color,
                selected_color=self.button_selected_color
            )
            if self.checked_buttons and i in self.checked_buttons:
                button_kwargs["is_checked"] = True
            button = self.Button_cls(**button_kwargs)
            self.buttons.append(button)
        
        if self.has_scroll_arrows:
            self.arrow_half_width = 10
            self.cur_scroll_y = 0
            self.up_arrow_img = Image.new("RGBA", size=(2 * self.arrow_half_width, 8), color="black")
            self.up_arrow_img_y = self.top_nav.height - 12
            arrow_draw = ImageDraw.Draw(self.up_arrow_img)
            arrow_draw.line((self.arrow_half_width, 1, 0, 7), fill=GUIConstants.BUTTON_FONT_COLOR)
            arrow_draw.line((self.arrow_half_width, 1, 2 * self.arrow_half_width, 7), fill=GUIConstants.BUTTON_FONT_COLOR)

            self.down_arrow_img = Image.new("RGBA", size=(2 * self.arrow_half_width, 8), color="black")
            self.down_arrow_img_y = self.canvas_height - 16 + 2
            arrow_draw = ImageDraw.Draw(self.down_arrow_img)
            center_x = int(self.canvas_width / 2)
            arrow_draw.line((self.arrow_half_width, 7, 0, 1), fill=GUIConstants.BUTTON_FONT_COLOR)
            arrow_draw.line((self.arrow_half_width, 7, 2 * self.arrow_half_width, 1), fill=GUIConstants.BUTTON_FONT_COLOR)

        cur_selected_button = self.buttons[self.selected_button]
        cur_selected_button.is_selected = True
        if self.has_scroll_arrows:
            frame_scroll = self.buttons[0].screen_y - cur_selected_button.screen_y
            for button in self.buttons:
                button.scroll_y -= frame_scroll


    def _render(self):
        super()._render()
        self._render_visible_buttons()


    def _render_visible_buttons(self):
        if self.has_scroll_arrows:
            self._render_up_arrow()
            self._render_down_arrow()

        for i, button in enumerate(self.buttons):
            if not self.has_scroll_arrows:
                button.render()
                continue

            button_position_y = button.screen_y - button.scroll_y
            if button_position_y >= self.top_nav.height and button_position_y < self.down_arrow_img_y:
                if i == 0:
                    # We rendered the top button; no more to scroll up for.
                    self._hide_up_arrow()

                if i == len(self.buttons) - 1:
                    # We just pulled up the last button; no more to scroll down for.
                    self._hide_down_arrow()

                # Render the button after the arrows to cover up overlap
                button.render()


    def _render_up_arrow(self):
        self.canvas.paste(self.up_arrow_img, (int(self.canvas_width / 2) - self.arrow_half_width, self.up_arrow_img_y))

    def _render_down_arrow(self):
        self.canvas.paste(self.down_arrow_img, (int(self.canvas_width / 2) - self.arrow_half_width, self.down_arrow_img_y))

    def _hide_up_arrow(self):
        self.image_draw.rectangle(
            (
                int(self.canvas_width / 2) - self.arrow_half_width, self.up_arrow_img_y,
                int(self.canvas_width / 2) + self.arrow_half_width, self.up_arrow_img_y + self.up_arrow_img.height
            ),
            fill="black"
        )

    def _hide_down_arrow(self):
        self.image_draw.rectangle(
            (
                int(self.canvas_width / 2) - self.arrow_half_width, self.down_arrow_img_y,
                int(self.canvas_width / 2) + self.arrow_half_width, self.down_arrow_img_y + self.down_arrow_img.height
            ),
            fill="black"
        )


    def _run(self):
        while True:
            user_input = self.hw_inputs.wait_for(
                [
                    HardwareButtonsConstants.KEY_UP,
                    HardwareButtonsConstants.KEY_DOWN,
                    HardwareButtonsConstants.KEY_LEFT,
                    HardwareButtonsConstants.KEY_RIGHT,
                    HardwareButtonsConstants.KEY_PRESS
                ],
                check_release=True,
                release_keys=[HardwareButtonsConstants.KEY_PRESS]
            )

            with self.renderer.lock:
                if not self.top_nav.is_selected and (
                        user_input == HardwareButtonsConstants.KEY_LEFT or (
                            user_input == HardwareButtonsConstants.KEY_UP and self.selected_button == 0
                        )
                    ):
                    # SHORTCUT to escape long menu screens!
                    # OR keyed UP from the top of the list.
                    # Move selection up to top_nav
                    # Only move navigation up there if there's something to select
                    if self.top_nav.show_back_button or self.top_nav.show_power_button:
                        self.buttons[self.selected_button].is_selected = False
                        self.buttons[self.selected_button].render()

                        self.top_nav.is_selected = True
                        self.top_nav.render()

                elif user_input == HardwareButtonsConstants.KEY_UP:
                    if self.top_nav.is_selected:
                        # Can't go up any further
                        pass
                    else:
                        cur_selected_button: Button = self.buttons[self.selected_button]
                        self.selected_button -= 1
                        next_selected_button: Button = self.buttons[self.selected_button]
                        cur_selected_button.is_selected = False
                        next_selected_button.is_selected = True
                        if self.has_scroll_arrows and next_selected_button.screen_y - next_selected_button.scroll_y + next_selected_button.height < self.top_nav.height:
                            # Selected a Button that's off the top of the screen
                            frame_scroll = cur_selected_button.screen_y - next_selected_button.screen_y
                            for button in self.buttons:
                                button.scroll_y -= frame_scroll
                            self._render_visible_buttons()
                        else:
                            cur_selected_button.render()
                            next_selected_button.render()

                elif user_input == HardwareButtonsConstants.KEY_DOWN or (
                        self.top_nav.is_selected and user_input == HardwareButtonsConstants.KEY_RIGHT
                    ):
                    if self.selected_button == len(self.buttons) - 1:
                        # Already at the bottom of the list. Nowhere to go. But may need
                        # to re-render if we're returning from top_nav; otherwise skip
                        # this update loop.
                        if not self.top_nav.is_selected:
                            continue

                    if self.top_nav.is_selected:
                        self.top_nav.is_selected = False
                        self.top_nav.render()

                        cur_selected_button = None
                        next_selected_button = self.buttons[self.selected_button]
                        next_selected_button.is_selected = True

                    else:
                        cur_selected_button: Button = self.buttons[self.selected_button]
                        self.selected_button += 1
                        next_selected_button: Button = self.buttons[self.selected_button]
                        cur_selected_button.is_selected = False
                        next_selected_button.is_selected = True

                    if self.has_scroll_arrows and (
                            next_selected_button.screen_y - next_selected_button.scroll_y + next_selected_button.height > self.down_arrow_img_y
                        ):
                        # Selected a Button that's off the bottom of the screen
                        frame_scroll = next_selected_button.screen_y - cur_selected_button.screen_y
                        for button in self.buttons:
                            button.scroll_y += frame_scroll
                        self._render_visible_buttons()
                    else:
                        if cur_selected_button:
                            cur_selected_button.render()
                        next_selected_button.render()

                elif user_input == HardwareButtonsConstants.KEY_PRESS:
                    if self.top_nav.is_selected:
                        return self.top_nav.selected_button
                    return self.selected_button

                # Write the screen updates
                self.renderer.show_image()



@dataclass
class LargeButtonScreen(BaseTopNavScreen):
    button_data: list = None                  # list can be a mix of str or tuple(label: str, icon_name: str)
    button_font_name: str = GUIConstants.BUTTON_FONT_NAME
    button_font_size: int = 20
    button_selected_color: str = GUIConstants.ACCENT_COLOR
    selected_button: int = 0

    def __post_init__(self):
        super().__post_init__()

        if len(self.button_data) not in [2, 4]:
            raise Exception("LargeButtonScreen only supports 2 or 4 buttons")

        # Maximize 2-across width; calc height with a 4:3 aspect ratio
        button_width = int((self.canvas_width - (2 * GUIConstants.EDGE_PADDING) - GUIConstants.COMPONENT_PADDING) / 2)
        button_height = int(button_width * (3.0 / 4.0))

        # Vertically center the buttons
        if len(self.button_data) == 2:
            button_start_y = self.top_nav.height + int((self.canvas_height - (self.top_nav.height + GUIConstants.COMPONENT_PADDING) - button_height) / 2)
        else:
            button_start_y = self.top_nav.height + int((self.canvas_height - (self.top_nav.height + GUIConstants.COMPONENT_PADDING) - (2 * button_height) - GUIConstants.COMPONENT_PADDING) / 2)

        self.buttons = []
        for i, button_label in enumerate(self.button_data):
            if type(button_label) == tuple:
                (button_label, icon_name) = button_label
            else:
                icon_name = None

            if i % 2 == 0:
                button_start_x = GUIConstants.EDGE_PADDING
            else:
                button_start_x = GUIConstants.EDGE_PADDING + button_width + GUIConstants.COMPONENT_PADDING

            button_args = {
                "text": button_label,
                "screen_x": button_start_x,
                "screen_y": button_start_y,
                "width": button_width,
                "height": button_height,
                "is_text_centered": True,
                "font_name": self.button_font_name,
                "font_size": self.button_font_size,
                "selected_color": self.button_selected_color,
            }
            if icon_name:
                button_args["icon_name"] = icon_name
                button_args["text_y_offset"] = int(48 / 240 * self.renderer.canvas_height) + GUIConstants.COMPONENT_PADDING
                button = LargeIconButton(**button_args)
            else:
                button = Button(**button_args)

            self.buttons.append(button)
            self.components.append(button)

            if i == 1:
                button_start_y += button_height + GUIConstants.COMPONENT_PADDING

        self.buttons[self.selected_button].is_selected = True


    def _run(self):
        def swap_selected_button(new_selected_button: int):
            self.buttons[self.selected_button].is_selected = False
            self.buttons[self.selected_button].render()
            self.selected_button = new_selected_button
            self.buttons[self.selected_button].is_selected = True
            self.buttons[self.selected_button].render()

        while True:
            user_input = self.hw_inputs.wait_for(
                [
                    HardwareButtonsConstants.KEY_UP,
                    HardwareButtonsConstants.KEY_DOWN,
                    HardwareButtonsConstants.KEY_LEFT,
                    HardwareButtonsConstants.KEY_RIGHT,
                    HardwareButtonsConstants.KEY_PRESS
                ],
                check_release=True,
                release_keys=[HardwareButtonsConstants.KEY_PRESS]
            )

            with self.renderer.lock:
                if user_input == HardwareButtonsConstants.KEY_UP:
                    if self.selected_button in [0, 1]:
                        # Move selection up to top_nav
                        self.top_nav.is_selected = True
                        self.top_nav.render()

                        self.buttons[self.selected_button].is_selected = False
                        self.buttons[self.selected_button].render()

                    elif len(self.buttons) == 4:
                        swap_selected_button(self.selected_button - 2)

                elif user_input == HardwareButtonsConstants.KEY_DOWN:
                    if self.top_nav.is_selected:
                        self.top_nav.is_selected = False
                        self.top_nav.render()

                        self.buttons[self.selected_button].is_selected = True
                        self.buttons[self.selected_button].render()

                    elif self.selected_button in [2, 3]:
                        pass
                    elif len(self.buttons) == 4:
                        swap_selected_button(self.selected_button + 2)

                elif user_input == HardwareButtonsConstants.KEY_RIGHT and not self.top_nav.is_selected:
                    if self.selected_button in [0, 2]:
                        swap_selected_button(self.selected_button + 1)
                
                elif (user_input == HardwareButtonsConstants.KEY_RIGHT and
                        self.top_nav.is_selected and not self.top_nav.show_power_button
                    ):
                    self.top_nav.is_selected = False
                    self.top_nav.render()

                    self.buttons[self.selected_button].is_selected = True
                    self.buttons[self.selected_button].render()

                elif user_input == HardwareButtonsConstants.KEY_LEFT and not self.top_nav.is_selected:
                    if self.selected_button in [1, 3]:
                        swap_selected_button(self.selected_button - 1)
                    else:
                        # Left from the far edge takes us up to the BACK arrow
                        if self.top_nav.show_back_button:
                            self.top_nav.is_selected = True
                            self.top_nav.render()

                            self.buttons[self.selected_button].is_selected = False
                            self.buttons[self.selected_button].render()

                elif user_input == HardwareButtonsConstants.KEY_PRESS:
                    if self.top_nav.is_selected:
                        return self.top_nav.selected_button
                    return self.selected_button

                # Write the screen updates
                self.renderer.show_image()



@dataclass
class QRDisplayScreen(BaseScreen):
    qr_encoder: EncodeQR = None

    def _run(self):
        from seedsigner.models.settings import Settings
        settings = Settings.get_instance()
        cur_brightness = settings.get_value(SettingsConstants.SETTING__QR_BRIGHTNESS)

        # Loop whether the QR is a single frame or animated; each loop might adjust
        # brightness setting.
        while True:
            # convert the cur_brightness integer (31-255) into hex triplets
            hex_color = (hex(cur_brightness).split('x')[1]) * 3
            image = self.qr_encoder.next_part_image(240,240, border=2, background_color=hex_color)
            self.renderer.show_image(image)

            # Target n held frames per second before rendering next QR image
            time.sleep(5/30.0)

            if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_DOWN):
                # Reduce QR code background brightness
                cur_brightness = max(31, cur_brightness - 31)

            elif self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_UP):
                # Incrase QR code background brightness
                cur_brightness = min(cur_brightness + 31, 255)

            elif self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT):
                break


        settings.set_value(SettingsConstants.SETTING__QR_BRIGHTNESS, cur_brightness)

        # TODO: handle left as BACK



@dataclass
class LargeIconStatusScreen(ButtonListScreen):
    title: str = "Success!"
    status_icon_name: str = SeedSignerCustomIconConstants.CIRCLE_CHECK
    status_icon_size: int = GUIConstants.ICON_PRIMARY_SCREEN_SIZE
    status_color: str = GUIConstants.SUCCESS_COLOR
    status_headline: str = "Success!"  # The colored text under the large icon
    text: str = ""                          # The body text of the screen
    button_data: list = None

    def __post_init__(self):
        self.is_bottom_list: bool = True
        if not self.button_data:
            self.button_data = ["OK"]
        super().__post_init__()

        self.status_icon = Icon(
            icon_name=self.status_icon_name,
            icon_size=self.status_icon_size,
            icon_color=self.status_color,
        )
        self.status_icon.screen_y = self.top_nav.height - int(GUIConstants.COMPONENT_PADDING/2)
        self.status_icon.screen_x = int((self.canvas_width - self.status_icon.width) / 2)
        self.components.append(self.status_icon)

        next_y = self.status_icon.screen_y + self.status_icon.height + 4
        if self.status_headline:
            self.warning_headline_textarea = TextArea(
                text=self.status_headline,
                width=self.canvas_width,
                screen_y=next_y,
                font_color=self.status_color,
            )
            self.components.append(self.warning_headline_textarea)
            next_y = next_y + self.warning_headline_textarea.height

        self.components.append(TextArea(
            height=self.buttons[0].screen_y - next_y,
            text=self.text,
            width=self.canvas_width,
            screen_y=next_y,
        ))


class WarningEdgesThread(BaseThread):
    def __init__(self, args):
        super().__init__()
        self.args = args


    def run(self):
        screen = self.args[0]
        inhale_step = 1
        inhale_max = 10
        inhale_hold = 8
        cur_inhale_hold = 0
        inhale_factor = 0
        rgb = ImageColor.getrgb(screen.status_color)

        def render_border(color, width):
            screen.image_draw.rectangle(
                (0, 0, screen.canvas_width, screen.canvas_height),
                fill=None,
                outline=color,
                width=width,
                # radius=5
            )

        while self.keep_running:
            with screen.renderer.lock:
                # Ramp the edges from a darker version out to full color
                inhale_scalar = inhale_factor * int(255/inhale_max)
                for index, n in enumerate(range(4, -1, -1)):
                    # Reverse range steadily increases rgb in brightness until reaching full.
                    # 34 == 0x22; just eyeballed a good step size

                    r = max(0, rgb[0] - 34*n - inhale_scalar)
                    g = max(0, rgb[1] - 34*n - inhale_scalar)
                    b = max(0, rgb[2] - 34*n - inhale_scalar)

                    # `index` shrinks the border at each step
                    render_border((r, g, b), GUIConstants.EDGE_PADDING - 2 - index)

                # Write the screen updates
                screen.renderer.show_image()
            
            if inhale_factor == inhale_max:
                inhale_step = -1
            elif inhale_factor == 0 and inhale_step == -1:
                cur_inhale_hold += 1
                if cur_inhale_hold > inhale_hold:
                    inhale_step = 1
                    cur_inhale_hold = 0
                else:
                    # It's about to be decremented below zero
                    inhale_factor = 1
            inhale_factor += inhale_step

            # Target ~10fps
            time.sleep(0.05)



@dataclass
class WarningEdgesMixin:
    status_color: str = GUIConstants.WARNING_COLOR

    def __post_init__(self):
        super().__post_init__()

        self.threads.append(WarningEdgesThread(args=(self,)))



@dataclass
class WarningScreen(WarningEdgesMixin, LargeIconStatusScreen):
    title: str = "Caution"
    status_icon_name: str = SeedSignerCustomIconConstants.CIRCLE_EXCLAMATION
    status_color: str = "yellow"
    status_headline: str = "Privacy Leak!"     # The colored text under the alert icon

    def __post_init__(self):
        if not self.button_data:
            self.button_data = ["I Understand"]
        super().__post_init__()


@dataclass
class DireWarningScreen(WarningScreen):
    status_headline: str = "Classified Info!"     # The colored text under the alert icon
    status_color: str = GUIConstants.DIRE_WARNING_COLOR


