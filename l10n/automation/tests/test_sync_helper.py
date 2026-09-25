"""Tests for the post-merge change-detection helper."""

import pytest

pytest.importorskip("babel")

import pot_sync_helper  # noqa: E402
from conftest import write_pot  # noqa: E402


def test_no_change_when_strings_match(tmp_path):
    committed = write_pot(tmp_path / "c.pot", [{"id": "Hello"}, {"id": "Bye"}])
    regen = write_pot(tmp_path / "r.pot", [{"id": "Hello"}, {"id": "Bye"}])
    changed, counts = pot_sync_helper.has_meaningful_change(committed, regen)
    assert changed is False
    assert counts["added"] == counts["removed"] == counts["changed"] == 0


def test_change_when_string_added(tmp_path):
    committed = write_pot(tmp_path / "c.pot", [{"id": "Hello"}])
    regen = write_pot(tmp_path / "r.pot", [{"id": "Hello"}, {"id": "New"}])
    changed, counts = pot_sync_helper.has_meaningful_change(committed, regen)
    assert changed is True
    assert counts["added"] == 1


def test_cli_outputs_bool(tmp_path, capsys):
    committed = write_pot(tmp_path / "c.pot", [{"id": "Hello"}])
    regen = write_pot(tmp_path / "r.pot", [{"id": "Hello"}, {"id": "New"}])
    rc = pot_sync_helper.main(["--committed", committed, "--regenerated", regen])
    out = capsys.readouterr()
    assert rc == 0
    assert out.out.strip() == "true"
