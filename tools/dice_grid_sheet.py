import argparse
import os

from PIL import Image, ImageDraw, ImageFont

from seedsigner.helpers import dice_grid_reader as sheet

"""
Writes the printable dice grid sheet for SeedSigner's "24 words (scan grid)" option:
a frame for 100 dice pushed together into a 10x10 block, with the corner markers the
camera needs. All geometry comes from dice_grid_reader, so the sheet always matches
what the reader expects.

tldr:
    pip3 install -e .
    cd tools
    python3 dice_grid_sheet.py dice_grid_letter.pdf --paper letter
    python3 dice_grid_sheet.py dice_grid_a4.pdf --paper a4

Print at 100% / "Actual size" and check the 100 mm bar with a ruler.
"""

PAPER_MM = {"letter": (215.9, 279.4), "a4": (210.0, 297.0)}
DPI = 600
FONT_DIR = os.path.join(os.path.dirname(sheet.__file__), "..", "resources", "fonts")


def make_sheet(paper: str) -> Image.Image:
    page_w, page_h = PAPER_MM[paper]
    px_per_mm = DPI / 25.4
    image = Image.new("L", (round(page_w * px_per_mm), round(page_h * px_per_mm)), 255)
    draw = ImageDraw.Draw(image)

    # Sheet mm (frame top-left origin, y down) -> image pixels, with the markers and
    # frame centered on the page.
    content_h = sheet.GRID_MM + 2 * (sheet.MARKER_GAP_MM + sheet.MARKER_MM)
    origin_x = (page_w - sheet.GRID_MM) / 2
    origin_y = (page_h - content_h) / 2 + sheet.MARKER_GAP_MM + sheet.MARKER_MM

    def px(x_mm, y_mm):
        return (round((origin_x + x_mm) * px_per_mm), round((origin_y + y_mm) * px_per_mm))

    def line_width(mm):
        return max(1, round(mm * px_per_mm))

    def font(size_mm, bold=False):
        name = "OpenSans-SemiBold.ttf" if bold else "OpenSans-Regular.ttf"
        return ImageFont.truetype(os.path.join(FONT_DIR, name), round(size_mm * px_per_mm))

    def text(x_mm, y_mm, s, size_mm=2.8, fill=70, bold=False):
        draw.text(px(x_mm, y_mm), s, fill=fill, font=font(size_mm, bold), anchor="ms")

    # The frame. The dice cover the inside, so there are no interior lines; short
    # ticks outside the frame mark the rows and columns.
    grid = sheet.GRID_MM
    cell = grid / sheet.GRID_SIZE
    draw.rectangle((*px(0, 0), *px(grid, grid)), outline=70, width=line_width(0.6))
    for i in range(1, sheet.GRID_SIZE):
        t = i * cell
        for a, b in (((t, 0), (t, -1.5)), ((0, t), (-1.5, t)), ((t, grid), (t, grid + 1.5)), ((grid, t), (grid + 1.5, t))):
            draw.line((*px(*a), *px(*b)), fill=140, width=line_width(0.3))
    for i in range(sheet.GRID_SIZE):
        middle = (i + 0.5) * cell
        text(middle, -2.2, str(i + 1), size_mm=2.4)
        draw.text(px(-2.5, middle), str(i + 1), fill=70, font=font(2.4), anchor="rm")

    # Markers, module by module
    module = sheet.MARKER_MM / sheet.MARKER_MODULES
    for marker_id, (mx, my) in sheet.MARKER_ORIGINS_MM.items():
        draw.rectangle((*px(mx, my), *px(mx + sheet.MARKER_MM, my + sheet.MARKER_MM)), fill=0)
        for r, bits in enumerate(sheet.MARKER_BITS[marker_id]):
            for c, bit in enumerate(bits):
                if bit == "1":
                    x0, y0 = mx + (c + 1) * module, my + (r + 1) * module
                    draw.rectangle((*px(x0, y0), *px(x0 + module, y0 + module)), fill=255)

    # Instructions, between the top markers
    top = -sheet.MARKER_GAP_MM - sheet.MARKER_MM
    text(grid / 2, top + 6, f"SEEDSIGNER DICE GRID  -  10 x 10, {sheet.DIE_MM:g} mm dice", size_mm=3.6, fill=0, bold=True)
    text(grid / 2, top + 11.5, "Push 100 dice together into one square block inside the frame.")
    text(grid / 2, top + 15.5, "The first 99, read left to right from the top, make the seed.")

    # Scale check bar, between the bottom markers
    bar_y = grid + sheet.MARKER_GAP_MM + 8
    bar_x = (grid - 100) / 2
    draw.rectangle((*px(bar_x, bar_y), *px(bar_x + 100, bar_y + 1.2)), fill=0)
    for t in range(0, 101, 10):
        draw.line((*px(bar_x + t, bar_y - (2.5 if t % 50 == 0 else 1.5)), *px(bar_x + t, bar_y)), fill=0, width=line_width(0.3))
    text(grid / 2, bar_y + 5, 'This bar must measure exactly 100 mm. Print at 100% / "Actual size".', size_mm=2.5)
    text(grid / 2, bar_y + 9.5, f"{paper.upper()}  -  frame {grid:g} mm  -  markers {sheet.MARKER_MM:g} mm", size_mm=2.1, fill=140)

    # Corner marks near the page edges. Without them the ink sits in the middle of
    # the page, and print paths that trim whitespace and fit to the paper enlarge
    # the sheet by ~15%.
    inset, arm = 8.0, 5.0
    for cx, sx in ((inset, 1), (page_w - inset, -1)):
        for cy, sy in ((inset, 1), (page_h - inset, -1)):
            corner = (round(cx * px_per_mm), round(cy * px_per_mm))
            draw.line((*corner, round((cx + sx * arm) * px_per_mm), corner[1]), fill=140, width=line_width(0.3))
            draw.line((*corner, corner[0], round((cy + sy * arm) * px_per_mm)), fill=140, width=line_width(0.3))

    return image


def main():
    parser = argparse.ArgumentParser(description="Write the printable SeedSigner dice grid sheet as a PDF.")
    parser.add_argument("out", help="output PDF path")
    parser.add_argument("--paper", choices=sorted(PAPER_MM), default="letter")
    args = parser.parse_args()

    # The PDF page size comes from the image size at DPI, so it prints at true scale.
    make_sheet(args.paper).save(args.out, resolution=DPI)
    print(f"Wrote {args.out} ({args.paper})")


if __name__ == "__main__":
    main()
