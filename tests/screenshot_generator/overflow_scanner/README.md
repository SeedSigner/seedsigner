# Translation Overflow Scanner

Detects layout overflow caused by translated text on SeedSigner's 240x240
screens. Runs as part of the screenshot generator with zero production code
changes.

## What it detects

- **Bounds overflow**: a component extends past the 240px canvas bottom.
- **Body-vs-button collision**: body content overlaps bottom-anchored buttons
  (only flagged when the overlap exceeds the English baseline).

## How it works

After each screen is fully constructed by the screenshot generator, the
scanner inspects the live component positions (`screen_y`, `height`) to check
for overflow. For fixed-height `TextArea` components, where text can render
past the allocated box, it recomputes the true rendered height from the
component's own attributes.

Flagged component text is resolved back to its `msgid`/`msgstr` pair through
the locale's `.po` catalog (parsed with Babel; plural forms map back to their
singular `msgid`, and format strings whose placeholders were substituted at
render time are matched by pattern).

For each flagged screen a composite PNG is generated with:

- English screenshot on the left, translated on the right
- red (bounds) / yellow (collision) outlines on the overflow areas
- the `msgid`, `msgstr`, and overflow amount in pixels

## Usage

### Single locale (via pytest)

```bash
PYTHONPATH=src python -m pytest tests/screenshot_generator/generator.py \
    --locale ja --overflow-scan -s
```

### Machine-readable output (for CI)

`--overflow-json <path>` writes the events as JSON, keyed by locale. An empty
list means the locale was scanned and came up clean. It can be combined with
`--overflow-scan` (human report + JSON) or used alone (JSON only, no
composites):

```bash
PYTHONPATH=src python -m pytest tests/screenshot_generator/generator.py \
    --locale ja --overflow-scan --overflow-json overflow.json -s
```

### Reviewing a translation change locally

Point the translations submodule at the catalogs to check (e.g. check out the
PR branch inside `src/seedsigner/resources/seedsigner-translations`), compile
and scan. English must be rendered first so the composites have their
left-hand side:

```bash
pybabel compile -d src/seedsigner/resources/seedsigner-translations/l10n -l ja --use-fuzzy
PYTHONPATH=src python -m pytest tests/screenshot_generator/generator.py --locale en
PYTHONPATH=src python -m pytest tests/screenshot_generator/generator.py \
    --locale ja --overflow-scan -s
```

## Output

```
seedsigner-screenshots/
  reports/
    <locale>/
      <ScreenName>_overflow.png    # annotated side-by-side composite
      summary.txt                  # one line per issue
```

The core scanner lives in `overflow.py`: `scan_for_overflow()`, the msgid
reverse lookup, the composite image generator and the report writers. Unit
tests live in `tests/screenshot_generator/test_overflow_scanner.py` and run
as part of the main suite.

## Known false positives and limitations

Overflow detection is advisory; a flagged screen needs human judgment:

- Translation PRs must be based on a commit that includes the `fonts/`
  directory in the translations submodule. Older PRs (predating
  seedsigner-translations PR #65) render with wrong font metrics and need a
  rebase onto `dev` first.
- `PSBTOpReturnView_raw_hex_data` overflow is caused by the long hex payload,
  not translation length. It appears in every locale identically.
- Untranslated literals can overflow without being a translation defect, e.g.
  `seedsigner.com` on `DonateView` is the same string in every locale.
- Placeholder bugs in a translation (e.g. positional `{}` where the source
  uses named `{mnemonic_length}`) crash at render time; that class of defect
  is caught by the translations repo's placeholder check, not this scanner.
