"""Tests for the manifest validator: schema enforcement plus trust anchors.

This is the security boundary between the untrusted diff job and the trusted
comment job, so each rejection path is checked explicitly.
"""

import json
import os

import pytest

pytest.importorskip("jsonschema")

import validate_manifest  # noqa: E402

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "schema",
                      "review-manifest.schema.json")
HEAD = "a" * 40
REPO = "owner/repo"

EMPTY_DIFF = {
    "added": [], "removed": [], "changed": [],
    "counts": {"added": 0, "removed": 0, "changed": 0,
               "total_base": 0, "total_head": 0},
    "truncated": False,
}


def valid_manifest(**over):
    m = {
        "schema_version": "1.0",
        "stream": "messages-pot",
        "generated_at": "2026-06-09T00:00:00Z",
        "repository": REPO,
        "pr": {"number": 7, "head_sha": HEAD, "base_sha": None, "base_ref": "dev"},
        "regen_ok": True,
        "source_strings": dict(EMPTY_DIFF),
        "notes": [],
    }
    m.update(over)
    return m


def run(tmp_path, manifest, *, head=HEAD, repo=REPO):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return validate_manifest.validate(str(p), SCHEMA, head, repo)


def test_valid_manifest_has_no_errors(tmp_path):
    assert run(tmp_path, valid_manifest()) == []


def test_wrong_repository_rejected(tmp_path):
    errors = run(tmp_path, valid_manifest(), repo="someone/else")
    assert any("repository" in e for e in errors)


def test_wrong_head_sha_rejected(tmp_path):
    errors = run(tmp_path, valid_manifest(), head="b" * 40)
    assert any("head" in e for e in errors)


def test_schema_version_must_match(tmp_path):
    # schema_version is a const, so any other value must be rejected.
    errors = run(tmp_path, valid_manifest(schema_version="2.0"))
    assert any(e.startswith("schema:") for e in errors)


def test_unknown_top_level_field_rejected(tmp_path):
    # additionalProperties:false guards against smuggled fields.
    errors = run(tmp_path, valid_manifest(injected="surprise"))
    assert any(e.startswith("schema:") for e in errors)


def test_oversized_entry_list_rejected(tmp_path):
    # The 50-entry cap lives in the untrusted producer; the schema must enforce
    # it independently so a tampered producer cannot emit an unbounded list.
    entry = {"msgid": "x", "msgctxt": None, "plural": False}
    oversized = dict(EMPTY_DIFF, added=[entry] * 51)
    errors = run(tmp_path, valid_manifest(source_strings=oversized))
    assert any(e.startswith("schema:") for e in errors)


def test_missing_manifest_is_a_clean_error(tmp_path):
    errors = validate_manifest.validate(
        str(tmp_path / "nope.json"), SCHEMA, HEAD, REPO)
    assert any(e.startswith("manifest: cannot read") for e in errors)


def test_malformed_manifest_is_a_clean_error(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{ this is not json", encoding="utf-8")
    errors = validate_manifest.validate(str(p), SCHEMA, HEAD, REPO)
    assert any("is not valid JSON" in e for e in errors)


def test_empty_manifest_is_a_clean_error(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("", encoding="utf-8")
    errors = validate_manifest.validate(str(p), SCHEMA, HEAD, REPO)
    assert any("is not valid JSON" in e for e in errors)


def test_non_object_manifest_is_rejected(tmp_path):
    # Valid JSON, but not an object: must never validate clean, and must not
    # reach the .get() calls that assume a mapping.
    for payload in ("null", "[]", '"nope"'):
        p = tmp_path / "manifest.json"
        p.write_text(payload, encoding="utf-8")
        errors = validate_manifest.validate(str(p), SCHEMA, HEAD, REPO)
        assert f"manifest: {str(p)!r} is not a JSON object" in errors
