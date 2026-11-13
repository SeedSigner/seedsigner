"""Decide whether a freshly regenerated messages.pot is a meaningful change.

Used by the post-merge sync workflow to stay idempotent: the rolling PR and the
translations mirror are only touched when source strings actually changed.
Header churn (e.g. POT-Creation-Date) and source-location moves are ignored,
because they carry no translator-facing meaning.

Prints ``true``/``false`` to stdout and a human summary to stderr.
"""

import argparse
import sys

import pot_diff


def has_meaningful_change(committed_path: str, regenerated_path: str) -> tuple[bool, dict]:
    committed = pot_diff.load_catalog(committed_path)
    regenerated = pot_diff.load_catalog(regenerated_path)
    diff = pot_diff.diff_catalogs(committed, regenerated)
    c = diff["counts"]
    changed = bool(c["added"] or c["removed"] or c["changed"])
    return changed, c


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--committed", required=True)
    p.add_argument("--regenerated", required=True)
    args = p.parse_args(argv)

    changed, c = has_meaningful_change(args.committed, args.regenerated)
    print("true" if changed else "false")
    print(
        f"source strings: +{c['added']} -{c['removed']} ~{c['changed']} "
        f"(committed={c['total_base']}, regenerated={c['total_head']})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
