"""Tests for the catalog diff and review-manifest builder.

Run standalone (not part of the main suite):

    python -m pytest l10n/automation/tests -q
"""

import json

import pytest

# Parsing real .pot files needs Babel; skip cleanly where it is absent rather
# than erroring during collection.
pytest.importorskip("babel")

import pot_diff  # noqa: E402
from conftest import write_pot  # noqa: E402


def keys_of(entries):
    return {(e.get("msgctxt"), e["msgid"]) for e in entries}


def test_added_and_removed(tmp_path):
    base = write_pot(tmp_path / "base.pot", [{"id": "Hello"}, {"id": "Bye"}])
    head = write_pot(tmp_path / "head.pot", [{"id": "Hello"}, {"id": "New"}])

    d = pot_diff.diff_catalogs(pot_diff.load_catalog(base), pot_diff.load_catalog(head))

    assert keys_of(d["added"]) == {(None, "New")}
    assert keys_of(d["removed"]) == {(None, "Bye")}
    assert d["counts"] == {"added": 1, "removed": 1, "changed": 0,
                           "total_base": 2, "total_head": 2}
    assert d["truncated"] is False


def test_context_disambiguates(tmp_path):
    base = write_pot(tmp_path / "base.pot", [{"id": "File"}])
    head = write_pot(tmp_path / "head.pot", [{"id": "File"}, {"id": "File", "ctx": "menu"}])

    d = pot_diff.diff_catalogs(pot_diff.load_catalog(base), pot_diff.load_catalog(head))

    assert keys_of(d["added"]) == {("menu", "File")}
    assert d["counts"]["removed"] == 0


def test_plural_toggle_is_a_change(tmp_path):
    base = write_pot(tmp_path / "base.pot", [{"id": "apple"}])
    head = write_pot(tmp_path / "head.pot", [{"id": "apple", "plural": "apples"}])

    d = pot_diff.diff_catalogs(pot_diff.load_catalog(base), pot_diff.load_catalog(head))

    assert d["counts"] == {"added": 0, "removed": 0, "changed": 1,
                           "total_base": 1, "total_head": 1}
    assert d["changed"][0]["plural"] is True


def test_missing_files_are_empty(tmp_path):
    assert pot_diff.load_catalog(None) == {}
    assert pot_diff.load_catalog(str(tmp_path / "nope.pot")) == {}


def test_truncation_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(pot_diff, "MAX_ENTRIES", 2)
    base = write_pot(tmp_path / "base.pot", [])
    head = write_pot(tmp_path / "head.pot", [{"id": f"s{i}"} for i in range(5)])

    d = pot_diff.diff_catalogs(pot_diff.load_catalog(base), pot_diff.load_catalog(head))

    assert d["counts"]["added"] == 5  # exact
    assert len(d["added"]) == 2       # capped
    assert d["truncated"] is True


def test_manifest_reports_pr_impact(tmp_path):
    base = write_pot(tmp_path / "base.pot", [{"id": "Hello"}])
    head = write_pot(tmp_path / "head.pot", [{"id": "Hello"}, {"id": "New"}])

    m = pot_diff.build_manifest(
        base=base, head=head,
        repository="owner/repo", pr_number=7, head_sha="abc1234", base_ref="dev",
    )

    assert m["schema_version"] == "1.0"
    assert m["regen_ok"] is True
    assert m["source_strings"]["counts"]["added"] == 1  # "New" vs base


def test_manifest_regen_failure_is_noted(tmp_path):
    base = write_pot(tmp_path / "base.pot", [{"id": "Hello"}])
    head = write_pot(tmp_path / "head.pot", [{"id": "Hello"}, {"id": "New"}])

    m = pot_diff.build_manifest(
        base=base, head=head,
        repository="owner/repo", pr_number=9, head_sha="aaa", base_ref="dev",
        regen_ok=False,
    )

    assert m["regen_ok"] is False
    assert any("could not be fully regenerated" in n for n in m["notes"])


def test_cli_writes_manifest(tmp_path):
    base = write_pot(tmp_path / "base.pot", [{"id": "Hello"}])
    head = write_pot(tmp_path / "head.pot", [{"id": "Hello"}, {"id": "New"}])
    out = tmp_path / "manifest.json"

    rc = pot_diff.main([
        "--base", base, "--head", head,
        "--repository", "owner/repo", "--pr-number", "11",
        "--head-sha", "cafe123", "--base-ref", "dev", "--out", str(out),
    ])

    assert rc == 0
    manifest = json.loads(out.read_text())
    assert manifest["pr"]["number"] == 11
    assert manifest["repository"] == "owner/repo"
    assert manifest["source_strings"]["counts"]["added"] == 1


def test_non_ascii_survives_both_output_paths(tmp_path, capsysbinary):
    # ensure_ascii=False means the payload carries raw non-ASCII, so neither
    # output path may depend on the runner's stdout encoding being UTF-8.
    # Escaped so this file itself stays ASCII.
    accented = "Phrase de passe incorrecte : r\u00e9essayez"
    base = write_pot(tmp_path / "base.pot", [])
    head = write_pot(tmp_path / "head.pot", [{"id": accented}])
    out = tmp_path / "manifest.json"
    argv = ["--base", base, "--head", head, "--repository", "owner/repo",
            "--pr-number", "3", "--head-sha", "abc", "--base-ref", "dev"]

    assert pot_diff.main(argv + ["--out", str(out)]) == 0
    assert accented in out.read_text(encoding="utf-8")

    assert pot_diff.main(argv + ["--out", "-"]) == 0
    assert accented in capsysbinary.readouterr().out.decode("utf-8")
