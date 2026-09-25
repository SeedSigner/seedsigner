"""Make the l10n automation modules importable when these tests run.

These tests are intentionally outside the project's configured `testpaths`
(["tests"]), so they are not collected by the main pytest run. Run them with:

    python -m pytest l10n/automation/tests
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_HEADER = 'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'


def write_pot(path, entries):
    """Write a minimal .pot file to path. entries: list of {id, plural?, ctx?}."""
    chunks = [_HEADER]
    for e in entries:
        block = ""
        if e.get("ctx"):
            block += f'msgctxt "{e["ctx"]}"\n'
        block += f'msgid "{e["id"]}"\n'
        if e.get("plural"):
            block += f'msgid_plural "{e["plural"]}"\n'
            block += 'msgstr[0] ""\nmsgstr[1] ""\n'
        else:
            block += 'msgstr ""\n'
        chunks.append(block + "\n")
    path.write_text("".join(chunks), encoding="utf-8")
    return str(path)
