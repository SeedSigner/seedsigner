from PIL import Image

from seedsigner.helpers import bitsquiggle32


def fingerprint_to_image(fingerprint: str, scale: int = None, max_width: int = None, max_height: int = None,
                          max_scale: int = None, style: str = bitsquiggle32.STANDARD) -> Image.Image:
    """
    Renders a BitSquiggle32 visualization (see https://github.com/maggo83/BitSquiggles)
    for the given hex master fingerprint, as an exact nearest-neighbor-scaled
    RGB image. Lets a user visually compare the fingerprint shown on-device
    against the same fingerprint shown in a companion wallet app, without
    having to carefully read and match hex characters.

    Either `scale` or a `(max_width, max_height)` bounding box must be supplied;
    when a bounding box is given, the largest integer scale that fits is used
    (the raster is always rendered pixel-exact, never interpolated). `max_scale`
    additionally caps that fit so the glyph stays a small, icon-sized accent
    instead of ballooning to fill whatever space happens to be free.
    """
    if scale is None:
        if max_width is None or max_height is None:
            raise ValueError("must supply either scale or max_width and max_height")
        scale = max(1, min(max_width // bitsquiggle32.PIXEL_WIDTH, max_height // bitsquiggle32.PIXEL_HEIGHT))
    if max_scale is not None:
        scale = min(scale, max_scale)

    bits = int(fingerprint, 16)
    grid = bitsquiggle32.pixels(bits, style=style)

    image = Image.new("RGB", (grid["width"], grid["height"]))
    background = grid["background"]["hex"]
    foreground = grid["foreground"]["hex"]
    pixel_data = grid["pixels"]
    for row in range(grid["height"]):
        for column in range(grid["width"]):
            color = foreground if pixel_data[row * grid["width"] + column] else background
            image.putpixel((column, row), tuple(int(color[i:i + 2], 16) for i in (1, 3, 5)))

    if scale != 1:
        image = image.resize((grid["width"] * scale, grid["height"] * scale), Image.Resampling.NEAREST)

    return image
