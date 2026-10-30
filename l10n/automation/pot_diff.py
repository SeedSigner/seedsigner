"""Structured diff between gettext catalogs (.pot/.po) for the l10n automation.

Produces the review manifest consumed by the trusted follow-up comment job.
Entries are keyed on (msgctxt, msgid); a change to a string's plural form is
reported as a change to that entry. Source-location churn and header metadata
are ignored, so they never show up as noise.

The manifest reports the source strings a PR changes: the catalog is extracted
from the base branch source and from the PR head source, and the two are
diffed. The committed messages.pot is never consulted, so the result is correct
regardless of whether it is up to date (it is maintained automatically by the
post-merge sync, not by hand).

Run as a script to emit a manifest JSON validated by
``l10n/automation/schema/review-manifest.schema.json``::

    python l10n/automation/pot_diff.py \
        --base base.pot --head head.pot \
        --repository owner/name --pr-number 123 \
        --head-sha <sha> --base-ref dev --out manifest.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

SCHEMA_VERSION = "1.0"
STREAM = "messages-pot"

# Cap how many individual entries we serialize per bucket. Counts stay exact;
# only the listed examples are capped (manifest.*.truncated flags this).
MAX_ENTRIES = 50

# Catalog key: (context, singular msgid). The context disambiguates identical
# source strings, exactly as gettext does.
Key = Tuple[Optional[str], str]


def write_text(text: str, out: str) -> None:
    """Write UTF-8 text to ``out``, or to stdout when ``out`` is ``-``.

    Source strings are emitted verbatim (``ensure_ascii=False``), so writing to
    stdout goes through its binary buffer: a runner whose stdout encoding is
    ASCII would otherwise raise UnicodeEncodeError on the first non-ASCII
    string. The buffer is absent when stdout is substituted (captured in
    tests), in which case the text layer already handles the encoding.
    """
    if out != "-":
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        return

    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(text)
    else:
        buffer.write(text.encode("utf-8"))
        buffer.flush()


def load_catalog(path: Optional[str]) -> Dict[Key, dict]:
    """Load a .pot/.po into a dict keyed by (msgctxt, msgid).

    A missing or empty path yields an empty catalog so the very first run (no
    prior .pot) and deleted files degrade gracefully rather than crashing.
    """
    if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
        return {}

    # Imported lazily so importing this module (e.g. for tests on hosts without
    # Babel) does not hard-fail; callers that actually parse need Babel present.
    from babel.messages.pofile import read_po

    with open(path, "rb") as fh:
        catalog = read_po(fh)

    out: Dict[Key, dict] = {}
    for message in catalog:
        # The header message has an empty id; skip it.
        if not message.id:
            continue
        if isinstance(message.id, (list, tuple)):
            singular = message.id[0]
            plural_text: Optional[str] = message.id[1] if len(message.id) > 1 else None
            is_plural = len(message.id) > 1
        else:
            singular = message.id
            plural_text = None
            is_plural = False
        key: Key = (message.context, singular)
        out[key] = {
            "msgid": singular,
            "msgctxt": message.context,
            "plural": is_plural,
            "_plural_text": plural_text,
        }
    return out


def _entry(record: dict) -> dict:
    # The manifest entry shape, kept to just the translator-facing fields.
    return {"msgid": record["msgid"], "msgctxt": record["msgctxt"], "plural": record["plural"]}


def _sorted_keys(keys) -> List[Key]:
    # Deterministic ordering: by context (None first), then msgid.
    return sorted(keys, key=lambda k: (k[0] is not None, k[0] or "", k[1]))


def diff_catalogs(base: Dict[Key, dict], head: Dict[Key, dict]) -> dict:
    """Compute added/removed/changed between two catalogs.

    * added   -- keys present in ``head`` but not ``base``
    * removed -- keys present in ``base`` but not ``head``
    * changed -- keys in both whose plural form (presence or text) differs,
                 i.e. what translators must now provide changed
    """
    base_keys = set(base)
    head_keys = set(head)

    added = [_entry(head[k]) for k in _sorted_keys(head_keys - base_keys)]
    removed = [_entry(base[k]) for k in _sorted_keys(base_keys - head_keys)]

    changed: List[dict] = []
    for k in _sorted_keys(base_keys & head_keys):
        b, h = base[k], head[k]
        if b["plural"] != h["plural"] or b.get("_plural_text") != h.get("_plural_text"):
            changed.append(_entry(h))

    counts = {
        "added": len(added),
        "removed": len(removed),
        "changed": len(changed),
        "total_base": len(base),
        "total_head": len(head),
    }
    truncated = any(len(b) > MAX_ENTRIES for b in (added, removed, changed))
    return {
        "added": added[:MAX_ENTRIES],
        "removed": removed[:MAX_ENTRIES],
        "changed": changed[:MAX_ENTRIES],
        "counts": counts,
        "truncated": truncated,
    }


def build_manifest(
    *,
    base: Optional[str],
    head: Optional[str],
    repository: str,
    pr_number: int,
    head_sha: str,
    base_ref: str,
    base_sha: Optional[str] = None,
    regen_ok: bool = True,
    generated_at: Optional[str] = None,
) -> dict:
    """Assemble the review manifest from the base and head catalogs.

    ``base`` and ``head`` are catalogs freshly extracted from the base branch
    source and the PR head source respectively, so ``source_strings`` reflects
    exactly the source strings this PR changes.
    """
    source_strings = diff_catalogs(load_catalog(base), load_catalog(head))

    notes: List[str] = []
    if not regen_ok:
        notes.append("messages.pot could not be fully regenerated from source; "
                     "the impact below may be incomplete.")

    return {
        "schema_version": SCHEMA_VERSION,
        "stream": STREAM,
        "generated_at": generated_at or datetime.now(timezone.utc)
        .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repository": repository,
        "pr": {
            "number": int(pr_number),
            "head_sha": head_sha,
            "base_sha": base_sha,
            "base_ref": base_ref,
        },
        "regen_ok": bool(regen_ok),
        "source_strings": source_strings,
        "notes": notes,
    }


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build the l10n review manifest.")
    p.add_argument("--base", help="messages.pot extracted from the base branch source")
    p.add_argument("--head", help="messages.pot extracted from the PR head source")
    p.add_argument("--repository", required=True)
    p.add_argument("--pr-number", type=int, required=True)
    p.add_argument("--head-sha", required=True)
    p.add_argument("--base-ref", required=True)
    p.add_argument("--base-sha", default=None)
    p.add_argument("--regen-ok", choices=["true", "false"], default="true",
                   help="whether extraction succeeded for both base and head")
    p.add_argument("--out", default="-", help="output path, or - for stdout")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    manifest = build_manifest(
        base=args.base,
        head=args.head,
        repository=args.repository,
        pr_number=args.pr_number,
        head_sha=args.head_sha,
        base_ref=args.base_ref,
        base_sha=args.base_sha,
        regen_ok=(args.regen_ok == "true"),
    )
    payload = json.dumps(manifest, indent=2, ensure_ascii=False)
    write_text(payload + "\n", args.out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
