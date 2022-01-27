import dataclasses
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from typing import List

from .screen import BaseTopNavScreen, ButtonListScreen
from ..components import (BaseComponent, GUIConstants, Fonts, IconTextLine, TextArea,
    calc_text_centering, calc_bezier_curve)



@dataclass
class PSBTOverviewScreen(ButtonListScreen):
    title: str = "Review PSBT"
    is_bottom_list: bool = True
    spend_amount: int = 0
    change_amount: int = 0
    fee_amount: int = 0
    num_inputs: int = 0
    destination_addresses: List[str] = None
    

    def __post_init__(self):
        # Customize defaults
        self.button_data = ["Next"]

        super().__post_init__()

        self.components: List[BaseComponent] = []

        # # Prep the "spend:" label
        # self.components.append(TextArea(
        #     text="spend:",
        #     screen_y=self.top_nav.height - GUIConstants.COMPONENT_PADDING,
        #     font_size=GUIConstants.LABEL_FONT_SIZE,
        #     font_color=GUIConstants.LABEL_FONT_COLOR,
        #     is_text_centered=True,
        #     auto_line_break=False,
        # ))

        # Prep the headline amount being spent in large callout
        # icon_text_lines_y = self.components[-1].screen_y + self.components[-1].height
        icon_text_lines_y = self.top_nav.height
        self.components.append(IconTextLine(
            icon_name="btc_logo_30x30",
            is_text_centered=True,
            value_text=f" {self.spend_amount:,} sats",
            font_size=24,
            screen_x=GUIConstants.COMPONENT_PADDING,
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

        association_line_color = "#999"
        association_line_width = ssf
        # chart_font_color = GUIConstants.BODY_FONT_COLOR
        chart_font_color = "#ddd"
        
        # First calculate how wide the inputs col will be
        inputs_column = []
        if self.num_inputs == 1:
            inputs_column.append("1 input")
        elif self.num_inputs > 5:
            inputs_column.append("input 1")
            inputs_column.append("input 2")
            # inputs_column.append("     [ ... ]")
            inputs_column.append("     [ ... ]")
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
            int(GUIConstants.COMPONENT_PADDING*ssf/2) + curve_width + \
                center_bar_width + \
                    curve_width + int(GUIConstants.COMPONENT_PADDING*ssf/2) + \
                        GUIConstants.EDGE_PADDING*ssf)
        
        if self.num_inputs == 1:
            # Use up more of the space on the input side
            max_destination_col_width += curve_width
        
        print(f"max_destination_col_width: {max_destination_col_width}")

        # Now let's maximize the actual destination col by adjusting our addr truncation
        def calculate_destination_col_width(truncate_at: int):
            def truncate_destination_addr(addr):
                return f"{addr[:truncate_at]}..."
            
            destination_column = []

            if not self.destination_addresses:
                # This is an internal transfer; no external addresses
                destination_column.append(f"self transfer")

            elif len(self.destination_addresses) <= 3:
                for addr in self.destination_addresses:
                    destination_column.append(truncate_destination_addr(addr))
            else:
                # destination_column.append(f"{len(self.destination_addresses)} recipients")
                destination_column.append(f"recipient 1")
                destination_column.append(f"[ ... ]")
                destination_column.append(f"recipient {len(self.destination_addresses)}")

            if self.change_amount > 0 and self.destination_addresses:
                destination_column.append("change")

            destination_column.append(f"fee: {self.fee_amount:,}")

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
                    print(f"new_width: {new_width}")
                    break
                destination_text_width = new_width
                destination_column = new_col_text

        destination_col_x = image.width - (destination_text_width + GUIConstants.EDGE_PADDING*ssf)

        # Now we can finalize our center bar values
        center_bar_x = GUIConstants.EDGE_PADDING*ssf + max_inputs_text_width + int(GUIConstants.COMPONENT_PADDING*ssf/2) + curve_width

        # Center bar stretches to fill any excess width
        center_bar_width = (destination_col_x - int(GUIConstants.COMPONENT_PADDING*ssf/2) - curve_width) - center_bar_x 

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

        for input in inputs_column:
            draw.text(
                (inputs_x, inputs_y),
                text=input,
                font=font,
                fill=chart_font_color,
            )

            # Render the association line from the conjunction point
            # First calculate a bezier curve to an inflection point
            start_pt = (
                inputs_x + max_inputs_text_width + int(GUIConstants.COMPONENT_PADDING/2)*ssf,
                inputs_y + int(chart_text_height/2)
            )
            conjunction_pt = (inputs_conjunction_x, vertical_center)
            mid_pt = (
                int(start_pt[0]*0.5 + conjunction_pt[0]*0.5), 
                int(start_pt[1]*0.5 + conjunction_pt[1]*0.5)
            )
            bezier_points = calc_bezier_curve(
                start_pt,
                (mid_pt[0], start_pt[1]),
                mid_pt,
                4
            )
            # We don't need the "final" point as it's repeated below
            bezier_points.pop()

            # Now render the second half after the inflection point
            curve_bias = 1.0
            bezier_points += calc_bezier_curve(
                mid_pt,
                (int(mid_pt[0]*curve_bias + conjunction_pt[0]*(1.0-curve_bias)), conjunction_pt[1]),
                conjunction_pt,
                4
            )

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
                4
            )
            # We don't need the "final" point as it's repeated below
            bezier_points.pop()

            # Now render the second half after the inflection point
            curve_bias = 1.0
            bezier_points += calc_bezier_curve(
                mid_pt,
                (int(mid_pt[0]*curve_bias + end_pt[0]*(1.0-curve_bias)), end_pt[1]),
                end_pt,
                4
            )

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
        self.chart_img = image.filter(ImageFilter.SHARPEN)


    def _render(self):
        super()._render()

        for component in self.components:
            component.render()

        self.canvas.paste(self.chart_img, (self.chart_x, self.chart_y))

        # Write the screen updates
        self.renderer.show_image()
