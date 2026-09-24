"""
Reads a photo of 100 dice packed into a 10x10 block on the printed dice grid sheet.

The sheet has a square frame for the dice and an ArUco 4x4 marker (IDs 0-3) above and
below each frame corner. Reading a photo takes five steps:

1. Find the markers. They fix the sheet's position and orientation in the photo.
2. Recover the camera pose from the markers. The pips are on the dice tops, one die
   height above the paper. Those tops are closer to the camera, so they look larger and
   pushed away from the point under the lens. The pose lets us locate the frame on that
   raised plane instead of on the paper.
3. Snap the grid onto the dice. The dark seams between packed dice are found and a
   regular 10x10 lattice is fitted to them. This absorbs errors in die height, focal
   length and where the block sits in the frame.
4. Snap each cell onto its own die, since packed dice never line up perfectly.
5. Read each die. Once a cell is aligned with its die, pips can only sit at the 9
   points of a 3x3 layout. Each face value is one pattern of those points, so the die
   reads as whichever pattern best separates pips from die body. Dark pips on light
   dice and light pips on dark or colored dice are both handled.

Only numpy and Pillow are used, since those are what the device has.

The sheet geometry below must match the printed sheet.
"""
from dataclasses import dataclass, field

import numpy as np
from PIL import Image


GRID_SIZE = 10
DIE_MM = 16.0                             # nominal die edge, and so the height of the dice tops
SLACK_MM = 2.0                            # frame allowance for dice running over nominal
GRID_MM = GRID_SIZE * DIE_MM + SLACK_MM   # 162 mm square frame
MARKER_MM = 20.0                          # marker edge, including its black border
MARKER_GAP_MM = 8.0                       # frame edge to marker edge

# Marker ID -> top-left corner of that marker, in sheet mm. The origin is the frame's
# top-left corner, x to the right and y down the page.
_MARKER_TOP = -MARKER_GAP_MM - MARKER_MM
_MARKER_BOTTOM = GRID_MM + MARKER_GAP_MM
MARKER_ORIGINS_MM = {
    0: (0.0, _MARKER_TOP),
    1: (GRID_MM - MARKER_MM, _MARKER_TOP),
    2: (GRID_MM - MARKER_MM, _MARKER_BOTTOM),
    3: (0.0, _MARKER_BOTTOM),
}

# Inner 4x4 bits of ArUco DICT_4X4_50 markers 0-3, row by row from the marker's
# top-left; 1 = white. Each marker is 6x6 modules: these bits inside a black border.
MARKER_BITS = {
    0: ("1011", "0101", "0011", "0010"),
    1: ("0000", "1111", "1001", "1010"),
    2: ("0011", "0011", "0010", "1101"),
    3: ("1001", "1001", "0100", "0110"),
}
MARKER_MODULES = 6

# Warped ("canonical") image scale: pixels per grid cell. 60 px keeps pips around
# 12 px across, plenty for the 3x3 pip layout, while staying quick on a Pi Zero.
CELL_PX = 60

# Pip layout: the 3x3 points where pips can sit, as fractions of the die face. Dice
# differ a little in pip spacing, and a die can sit a little off its cell, so the
# layout is tried at several spacings and shifted as a whole across the cell.
PIP_INSETS = (0.24, 0.27, 0.30)    # outer pip rows/columns, fraction in from the edge
PIP_SHIFT = 0.06                   # layout shift, up to this fraction of a cell. Keep it well
                                   # under half the pip spacing (~0.11): a larger shift lets
                                   # the center point slide onto any single pip and read a 1.
PIP_RADIUS = 0.06                  # averaging radius at each point, fraction of a cell

# Pip patterns on the 3x3 layout, indexed row * 3 + col. Faces 2, 3 and 6 look
# different when the die is turned a quarter turn, so they have two patterns each.
_CORNERS = {0, 2, 6, 8}
FACE_PATTERNS = {
    1: [{4}],
    2: [{0, 8}, {2, 6}],
    3: [{0, 4, 8}, {2, 4, 6}],
    4: [_CORNERS],
    5: [_CORNERS | {4}],
    6: [_CORNERS | {3, 5}, _CORNERS | {1, 7}],
}

# A die reads as uncertain when its best pattern separates pips from body by less
# than this fraction of the strongest pip contrast in the cell.
MIN_CONFIDENT_MARGIN = 0.25

# A cell whose strongest pip contrast is below this (0-255 scale) holds no die.
MIN_PIP_CONTRAST = 25



class DiceGridReadError(Exception):
    pass



class MarkersNotFound(DiceGridReadError):
    pass



@dataclass
class DiceGridReading:
    """
    rolls: 100 face values in reading order (left to right, top to bottom); 0 where
        no die could be read.
    uncertain: 100 flags; True where the reading deserves a human look.
    """
    rolls: list[int]
    uncertain: list[bool]
    # Diagnostics for development tools; not needed to use the reading.
    grid_corners: np.ndarray = field(default=None, repr=False)
    cell_offsets: np.ndarray = field(default=None, repr=False)



def read_dice_grid(image: Image.Image, focal_px: float = None) -> DiceGridReading:
    """
    Read the 100 dice in a photo of the dice grid sheet.

    focal_px is the camera's focal length in pixels at this image's resolution. When
    omitted, a typical ~53 degree horizontal field of view is assumed. It only has to
    be roughly right: the grid is snapped onto the dice afterwards.

    Raises MarkersNotFound if fewer than 3 of the 4 sheet markers are visible.
    """
    rgb = np.asarray(image.convert("RGB"))
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    height, width = gray.shape
    if focal_px is None:
        focal_px = 0.99 * max(width, height)

    markers = find_markers(gray)
    if len(markers) < 3:
        raise MarkersNotFound(f"Found sheet markers {sorted(markers)}; need at least 3 of 0-3")

    corners = locate_dice_tops(markers, focal_px, (width, height))
    corners = snap_grid_to_dice(rgb, corners)

    pad = int(round(CELL_PX * 0.15))
    warped = warp_grid(rgb, corners, pad)
    offsets = snap_cells(warped, pad)
    rolls, uncertain = read_cells(warped, pad, offsets)

    return DiceGridReading(
        rolls=rolls,
        uncertain=uncertain,
        grid_corners=corners,
        cell_offsets=offsets,
    )



"""****************************************************************************
    Geometry helpers
****************************************************************************"""
def fit_homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """ 3x3 homography mapping src points (Nx2, N >= 4) onto dst points, least squares. """
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)

    def normalizer(points):
        # Hartley normalization keeps the least-squares fit well conditioned.
        center = points.mean(axis=0)
        scale = np.sqrt(2) / max(np.sqrt(((points - center) ** 2).sum(axis=1)).mean(), 1e-9)
        return np.array([[scale, 0, -scale * center[0]], [0, scale, -scale * center[1]], [0, 0, 1]])

    t_src, t_dst = normalizer(src), normalizer(dst)
    s = apply_homography(t_src, src)
    d = apply_homography(t_dst, dst)
    rows = []
    for (x, y), (u, v) in zip(s, d):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vt = np.linalg.svd(np.array(rows))
    h = vt[-1].reshape(3, 3)
    h = np.linalg.inv(t_dst) @ h @ t_src
    return h / h[2, 2]



def apply_homography(h: np.ndarray, points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    ones = np.ones((len(points), 1))
    projected = np.hstack([points, ones]) @ h.T
    return projected[:, :2] / projected[:, 2:3]



def warp(image: np.ndarray, image_from_out: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """ Perspective-warp an image; image_from_out maps output pixels to image pixels. """
    h = image_from_out / image_from_out[2, 2]
    coefficients = tuple(h.flatten()[:8])
    mode = "RGB" if image.ndim == 3 else "L"
    pil_image = Image.fromarray(image.astype(np.uint8), mode)
    warped = pil_image.transform(size, Image.Transform.PERSPECTIVE, coefficients, Image.Resampling.BILINEAR)
    return np.asarray(warped)



def grid_corners_px(size: float) -> np.ndarray:
    return np.array([[0, 0], [size, 0], [size, size], [0, size]], dtype=np.float64)



def warp_grid(rgb: np.ndarray, corners: np.ndarray, pad: int) -> np.ndarray:
    """ The grid squared up at CELL_PX per cell, with pad pixels of surroundings. """
    side = GRID_SIZE * CELL_PX
    out_corners = grid_corners_px(side) + pad
    image_from_out = fit_homography(out_corners, corners)
    return warp(rgb, image_from_out, (side + 2 * pad, side + 2 * pad))



"""****************************************************************************
    Step 1: sheet markers
****************************************************************************"""
def find_markers(gray: np.ndarray) -> dict[int, np.ndarray]:
    """
    Find the sheet's markers. Returns {marker_id: 4x2 corners}, corners in the
    marker's own TL, TR, BR, BL order as printed, in image pixels.
    """
    # Candidates are found in a small copy of the image: markers are the largest
    # solid dark squares on the sheet, and labeling is much faster at low resolution.
    height, width = gray.shape
    scale = min(1.0, 480 / max(width, height))
    small = np.asarray(
        Image.fromarray(gray.astype(np.uint8)).resize(
            (max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.BOX
        ),
        dtype=np.float32,
    )
    dark = small < local_mean(small, max(small.shape) // 12) * 0.75
    min_side = 0.025 * max(small.shape)
    max_side = 0.25 * max(small.shape)

    markers = {}
    for top, left, bottom, right, filled in bounding_boxes(dark):
        box_w, box_h = right - left + 1, bottom - top + 1
        if not (min_side <= box_w <= max_side and min_side <= box_h <= max_side):
            continue
        if not (0.5 <= box_w / box_h <= 2.0):
            continue
        if not (0.3 <= filled / (box_w * box_h) <= 0.97):
            continue

        # Work on the candidate at full resolution, with a margin around it.
        margin = max(box_w, box_h) * 0.3
        roi = (
            max(0, int((left - margin) / scale)),
            max(0, int((top - margin) / scale)),
            min(width, int((right + 1 + margin) / scale) + 1),
            min(height, int((bottom + 1 + margin) / scale) + 1),
        )
        found = decode_marker(gray, roi)
        if found is not None:
            marker_id, corners = found
            markers.setdefault(marker_id, corners)
    return markers



def local_mean(image: np.ndarray, radius: int) -> np.ndarray:
    """ Mean over a (2*radius+1)^2 box around each pixel, edges clamped. """
    radius = max(1, int(radius))
    padded = np.pad(image.astype(np.float64), radius + 1, mode="edge")
    summed = padded.cumsum(axis=0).cumsum(axis=1)
    size = 2 * radius + 1
    total = (
        summed[size:, size:] - summed[:-size, size:] - summed[size:, :-size] + summed[:-size, :-size]
    )
    return (total / size ** 2)[: image.shape[0], : image.shape[1]].astype(np.float32)



def label_runs(mask: np.ndarray) -> tuple[list[int], list[int], list[int], list[int]]:
    """
    8-connected components of a boolean mask, labeled by runs of pixels rather than
    pixels, which keeps the pure Python part small. Returns parallel lists: each
    run's row, first column, last column and component label.
    """
    parent = []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    run_rows, run_starts, run_ends = [], [], []
    previous = []          # (start, end, run_index) in the row above
    for y in range(mask.shape[0]):
        row = mask[y]
        if not row.any():
            previous = []
            continue
        edges = np.flatnonzero(np.diff(np.concatenate(([0], row.view(np.int8), [0]))))
        current = []
        p = 0
        for start, end in zip(edges[::2].tolist(), (edges[1::2] - 1).tolist()):
            index = len(parent)
            parent.append(index)
            run_rows.append(y)
            run_starts.append(start)
            run_ends.append(end)
            # Skip runs above that end before this one starts (8-connected: +-1 px).
            while p < len(previous) and previous[p][1] < start - 1:
                p += 1
            q = p
            while q < len(previous) and previous[q][0] <= end + 1:
                a, b = find(previous[q][2]), find(index)
                if a != b:
                    parent[b] = a
                q += 1
            current.append((start, end, index))
        previous = current

    labels = [find(i) for i in range(len(parent))]
    return run_rows, run_starts, run_ends, labels



def bounding_boxes(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    """ 8-connected components of a boolean mask, as (top, left, bottom, right, pixel_count). """
    boxes = {}
    for y, start, end, label in zip(*label_runs(mask)):
        box = boxes.get(label)
        if box is None:
            boxes[label] = [y, start, y, end, end - start + 1]
        else:
            box[0] = min(box[0], y)
            box[1] = min(box[1], start)
            box[2] = max(box[2], y)
            box[3] = max(box[3], end)
            box[4] += end - start + 1
    return [tuple(box) for box in boxes.values()]



def decode_marker(gray: np.ndarray, roi: tuple[int, int, int, int]):
    """
    Try to read one of the sheet's markers inside roi (left, top, right, bottom).
    Returns (marker_id, 4x2 corners in printed TL, TR, BR, BL order) or None.
    """
    left, top, right, bottom = roi
    patch = gray[top:bottom, left:right]
    if patch.size == 0:
        return None
    threshold = otsu_threshold(patch)
    dark = patch < threshold

    # The marker is the largest dark component in the patch; its outline is the
    # marker's outer square, since the black border is solid.
    ys, xs = largest_component_pixels(dark)
    if len(xs) < 50:
        return None
    quad = quad_corners(xs.astype(np.float64), ys.astype(np.float64))
    if quad is None:
        return None
    quad += (left, top)

    # Sample every module center, trying each quad corner as the printed top-left.
    modules = MARKER_MODULES
    centers = (np.arange(modules) + 0.5)
    grid_x, grid_y = np.meshgrid(centers, centers)
    module_points = np.stack([grid_x.ravel(), grid_y.ravel()], axis=1)
    unit_square = np.array([[0, 0], [modules, 0], [modules, modules], [0, modules]], dtype=np.float64)

    for start in range(4):
        ordered = np.roll(quad, -start, axis=0)
        h = fit_homography(unit_square, ordered)
        points = apply_homography(h, module_points)
        xi = np.clip(np.round(points[:, 0]).astype(int), 0, gray.shape[1] - 1)
        yi = np.clip(np.round(points[:, 1]).astype(int), 0, gray.shape[0] - 1)
        white = (gray[yi, xi] >= threshold).reshape(modules, modules)

        border = np.concatenate([white[0], white[-1], white[1:-1, 0], white[1:-1, -1]])
        if border.sum() > 2:
            # Not a marker border (or badly sampled); no rotation will fix that.
            return None
        inner = white[1:-1, 1:-1].astype(int)
        for marker_id, bits in MARKER_BITS.items():
            expected = np.array([[int(b) for b in row] for row in bits])
            if np.abs(inner - expected).sum() <= 1:
                return marker_id, ordered
    return None



def otsu_threshold(values: np.ndarray) -> float:
    histogram = np.bincount(np.clip(values, 0, 255).astype(np.uint8).ravel(), minlength=256).astype(np.float64)
    total = histogram.sum()
    levels = np.arange(256)
    weight_low = histogram.cumsum()
    mean_low = (histogram * levels).cumsum()
    weight_high = total - weight_low
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (mean_low[-1] * weight_low / total - mean_low) ** 2 / (weight_low * weight_high)
    between[~np.isfinite(between)] = 0
    return float(np.argmax(between)) + 0.5



def largest_component_pixels(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """ Pixel coordinates (ys, xs) of the largest 8-connected component. """
    rows, starts, ends, labels = label_runs(mask)
    if not labels:
        return np.array([]), np.array([])
    sizes = {}
    for start, end, label in zip(starts, ends, labels):
        sizes[label] = sizes.get(label, 0) + end - start + 1
    largest = max(sizes, key=sizes.get)
    ys, xs = [], []
    for y, start, end, label in zip(rows, starts, ends, labels):
        if label == largest:
            xs.append(np.arange(start, end + 1))
            ys.append(np.full(end - start + 1, y))
    return np.concatenate(ys), np.concatenate(xs)



def quad_corners(xs: np.ndarray, ys: np.ndarray):
    """
    The 4 corners of a roughly square blob of pixels, clockwise on screen (image y
    points down). Works at any rotation: the farthest pixel from the centroid is a
    corner, the farthest from that is the opposite corner, and the other two are the
    farthest from the diagonal between them, one on each side.
    """
    points = np.stack([xs, ys], axis=1)
    center = points.mean(axis=0)
    a = points[np.argmax(((points - center) ** 2).sum(axis=1))]
    c = points[np.argmax(((points - a) ** 2).sum(axis=1))]
    direction = c - a
    side = (points[:, 0] - a[0]) * direction[1] - (points[:, 1] - a[1]) * direction[0]
    if side.max() <= 0 or side.min() >= 0:
        return None
    b = points[np.argmax(side)]
    d = points[np.argmin(side)]
    quad = np.array([a, b, c, d], dtype=np.float64)

    # Pixel centers sit half a pixel inside the true outline; push corners outward.
    quad += np.sign(quad - quad.mean(axis=0)) * 0.5

    # Order clockwise as seen on screen (y down).
    angles = np.arctan2(quad[:, 1] - center[1], quad[:, 0] - center[0])
    return quad[np.argsort(angles)]



"""****************************************************************************
    Step 2: camera pose and the raised plane of the dice tops
****************************************************************************"""
def marker_corners_mm(marker_id: int) -> np.ndarray:
    x, y = MARKER_ORIGINS_MM[marker_id]
    return np.array([[x, y], [x + MARKER_MM, y], [x + MARKER_MM, y + MARKER_MM], [x, y + MARKER_MM]])



def locate_dice_tops(markers: dict[int, np.ndarray], focal_px: float, image_size: tuple[int, int]) -> np.ndarray:
    """
    The frame's corners (TL, TR, BR, BL as printed) on the plane of the dice tops,
    DIE_MM above the paper, in image pixels.
    """
    sheet_points = np.vstack([marker_corners_mm(i) for i in sorted(markers)])
    image_points = np.vstack([markers[i] for i in sorted(markers)])
    h = fit_homography(sheet_points, image_points)

    # With the camera matrix K, the paper-plane homography is K [r1 r2 t] up to
    # scale; recover the rotation and translation from it.
    width, height = image_size
    k = np.array([[focal_px, 0, (width - 1) / 2], [0, focal_px, (height - 1) / 2], [0, 0, 1]])
    m = np.linalg.inv(k) @ h
    scale = 2 / (np.linalg.norm(m[:, 0]) + np.linalg.norm(m[:, 1]))
    r1, r2, t = m[:, 0] * scale, m[:, 1] * scale, m[:, 2] * scale
    if t[2] < 0:
        r1, r2, t = -r1, -r2, -t
    u, _, vt = np.linalg.svd(np.stack([r1, r2, np.cross(r1, r2)], axis=1))
    rotation = u @ vt

    # Sheet axes run x right and y down the page, so +z points into the paper and the
    # dice tops sit at z = -DIE_MM.
    corners_mm = grid_corners_px(GRID_MM)
    raised = np.hstack([corners_mm, np.full((4, 1), -DIE_MM)])
    camera_points = raised @ rotation.T + t
    projected = camera_points @ k.T
    return projected[:, :2] / projected[:, 2:3]



"""****************************************************************************
    Steps 3 and 4: snap the grid, then each cell, onto the dice
****************************************************************************"""
def sliding_extreme(values: np.ndarray, window: int, axis: int, func) -> np.ndarray:
    """ Centered sliding max/min along one axis, edges clamped. """
    before = window // 2
    after = window - 1 - before
    pad = [(0, 0)] * values.ndim
    pad[axis] = (before, after)
    padded = np.pad(values, pad, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, window, axis=axis)
    return func(windows, axis=-1)



def seam_map(gray: np.ndarray, axis: int) -> np.ndarray:
    """
    Seam strength per pixel, for seams running across axis 0 (vertical seams) or
    axis 1 (horizontal seams): a black-hat across the seam direction picks out what
    is narrower and darker than its surroundings, widened a little because seams
    wander by a few pixels.
    """
    across = 1 if axis == 0 else 0
    kernel = max(3, CELL_PX // 4)
    closed = sliding_extreme(sliding_extreme(gray, kernel, across, np.max), kernel, across, np.min)
    blackhat = closed - gray
    return sliding_extreme(blackhat, 2 * max(1, CELL_PX // 28) + 1, across, np.max)



def fit_lattice(profile: np.ndarray, origin: float) -> tuple[float, float]:
    """
    Best (start, pitch), in canonical pixels, for GRID_SIZE+1 equally spaced lines
    along a seam profile whose first sample sits at origin. Only the interior seams
    are scored: the block's outer edge meets the paper, not another die.
    """
    positions = np.arange(len(profile), dtype=np.float64) + origin
    pitches = np.arange(0.85, 1.15, 0.0025) * CELL_PX
    starts = np.arange(-0.4, 0.4, 0.005) * CELL_PX
    seams = np.arange(1, GRID_SIZE)
    lines = starts[:, None, None] + pitches[None, :, None] * seams[None, None, :]
    scores = np.interp(lines, positions, profile).mean(axis=2)
    best_start, best_pitch = np.unravel_index(np.argmax(scores), scores.shape)
    return float(starts[best_start]), float(pitches[best_pitch])



def snap_grid_to_dice(rgb: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """
    Refine approximate grid corners onto the block of packed dice by fitting a
    regular lattice to the seams between dice. Seams are scored by their median
    strength along the block: a seam is dark nearly end to end, while pips that
    line up into a stripe (as they do when all the dice look alike) are dark only
    in spots.
    """
    side = GRID_SIZE * CELL_PX
    pad = CELL_PX // 2
    image_from_canonical = fit_homography(grid_corners_px(side), corners)
    warped = warp_grid(rgb, corners, pad)
    gray = warped.max(axis=2).astype(np.float32)

    x0, pitch_x = fit_lattice(np.median(seam_map(gray, 0), axis=0), -pad)
    y0, pitch_y = fit_lattice(np.median(seam_map(gray, 1), axis=1), -pad)
    x1, y1 = x0 + GRID_SIZE * pitch_x, y0 + GRID_SIZE * pitch_y
    refined = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    return apply_homography(image_from_canonical, refined)



def snap_cells(warped: np.ndarray, pad: int) -> np.ndarray:
    """
    Shift each cell to sit on its own die: returns GRID_SIZE x GRID_SIZE x 2 (dx, dy)
    offsets, each within +-pad canonical pixels.

    Each candidate edge is scored by the seam strength it keeps along 80% of its
    length (the 20th percentile): a seam is dark nearly end to end, while a line of
    pips beside the edge (up to ~60% of it on a 6) must not pass. An edge facing bare
    paper has no seam and simply doesn't pull. A small penalty on distance keeps cells
    with no clear seams where the lattice put them.
    """
    gray = warped.max(axis=2).astype(np.float32)
    vertical = seam_map(gray, 0)
    horizontal_t = seam_map(gray, 1).T
    shifts = np.arange(-pad, pad + 1)
    penalty = 0.05 * np.abs(shifts)
    size = CELL_PX
    kth = size // 5            # 20th percentile of the size values along an edge

    def percentile_20(values):
        return np.partition(values, kth, axis=0)[kth]

    def best(seams, span_start, edge_start):
        band = seams[span_start:span_start + size]
        last = band.shape[1] - 1
        first_edge = band[:, np.clip(edge_start + shifts, 0, last)]
        second_edge = band[:, np.clip(edge_start + size + shifts, 0, last)]
        score = percentile_20(first_edge) + percentile_20(second_edge)
        return int(shifts[np.argmax(score - penalty)])

    offsets = np.zeros((GRID_SIZE, GRID_SIZE, 2), dtype=int)
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            x0, y0 = pad + col * size, pad + row * size
            dx = dy = 0
            for _ in range(2):   # the two axes barely interact; twice settles it
                dx = best(vertical, y0 + dy, x0)
                dy = best(horizontal_t, x0 + dx, y0)
            offsets[row, col] = dx, dy
    return offsets



"""****************************************************************************
    Step 5: read each die
****************************************************************************"""
def pip_layouts(size: int) -> np.ndarray:
    """
    Every candidate placement of the 3x3 pip layout in a size x size cell, as an
    (n, 9, 2) array of integer (y, x) points, indexed row * 3 + col.
    """
    reach = int(round(size * PIP_SHIFT))
    shifts = np.arange(-reach, reach + 1)
    layouts = []
    for inset in PIP_INSETS:
        steps = size * np.array([inset, 0.5, 1 - inset])
        ys, xs = np.meshgrid(steps, steps, indexing="ij")
        base = np.stack([ys.ravel(), xs.ravel()], axis=1)
        for dy in shifts:
            for dx in shifts:
                layouts.append(base + (dy, dx))
    return np.clip(np.round(np.array(layouts)).astype(int), 0, size - 1)



def pip_contrasts(box_mean: np.ndarray, layouts: np.ndarray, darker: bool) -> np.ndarray:
    """
    Pip contrast at each layout point, for every candidate layout: (n, 9).

    box_mean is the cell's channel averaged over a pip-sized box. Pips are darker
    than the die body (darker=True) or lighter, and contrast is measured against
    the die body's typical value.
    """
    size = box_mean.shape[0]
    inset = int(round(size * 0.15))
    body = np.median(box_mean[inset:size - inset, inset:size - inset])
    values = box_mean[layouts[..., 0], layouts[..., 1]]
    return body - values if darker else values - body



def _pattern_masks() -> tuple[list[int], np.ndarray]:
    values, masks = [], []
    for value, patterns in FACE_PATTERNS.items():
        for pattern in patterns:
            values.append(value)
            masks.append([i in pattern for i in range(9)])
    return values, np.array(masks)

PATTERN_VALUES, PATTERN_MASKS = _pattern_masks()



def classify_face(contrasts: np.ndarray) -> tuple[int, float]:
    """
    Best face value over all candidate layouts' pip contrasts (n, 9), and its margin:
    the weakest pip in the pattern minus the strongest point outside it. Positive
    means the pattern cleanly separates pips from body.
    """
    contrasts = np.atleast_2d(contrasts)
    on = np.where(PATTERN_MASKS[:, None, :], contrasts[None], np.inf).min(axis=2)
    off = np.where(PATTERN_MASKS[:, None, :], -np.inf, contrasts[None]).max(axis=2)
    margins = on - off                                  # (patterns, layouts)
    pattern, _ = np.unravel_index(np.argmax(margins), margins.shape)
    return PATTERN_VALUES[pattern], float(margins.max())



def count_pip_blobs(channel: np.ndarray, body: float, pip_contrast: float, darker: bool) -> int:
    """
    Count pip-shaped blobs in one cell, as a second opinion on the face reading.

    A pixel belongs to a pip when it differs from the die body by at least half the
    reading's pip contrast. Blobs touching the cell edge are ignored (they are
    neighbors' pips or seams). All pips on a die are about the same size, so blobs
    much smaller than the largest (glare on glossy dice, specks) are ignored too.
    """
    size = channel.shape[0]
    difference = body - channel if darker else channel - body
    mask = difference > pip_contrast / 2
    areas = [
        area for top, left, bottom, right, area in bounding_boxes(mask)
        if top > 0 and left > 0 and bottom < size - 1 and right < size - 1
        and 0.004 * size * size <= area <= 0.06 * size * size
    ]
    if not areas:
        return 0
    return sum(area >= 0.65 * max(areas) for area in areas)



def read_cells(warped: np.ndarray, pad: int, offsets: np.ndarray) -> tuple[list[int], list[bool]]:
    """
    Read every die. Dark pips are dark in every color channel, so they are measured
    in the per-pixel max channel; light pips are bright in every channel, so they
    stand out in the per-pixel min channel, where a colored die body is dark. Both
    readings are tried and the one that separates pips from body more cleanly wins.

    A die is flagged uncertain when its pattern only narrowly beats the others, or
    when a plain count of pip-shaped blobs disagrees with it. The blob count catches
    a die sitting well off its cell, where the pattern can fit the wrong points.
    """
    brightest = warped.max(axis=2).astype(np.float32)   # dark pips show here
    dimmest = warped.min(axis=2).astype(np.float32)     # light pips show here
    radius = max(1, int(round(CELL_PX * PIP_RADIUS)))
    brightest_mean = local_mean(brightest, radius)
    dimmest_mean = local_mean(dimmest, radius)
    layouts = pip_layouts(CELL_PX)

    rolls, uncertain = [], []
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            dx, dy = offsets[row, col]
            x0, y0 = pad + dx + col * CELL_PX, pad + dy + row * CELL_PX
            cell = (slice(y0, y0 + CELL_PX), slice(x0, x0 + CELL_PX))

            best = None
            for channel, box_mean, darker in (
                (brightest, brightest_mean, True),
                (dimmest, dimmest_mean, False),
            ):
                contrasts = pip_contrasts(box_mean[cell], layouts, darker)
                value, margin = classify_face(contrasts)
                strength = contrasts.max()
                if best is None or margin > best[1]:
                    best = (value, margin, strength, channel, box_mean, darker)

            value, margin, strength, channel, box_mean, darker = best
            if strength < MIN_PIP_CONTRAST:
                rolls.append(0)
                uncertain.append(True)
                continue

            inset = int(round(CELL_PX * 0.15))
            body = np.median(box_mean[cell][inset:-inset, inset:-inset])
            blobs = count_pip_blobs(channel[cell], body, strength, darker)
            rolls.append(value)
            uncertain.append(margin < MIN_CONFIDENT_MARGIN * strength or blobs != value)
    return rolls, uncertain
