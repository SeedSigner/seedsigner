from base import BaseTest

from seedsigner.gui.components import (
    Fonts,
    GUIConstants,
    reflow_text_for_width,
    reflow_text_into_pages,
)


FIDELITY_BOND_CERTIFICATE = (
    "fidelity-bond-cert|"
    "0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c|375"
)


class TestTextReflow(BaseTest):
    def test_preserves_normal_word_wrapping(self):
        lines = reflow_text_for_width("one two three", width=75)

        assert [line["text"] for line in lines] == ["one two", "three"]

    def test_hard_wraps_long_unbroken_message_without_losing_content(self):
        width = 224
        lines = reflow_text_for_width(FIDELITY_BOND_CERTIFICATE, width=width)

        assert len(lines) > 1
        assert all(line["text_width"] < width for line in lines)
        assert "".join(line["text"] for line in lines) == FIDELITY_BOND_CERTIFICATE

    def test_exact_width_token_uses_existing_strict_width_limit(self):
        token = "fidelity"
        font = Fonts.get_font(
            font_name=GUIConstants.get_body_font_name(),
            size=GUIConstants.get_body_font_size(),
        )
        left, top, right, bottom = font.getbbox(token, anchor="ls")

        lines = reflow_text_for_width(token, width=right - left)

        assert len(lines) == 2
        assert "".join(line["text"] for line in lines) == token

    def test_pages_preserve_long_unbroken_message(self):
        pages = reflow_text_into_pages(
            FIDELITY_BOND_CERTIFICATE,
            width=224,
            height=134,
        )

        assert len(pages) == 1
        assert pages[0].count("\n") == 3
        assert "".join(pages).replace("\n", "") == FIDELITY_BOND_CERTIFICATE
