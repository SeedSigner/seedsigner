from unittest.mock import Mock

from seedsigner.gui.components import _get_single_paragraph_text_bbox


def test_get_single_paragraph_text_bbox_replaces_newlines():
    font = Mock()
    expected_bbox = (0, -16, 241, 0)
    font.getbbox.return_value = expected_bbox

    bbox = _get_single_paragraph_text_bbox(
        font,
        "You must remove the\nMicroSD card to continue.",
    )

    assert bbox == expected_bbox
    font.getbbox.assert_called_once_with(
        "You must remove the MicroSD card to continue.",
        anchor="ls",
    )
