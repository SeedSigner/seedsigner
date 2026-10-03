"""BitSquiggle32 injective connection-graph visualization.

The module uses only core MicroPython features plus ``math``. Connections are
stored in lexical ``(start_row, start_column, end_row, end_column)`` order.

Vendored unmodified from https://github.com/maggo83/BitSquiggles
(micropython/bitsquiggle32.py) for use as the master-fingerprint visualization
on SeedSigner's seed finalize screen.

Grug 2-Clause License: do what want; not sue grug.
"""

import math

ROWS = 7
COLUMNS = 5
EDGE_COUNT = 58
PIXEL_WIDTH = 16
PIXEL_HEIGHT = 22

STANDARD = "standard"
HIGH_CONTRAST = "high-contrast"
MONOCHROME = "monochrome"
BLACK_AND_WHITE = "black-and-white"
STYLES = (STANDARD, HIGH_CONTRAST, MONOCHROME, BLACK_AND_WHITE)

LEFT_RIGHT = "A|"
TOP_BOTTOM = "A-"
HALF_TURN = "A+"
DIAGONAL_SLASH = "A/"
MODES = (
    LEFT_RIGHT,
    TOP_BOTTOM,
    HALF_TURN,
    DIAGONAL_SLASH,
)

__all__ = (
    "ROWS", "COLUMNS", "EDGE_COUNT", "PIXEL_WIDTH", "PIXEL_HEIGHT", "EDGES",
    "STANDARD", "HIGH_CONTRAST", "MONOCHROME", "BLACK_AND_WHITE", "STYLES",
    "LEFT_RIGHT", "TOP_BOTTOM", "HALF_TURN", "DIAGONAL_SLASH", "MODES",
    "mix32", "free_connection_count", "matches_mode", "spec", "pixels",
    "smooth_blobs",
)

BASE_L_MIN = 0.5
BASE_L_MAX = 0.7
CHROMA_MIN = 0.05
CHROMA_MAX = 0.25
HC_L_ADD = 0.30
BG_L_SPREAD = 0.50
BG_L_EXTRA_HC = 0.30
CHROMA_HC_ADD = 0.10
MASK32 = 0xFFFFFFFF

LEFT_RIGHT_TEMPLATE = (
    "A B C B' A'",
    "D E F E' D'",
    "G H I H' G'",
    "J K L K' J'",
    "M N O N' M'",
    "P Q R Q' P'",
    "S T U T' S'",
)
TOP_BOTTOM_TEMPLATE = (
    "A B C D E",
    "F G H I J",
    "K L M N O",
    "P Q R S T",
    "K' L' M' N' O'",
    "F' G' H' I' J'",
    "A' B' C' D' E'",
)
HALF_TURN_TEMPLATE = (
    "A B C D E",
    "F G H I J",
    "K L M N O",
    "P Q R Q' P'",
    "O' N' M' L' K'",
    "J' I' H' G' F'",
    "E' D' C' B' A'",
)
DIAGONAL_SLASH_TEMPLATE = (
    "A B C D E",
    "F G H I J",
    "K L M N I'",
    "O P Q M' H'",
    "R S P' L' G'",
    "T R' O' K' F'",
    "E' D' C' B' A'",
)


def _create_edges():
    result = []
    for row in range(ROWS):
        for column in range(COLUMNS):
            if column + 1 < COLUMNS:
                result.append((row, column, row, column + 1))
            if row + 1 < ROWS:
                result.append((row, column, row + 1, column))
    return tuple(result)


EDGES = _create_edges()


def _create_mode_definition(mode, template_rows):
    template = tuple(tuple(row.split()) for row in template_rows)
    source_positions = {}
    references = []
    for row in range(ROWS):
        reference_row = []
        for column in range(COLUMNS):
            token = template[row][column]
            copied = token.endswith("'")
            name = token[:-1] if copied else token
            reference_row.append(name)
            if not copied:
                source_positions[name] = row * COLUMNS + column
        references.append(tuple(reference_row))

    classes = {}
    for edge_index, edge in enumerate(EDGES):
        start_row, start_column, end_row, end_column = edge
        start = references[start_row][start_column]
        end = references[end_row][end_column]
        first = source_positions[start]
        second = source_positions[end]
        if first == second:
            raise ValueError("invalid template edge in %s" % mode)
        key = (min(first, second), max(first, second))
        classes.setdefault(key, []).append(edge_index)

    ordered = []
    for key in sorted(classes):
        ordered.append((key, tuple(classes[key])))
    return {"mode": mode, "classes": tuple(ordered)}


_MODE_DEFINITIONS = (
    _create_mode_definition(LEFT_RIGHT, LEFT_RIGHT_TEMPLATE),
    _create_mode_definition(TOP_BOTTOM, TOP_BOTTOM_TEMPLATE),
    _create_mode_definition(HALF_TURN, HALF_TURN_TEMPLATE),
    _create_mode_definition(DIAGONAL_SLASH, DIAGONAL_SLASH_TEMPLATE),
)


def _validate_bits(bits):
    if not isinstance(bits, int) or bits < 0 or bits > MASK32:
        raise ValueError("bits must be an unsigned 32-bit integer")


def _popcount(value):
    count = 0
    while value:
        value &= value - 1
        count += 1
    return count


def mix32(value):
    """Return the bijective Murmur fmix32 permutation with a Weyl offset."""
    value = (value + 0x9E3779B9) & MASK32
    value ^= value >> 16
    value = (value * 0x85EBCA6B) & MASK32
    value ^= value >> 13
    value = (value * 0xC2B2AE35) & MASK32
    value ^= value >> 16
    return value & MASK32


def free_connection_count(mode):
    return len(_MODE_DEFINITIONS[MODES.index(mode)]["classes"])


def _expand(definition, values):
    result = bytearray(EDGE_COUNT)
    for index, connection_class in enumerate(definition["classes"]):
        for edge_index in connection_class[1]:
            result[edge_index] = values[index]
    return result


def _encode_default(mixed):
    values = bytearray(32)
    for index in range(32):
        values[index] = (mixed >> (31 - index)) & 1
    return _expand(_MODE_DEFINITIONS[0], values)


def _encode_connections(mixed, mode_index):
    if mode_index == 0:
        return _encode_default(mixed)
    definition = _MODE_DEFINITIONS[mode_index]
    payload = mixed & 0x3FFFFFFF
    values = bytearray(len(definition["classes"]))
    for index in range(len(values)):
        values[index] = (payload >> (29 - (index % 30))) & 1
    return _expand(definition, values)


def _preferred_mode_has_capacity(mixed, mode_index):
    missing_bits = 30 - len(_MODE_DEFINITIONS[mode_index]["classes"])
    if missing_bits <= 0:
        return True
    return (mixed & ((1 << missing_bits) - 1)) == 0


def matches_mode(connections, mode):
    definition = _MODE_DEFINITIONS[MODES.index(mode)]
    for connection_class in definition["classes"]:
        occurrences = connection_class[1]
        expected = connections[occurrences[0]]
        for edge_index in occurrences[1:]:
            actual = connections[edge_index]
            if actual != expected:
                return False
    return True


def _conflicts_with_earlier_mode(connections, mode_index):
    for earlier in range(mode_index):
        if matches_mode(connections, MODES[earlier]):
            return True
    return False


def _active_cells(connections):
    cells = [[0 for _ in range(COLUMNS)] for _ in range(ROWS)]
    for index, edge in enumerate(EDGES):
        if not connections[index]:
            continue
        start_row, start_column, end_row, end_column = edge
        cells[start_row][start_column] = 1
        cells[end_row][end_column] = 1
    return cells


def _clamp01(value):
    return max(0.0, min(1.0, value))


def _srgb_encode(value):
    value = _clamp01(value)
    if value <= 0.0031308:
        return 12.92 * value
    return 1.055 * math.pow(value, 1.0 / 2.4) - 0.055


def _make_color(lightness, chroma, hue):
    radians = hue * math.pi / 180.0
    a = chroma * math.cos(radians)
    b = chroma * math.sin(radians)
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    l3 = l_ * l_ * l_
    m3 = m_ * m_ * m_
    s3 = s_ * s_ * s_
    red = _srgb_encode(4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3)
    green = _srgb_encode(-1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3)
    blue = _srgb_encode(-0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3)
    red = max(0, min(255, int(red * 255 + 0.5)))
    green = max(0, min(255, int(green * 255 + 0.5)))
    blue = max(0, min(255, int(blue * 255 + 0.5)))
    return {"L": lightness, "C": chroma, "h": hue,
            "hex": "#%02x%02x%02x" % (red, green, blue)}


def _derive_colors(hue_index, chroma_index, luminance_index, swap, style):
    if style not in STYLES:
        raise ValueError("unknown style: %s" % style)
    foreground_hue = hue_index * (360.0 / 16.0)
    background_hue = (foreground_hue + 180.0) % 360.0
    chroma = CHROMA_MIN + chroma_index * ((CHROMA_MAX - CHROMA_MIN) / 15.0)
    base_l = BASE_L_MIN + luminance_index * ((BASE_L_MAX - BASE_L_MIN) / 3.0)
    if style == STANDARD:
        foreground_l = base_l
        background_l = foreground_l - BG_L_SPREAD
        foreground_c = chroma
        background_c = chroma
    elif style == HIGH_CONTRAST:
        foreground_l = base_l + HC_L_ADD
        background_l = foreground_l - BG_L_SPREAD - BG_L_EXTRA_HC
        foreground_c = chroma + CHROMA_HC_ADD
        background_c = chroma + CHROMA_HC_ADD
    elif style == MONOCHROME:
        foreground_l = base_l + HC_L_ADD
        background_l = foreground_l - BG_L_SPREAD - BG_L_EXTRA_HC
        foreground_c = 0.0
        background_c = 0.0
    else:
        foreground_l = 1.0
        background_l = 0.0
        foreground_c = 0.0
        background_c = 0.0
    foreground_l = _clamp01(foreground_l)
    background_l = _clamp01(background_l)
    if swap:
        foreground_l, background_l = background_l, foreground_l
    foreground = _make_color(foreground_l, foreground_c, foreground_hue)
    background = _make_color(background_l, background_c, background_hue)
    return background, foreground


def spec(bits, style=STANDARD):
    """Return the canonical connection visual for an unsigned 32-bit integer."""
    _validate_bits(bits)
    mixed = mix32(bits)
    mode_index = mixed >> 30
    candidate = _encode_connections(mixed, mode_index)
    fallback = mode_index != 0 and (
        not _preferred_mode_has_capacity(mixed, mode_index)
        or _conflicts_with_earlier_mode(candidate, mode_index))
    actual_mode = LEFT_RIGHT if fallback else MODES[mode_index]
    connections = _encode_default(mixed) if fallback else candidate
    hue_index = (mixed >> 12) & 0xF
    chroma_index = (mixed >> 8) & 0xF
    luminance_index = mixed & 0x3
    swapped = (_popcount(bits) & 1) == 1
    background, foreground = _derive_colors(
        hue_index, chroma_index, luminance_index, swapped, style)
    return {
        "input": bits,
        "mixed": mixed,
        "connections": connections,
        "cells": _active_cells(connections),
        "background": background,
        "foreground": foreground,
        "style": style,
        "preferred_mode": MODES[mode_index],
        "actual_mode": actual_mode,
        "fallback": fallback,
        "luminance_index": luminance_index,
        "swapped": swapped,
    }


def _connection(connections, start_row, start_column, end_row, end_column):
    target = (start_row, start_column, end_row, end_column)
    for index, edge in enumerate(EDGES):
        if edge == target:
            return connections[index]
    raise ValueError("not a canonical edge")


def _generate_pixels(connections):
    result = bytearray(PIXEL_WIDTH * PIXEL_HEIGHT)
    cells = _active_cells(connections)
    for row in range(ROWS):
        for column in range(COLUMNS):
            if not cells[row][column]:
                continue
            x = 1 + column * 3
            y = 1 + row * 3
            result[ y      * PIXEL_WIDTH + x    ] = 1
            result[ y      * PIXEL_WIDTH + x + 1] = 1
            result[(y + 1) * PIXEL_WIDTH + x    ] = 1
            result[(y + 1) * PIXEL_WIDTH + x + 1] = 1
    for index, edge in enumerate(EDGES):
        if not connections[index]:
            continue
        start_row, start_column, end_row, _ = edge
        x = 1 + start_column * 3
        y = 1 + start_row * 3
        if start_row == end_row:
            result[ y      * PIXEL_WIDTH + x + 2] = 1
            result[(y + 1) * PIXEL_WIDTH + x + 2] = 1
        else:
            result[(y + 2) * PIXEL_WIDTH + x    ] = 1
            result[(y + 2) * PIXEL_WIDTH + x + 1] = 1
    for row in range(ROWS - 1):
        for column in range(COLUMNS - 1):
            if (_connection(connections, row, column, row, column + 1)
                    and _connection(connections, row + 1, column, row + 1, column + 1)
                    and _connection(connections, row, column, row + 1, column)
                    and _connection(connections, row, column + 1, row + 1, column + 1)):
                result[(3 + row * 3) * PIXEL_WIDTH + 3 + column * 3] = 1
    return result


def pixels(bits, style=STANDARD):
    """Return the exact bordered 16x22 one-bit raster and its colors."""
    visual = spec(bits, style)
    return {
        "width": PIXEL_WIDTH,
        "height": PIXEL_HEIGHT,
        "pixels": _generate_pixels(visual["connections"]),
        "background": visual["background"],
        "foreground": visual["foreground"],
        "style": style,
    }


def _horizontal_edge_index(row, column):
    offset = (column if row == ROWS - 1 else 2 * column)
    return row * (2 * COLUMNS - 1) + offset


def _vertical_edge_index(row, column):
    offset = 2 * COLUMNS - 2 if column == COLUMNS - 1 else 2 * column + 1
    return row * (2 * COLUMNS - 1) + offset


def _junction_index(row, column):
    return row * (COLUMNS - 1) + column


def _required_edges(connections):
    if connections is None or len(connections) != EDGE_COUNT:
        raise ValueError("connections must contain 58 entries")
    result = 0
    for index in range(EDGE_COUNT):
        if connections[index] != 0 and connections[index] != 1:
            raise ValueError("connections must contain only zeroes and ones")
        if connections[index]:
            result |= 1 << index
    return result


def _connected_rectangle_edge_mask(top, left, bottom, right, required_edges):
    result = 0
    for row in range(top, bottom + 1):
        for column in range(left, right + 1):
            if column < right:
                edge = 1 << _horizontal_edge_index(row, column)
                if not required_edges & edge:
                    return 0
                result |= edge
            if row < bottom:
                edge = 1 << _vertical_edge_index(row, column)
                if not required_edges & edge:
                    return 0
                result |= edge
    return result


def _required_junctions(required_edges):
    result = 0
    for row in range(ROWS - 1):
        for column in range(COLUMNS - 1):
            if _connected_rectangle_edge_mask(
                    row, column, row + 1, column + 1, required_edges):
                result |= 1 << _junction_index(row, column)
    return result


def _rectangle_junction_mask(top, left, bottom, right, required_junctions):
    result = 0
    for row in range(top, bottom):
        for column in range(left, right):
            bit = 1 << _junction_index(row, column)
            if required_junctions & bit:
                result |= bit
    return result


def _is_better_blob(top, left, bottom, right, new_edges, new_junctions,
                    best_top, best_left, best_bottom, best_right,
                    best_new_edges, best_new_junctions):
    junction_count = _popcount(new_junctions)
    best_junction_count = _popcount(best_new_junctions)
    if junction_count != best_junction_count:
        return junction_count > best_junction_count
    edge_count = _popcount(new_edges)
    best_edge_count = _popcount(best_new_edges)
    if edge_count != best_edge_count:
        return edge_count > best_edge_count
    area = (bottom - top + 1) * (right - left + 1)
    best_area = (best_bottom - best_top + 1) * (best_right - best_left + 1)
    if area != best_area:
        return area < best_area
    if top != best_top:
        return top < best_top
    if left != best_left:
        return left < best_left
    if bottom != best_bottom:
        return bottom < best_bottom
    return right < best_right


def _first_uncovered_edge(required_edges, covered_edges):
    for index in range(EDGE_COUNT):
        if required_edges & ~covered_edges & (1 << index):
            return index
    return -1


def _first_uncovered_junction(required_junctions, covered_junctions):
    for index in range((ROWS - 1) * (COLUMNS - 1)):
        if required_junctions & ~covered_junctions & (1 << index):
            return index
    return -1


def smooth_blobs(connections):
    """Return canonical ``(top_row, left_column, bottom_row, right_column)`` blobs.

    The result covers selected connections and required four-cell junctions with
    valid, overlapping rounded rectangles. Four packed integer feature masks
    and early-aborted candidate scans keep the working set small; output is
    bounded at 82 blobs.
    """
    required_edges = _required_edges(connections)
    required_junctions = _required_junctions(required_edges)
    covered_edges = 0
    covered_junctions = 0
    result = [None] * (EDGE_COUNT + (ROWS - 1) * (COLUMNS - 1))  # type: list
    result_count = 0

    while True:
        anchor_edge = _first_uncovered_edge(required_edges, covered_edges)
        if anchor_edge >= 0:
            anchor_top, anchor_left, anchor_bottom, anchor_right = EDGES[anchor_edge]
        else:
            anchor_junction = _first_uncovered_junction(
                required_junctions, covered_junctions)
            if anchor_junction < 0:
                break
            anchor_top = anchor_junction // (COLUMNS - 1)
            anchor_left = anchor_junction % (COLUMNS - 1)
            anchor_bottom = anchor_top + 1
            anchor_right = anchor_left + 1

        best = None
        best_new_edges = 0
        best_new_junctions = 0
        left_inclusive = 0
        for top in range(anchor_top, -1, -1):
            for left in range(anchor_left, left_inclusive - 1, -1):
                right_exclusive = COLUMNS
                stop_left_expansion = False
                for bottom in range(anchor_bottom, ROWS):
                    for right in range(anchor_right, right_exclusive):
                        edges = _connected_rectangle_edge_mask(
                            top, left, bottom, right, required_edges)
                        if not edges:
                            if bottom == anchor_bottom and right == anchor_right:
                                left_inclusive = left + 1
                                stop_left_expansion = True
                            else:
                                right_exclusive = right
                            break
                        junctions = _rectangle_junction_mask(
                            top, left, bottom, right, required_junctions)
                        new_edges = edges & ~covered_edges
                        new_junctions = junctions & ~covered_junctions
                        if new_edges == 0 and new_junctions == 0:
                            continue
                        if (best is None or _is_better_blob(
                                top, left, bottom, right,
                                new_edges, new_junctions,
                                best[0], best[1], best[2], best[3],
                                best_new_edges, best_new_junctions)):
                            best = (top, left, bottom, right)
                            best_new_edges = new_edges
                            best_new_junctions = new_junctions
                    if stop_left_expansion or right_exclusive == anchor_right:
                        break
                if stop_left_expansion:
                    break

        if best is None:
            raise RuntimeError("uncoverable smooth feature")
        result[result_count] = best
        result_count += 1
        covered_edges |= _connected_rectangle_edge_mask(
            best[0], best[1], best[2], best[3], required_edges)
        covered_junctions |= _rectangle_junction_mask(
            best[0], best[1], best[2], best[3], required_junctions)

    return tuple(result[:result_count])
