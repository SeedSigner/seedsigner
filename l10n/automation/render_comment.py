"""Render the advisory PR comment markdown from a validated review manifest.

This runs in the trusted follow-up job from default-branch code, but the
manifest it consumes was produced by untrusted PR code. The source strings are
shown inside a ``diff`` fenced code block so GitHub colours them red/green, and
every entry line is prefixed with ``+``/``-`` with newlines flattened, so no
attacker-controlled text can start a line and break out of the code fence or
inject markup. (Fenced code is rendered literally, so HTML in a msgid shows as
text rather than executing.)

The comment is informational: it shows which translatable source strings the PR
changes. The canonical messages.pot is regenerated automatically after merge, so
the comment never asks the author to update or commit the catalog.
"""

import argparse
import html
import json
import sys
from typing import List

COMMENT_MARKER = "<!-- l10n-automation:comment=messages-pot -->"

# Keep individual rendered strings bounded regardless of source length.
_MAX_MSGID_CHARS = 200


def write_text(text: str, out: str) -> None:
    """Write UTF-8 text to ``out``, or to stdout when ``out`` is ``-``.

    The body embeds source strings verbatim, so writing to stdout goes through
    its binary buffer: a runner whose stdout encoding is ASCII would otherwise
    raise UnicodeEncodeError on the first non-ASCII string. The buffer is
    absent when stdout is substituted (captured in tests), in which case the
    text layer already handles the encoding.
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


def _clean(text: str) -> str:
    """Flatten to a single line and bound the length for safe fenced display."""
    flat = (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    if len(flat) > _MAX_MSGID_CHARS:
        flat = flat[:_MAX_MSGID_CHARS] + "..."
    return flat


def _annotations(entry: dict, *, include_plural: bool) -> List[str]:
    annos: List[str] = []
    ctx = entry.get("msgctxt")
    if ctx:
        annos.append(f"ctx: {_clean(str(ctx))}")
    if include_plural and entry.get("plural"):
        annos.append("plural")
    return annos


def _row(prefix: str, msgid: str, annos: List[str]) -> str:
    tail = f"    [{'; '.join(annos)}]" if annos else ""
    return f"{prefix} {_clean(msgid)}{tail}"


def _diff_block(impact: dict) -> List[str]:
    ic = impact["counts"]
    lines: List[str] = ["```diff"]

    for e in impact["added"]:
        lines.append(_row("+", e.get("msgid", ""), _annotations(e, include_plural=True)))
    if ic["added"] > len(impact["added"]):
        lines.append(f"  ...and {ic['added'] - len(impact['added'])} more added (count above)")

    for e in impact["removed"]:
        lines.append(_row("-", e.get("msgid", ""), _annotations(e, include_plural=True)))
    if ic["removed"] > len(impact["removed"]):
        lines.append(f"  ...and {ic['removed'] - len(impact['removed'])} more removed (count above)")

    # An entry is "changed" when its plural form gained, lost or reworded --
    # the manifest carries only the head state, not which of those it was, so
    # the annotation stays generic rather than claiming a singular/plural
    # toggle that may not have happened.
    for e in impact["changed"]:
        annos = _annotations(e, include_plural=True) + ["plural form changed"]
        lines.append(_row("+", e.get("msgid", ""), annos))
    if ic["changed"] > len(impact["changed"]):
        lines.append(f"  ...and {ic['changed'] - len(impact['changed'])} more changed (count above)")

    lines.append("```")
    return lines


def render(manifest: dict) -> str:
    impact = manifest["source_strings"]
    ic = impact["counts"]
    base_ref = (manifest["pr"].get("base_ref") or "base").replace("`", "")

    lines: List[str] = [COMMENT_MARKER, "## Localization: source-string impact", ""]

    if not manifest.get("regen_ok", True):
        lines += ["> **Warning:** Could not fully regenerate `messages.pot` from "
                  "this PR's source; the impact below may be incomplete.", ""]

    if ic["added"] == ic["removed"] == ic["changed"] == 0:
        lines += [f"This PR makes no changes to the translatable source strings "
                  f"(compared with `{base_ref}`)."]
    else:
        lines += [
            f"This PR changes the translatable source strings, compared with "
            f"`{base_ref}` ({ic['total_head']} strings total):",
            "",
            "| Added | Removed | Changed |",
            "| ----: | ------: | ------: |",
            f"| {ic['added']} | {ic['removed']} | {ic['changed']} |",
            "",
        ]
        lines += _diff_block(impact)

    for note in manifest.get("notes", []):
        lines += ["", f"> **Note:** {html.escape(' '.join(note.splitlines()))}"]

    lines += [
        "",
        "<sub>Advisory only; this check never blocks the PR. The canonical "
        "`l10n/messages.pot` is regenerated automatically after merge, so no "
        "manual update is needed.</sub>",
    ]
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Render advisory comment from a manifest.")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", default="-")
    args = p.parse_args(argv)

    with open(args.manifest, encoding="utf-8") as fh:
        manifest = json.load(fh)

    write_text(render(manifest), args.out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
