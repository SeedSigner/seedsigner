# AGENTS.md

## What this repo is

SeedSigner is an air-gapped, stateless Bitcoin signing device built from inexpensive
Raspberry Pi hardware. It generates and stores seeds only in memory, and communicates with
the outside world exclusively by scanning QR codes with its camera and displaying QR codes
on its screen.

**This repo contains only the Python application.** Two sibling repositories complete the
product:

| Repo | Contents |
| --- | --- |
| `SeedSigner/seedsigner` (here) | The app: Views/Screens/Controller, seed handling, PSBT + QR, tests. |
| [`SeedSigner/seedsigner-os`](https://github.com/SeedSigner/seedsigner-os) | Buildroot-based OS: kernel config, board defconfigs, rootfs overlay, image build. |
| [`SeedSigner/seedsigner-translations`](https://github.com/SeedSigner/seedsigner-translations) | `.po`/`.mo` catalogs + non-Latin fonts. Vendored here as a git submodule. |

## Repo map

| Path | Contents |
| --- | --- |
| `src/main.py` | Entry point. Parses `--loglevel`, starts `Controller`. |
| `src/seedsigner/controller.py` | `Controller` singleton, `BackStack`, main loop. |
| `src/seedsigner/views/` | Business logic per screen. Returns `Destination`s. |
| `src/seedsigner/gui/` | `Renderer`, `screens/` (reusable UI), `components.py` (primitives). |
| `src/seedsigner/models/` | `Settings`, `SettingsDefinition`, `Seed`, `SeedStorage`, PSBT parser, QR encode/decode. |
| `src/seedsigner/hardware/` | Buttons, camera, microSD, display drivers. |
| `src/seedsigner/helpers/` | embit utils, mnemonic generation, l10n, version, vendored `ur2/`. |
| `src/seedsigner/resources/` | Fonts, icons, images, and the translations submodule. |
| `tests/` | pytest suite, `base.py`, `screenshot_generator/`. |
| `l10n/` | `messages.pot` and the localization guide. |
| `docs/` | Project documentation. |
| `tools/` | Standalone CLI scripts (mnemonic verification, version file writer). |
| `enclosures/`, `docker/` | 3D print files; a test-only container. |

## Architecture

Roughly MVC, deliberately shaped like a Flask app (see `docs/code_structure.md`).
Canonical files: `src/seedsigner/controller.py`, `src/seedsigner/views/view.py`,
`src/seedsigner/gui/screens/screen.py`.

- A `View` holds business logic and returns a `Destination` — analogous to a web app
  returning `response.redirect(URL)`. A `Screen` renders. `gui/components` are primitives.
  Views must not know about pixel-level rendering.
- `Destination(View_cls, view_args, skip_current_view, clear_history)`. `BackStackView` is
  an empty marker class meaning "pop the back stack".
- `Controller` and `Settings` are singletons (`models/singleton.py`). The `Controller`
  holds all cross-view state; `MainMenuView` is special-cased to wipe both the back stack
  and any in-progress flow.
- Multi-step journeys that can be interrupted (scan a QR mid-flow, then resume) are tracked
  by `Controller.resume_main_flow` against the `FLOW__*` constants in `controller.py`.

Two things that trip people up:

- **Redirect pattern:** call `self.set_redirect(destination)` from `__init__` /
  `__post_init__`, then return immediately. A View that fails to call
  `super().__init__()` raises on `has_redirect`. This is the most common footgun here.
- **Import `Controller`, Screens, and follow-on Views inside methods, not at module top.**
  Circular imports are structural in this design; `controller.py` documents this in-code.

## Core domain

- **Seeds** (`models/seed.py`) are BIP-39 mnemonics, optionally with a passphrase, plus an
  `ElectrumSeed` subclass with deliberately reduced functionality (`docs/electrum.md`).
  They live in `SeedStorage` on the `Controller` — in memory only, for as long as the
  device is powered.
- **Seed creation** supports BIP-39 word entry, dice rolls, and camera image entropy
  (`helpers/mnemonic_generation.py`, which doubles as a verification CLI — see
  `docs/dice_verification.md`).
- **QR is the only I/O channel.** `models/decode_qr.py`, `models/encode_qr.py`, and
  `models/qr_type.py` handle every supported format: animated UR2 PSBTs, Specter base64,
  SeedQR and CompactSeedQR, plain mnemonics, and SettingsQR. Formats are specified in
  `docs/qr_formats.md`; the SeedQR spec and its test vectors are in `docs/seed_qr/`.
- **PSBT signing** parses with `models/psbt_parser.py` and walks the user through a review
  flow in `views/psbt_views.py` (overview → math → address details → change verification →
  finalize) before anything is signed.
- **Settings** are declared, not hardcoded: every option is a `SettingsEntry` in
  `models/settings_definition.py`, which drives the settings UI, SettingsQR parsing, and
  on-disk persistence automatically. Add options there, not in the views.
- Views are grouped by domain: `psbt_views`, `scan_views`, `seed_views`, `settings_views`,
  `tools_views`.

## Runtime environment

In production the app runs on SeedSigner OS, not a general-purpose Linux host, and the
differences matter when writing code:

- **No network stack exists.** `CONFIG_NET` is not enabled in any release kernel, and
  BusyBox ships without networking applets. Nothing in this codebase may assume sockets,
  DNS, HTTP, or NTP are available.
- **The root filesystem is an initramfs in RAM** and is discarded on power-off. The only
  writable location is `/mnt/microsd`, the FAT boot partition, and only while a card is
  inserted — that is where `settings.json` goes if the user enables persistent settings.
- **The app runs as root** from `/opt/src`, launched by a BusyBox init script. There is no
  other user account; the root account has no password and cannot be logged into.
- **The shipped tree is stripped**: no `tests/`, `tools/`, `docs/`, `.git`, or packaging
  metadata reach the device. Don't rely on them at runtime.
- **Behavior is keyed off the hostname.** `Settings.HOSTNAME` is compared against the
  literal `"seedsigner-os"` to gate the settings path, microSD detection, and version
  lookups. Development images use a different hostname and take the fallback paths.
- `-dev` OS images add networking and SSH for on-device development and are explicitly not
  security-hardened. They are not representative of production.

[`docs/seedsigner_os.md`](docs/seedsigner_os.md) covers the OS in depth — boot chain, how
this repo's code gets into an image, per-board hardware differences, and reproducible
builds. Read it before changing anything that touches boot, packaging, persistence, or
process privileges, and before drawing conclusions about the device's security properties.

## Commands

```bash
pip3 install -r requirements.txt -r tests/requirements.txt -r l10n/requirements-l10n.txt
pip3 install -e .                      # required: `seedsigner` must be importable
                                       # system dep: libzbar0 (or zbar-tools)
python setup.py compile_catalog        # .po -> .mo; needed before running the app or l10n tests
pytest
pytest tests/test_seed.py::test_name
pytest tests/screenshot_generator/generator.py --locale es
./tests/run_full_coverage.sh
```

Python >= 3.10; CI runs 3.10 and 3.12. Clone with `--recurse-submodules`.
**No linter or formatter is configured** — match the style of surrounding code and do not
reformat untouched lines.

## Testing

- Read `tests/base.py` first. It stubs the hardware modules into `sys.modules` with
  `MagicMock` **before** any `seedsigner` import — that ordering is load-bearing, and it is
  the only way this code runs off-device. There is no emulator in the production tree.
  `BaseTest` resets the `Controller` and `Settings` singletons between tests.
- `FlowTest` / `FlowStep` / `run_sequence()` is the framework for asserting navigation
  sequences. New or changed **flows require FlowTests**; new or changed functionality
  requires unit tests. This is the PR template's wording, not a suggestion.
- Modules with hardware dependencies are `omit`-ed from coverage in `pyproject.toml` —
  don't chase coverage there.
- New or modified screens need screenshots in the PR; generate them with the screenshot
  generator. It hard-fails if libraqm is unavailable, since device-parity rendering
  depends on it.

## Localization

Catalogs live in the **`seedsigner-translations` submodule** at
`src/seedsigner/resources/seedsigner-translations` (tracks `dev`), together with the
CJK/Arabic/Devanagari fonts. `*.po` and `*.mo` are gitignored in *this* repo. 21 locales
currently ship. `SettingsConstants.get_detected_languages()` autodiscovers languages by
walking for `.mo` files, so shipping a catalog is what enables a language.

Translation happens on **Transifex**, not in pull requests. Pull with `tx pull -f --all`
from the submodule directory, then `python setup.py compile_catalog`.

Three marking techniques — full rationale in [`l10n/README.md`](l10n/README.md):

- **`ButtonOption("...")`** for `button_data` entries. Marks the string for translation but
  **never returns a translated value**, because class attributes are evaluated once at
  import time and the English literal must stay the lookup key.
- **`_mft("...")`** (`mark_for_translation`, a no-op in `helpers/l10n.py`) for other
  class-level attributes. Used sparingly; prefer to avoid it.
- **`from gettext import gettext as _`** for dynamically evaluated code. Marks *and*
  retrieves.

Rule of thumb, from `l10n/README.md`: *"Mark for translation in the `View`. Retrieve
translated values in the `Screen`. Pass final display text into the basic gui
`Component`s."*

A `# TRANSLATOR_NOTE:` comment must sit on the line immediately preceding the executable
line it annotates. `.format()` goes **outside** the `_()` wrapper. Use `ngettext` for
plurals. Extraction keywords are configured in `setup.cfg`.

## Conventions

- The default branch is **`dev`**, not `main`. Both submodules track `dev`.
- PR expectations come from `.github/pull_request_template.md`: keep changes limited in
  scope, split unrelated findings into separate PRs, include screenshots for UI changes,
  and state which platform you tested on hands-on.
- Navigation wording (`views/view.py`): "Next" continues, "Done" ends a flow
  non-destructively, "OK"/"Close" exits a screen non-destructively, "Cancel" ends a task
  destructively.
- **Documentation in `docs/` can lag the code.** Treat the source tree as authoritative
  and verify any command, path, or filename from a doc against the tree before acting on it.
