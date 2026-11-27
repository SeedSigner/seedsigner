"""Tests for the advisory-comment renderer (red/green diff block + fence safety)."""

import json

import render_comment


def base_manifest(**over):
    m = {
        "schema_version": "1.0", "stream": "messages-pot",
        "generated_at": "2026-06-20T00:00:00Z", "repository": "owner/repo",
        "pr": {"number": 1, "head_sha": "abc", "base_sha": None, "base_ref": "dev"},
        "regen_ok": True,
        "source_strings": {"added": [], "removed": [], "changed": [],
                           "counts": {"added": 0, "removed": 0, "changed": 0,
                                      "total_base": 0, "total_head": 0},
                           "truncated": False},
        "notes": [],
    }
    m.update(over)
    return m


def test_render_marker_and_no_changes():
    body = render_comment.render(base_manifest())
    assert render_comment.COMMENT_MARKER in body
    assert "no changes to the translatable source strings" in body
    # Never nags the author to update or commit the catalog.
    assert "extract_messages" not in body
    assert "out of date" not in body


def test_render_diff_block_red_green():
    m = base_manifest(source_strings={
        "added": [{"msgid": "New label", "msgctxt": "menu", "plural": False},
                  {"msgid": "New plural", "msgctxt": None, "plural": True}],
        "removed": [{"msgid": "Old label", "msgctxt": None, "plural": False}],
        "changed": [{"msgid": "Toggles", "msgctxt": None, "plural": True}],
        "counts": {"added": 2, "removed": 1, "changed": 1,
                   "total_base": 10, "total_head": 11},
        "truncated": False})
    body = render_comment.render(m)
    assert "```diff" in body
    assert "+ New label    [ctx: menu]" in body
    assert "+ New plural    [plural]" in body
    assert "- Old label" in body
    # A changed entry is one line annotated with the head state; the manifest
    # does not say whether the plural form was gained, lost or reworded, so the
    # comment must not claim a singular/plural toggle.
    assert "+ Toggles    [plural; plural form changed]" in body
    assert "was singular form" not in body
    assert "now plural form" not in body


def test_render_truncation_note():
    added = [{"msgid": f"s{i}", "msgctxt": None, "plural": False} for i in range(50)]
    m = base_manifest(source_strings={
        "added": added, "removed": [], "changed": [],
        "counts": {"added": 63, "removed": 0, "changed": 0,
                   "total_base": 0, "total_head": 63},
        "truncated": True})
    body = render_comment.render(m)
    assert "...and 13 more added (count above)" in body


def test_render_fences_untrusted_msgid_safely():
    # Newlines flattened + a +/- prefix mean attacker text cannot start a line
    # and break out of the diff fence to inject markdown/HTML.
    nasty = "evil\n```\n## pwned heading\n- nope"
    m = base_manifest(source_strings={
        "added": [{"msgid": nasty, "msgctxt": None, "plural": False}],
        "removed": [], "changed": [],
        "counts": {"added": 1, "removed": 0, "changed": 0,
                   "total_base": 0, "total_head": 1},
        "truncated": False})
    body = render_comment.render(m)
    assert "+ evil\\n```\\n## pwned heading\\n- nope" in body
    assert body.count("```diff") == 1
    for line in body.splitlines():
        assert not line.startswith("## pwned")


def test_render_flattens_untrusted_notes():
    # Notes come from the manifest (untrusted producer); newlines are flattened
    # so a note cannot start a fresh line and break out of the blockquote to
    # inject markdown.
    m = base_manifest(notes=["regen failed\n\n## pwned heading\n- nope"])
    body = render_comment.render(m)
    assert "> **Note:** regen failed  ## pwned heading - nope" in body
    for line in body.splitlines():
        assert not line.startswith("## pwned")
        assert not line.startswith("- nope")


def test_non_ascii_survives_both_output_paths(tmp_path, capsysbinary):
    # Source strings are embedded verbatim, so neither output path may depend
    # on the runner's stdout encoding being UTF-8. Escaped so this file itself
    # stays ASCII.
    accented = "Phrase de passe : r\u00e9essayez"
    m = base_manifest(source_strings={
        "added": [{"msgid": accented, "msgctxt": None, "plural": False}],
        "removed": [], "changed": [],
        "counts": {"added": 1, "removed": 0, "changed": 0,
                   "total_base": 0, "total_head": 1},
        "truncated": False})
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(m), encoding="utf-8")
    out = tmp_path / "body.md"

    assert render_comment.main(["--manifest", str(manifest_path),
                                "--out", str(out)]) == 0
    assert accented in out.read_text(encoding="utf-8")

    assert render_comment.main(["--manifest", str(manifest_path),
                                "--out", "-"]) == 0
    assert accented in capsysbinary.readouterr().out.decode("utf-8")
