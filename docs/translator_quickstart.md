# Translator Quickstart

This guide is for anyone who wants to help translate SeedSigner into their language. No coding experience is required — all translation work happens in a web interface.

## Join the project on Transifex

SeedSigner uses [Transifex](https://www.transifex.com/) for translation management.

1. Create a free account at [transifex.com](https://www.transifex.com/)
2. Join the SeedSigner project: [app.transifex.com/seedsigner/seedsigner](https://app.transifex.com/seedsigner/seedsigner)
3. Request to join the team for your language, or start a new one if it doesn't exist yet

Once accepted, you'll see a list of English strings to translate. Each string appears in the context it's used — button labels, screen titles, instructions, error messages, etc.

## Understanding translator notes

Some strings include a `TRANSLATOR_NOTE:` comment that provides context. These appear in Transifex above the string you're translating. Pay attention to them — they explain where the string appears and what it means. For example:

- *"Option when scanning for a matching address; skips ten addresses ahead"* — helps you pick the right word for "Skip"
- *"QR code density option: Low, Medium, High"* — clarifies that "Low" refers to density, not quantity

Strings with `{}` placeholders contain values that are filled in at runtime (like a number or a name). Keep the `{}` in your translation and don't change the order unless your language requires it.

## Checking your work

### Screenshot gallery

Once translations are pulled into the project, the screenshot gallery shows every screen rendered in every active locale. You can see exactly how your translations look on the device:

- **Online gallery**: [seedsigner.github.io/seedsigner](https://seedsigner.github.io/seedsigner/)
- Each locale page shows translation completion percentage and screenshots grouped by section (Main Menu, Seed, PSBT, Tools, Settings, etc.)

**A note on completion percentages**: The gallery calculates completion against the current `l10n/messages.pot` in the codebase, while Transifex shows completion against whatever `.pot` was last uploaded to it. If new translatable strings were added to the code but not yet uploaded to Transifex, your Transifex percentage may appear higher than the gallery's. This is normal — it just means new strings need to be synced to Transifex.

### Running locally

If you have a local dev setup, you can generate screenshots for your locale:

```bash
pip install -r requirements.txt -r tests/requirements.txt
pip install -e .
pytest tests/screenshot_generator/generator.py --locale <your_locale_code>
```

Screenshots are written to `seedsigner-screenshots/<your_locale_code>/`.

See [tests/screenshot_generator/README.md](../tests/screenshot_generator/README.md) for more details.

## Locale statuses

Languages in SeedSigner go through several stages in [`settings_definition.py`](../src/seedsigner/models/settings_definition.py):

| Status | Meaning |
|--------|---------|
| Fully supported | Shown in the language menu without any prefix |
| (beta) | Shown with a "(beta)" prefix — mostly translated but may have gaps |
| (incomplete) | Shown with "(incomplete)" — work in progress |
| Coming soon | Not yet visible to users — waiting for enough translation coverage |

A language becomes available to users once it has compiled `.mo` files in the translations submodule. The `get_detected_languages()` function auto-discovers these at runtime.

## Activating a new locale

If your language has reached enough coverage on Transifex (at least 15%), here's the process to make it available:

1. A maintainer pulls the `.po` file from Transifex into the [seedsigner-translations](https://github.com/SeedSigner/seedsigner-translations) repo at `l10n/<locale_code>/LC_MESSAGES/messages.po`
2. The `.mo` file is compiled: `python setup.py compile_catalog -l <locale_code>`
3. The locale entry in `ALL_LOCALES` in `settings_definition.py` is updated from "coming soon" to the appropriate status
4. A PR is opened against both the translations repo and the main SeedSigner repo

If you'd like to request activation for your language, open an issue on the [SeedSigner repo](https://github.com/SeedSigner/seedsigner/issues) mentioning your Transifex completion percentage.

## Further reading

- [l10n/README.md](../l10n/README.md) — full technical details on how translations are implemented in the codebase (the three wrapping techniques, extraction workflow, and more)
- [Transifex documentation](https://docs.transifex.com/) — general help with the Transifex platform
- [SeedSigner Devs Telegram](https://t.me/seedsigner_new_devs) — join to discuss translations and get help
