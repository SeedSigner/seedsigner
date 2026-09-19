import math
import time

from dataclasses import dataclass
from gettext import gettext as _
from gettext import ngettext
from PIL import Image, ImageDraw, ImageFilter

from seedsigner.gui.components import (BtcAmount, Icon, FontAwesomeIconConstants, IconTextLine, FormattedAddress, GUIConstants, Fonts, SeedSignerIconConstants, TextArea,
    calc_bezier_curve, linear_interp)
from seedsigner.gui.renderer import Renderer
from seedsigner.models.threads import BaseThread

from .screen import ButtonListScreen, ButtonOption



@dataclass
class PSBTOverviewScreen(ButtonListScreen):
    spend_amount: int = 0
    change_amount: int = 0
    fee_amount: int = 0
    num_inputs: int = 0
    num_self_transfer_outputs: int = 0
    num_change_outputs: int = 0
    destination_addresses: list[str] = None
    op_return_amounts: list[int] = None
    is_high_fee_tx: bool = False

    # Appended to a row that needs the user's attention, drawn in the dire warning color
    WARNING_MARK = " (!)"
    

    @staticmethod
    def op_return_rows(op_return_amounts: list) -> list:
        """
            One row per OP_RETURN output for the flow diagram. Past three, collapse to the
            first and last with an ellipsis between, the same way recipients are; the
            chart has no minimum row height, so too many rows would squash it.

            An output that burns sats gets a "(!)" mark. Each output is marked on its own,
            not the whole group, so the mark points at the right one. When the middle rows
            are collapsed, the ellipsis carries the mark if any of them burn. The mark is
            baked into the label so the column is measured wide enough to fit it.
        """
        amounts = op_return_amounts or []

        def row(text: str, burns: bool) -> str:
            return text + PSBTOverviewScreen.WARNING_MARK if burns else text

        if len(amounts) <= 3:
            # TRANSLATOR_NOTE: Technical term, should probably NOT be translated in most languages
            return [row(_("OP_RETURN"), amount > 0) for amount in amounts]

        return [
            # TRANSLATOR_NOTE: "num" is the OP_RETURN output's position in the transaction (e.g. "OP_RETURN 1")
            row(_("OP_RETURN {num}").format(num=1), amounts[0] > 0),
            # TRANSLATOR_NOTE: Indicates that items have been omitted from a series: e.g. "1, 2, 3, [...], 8"
            row(_("[ ... ]"), any(amount > 0 for amount in amounts[1:-1])),
            row(_("OP_RETURN {num}").format(num=len(amounts)), amounts[-1] > 0),
        ]


    def __post_init__(self):
        # Customize defaults
        self.title = _("Review Transaction")
        self.is_bottom_list = True
        self.button_data = [ButtonOption("Review details")]

        super().__post_init__()

        # Prep the headline amount being spent in large callout
        # icon_text_lines_y = self.components[-1].screen_y + self.components[-1].height
        icon_text_lines_y = self.top_nav.height + GUIConstants.COMPONENT_PADDING

        if not self.destination_addresses:
            # This is a self-transfer
            spend_amount = self.change_amount
        else:
            spend_amount = self.spend_amount

        self.components.append(BtcAmount(
            total_sats=spend_amount,
            screen_y=icon_text_lines_y,
        ))

        # Prep the transaction flow chart
        self.chart_x = 0
        self.chart_y = self.components[-1].screen_y + self.components[-1].height + int(GUIConstants.COMPONENT_PADDING/2)
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
        font = Fonts.get_font(GUIConstants.get_body_font_name(), font_size)

        (left, top, right, bottom) = font.getbbox(text="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890[]", anchor="lt")
        chart_text_height = bottom
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
            inputs_column.append(_("1 input"))
        elif self.num_inputs > 5:
            inputs_column.append(_("input 1"))
            inputs_column.append(_("input 2"))
            # TRANSLATOR_NOTE: Indicates that items have been omitted from a series: e.g. "1, 2, 3, [...], 8"
            inputs_column.append(_("[ ... ]"))
            # TRANSLATOR_NOTE: Input number will be inserted (e.g. "input 3")
            inputs_column.append(_("input {}").format(self.num_inputs-1))
            inputs_column.append(_("input {}").format(self.num_inputs))
        else:
            for i in range(0, self.num_inputs):
                inputs_column.append(_("input {}").format(i+1))

        max_inputs_text_width = 0
        for input in inputs_column:
            left, top, right, bottom  = font.getbbox(input)
            tw, th = right - left, bottom - top
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
        def calculate_destination_col_width(truncate_at: int = 0):
            def truncate_destination_addr(addr):
                # TRANSLATOR_NOTE: Ellipsis ("...") characters used to truncate an address (e.g. "bc1qabc...")
                if len(addr) <= truncate_at + len(_("...")):
                    # No point in truncating
                    return addr

                return addr[:truncate_at] + _("...")
            
            destination_column = []

            # The rows `truncate_at` can actually shrink. The rest are fixed labels.
            truncatable_column = []

            if len(self.destination_addresses) + self.num_self_transfer_outputs <= 3:
                for addr in self.destination_addresses:
                    truncatable_column.append(truncate_destination_addr(addr))

                for i in range(0, self.num_self_transfer_outputs):
                    truncatable_column.append(truncate_destination_addr(_("self-transfer")))

                destination_column.extend(truncatable_column)
            else:
                # destination_column.append(f"{len(self.destination_addresses)} recipients")
                destination_column.append(_("recipient 1"))
                # TRANSLATOR_NOTE: Indicates that items have been omitted from a series: e.g. "1, 2, 3, [...], 8"
                destination_column.append(_("[ ... ]"))
                # TRANSLATOR_NOTE: Inserts the recipient number (e.g. the fifth one is: "recipient 5")
                destination_column.append(_("recipient {}").format(len(self.destination_addresses) + self.num_self_transfer_outputs))

            fee_label = _("fee")
            if self.is_high_fee_tx:
                # Part of the label, not something appended at render time: the column is
                # measured from these strings, so a mark added later would be drawn
                # outside the width that was reserved for the row.
                fee_label += PSBTOverviewScreen.WARNING_MARK
            destination_column.append(fee_label)

            destination_column.extend(PSBTOverviewScreen.op_return_rows(self.op_return_amounts))

            if self.num_change_outputs > 0:
                for i in range(0, self.num_change_outputs):
                    # TRANSLATOR_NOTE: Label for a change output in the PSBT Overview flow diagram
                    destination_column.append(_("change"))

            def widest(column):
                max_text_width = 0
                for destination in column:
                    left, top, right, bottom  = font.getbbox(destination)
                    tw, th = right - left, bottom - top
                    max_text_width = max(tw, max_text_width)
                return max_text_width

            return (widest(destination_column), widest(truncatable_column), destination_column)
        
        if len(self.destination_addresses) + self.num_self_transfer_outputs > 3:
            # We're not going to display any destination addrs so truncation doesn't matter
            (destination_text_width, _unused, destination_column) = calculate_destination_col_width()
        else:
            destination_text_width = None
            destination_column = None
            # Steadliy widen out the destination column until we run out of space.
            # Measured on the addresses alone: a fixed label that is wider than they are
            # (an OP_RETURN row carrying the "(!)" mark, say) sets the column width on its
            # own, and truncating the addresses below it would only lose characters
            # without narrowing anything.
            for i in range(6, 14):
                (new_width, new_truncatable_width, new_col_text) = calculate_destination_col_width(truncate_at=i)
                if new_truncatable_width > max_destination_col_width:
                    if not destination_text_width:
                        destination_text_width = new_width
                    if not destination_column:
                        destination_column = new_col_text
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
            left, top, right, bottom  = font.getbbox(input)
            tw, th = right - left, bottom - top
            cur_x = inputs_x + max_inputs_text_width - tw
            draw.text(
                (cur_x, inputs_y),
                text=input,
                font=font,
                fill=chart_font_color,
                anchor="lt",
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
            text_color = chart_font_color
            if destination.endswith(PSBTOverviewScreen.WARNING_MARK):
                text_color = GUIConstants.DIRE_WARNING_COLOR

            draw.text(
                (recipients_text_x, destination_y),
                text=destination,
                font=font,
                fill=text_color,
                anchor="lt"
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
        image = image.resize((self.canvas_width, chart_height), Image.Resampling.LANCZOS)
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
                time.sleep(0.02)



@dataclass
class PSBTMathScreen(ButtonListScreen):
    input_amount: int = 0
    num_inputs: int = 0
    spend_amount: int = 0
    num_recipients: int = 0
    fee_amount: int = 0
    change_amount: int = 0
    op_return_amount: int = 0
    is_high_fee_tx: bool = False


    def __post_init__(self):
        # Customize defaults
        self.title = _("Transaction Math")
        self.button_data = [ButtonOption("Review recipients")]
        self.is_bottom_list = True

        super().__post_init__()

        # Only show the "burned" line when something was actually burned; most OP_RETURNs
        # carry no value and a "0 burned" row would just be noise. Decide now, before the
        # amount is reformatted into a string below.
        shows_burned_amount = self.op_return_amount > 0

        if self.input_amount > 1e6:
            denomination = _("btc")
            self.input_amount /= 1e8
            self.spend_amount /= 1e8
            self.change_amount /= 1e8
            self.op_return_amount /= 1e8
            self.input_amount = f"{self.input_amount:,.8f}"
            self.spend_amount = f"{self.spend_amount:,.8f}"
            self.change_amount = f"{self.change_amount:,.8f}"
            self.op_return_amount = f"{self.op_return_amount:,.8f}"

            # Note: We keep the fee denominated in sats; just left pad it so it still
            # lines up properly.
            self.fee_amount = f"{self.fee_amount:10}"
        else:
            denomination = _("sats")
            self.input_amount = f"{self.input_amount:,}"
            self.spend_amount = f"{self.spend_amount:,}"
            self.fee_amount = f"{self.fee_amount:,}"
            self.change_amount = f"{self.change_amount:,}"
            self.op_return_amount = f"{self.op_return_amount:,}"

        longest_amount = max(len(self.input_amount), len(self.spend_amount), len(self.fee_amount), len(self.change_amount), len(self.op_return_amount))
        if len(self.input_amount) < longest_amount:
            self.input_amount = " " * (longest_amount - len(self.input_amount)) + self.input_amount

        if len(self.spend_amount) < longest_amount:
            self.spend_amount = " " * (longest_amount - len(self.spend_amount)) + self.spend_amount

        if len(self.fee_amount) < longest_amount:
            self.fee_amount = " " * (longest_amount - len(self.fee_amount)) + self.fee_amount

        if len(self.change_amount) < longest_amount:
            self.change_amount = " " * (longest_amount - len(self.change_amount)) + self.change_amount

        if len(self.op_return_amount) < longest_amount:
            self.op_return_amount = " " * (longest_amount - len(self.op_return_amount)) + self.op_return_amount

        # Render the info to temp Image
        # TODO: Test rendering the numeric amounts without the supersampling
        body_width = self.canvas_width - 2*GUIConstants.EDGE_PADDING
        body_height = self.buttons[0].screen_y - self.top_nav.height - 2*GUIConstants.COMPONENT_PADDING
        ssf = 2  # Super-sampling factor
        image = Image.new("RGB", (body_width*ssf, body_height*ssf))
        draw = ImageDraw.Draw(image)

        body_font = Fonts.get_font(GUIConstants.get_body_font_name(), (GUIConstants.get_body_font_size())*ssf)
        fixed_width_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, (GUIConstants.get_body_font_size() + 6)*ssf)
        left, top, right, bottom  = fixed_width_font.getbbox(self.input_amount + "+")
        digits_width, digits_height = right - left, bottom - top

        # Draw each line of the equation
        cur_y = 0

        def render_amount(cur_y, amount_str, info_text, info_text_color=GUIConstants.BODY_FONT_COLOR):
            secondary_digit_color = "#888"
            tertiary_digit_color = "#666"
            digit_group_spacing = 2 * ssf
            # secondary_digit_color = GUIConstants.BODY_FONT_COLOR
            # tertiary_digit_color = GUIConstants.BODY_FONT_COLOR
            # digit_group_spacing = 0
            if denomination == _('btc'):
                display_str = amount_str
                main_zone = display_str[:-6]
                mid_zone = display_str[-6:-3]
                end_zone = display_str[-3:]
                left, top, right, bottom  = fixed_width_font.getbbox(main_zone)
                main_zone_width, th = right - left, bottom - top
                left, top, right, bottom  = fixed_width_font.getbbox(end_zone)
                mid_zone_width, th = right - left, bottom - top
                draw.text((0, cur_y), text=main_zone, font=fixed_width_font, fill=GUIConstants.BODY_FONT_COLOR)
                draw.text((main_zone_width + digit_group_spacing, cur_y), text=mid_zone, font=fixed_width_font, fill=secondary_digit_color)
                draw.text((main_zone_width + digit_group_spacing + mid_zone_width + digit_group_spacing, cur_y), text=end_zone, font=fixed_width_font, fill=tertiary_digit_color)
            else:
                draw.text((0, cur_y), text=amount_str, font=fixed_width_font, fill=GUIConstants.BODY_FONT_COLOR)
            draw.text((digits_width + 3*digit_group_spacing, cur_y), text=info_text, font=body_font, fill=info_text_color)

        render_amount(
            cur_y,
            f" {self.input_amount}",
            info_text=ngettext("input", "inputs", self.num_inputs),
        )

        # spend_amount will be zero on self-transfers; only display when there's an
        # external recipient.
        if self.num_recipients > 0:
            cur_y += digits_height + GUIConstants.BODY_LINE_SPACING * ssf
            render_amount(
                cur_y,
                f"-{self.spend_amount}",
                info_text=ngettext("recipient", "recipients", self.num_recipients),
            )

        # Burned sats get their own line so the numbers on screen still add up to the
        # inputs. They are neither spend nor change, so they can't be folded into either.
        if shows_burned_amount:
            cur_y += digits_height + GUIConstants.BODY_LINE_SPACING * ssf
            render_amount(
                cur_y,
                f"-{self.op_return_amount}",
                # TRANSLATOR_NOTE: Sats destroyed by an OP_RETURN output; sits alongside "recipients", "fee", and "change" in the transaction's arithmetic
                info_text=_("burned") + " (!)",
                info_text_color=GUIConstants.DIRE_WARNING_COLOR,
            )

        cur_y += digits_height + GUIConstants.BODY_LINE_SPACING * ssf

        info_text = _("fee")
        info_text_color = GUIConstants.BODY_FONT_COLOR
        if self.is_high_fee_tx:
            info_text += PSBTOverviewScreen.WARNING_MARK
            info_text_color = GUIConstants.DIRE_WARNING_COLOR
        render_amount(
            cur_y,
            f"-{self.fee_amount}",
            info_text=info_text,
            info_text_color=info_text_color,
        )

        cur_y += digits_height + GUIConstants.BODY_LINE_SPACING * ssf
        draw.line((0, cur_y, image.width, cur_y), fill=GUIConstants.BODY_FONT_COLOR, width=1)
        cur_y += GUIConstants.BODY_LINE_SPACING * ssf

        render_amount(
            cur_y,
            f" {self.change_amount}",
            # TRANSLATOR_NOTE: Denonination is inserted (e.g. your "btc change" or "sats change")
            info_text=_("{} change").format(denomination),
            info_text_color="darkorange"  # super-sampling alters the perceived color
        )

        # Resize to target and sharpen final image
        image = image.resize((body_width, body_height), Image.Resampling.LANCZOS)
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

        btc_amount = BtcAmount(
            image_draw=draw,
            canvas=center_img,
            total_sats=self.amount,
            screen_y=int(GUIConstants.COMPONENT_PADDING/2),
        )

        formatted_address = FormattedAddress(
            image_draw=draw,
            canvas=center_img,
            width=self.canvas_width - 2*GUIConstants.EDGE_PADDING,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=btc_amount.height + GUIConstants.COMPONENT_PADDING,
            font_size=24,
            address=self.address,
        )

        # Render each to the temp img we passed in
        btc_amount.render()
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

        self.components.append(BtcAmount(
            total_sats=self.amount,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
        ))

        screen_y = self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING

        if self.is_change_derivation_path :
            # TRANSLATOR_NOTE: Describes the address type (change or receive)
            addr_type = _("change address")
        else: 
            addr_type = _("receive address")

        # TRANSLATOR_NOTE: Symbol for index number, e.g. "address #3"
        index_num_symbol = _("#")

        # note: NOT marking this for translation, hoping that the var ordering will not
        # need to change in other languages.
        value_text = f"{addr_type} {index_num_symbol}{self.derivation_path_addr_index}"
        self.components.append(TextArea(
            text=value_text,
            font_color=GUIConstants.LABEL_FONT_COLOR,
            font_size=GUIConstants.LABEL_FONT_SIZE,
            is_text_centered=True,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=screen_y,
        ))

        self.components.append(FormattedAddress(
            screen_y=self.components[-1].screen_y + self.components[-1].height,
            address=self.address,
            max_lines=1,
        ))

        if self.is_change_addr_verified:
            # How much empty space is left between the bottom of the addr and the first button?
            available_y = self.buttons[0].screen_y - (self.components[-1].screen_y + self.components[-1].height)

            self.components.append(IconTextLine(
                icon_name=SeedSignerIconConstants.SUCCESS,
                icon_color=GUIConstants.SUCCESS_COLOR,
                value_text=_("Address verified!"),
                is_text_centered=True,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=self.components[-1].screen_y + self.components[-1].height,
                height=available_y,  # Let the component auto-center vertically
            ))



@dataclass
class PSBTOpReturnScreen(ButtonListScreen):
    """
        Shows one page of one OP_RETURN output's payload.

        Payloads can be any size, so PSBTOpReturnView splits them into pages and tells
        this screen which page to draw, along with the payload's real size and whether
        any of it had to be left out. When something isn't being shown, the screen says
        so, so a cut-short payload never passes for the whole thing.
    """
    page_text: str = ""
    is_hex: bool = False
    total_bytes: int = 0
    amount: int = 0
    page_num: int = 0
    num_pages: int = 1
    bytes_shown: int = 0
    is_truncated: bool = False

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True

        super().__post_init__()

        screen_y = self.top_nav.height

        # The label says what the user can't tell from the page itself: that it's hex,
        # the full size, that it was cut short, which page this is. Readable text that
        # fits on one screen has nothing to say and gets no label, as before.
        qualifiers = []
        is_last_page = self.page_num == self.num_pages - 1

        if self.is_truncated and is_last_page:
            # This is the page where the data runs out. Without this line, the last page
            # of a cut-short payload would look just like the last page of a complete one.
            # TRANSLATOR_NOTE: How much of an OP_RETURN payload could not be displayed. "not_shown" and "total" are byte counts (e.g. "3,456 of 4,096 bytes not shown")
            qualifiers.append(_("{not_shown} of {total} bytes not shown").format(
                not_shown=f"{self.total_bytes - self.bytes_shown:,}", total=f"{self.total_bytes:,}"))

        elif self.num_pages > 1 or self.is_truncated:
            # TRANSLATOR_NOTE: Size of an OP_RETURN payload. "num_bytes" is the byte count (e.g. "300 bytes")
            qualifiers.append(_("{num_bytes} bytes").format(num_bytes=f"{self.total_bytes:,}"))

        if self.is_hex:
            # TRANSLATOR_NOTE: Shown when displaying OP_RETURN as non-human-readable hexadecimal data
            qualifiers.append(_("raw hex data"))

        if self.is_truncated and not is_last_page:
            # TRANSLATOR_NOTE: The OP_RETURN payload is too large to show all of
            qualifiers.append(_("truncated"))

        if qualifiers:
            size_text = ", ".join(qualifiers)
            if self.num_pages > 1 and not (self.is_truncated and is_last_page):
                # TRANSLATOR_NOTE: Which page of an OP_RETURN payload is on screen. "page" is the current page, "num_pages" the total (e.g. "2 of 5")
                size_text += "  " + _("{page} of {num_pages}").format(page=self.page_num + 1, num_pages=self.num_pages)

            self.components.append(TextArea(
                text=size_text,
                # Hidden data gets the warning color; the dire color is kept for burned sats.
                font_color=(GUIConstants.WARNING_COLOR if self.is_truncated
                    else GUIConstants.LABEL_FONT_COLOR),
                font_size=GUIConstants.LABEL_FONT_SIZE,
                screen_y=screen_y,
            ))
            screen_y = self.components[-1].screen_y + self.components[-1].height

        # Say that the sats are burned here too, not just on the totals screens. No "(!)"
        # on this one: that mark is for picking out a row on the screens that list every
        # output, and this screen is only ever about one.
        if self.amount > 0:
            self.components.append(TextArea(
                # TRANSLATOR_NOTE: An OP_RETURN output destroys any value sent to it. "amount" is in sats (e.g. "burns 10,000 sats")
                text=_("burns {amount} sats").format(amount=f"{self.amount:,}"),
                font_color=GUIConstants.DIRE_WARNING_COLOR,
                font_size=GUIConstants.LABEL_FONT_SIZE,
                screen_y=screen_y,
            ))
            screen_y = self.components[-1].screen_y + self.components[-1].height

        screen_y += GUIConstants.COMPONENT_PADDING

        if self.total_bytes == 0:
            # A bare OP_RETURN carries no data. Say so rather than leave the screen blank,
            # which would look like a rendering bug.
            self.components.append(TextArea(
                text=_("(no data)"),
                font_color=GUIConstants.LABEL_FONT_COLOR,
                screen_y=screen_y,
                height=self.buttons[0].screen_y - screen_y - GUIConstants.COMPONENT_PADDING,
            ))
            return

        if not self.is_hex:
            # Simple case: display human-readable text
            self.components.append(TextArea(
                text=self.page_text,
                font_size=GUIConstants.get_top_nav_title_font_size(),
                is_text_centered=True,
                screen_y=screen_y,
                height=self.buttons[0].screen_y - screen_y - GUIConstants.COMPONENT_PADDING,
            ))
            return

        # Contains data that can't be converted to UTF-8; probably encoded and not
        # meant to be human readable.
        font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, size=GUIConstants.get_body_font_size())
        (left, top, right, bottom) = font.getbbox("X", anchor="ls")
        chars_per_line = int((self.canvas_width - 2*GUIConstants.EDGE_PADDING) / (right - left))
        num_lines = math.ceil(len(self.page_text) / chars_per_line)
        text = ""
        for i in range(num_lines):
            text += (self.page_text[i*chars_per_line:(i+1)*chars_per_line]) + "\n"
        text = text[:-1]

        self.components.append(TextArea(
            text=text,
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_size=GUIConstants.get_body_font_size(),
            screen_y=screen_y,
        ))


@dataclass
class PSBTFinalizeScreen(ButtonListScreen):
    def __post_init__(self):
        # Customize defaults
        self.title = _("Sign Transaction")
        self.is_bottom_list = True
        super().__post_init__()

        icon = Icon(
            icon_name=SeedSignerIconConstants.SIGN,
            icon_color=GUIConstants.INFO_COLOR,
            icon_size=GUIConstants.ICON_LARGE_BUTTON_SIZE,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        icon.screen_x = int((self.canvas_width - icon.width)/2)
        self.components.append(icon)

        self.components.append(TextArea(
            text=_("Click to approve this transaction"),
            screen_y=icon.screen_y + icon.height + 2*GUIConstants.COMPONENT_PADDING
        ))
