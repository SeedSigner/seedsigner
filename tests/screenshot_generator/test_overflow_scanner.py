import json
import sys
from dataclasses import dataclass, field
from typing import List
from unittest.mock import MagicMock

import pytest

# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.gui.renderer'] = MagicMock()
sys.modules['seedsigner.hardware.buttons'] = MagicMock()
sys.modules['seedsigner.hardware.st7789_mpy'] = MagicMock()
sys.modules['seedsigner.hardware.ili9341'] = MagicMock()

from screenshot_generator.overflow_scanner import overflow



@dataclass
class FakeComponent:
    """Positioned like a gui component, but not a TextArea, so its effective
    height is just .height."""
    screen_y: int = 0
    height: int = 0
    text: str = ""


@dataclass
class FakeTextLine:
    px_below_baseline: int = 0

    def get(self, key, default=0):
        return getattr(self, key, default)


@dataclass
class FakeScreen:
    components: List = field(default_factory=list)
    buttons: List = field(default_factory=list)
    paste_images: List = field(default_factory=list)
    has_scroll_arrows: bool = False
    is_bottom_list: bool = False



class TestGetTrueTextHeight:
    def make_textarea(self, num_lines, above=20, below=5, spacing=4, ignores_below=False):
        textarea = MagicMock()
        textarea.text_lines = [FakeTextLine(px_below_baseline=below) for _ in range(num_lines)]
        textarea.text_height_above_baseline = above
        textarea.text_height_below_baseline = below
        textarea.line_spacing = spacing
        textarea.height_ignores_below_baseline = ignores_below
        return textarea


    def test_single_line(self):
        assert overflow.get_true_text_height(self.make_textarea(1)) == 25  # 20 + 5


    def test_single_line_ignores_below_baseline(self):
        assert overflow.get_true_text_height(self.make_textarea(1, ignores_below=True)) == 20


    def test_multi_line(self):
        # 3 lines: 3*20 above + 2*4 spacing + 5 below the last line
        assert overflow.get_true_text_height(self.make_textarea(3)) == 73



class TestScanForOverflow:
    def test_clean_screen_yields_no_events(self):
        screen = FakeScreen(components=[FakeComponent(screen_y=50, height=100)])
        assert overflow.scan_for_overflow(screen, "SomeView", "de") == []


    def test_component_past_canvas_bottom_is_bounds_overflow(self):
        screen = FakeScreen(components=[FakeComponent(screen_y=200, height=52, text="zu lang")])
        events = overflow.scan_for_overflow(screen, "SomeView", "de")

        assert len(events) == 1
        assert events[0].event_type == "bounds"
        assert events[0].overflow_px == 12
        assert events[0].component_text == "zu lang"
        assert events[0].screen_name == "SomeView"
        assert events[0].locale == "de"


    def test_component_ending_exactly_at_bottom_is_fine(self):
        screen = FakeScreen(components=[FakeComponent(screen_y=140, height=100)])
        assert overflow.scan_for_overflow(screen, "SomeView", "de") == []


    def test_button_overflow_flagged_only_without_scroll_arrows(self):
        button = FakeComponent(screen_y=230, height=32)
        screen = FakeScreen(buttons=[button])
        events = overflow.scan_for_overflow(screen, "SomeView", "de")
        assert len(events) == 1
        assert events[0].event_type == "bounds"

        # Scroll arrows mean the button is reachable by scrolling: not a defect
        screen = FakeScreen(buttons=[button], has_scroll_arrows=True)
        assert overflow.scan_for_overflow(screen, "SomeView", "de") == []


    def test_body_colliding_with_buttons(self):
        body = FakeComponent(screen_y=100, height=100, text="langer Text")
        button = FakeComponent(screen_y=190, height=40)
        screen = FakeScreen(components=[body], buttons=[button], is_bottom_list=True)
        events = overflow.scan_for_overflow(screen, "SomeView", "de")

        assert len(events) == 1
        assert events[0].event_type == "collision"
        assert events[0].overflow_px == 10  # body bottom 200 vs button top 190


    def test_known_overlap_prefix_raises_collision_threshold(self):
        body = FakeComponent(screen_y=100, height=100, text="opts")
        button = FakeComponent(screen_y=190, height=40)
        screen = FakeScreen(components=[body], buttons=[button], is_bottom_list=True)

        # 10px overlap is within the known 22px EN baseline for this screen
        assert overflow.scan_for_overflow(screen, "SettingsEntryUpdateSelectionView_persistent", "de") == []

        # but not past it
        body.height = 115  # 25px overlap
        events = overflow.scan_for_overflow(screen, "SettingsEntryUpdateSelectionView_persistent", "de")
        assert len(events) == 1


    def test_pasted_image_overflow(self):
        img = MagicMock()
        img.height = 100
        screen = FakeScreen(paste_images=[(img, (0, 180))])
        events = overflow.scan_for_overflow(screen, "SomeView", "de")

        assert len(events) == 1
        assert events[0].component_type == "paste_image"
        assert events[0].overflow_px == 40



PO_HEADER = 'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'

# Entries kept as escapes so this file stays ASCII: "L\u00e4nge" etc.
PO_BODY = (
    'msgid "Passphrase"\n'
    'msgstr "Passphrase eingeben"\n\n'
    'msgid "Enter {name} length"\n'
    'msgstr "L\u00e4nge von {name} eingeben"\n\n'
    'msgid "{} word"\n'
    'msgid_plural "{} words"\n'
    'msgstr[0] "{} Wort"\n'
    'msgstr[1] "{} W\u00f6rter"\n'
)


@pytest.fixture
def po_mapping(tmp_path, monkeypatch):
    po_file = tmp_path / "messages.po"
    po_file.write_text(PO_HEADER + PO_BODY, encoding="utf-8")
    monkeypatch.setattr(overflow, "_po_path", lambda locale: str(po_file))
    monkeypatch.setattr(overflow, "_po_cache", {})



class TestReverseLookupMsgid:
    def test_direct_match(self, po_mapping):
        assert overflow.reverse_lookup_msgid("Passphrase eingeben", "de") == \
            ("Passphrase", "Passphrase eingeben")


    def test_english_passthrough(self):
        assert overflow.reverse_lookup_msgid("Some text", "en") == ("Some text", "Some text")


    def test_format_string_with_substituted_placeholder(self, po_mapping):
        # The rendered text has the placeholder already filled in
        msgid, msgstr = overflow.reverse_lookup_msgid("L\u00e4nge von Seed A eingeben", "de")
        assert msgid == "Enter {name} length"
        assert msgstr == "L\u00e4nge von {name} eingeben"


    def test_plural_forms_map_to_singular_msgid(self, po_mapping):
        assert overflow.reverse_lookup_msgid("{} Wort", "de")[0] == "{} word"
        assert overflow.reverse_lookup_msgid("{} W\u00f6rter", "de")[0] == "{} word"


    def test_unknown_text_returns_empty_msgid(self, po_mapping):
        assert overflow.reverse_lookup_msgid("nicht vorhanden", "de") == ("", "nicht vorhanden")


    def test_missing_po_file_degrades_gracefully(self, tmp_path, monkeypatch):
        monkeypatch.setattr(overflow, "_po_path", lambda locale: str(tmp_path / "nope.po"))
        monkeypatch.setattr(overflow, "_po_cache", {})
        assert overflow.reverse_lookup_msgid("irgendwas", "de") == ("", "irgendwas")



class TestWrapText:
    def setup_method(self):
        from PIL import ImageFont
        self.font = ImageFont.load_default()


    def test_short_text_is_one_line(self):
        assert overflow._wrap_text("hello", self.font, 500) == ["hello"]


    def test_wraps_on_word_boundaries(self):
        lines = overflow._wrap_text("aaa bbb ccc ddd", self.font, 30)
        assert len(lines) > 1
        assert "".join(lines).replace(" ", "") == "aaabbbcccddd"


    def test_unbroken_word_falls_back_to_character_break(self):
        # No spaces to break on (the CJK case): must still wrap
        lines = overflow._wrap_text("a" * 200, self.font, 40)
        assert len(lines) > 1
        assert "".join(lines) == "a" * 200


    def test_preserves_explicit_newlines(self):
        assert overflow._wrap_text("one\ntwo", self.font, 500) == ["one", "two"]



class TestReports:
    def make_event(self, **over):
        defaults = dict(
            event_type="bounds", screen_name="SomeView", locale="de",
            component_text="text", overflow_px=12, component_type="TextArea",
            screen_y=200, effective_height=52, msgid="src", msgstr="text",
        )
        defaults.update(over)
        return overflow.OverflowEvent(**defaults)


    def test_write_summary(self, tmp_path):
        events = [self.make_event(), self.make_event(event_type="collision", overflow_px=30)]
        path = overflow.write_summary(events, str(tmp_path), "de")

        content = open(path, encoding="utf-8").read()
        assert "Total issues: 2" in content
        # Sorted by descending overflow
        assert content.index("30px") < content.index("12px")


    def test_write_json_round_trip(self, tmp_path):
        path = str(tmp_path / "overflow.json")
        overflow.write_json([self.make_event()], path, "de")

        data = json.loads(open(path, encoding="utf-8").read())
        assert list(data.keys()) == ["de"]
        assert data["de"][0]["event_type"] == "bounds"
        assert data["de"][0]["overflow_px"] == 12
        assert data["de"][0]["msgid"] == "src"


    def test_write_json_merges_locales_and_replaces_rescans(self, tmp_path):
        path = str(tmp_path / "overflow.json")
        overflow.write_json([self.make_event(locale="de")], path, "de")
        overflow.write_json([self.make_event(locale="ja"), self.make_event(locale="ja")], path, "ja")
        # Rescan of de comes up clean; its entry must be replaced, not appended
        overflow.write_json([], path, "de")

        data = json.loads(open(path, encoding="utf-8").read())
        assert data["de"] == []
        assert len(data["ja"]) == 2


    def test_write_json_empty_scan_still_records_the_locale(self, tmp_path):
        path = str(tmp_path / "overflow.json")
        overflow.write_json([], path, "de")

        data = json.loads(open(path, encoding="utf-8").read())
        assert data == {"de": []}


    def test_write_json_recovers_from_corrupt_file(self, tmp_path):
        path = tmp_path / "overflow.json"
        path.write_text("{ not json", encoding="utf-8")
        overflow.write_json([self.make_event()], str(path), "de")

        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["de"]) == 1



class TestCompositeImage:
    def test_composite_layout(self, tmp_path):
        from PIL import Image

        en_path = tmp_path / "en.png"
        tr_path = tmp_path / "tr.png"
        Image.new("RGB", (240, 240), color=(10, 10, 10)).save(en_path)
        Image.new("RGB", (240, 240), color=(20, 20, 20)).save(tr_path)

        event = overflow.OverflowEvent(
            event_type="bounds", screen_name="SomeView", locale="de",
            component_text="text", overflow_px=12, component_type="TextArea",
            screen_y=200, effective_height=52, msgid="src", msgstr="text")
        composite = overflow.generate_composite_image(
            str(en_path), str(tr_path), [event], "SomeView")

        # Side-by-side + padding wide; taller than one screen (header + annotations)
        assert composite.width == 16 + 240 + 16 + 240 + 16
        assert composite.height > 240


    def test_missing_en_screenshot_uses_placeholder(self, tmp_path):
        from PIL import Image

        tr_path = tmp_path / "tr.png"
        Image.new("RGB", (240, 240), color=(20, 20, 20)).save(tr_path)

        composite = overflow.generate_composite_image(
            str(tmp_path / "missing.png"), str(tr_path), [], "SomeView")
        assert composite.width == 528


class TestWriteReports:
    def setup_screens(self, tmp_path):
        from PIL import Image
        for rel in ["en/section_a/SomeView.png", "de/section_a/SomeView.png"]:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (240, 240), color=(10, 10, 10)).save(path)

    def make_event(self):
        return overflow.OverflowEvent(
            event_type="bounds", screen_name="SomeView", locale="de",
            component_text="zu lang", overflow_px=12, component_type="TextArea",
            screen_y=200, effective_height=52)

    def test_full_report(self, tmp_path, monkeypatch):
        # No .po available: msgid resolution degrades to an empty msgid
        monkeypatch.setattr(overflow, "_po_path", lambda locale: str(tmp_path / "nope.po"))
        monkeypatch.setattr(overflow, "_po_cache", {})
        self.setup_screens(tmp_path)
        json_path = tmp_path / "overflow.json"

        overflow.write_reports([self.make_event()], {"SomeView": "section_a"},
                               str(tmp_path), "de", json_path=str(json_path))

        report_dir = tmp_path / "reports" / "de"
        assert (report_dir / "summary.txt").exists()
        assert (report_dir / "SomeView_overflow.png").exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["de"][0]["msgstr"] == "zu lang"

    def test_rescan_clears_stale_report(self, tmp_path):
        self.setup_screens(tmp_path)
        stale = tmp_path / "reports" / "de" / "OldView_overflow.png"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"stale")

        overflow.write_reports([], {}, str(tmp_path), "de")

        assert not stale.exists()

    def test_json_only_mode_writes_no_human_report(self, tmp_path):
        self.setup_screens(tmp_path)
        json_path = tmp_path / "overflow.json"

        overflow.write_reports([], {}, str(tmp_path), "de",
                               json_path=str(json_path), human_report=False)

        assert json.loads(json_path.read_text(encoding="utf-8")) == {"de": []}
        assert not (tmp_path / "reports").exists()
