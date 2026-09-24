import random

import numpy as np
import pytest
from PIL import Image, ImageDraw

from seedsigner.helpers import dice_grid_reader as reader


"""
    End-to-end checks of the dice grid reader on synthetic photos: the printed sheet's
    markers and frame, 100 dice packed edge to edge with known faces, seen through a
    tilted camera. Real photos are much messier (glare, shadows, dice slightly out of
    line); these tests pin down geometry, orientation and face patterns.
"""

PX_PER_MM = 4.0
DIE_COLORS = [
    # (body, pips)
    ((245, 245, 240), (20, 20, 20)),      # white with black pips
    ((200, 30, 40), (250, 250, 250)),     # red with white pips
    ((30, 60, 170), (250, 250, 250)),     # blue with white pips
    ((25, 25, 25), (240, 240, 240)),      # black with white pips
    ((240, 200, 40), (250, 250, 250)),    # yellow with white pips
]
PIP_POINTS = {
    1: [(1, 1)],
    2: [(0, 0), (2, 2)],
    3: [(0, 0), (1, 1), (2, 2)],
    4: [(0, 0), (0, 2), (2, 0), (2, 2)],
    5: [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)],
    6: [(0, 0), (1, 0), (2, 0), (0, 2), (1, 2), (2, 2)],
}


def render_sheet(rolls: list[int], seed: int = 0) -> Image.Image:
    """ A flat, top-down rendering of the sheet with dice on it, in sheet orientation. """
    rng = random.Random(seed)
    margin_mm = 25
    width_mm = reader.GRID_MM + 2 * margin_mm
    height_mm = reader.GRID_MM + 2 * (reader.MARKER_GAP_MM + reader.MARKER_MM) + 2 * margin_mm
    image = Image.new("RGB", (int(width_mm * PX_PER_MM), int(height_mm * PX_PER_MM)), (235, 235, 230))
    draw = ImageDraw.Draw(image)
    origin = (margin_mm, margin_mm + reader.MARKER_GAP_MM + reader.MARKER_MM)

    def px(x_mm, y_mm):
        return ((origin[0] + x_mm) * PX_PER_MM, (origin[1] + y_mm) * PX_PER_MM)

    # Markers: black border, inner bits as printed (1 = white)
    module_mm = reader.MARKER_MM / reader.MARKER_MODULES
    for marker_id, (mx, my) in reader.MARKER_ORIGINS_MM.items():
        draw.rectangle((*px(mx, my), *px(mx + reader.MARKER_MM, my + reader.MARKER_MM)), fill=(0, 0, 0))
        for r, bits in enumerate(reader.MARKER_BITS[marker_id]):
            for c, bit in enumerate(bits):
                if bit == "1":
                    x0, y0 = mx + (c + 1) * module_mm, my + (r + 1) * module_mm
                    draw.rectangle((*px(x0, y0), *px(x0 + module_mm, y0 + module_mm)), fill=(255, 255, 255))

    # Frame outline
    draw.rectangle((*px(0, 0), *px(reader.GRID_MM, reader.GRID_MM)), outline=(80, 80, 80), width=2)

    # Dice packed edge to edge from the frame's top-left, with shaded seams between them
    die = reader.DIE_MM
    for index, roll in enumerate(rolls):
        row, col = divmod(index, reader.GRID_SIZE)
        x0, y0 = 0.5 + col * die, 0.5 + row * die
        draw.rectangle((*px(x0, y0), *px(x0 + die, y0 + die)), fill=(60, 60, 60))
        body, pip = DIE_COLORS[rng.randrange(len(DIE_COLORS))]
        draw.rounded_rectangle((*px(x0 + 0.4, y0 + 0.4), *px(x0 + die - 0.4, y0 + die - 0.4)), radius=2 * PX_PER_MM, fill=body)
        points = PIP_POINTS[roll]
        if roll in (2, 3, 6) and rng.random() < 0.5:
            # The same face turned a quarter turn
            points = [(c, 2 - r) for r, c in points]
        for r, c in points:
            cx, cy = px(x0 + die * (0.27 + 0.23 * c), y0 + die * (0.27 + 0.23 * r))
            radius = die * 0.09 * PX_PER_MM
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=pip)
    return image


def photograph(sheet: Image.Image, rotate: int = 0, tilt: float = 0.06) -> Image.Image:
    """ View the sheet through a mild perspective, optionally turned in the frame. """
    w, h = sheet.size
    # Output corners for the sheet's corners (TL, TR, BR, BL): a keystone, as from a
    # camera tilted toward the top of the sheet.
    out_w, out_h = int(w * 1.1), int(h * 1.1)
    dst = np.array([
        [w * (0.05 + tilt), h * 0.05],
        [w * (1.05 - tilt), h * 0.05],
        [w * 1.05, h * 1.05],
        [w * 0.05, h * 1.05],
    ])
    src = np.array([[0, 0], [w, 0], [w, h], [0, h]])
    sheet_from_photo = reader.fit_homography(dst, src)
    coefficients = tuple((sheet_from_photo / sheet_from_photo[2, 2]).flatten()[:8])
    photo = sheet.transform((out_w, out_h), Image.Transform.PERSPECTIVE, coefficients, Image.Resampling.BILINEAR, fillcolor=(40, 40, 40))
    return photo.rotate(rotate, expand=True, fillcolor=(40, 40, 40))


@pytest.fixture(scope="module")
def rolls():
    rng = random.Random(42)
    return [rng.randint(1, 6) for _ in range(reader.GRID_SIZE ** 2)]


@pytest.mark.parametrize("rotate", [0, 90, 180, 270])
def test_reads_every_die_in_any_orientation(rolls, rotate):
    """ Markers fix the orientation: roll 1 is always the die by marker 0. """
    photo = photograph(render_sheet(rolls), rotate=rotate)
    reading = reader.read_dice_grid(photo)
    assert reading.rolls == rolls


def test_every_face_in_both_quarter_turns():
    """ 2, 3 and 6 look different turned a quarter turn; both must read. """
    faces = [1, 2, 3, 4, 5, 6] * 16 + [1, 2, 3, 4]
    for seed in range(2):
        reading = reader.read_dice_grid(photograph(render_sheet(faces, seed=seed)))
        assert reading.rolls == faces


def test_missing_markers_raise():
    blank = Image.new("RGB", (800, 1000), (230, 230, 230))
    with pytest.raises(reader.MarkersNotFound):
        reader.read_dice_grid(blank)


def test_three_markers_are_enough(rolls):
    sheet = render_sheet(rolls)
    # Cover marker 2 (bottom right)
    draw = ImageDraw.Draw(sheet)
    mx, my = reader.MARKER_ORIGINS_MM[2]
    left = (25 + mx - 2) * PX_PER_MM
    top = (25 + reader.MARKER_GAP_MM + reader.MARKER_MM + my - 2) * PX_PER_MM
    draw.rectangle((left, top, left + (reader.MARKER_MM + 4) * PX_PER_MM, top + (reader.MARKER_MM + 4) * PX_PER_MM), fill=(235, 235, 230))
    assert sorted(reader.find_markers(np.asarray(photograph(sheet).convert("L"), dtype=np.float32))) == [0, 1, 3]
    assert reader.read_dice_grid(photograph(sheet)).rolls == rolls


def test_empty_cell_reads_zero_and_uncertain(rolls):
    sheet = render_sheet(rolls)
    # Cover one die with plain paper
    draw = ImageDraw.Draw(sheet)
    origin_y = 25 + reader.MARKER_GAP_MM + reader.MARKER_MM
    x0, y0 = (25 + 0.5 + 3 * reader.DIE_MM) * PX_PER_MM, (origin_y + 0.5 + 4 * reader.DIE_MM) * PX_PER_MM
    draw.rectangle((x0, y0, x0 + reader.DIE_MM * PX_PER_MM, y0 + reader.DIE_MM * PX_PER_MM), fill=(235, 235, 230))
    reading = reader.read_dice_grid(photograph(sheet))
    assert reading.rolls[43] == 0
    assert reading.uncertain[43]


def test_classify_face_patterns():
    """ Each face's own pattern wins, whichever way a pip-shaped contrast falls. """
    for value, patterns in reader.FACE_PATTERNS.items():
        for pattern in patterns:
            contrasts = np.array([100.0 if i in pattern else 5.0 for i in range(9)])
            assert reader.classify_face(contrasts)[0] == value


def test_fit_homography_recovers_known_mapping():
    h = np.array([[1.2, 0.1, 30], [-0.05, 0.9, 12], [0.0004, -0.0002, 1]])
    src = np.array([[0, 0], [100, 0], [100, 80], [0, 80], [50, 40], [20, 70]], dtype=float)
    dst = reader.apply_homography(h, src)
    fitted = reader.fit_homography(src, dst)
    assert np.allclose(reader.apply_homography(fitted, src), dst, atol=1e-6)
