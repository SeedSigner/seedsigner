# Contributing to SeedSigner

## Localization

SeedSigner uses [Babel](https://babel.pocoo.org/) to extract translatable strings into `l10n/messages.pot`. If you add or change any string wrapped with `_()`, `_mft()`, or `ButtonOption()`, you must regenerate the `.pot` file before pushing:

```bash
pip install -r l10n/requirements-l10n.txt   # one-time setup
python setup.py extract_messages
```

CI will fail if `l10n/messages.pot` is out of date.

For more details on the three translation wrapping techniques and the full localization workflow, see `l10n/README.md`.
