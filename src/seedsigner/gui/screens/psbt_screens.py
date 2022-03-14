from dataclasses import dataclass
from lzma import is_check_supported
from PIL import Image, ImageDraw, ImageFilter
from typing import List

from seedsigner.gui.renderer import Renderer
from seedsigner.models.threads import BaseThread

from .screen import ButtonListScreen, WarningScreen
from ..components import (Button, Icon, FontAwesomeIconConstants, IconTextLine, FormattedAddress, GUIConstants, Fonts, SeedSignerCustomIconConstants, TextArea,
    calc_bezier_curve, linear_interp)



@dataclass
class PSBTOverviewScreen(ButtonListScreen):
    spend_amount: int = 0
    change_amount: int = 0
    fee_amount: int = 0
    num_inputs: int = 0
    num_self_transfer_outputs: int = 0
    num_change_outputs: int = 0
    destination_addresses: List[str] = None
    

    def __post_init__(self):
        # Customize defaults
        self.title = "Review PSBT"
        self.is_bottom_list = True
        self.button_data = ["Review Details"]

        # This screen can take a while to load while parsing the PSBT
        self.show_loading_screen = True

        super().__post_init__()

        # Prep the headline amount being spent in large callout
        # icon_text_lines_y = self.components[-1].screen_y + self.components[-1].height
        icon_text_lines_y = self.top_nav.height + GUIConstants.COMPONENT_PADDING


        if not self.destination_addresses:
            # This is a self-transfer
            spend_amount = self.change_amount
        else:
            spend_amount = self.spend_amount

        if spend_amount <= 1e6:
            amount_display = f"{spend_amount:,} sats"
        else:
            amount_display = f"{spend_amount/1e8:,} btc"
        self.components.append(IconTextLine(
            icon_name=SeedSignerCustomIconConstants.BITCOIN_LOGO,
            icon_color=GUIConstants.ACCENT_COLOR,
            icon_size=34,
            is_text_centered=True,
            value_text=f"{amount_display}",
            font_size=24,
            screen_y=icon_text_lines_y,
        ))

        # Prep the transaction flow chart
        self.chart_x = 0
        self.chart_y = self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING
        chart_height = self.buttons[0].screen_y - self.chart_y - GUIConstants.COMPONENT_PADDING

        # We need to supersample the whole panel so that small/thin elements render
        # clearly.
        ssf = 4  # super-sampling factor

        # Set up our temp supersampled rendering surface
        image = Image.new(
            "RGB",
            (self.canvas_width * ssf, chart_height * ssf),
            GUIConstants.BACKGROUND_COLOR
        )
        draw = ImageDraw.Draw(image)

        font_size = GUIConstants.BODY_FONT_MIN_SIZE * ssf
        font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, font_size)

        tw, chart_text_height = font.getsize("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")  # All possible chars for max range
        vertical_center = int(image.height/2)
        # Supersampling renders thin elements poorly if they land on an even line before scaling down
        if vertical_center % 2 == 1:
            vertical_center += 1

        association_line_color = "#666"
        association_line_width = 3*ssf
        curve_steps = 4
        chart_font_color = "#ddd"
        
        # First calculate how wide the inputs col will be
        inputs_column = []
        if self.num_inputs == 1:
            inputs_column.append("1 input")
        elif self.num_inputs > 5:
            inputs_column.append("input 1")
            inputs_column.append("input 2")
            inputs_column.append("[ ... ]")
            inputs_column.append(f"input {self.num_inputs-1}")
            inputs_column.append(f"input {self.num_inputs}")
        else:
            for i in range(0, self.num_inputs):
                inputs_column.append(f"input {i+1}")

        max_inputs_text_width = 0
        for input in inputs_column:
            tw, th = font.getsize(input)
            max_inputs_text_width = max(tw, max_inputs_text_width)

        # Given how wide we want our curves on each side to be...
        curve_width = 4*GUIConstants.COMPONENT_PADDING*ssf

        # ...and the minimum center divider width...
        center_bar_width = 2*GUIConstants.COMPONENT_PADDING*ssf

        # We can calculate how wide the destination col can be
        max_destination_col_width = image.width - (GUIConstants.EDGE_PADDING*ssf + max_inputs_text_width + \
            int(GUIConstants.COMPONENT_PADDING*ssf/4) + curve_width + \
                center_bar_width + \
                    curve_width + int(GUIConstants.COMPONENT_PADDING*ssf/4) + \
                        GUIConstants.EDGE_PADDING*ssf)
        
        # if self.num_inputs == 1:
        #     # Use up more of the space on the input side
        #     max_destination_col_width += curve_width
        
        # Now let's maximize the actual destination col by adjusting our addr truncation
        def calculate_destination_col_width(truncate_at: int):
            def truncate_destination_addr(addr):
                return f"{addr[:truncate_at]}..."
            
            destination_column = []

            if len(self.destination_addresses) <= 3:
                for addr in self.destination_addresses:
                    destination_column.append(truncate_destination_addr(addr))
            else:
                # destination_column.append(f"{len(self.destination_addresses)} recipients")
                destination_column.append(f"recipient 1")
                destination_column.append(f"[ ... ]")
                destination_column.append(f"recipient {len(self.destination_addresses)}")

            if self.num_self_transfer_outputs > 0:
                for i in range(0, self.num_self_transfer_outputs):
                    destination_column.append(f"self-transfer")

            destination_column.append(f"fee")

            if self.num_change_outputs > 0:
                for i in range(0, self.num_change_outputs):
                    destination_column.append("change")

            max_destination_text_width = 0
            for destination in destination_column:
                tw, th = font.getsize(destination)
                max_destination_text_width = max(tw, max_destination_text_width)
            
            return (max_destination_text_width, destination_column)
        
        if len(self.destination_addresses) > 3:
            # We're not going to display any destination addrs so truncation doesn't matter
            (destination_text_width, destination_column) = calculate_destination_col_width(truncate_at=0)
        else:
            # Steadliy widen out the destination column until we run out of space
            for i in range(6, 13):
                (new_width, new_col_text) = calculate_destination_col_width(truncate_at=i)
                if new_width > max_destination_col_width:
                    break
                destination_text_width = new_width
                destination_column = new_col_text

        destination_col_x = image.width - (destination_text_width + GUIConstants.EDGE_PADDING*ssf)

        # Now we can finalize our center bar values
        center_bar_x = GUIConstants.EDGE_PADDING*ssf + max_inputs_text_width + int(GUIConstants.COMPONENT_PADDING*ssf/4) + curve_width

        # Center bar stretches to fill any excess width
        center_bar_width = destination_col_x - int(GUIConstants.COMPONENT_PADDING*ssf/4) - curve_width - center_bar_x 

        # Position each input row
        num_rendered_inputs = len(inputs_column)
        if self.num_inputs == 1:
            inputs_y = vertical_center - int(chart_text_height/2)
            inputs_y_spacing = 0  # Not used
        else:
            inputs_y = int((image.height - num_rendered_inputs*chart_text_height) / (num_rendered_inputs + 1))
            inputs_y_spacing = inputs_y + chart_text_height

        # Don't render lines from an odd number
        if inputs_y % 2 == 1:
            inputs_y += 1
        if inputs_y_spacing % 2 == 1:
            inputs_y_spacing += 1

        inputs_conjunction_x = center_bar_x
        inputs_x = GUIConstants.EDGE_PADDING*ssf

        input_curves = []
        for input in inputs_column:
            # Calculate right-justified input display
            tw, th = font.getsize(input)
            cur_x = inputs_x + max_inputs_text_width - tw
            draw.text(
                (cur_x, inputs_y),
                text=input,
                font=font,
                fill=chart_font_color,
            )

            # Render the association line to the conjunction point
            # First calculate a bezier curve to an inflection point
            start_pt = (
                inputs_x + max_inputs_text_width + int(GUIConstants.COMPONENT_PADDING*ssf/4),
                inputs_y + int(chart_text_height/2)
            )
            conjunction_pt = (inputs_conjunction_x, vertical_center)
            mid_pt = (
                int(start_pt[0]*0.5 + conjunction_pt[0]*0.5), 
                int(start_pt[1]*0.5 + conjunction_pt[1]*0.5)
            )

            if len(inputs_column) == 1:
                # Use fewer segments for single input straight line
                bezier_points = [
                    start_pt,
                    linear_interp(start_pt, conjunction_pt, 0.33),
                    linear_interp(start_pt, conjunction_pt, 0.66),
                    conjunction_pt
                ]
            else:
                bezier_points = calc_bezier_curve(
                    start_pt,
                    (mid_pt[0], start_pt[1]),
                    mid_pt,
                    curve_steps
                )
                # We don't need the "final" point as it's repeated below
                bezier_points.pop()

                # Now render the second half after the inflection point
                bezier_points += calc_bezier_curve(
                    mid_pt,
                    (mid_pt[0], conjunction_pt[1]),
                    conjunction_pt,
                    curve_steps
                )

            input_curves.append(bezier_points)

            prev_pt = bezier_points[0]
            for pt in bezier_points[1:]:
                draw.line(
                    (prev_pt[0], prev_pt[1], pt[0], pt[1]),
                    fill=association_line_color,
                    width=association_line_width + 1,
                    joint="curve",
                )
                prev_pt = pt

            inputs_y += inputs_y_spacing
        
        # Render center bar
        draw.line(
            (
                center_bar_x,
                vertical_center,
                center_bar_x + center_bar_width,
                vertical_center
            ),
            fill=association_line_color,
            width=association_line_width
        )

        # Position each destination
        num_rendered_destinations = len(destination_column)
        if num_rendered_destinations == 1:
            destination_y = vertical_center - int(chart_text_height/2)
            destination_y_spacing = 0
        else:
            destination_y = int((image.height - num_rendered_destinations*chart_text_height) / (num_rendered_destinations + 1))
            destination_y_spacing = destination_y + chart_text_height

        # Don't render lines from an odd number
        if destination_y % 2 == 1:
            destination_y += 1
        if destination_y_spacing % 2 == 1:
            destination_y_spacing += 1

        destination_conjunction_x = center_bar_x + center_bar_width
        recipients_text_x = destination_col_x

        output_curves = []
        for destination in destination_column:
            draw.text(
                (recipients_text_x, destination_y),
                text=destination,
                font=font,
                fill=chart_font_color,
            )

            # Render the association line from the conjunction point
            # First calculate a bezier curve to an inflection point
            conjunction_pt = (destination_conjunction_x, vertical_center)
            end_pt = (
                conjunction_pt[0] + curve_width,
                destination_y + int(chart_text_height/2)
            )
            mid_pt = (
                int(conjunction_pt[0]*0.5 + end_pt[0]*0.5), 
                int(conjunction_pt[1]*0.5 + end_pt[1]*0.5)
            )

            bezier_points = calc_bezier_curve(
                conjunction_pt,
                (mid_pt[0], conjunction_pt[1]),
                mid_pt,
                curve_steps
            )
            # We don't need the "final" point as it's repeated below
            bezier_points.pop()

            # Now render the second half after the inflection point
            curve_bias = 1.0
            bezier_points += calc_bezier_curve(
                mid_pt,
                (int(mid_pt[0]*curve_bias + end_pt[0]*(1.0-curve_bias)), end_pt[1]),
                end_pt,
                curve_steps
            )

            output_curves.append(bezier_points)

            prev_pt = bezier_points[0]
            for pt in bezier_points[1:]:
                draw.line(
                    (prev_pt[0], prev_pt[1], pt[0], pt[1]),
                    fill=association_line_color,
                    width=association_line_width + 1,
                    joint="curve",
                )
                prev_pt = pt

            destination_y += destination_y_spacing

        # Resize to target and sharpen final image
        image = image.resize((self.canvas_width, chart_height), Image.LANCZOS)
        self.paste_images.append((image.filter(ImageFilter.SHARPEN), (self.chart_x, self.chart_y)))

        # Pass input and output curves to the animation thread
        self.threads.append(
            PSBTOverviewScreen.TxExplorerAnimationThread(
                inputs=input_curves,
                outputs=output_curves,
                supersampling_factor=ssf,
                offset_y=self.chart_y,
                renderer=self.renderer
            )
        )



    class TxExplorerAnimationThread(BaseThread):
        def __init__(self, inputs, outputs, supersampling_factor, offset_y, renderer: Renderer):
            super().__init__()

            # Translate the point coords into renderer space
            ssf = supersampling_factor
            self.inputs = [[(int(i[0]/ssf), int(i[1]/ssf + offset_y)) for i in curve] for curve in inputs]
            self.outputs = [[(int(i[0]/ssf), int(i[1]/ssf + offset_y)) for i in curve] for curve in outputs]
            self.renderer = renderer


        def run(self):
            pulse_color = GUIConstants.ACCENT_COLOR
            reset_color = "#666"
            line_width = 3

            pulses = []

            # The center bar needs to be segmented to support animation across it
            start_pt = self.inputs[0][-1]
            end_pt = self.outputs[0][0]
            if start_pt == end_pt:
                # In single input the center bar width can be zeroed out.
                # Ugly hack: Insert this line segment that will be skipped otherwise.
                center_bar_pts = [end_pt, self.outputs[0][1]]
            else:
                center_bar_pts = [
                    start_pt,
                    linear_interp(start_pt, end_pt, 0.25),
                    linear_interp(start_pt, end_pt, 0.50),
                    linear_interp(start_pt, end_pt, 0.75),
                    end_pt,
                ]

            def draw_line_segment(curves, i, j, color):
                # print(f"draw: {curves[0][i]} to {curves[0][j]}")
                for points in curves:
                    pt1 = points[i]
                    pt2 = points[j]
                    self.renderer.draw.line(
                        (pt1[0], pt1[1], pt2[0], pt2[1]),
                        fill=color,
                        width=line_width
                    )

            prev_color = reset_color
            while self.keep_running:
                with self.renderer.lock:
                    # Only generate one new pulse at a time; trailing "reset_color" pulse
                    # erases the most recent pulse.
                    if not pulses or (
                        prev_color == pulse_color and pulses[-1][0] == 10):
                        # Create a new pulse
                        if prev_color == pulse_color:
                            pulses.append([0, reset_color])
                        else:
                            pulses.append([0, pulse_color])
                        prev_color = pulses[-1][1]

                    for pulse_num, pulse in enumerate(pulses):
                        i = pulse[0]
                        color = pulse[1]
                        if i < len(self.inputs[0]) - 1:
                            # We're in the input curves
                            draw_line_segment(self.inputs, i, i+1, color)
                        elif i < len(self.inputs[0]) + len(center_bar_pts) - 2:
                            # We're in the center bar
                            index = i - len(self.inputs[0]) + 1
                            draw_line_segment([center_bar_pts], index, index+1, color)
                        elif i < len(self.inputs[0]) + len(center_bar_pts) - 2 + len(self.outputs[0]) - 1:
                            index = i - (len(self.inputs[0]) + len(center_bar_pts) - 2)
                            draw_line_segment(self.outputs, index, index+1, color)
                        else:
                            # This pulse is done
                            del pulses[pulse_num]
                            continue

                        pulse[0] += 1

                    self.renderer.show_image()

                # No need to CPU limit when running in its own thread?
                # time.sleep(0.02)



@dataclass
class PSBTMathScreen(ButtonListScreen):
    input_amount: int = 0
    num_inputs: int = 0
    spend_amount: int = 0
    num_recipients: int = 0
    fee_amount: int = 0
    change_amount: int = 0


    def __post_init__(self):
        # Customize defaults
        self.title = "PSBT Math"
        self.button_data = ["Review Recipients"]
        self.is_bottom_list = True

        super().__post_init__()

        if self.input_amount > 1e6:
            denomination = "btc"
            self.input_amount /= 1e8
            self.spend_amount /= 1e8
            self.change_amount /= 1e8
            self.input_amount = f"{self.input_amount:,.8f}"
            self.spend_amount = f"{self.spend_amount:,.8f}"
            self.change_amount = f"{self.change_amount:,.8f}"

            # Note: We keep the fee denominated in sats; just left pad it so it still
            # lines up properly.
            self.fee_amount = f"{self.fee_amount:10}"
        else:
            denomination = "sats"
            self.input_amount = f"{self.input_amount:,}"
            self.spend_amount = f"{self.spend_amount:,}"
            self.fee_amount = f"{self.fee_amount:,}"
            self.change_amount = f"{self.change_amount:,}"

        longest_amount = max(len(self.input_amount), len(self.spend_amount), len(self.fee_amount), len(self.change_amount))
        if len(self.input_amount) < longest_amount:
            self.input_amount = " " * (longest_amount - len(self.input_amount)) + self.input_amount

        if len(self.spend_amount) < longest_amount:
            self.spend_amount = " " * (longest_amount - len(self.spend_amount)) + self.spend_amount

        if len(self.fee_amount) < longest_amount:
            self.fee_amount = " " * (longest_amount - len(self.fee_amount)) + self.fee_amount

        if len(self.change_amount) < longest_amount:
            self.change_amount = " " * (longest_amount - len(self.change_amount)) + self.change_amount

        # Render the info to temp Image
        # TODO: Test rendering the numeric amounts without the supersampling
        body_width = self.canvas_width - 2*GUIConstants.EDGE_PADDING
        body_height = self.buttons[0].screen_y - self.top_nav.height - 2*GUIConstants.COMPONENT_PADDING
        ssf = 2  # Super-sampling factor
        image = Image.new("RGB", (body_width*ssf, body_height*ssf))
        draw = ImageDraw.Draw(image)

        body_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, (GUIConstants.BODY_FONT_SIZE)*ssf)
        fixed_width_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, (GUIConstants.BODY_FONT_SIZE + 6)*ssf)
        digits_width, digits_height = fixed_width_font.getsize(self.input_amount + "+")

        # Draw each line of the equation
        cur_y = 0

        def render_amount(cur_y, amount_str, info_text, info_text_color=GUIConstants.BODY_FONT_COLOR):
            secondary_digit_color = "#888"
            tertiary_digit_color = "#666"
            digit_group_spacing = 2 * ssf
            # secondary_digit_color = GUIConstants.BODY_FONT_COLOR
            # tertiary_digit_color = GUIConstants.BODY_FONT_COLOR
            # digit_group_spacing = 0
            if denomination == 'btc':
                display_str = amount_str
                main_zone = display_str[:-6]
                mid_zone = display_str[-6:-3]
                end_zone = display_str[-3:]
                main_zone_width, th = fixed_width_font.getsize(main_zone)
                mid_zone_width, th = fixed_width_font.getsize(end_zone)
                draw.text((0, cur_y), text=main_zone, font=fixed_width_font, fill=GUIConstants.BODY_FONT_COLOR)
                draw.text((main_zone_width + digit_group_spacing, cur_y), text=mid_zone, font=fixed_width_font, fill=secondary_digit_color)
                draw.text((main_zone_width + digit_group_spacing + mid_zone_width + digit_group_spacing, cur_y), text=end_zone, font=fixed_width_font, fill=tertiary_digit_color)
            else:
                draw.text((0, cur_y), text=amount_str, font=fixed_width_font, fill=GUIConstants.BODY_FONT_COLOR)
            draw.text((digits_width + 2*digit_group_spacing, cur_y), text=info_text, font=body_font, fill=info_text_color)

        render_amount(
            cur_y,
            f" {self.input_amount}",
            # info_text=f""" {self.num_inputs} input{"s" if self.num_inputs > 1 else ""}""",
            info_text=f""" input{"s" if self.num_inputs > 1 else ""}""",
        )

        # spend_amount will be zero on self-transfers; only display when there's an
        # external recipient.
        if self.num_recipients > 0:
            cur_y += int(digits_height * 1.2)
            render_amount(
                cur_y,
                f"-{self.spend_amount}",
                # info_text=f""" {self.num_recipients} recipient{"s" if self.num_recipients > 1 else ""}""",
                info_text=f""" recipient{"s" if self.num_recipients > 1 else ""}""",
            )

        cur_y += int(digits_height * 1.2)
        render_amount(
            cur_y,
            f"-{self.fee_amount}",
            info_text=f""" fee""",
        )

        cur_y += int(digits_height * 1.2) + 4 * ssf
        draw.line((0, cur_y, image.width, cur_y), fill=GUIConstants.BODY_FONT_COLOR, width=1)
        cur_y += 8 * ssf

        render_amount(
            cur_y,
            f" {self.change_amount}",
            info_text=f" {denomination} change",
            info_text_color="darkorange"  # super-sampling alters the perceived color
        )

        # Resize to target and sharpen final image
        image = image.resize((body_width, body_height), Image.LANCZOS)
        self.paste_images.append((image.filter(ImageFilter.SHARPEN), (GUIConstants.EDGE_PADDING, self.top_nav.height + GUIConstants.COMPONENT_PADDING)))



@dataclass
class PSBTAddressDetailsScreen(ButtonListScreen):
    address: str = None
    amount: int = 0

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True

        super().__post_init__()

        center_img_height = self.buttons[0].screen_y - self.top_nav.height

        # Figuring out how to vertically center the sats and the address is
        # difficult so we just render to a temp image and paste it in place.
        center_img = Image.new("RGB", (self.canvas_width, center_img_height), GUIConstants.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(center_img)

        if self.amount <= 1e7:
            amount_display = f"{self.amount:,} sats"
        else:
            amount_display = f"{self.amount/1e8:,} btc"

        icon_text_line = IconTextLine(
            image_draw=draw,
            canvas=center_img,
            icon_name=SeedSignerCustomIconConstants.BITCOIN_LOGO,
            icon_color=GUIConstants.ACCENT_COLOR,
            icon_size=28,
            is_text_centered=True,
            value_text=f"{amount_display}",
            font_size=22,
            screen_y=int(GUIConstants.COMPONENT_PADDING/2),
        )

        formatted_address = FormattedAddress(
            image_draw=draw,
            canvas=center_img,
            width=self.canvas_width - 2*GUIConstants.EDGE_PADDING,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=icon_text_line.height + GUIConstants.COMPONENT_PADDING,
            font_size=24,
            address=self.address,
        )

        # Render each to the temp img we passed in
        icon_text_line.render()
        formatted_address.render()

        self.body_img = center_img.crop((
            0,
            0,
            self.canvas_width,
            formatted_address.screen_y + formatted_address.height
        ))
        body_img_y = self.top_nav.height + int((center_img_height - self.body_img.height - GUIConstants.COMPONENT_PADDING)/2)

        self.paste_images.append((self.body_img, (0, body_img_y)))



@dataclass
class PSBTChangeDetailsScreen(ButtonListScreen):
    title: str = "Your Change"
    amount: int = 0
    address: str = None
    is_multisig: bool = False
    fingerprint: str = None
    derivation_path: str = None
    is_change_derivation_path: bool = True
    derivation_path_addr_index: int = 0
    is_change_addr_verified: bool = False

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(IconTextLine(
            icon_name=SeedSignerCustomIconConstants.BITCOIN_LOGO,
            icon_color=GUIConstants.ACCENT_COLOR,
            icon_size=28,
            value_text=f"{self.amount} sats" if self.amount < 1e6 else f"{self.amount/1e8:0.8f} btc",
            font_size=22,
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        ))
        self.components.append(FormattedAddress(
            screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
            address=self.address,
            max_lines=1,
        ))

        screen_y = self.components[-1].screen_y + self.components[-1].height + 2*GUIConstants.COMPONENT_PADDING
        if self.is_multisig and not self.is_change_addr_verified:
            # Adjust the vertical spacing
            screen_y -= GUIConstants.COMPONENT_PADDING
        self.components.append(IconTextLine(
            icon_name=SeedSignerCustomIconConstants.FINGERPRINT,
            icon_color="blue",
            value_text=f"""{"Multisig" if self.is_multisig else self.fingerprint}: {"Change" if self.is_change_derivation_path else "Addr"} #{self.derivation_path_addr_index}""",
            is_text_centered=False,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=screen_y,
        ))

        if self.is_change_addr_verified:
            self.components.append(IconTextLine(
                icon_name=SeedSignerCustomIconConstants.CIRCLE_CHECK,
                icon_color="#00dd00",
                value_text="Address verified!",
                is_text_centered=False,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
            ))
        else:
            pass



@dataclass
class PSBTFinalizeScreen(ButtonListScreen):
    def __post_init__(self):
        # Customize defaults
        self.title = "Sign PSBT"
        self.is_bottom_list = True
        super().__post_init__()

        icon = Icon(
            icon_name=FontAwesomeIconConstants.PAPER_PLANE,
            icon_color=GUIConstants.SUCCESS_COLOR,
            icon_size=GUIConstants.ICON_LARGE_BUTTON_SIZE,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        icon.screen_x = int((self.canvas_width - icon.width)/2)
        self.components.append(icon)

        self.components.append(TextArea(
            text="Click to authorize this transaction",
            screen_y=icon.screen_y + icon.height + GUIConstants.COMPONENT_PADDING
        ))



@dataclass
class PSBTSelectCoordinatorScreen(ButtonListScreen):
    def __post_init__(self):
        # Customize defaults
        self.title = "Signed PSBT"
        self.is_bottom_list = True
        super().__post_init__()

        self.components.append(TextArea(
            text="Export as a QR code for:",
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        ))
