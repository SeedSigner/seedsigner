# AGENTS.md

## What this repo is

SeedSigner is an air-gapped, stateless Bitcoin signing device built from inexpensive
Raspberry Pi hardware. It keeps seeds only in memory, and it talks to the outside world only
by scanning QR codes with its camera and showing QR codes on its screen.

**This repo contains only the Python application.** Two sibling repositories complete the
product:

| Repo | Contents |
| --- | --- |
| `SeedSigner/seedsigner` (here) | The app: Views/Screens/Controller, seed handling, PSBT + QR, tests. |
| [`SeedSigner/seedsigner-os`](https://github.com/SeedSigner/seedsigner-os) | Buildroot-based OS: kernel config, board defconfigs, rootfs overlay, image build. |
| [`SeedSigner/seedsigner-translations`](https://github.com/SeedSigner/seedsigner-translations) | `.po` catalogs plus the Arabic, CJK and Thai fonts. A git submodule here. |

**The docs in this repo often lag the code.** That includes `docs/`, the READMEs and this
file. Treat the source tree as the source of truth, and check any command, path or behavior
a doc describes against the code before you rely on it.

## Repo map

| Path | Contents |
| --- | --- |
| `src/main.py` | Entry point. Parses `--loglevel`, starts `Controller`. |
| `src/seedsigner/controller.py` | `Controller` singleton, `BackStack`, main loop. |
| `src/seedsigner/views/` | Business logic per screen. Returns `Destination`s. |
| `src/seedsigner/gui/` | `Renderer`, `screens/` (generic and per-domain Screens), `components.py` (primitives), keyboard, toasts. |
| `src/seedsigner/models/` | `Settings`, `SettingsDefinition`, `Seed`, `SeedStorage`, PSBT parser, QR encode/decode. |
| `src/seedsigner/hardware/` | Buttons, camera, microSD, display drivers. |
| `src/seedsigner/helpers/` | embit utils, mnemonic generation, l10n, version, vendored `ur2/`. |
| `src/seedsigner/resources/` | Fonts, icons, images, and the translations submodule. |
| `tests/` | pytest suite, `base.py`, `psbt_testing_util.py`, `screenshot_generator/`. |
| `l10n/` | `messages.pot` and the localization guide. |
| `docs/` | Project documentation. |
| `tools/` | Standalone CLI scripts (mnemonic verification, testing/dev-only SeedQR generator, version file writer). |
| `seedsigner-screenshots/` | Submodule the screenshot generator writes into. Not checked out by default. |
| `enclosures/`, `docker/` | 3D print files; a test-only container. |

## Architecture

Roughly MVC, deliberately shaped like a Flask app (see `docs/code_structure.md`).
Canonical files: `src/seedsigner/controller.py`, `src/seedsigner/views/view.py`,
`src/seedsigner/gui/screens/screen.py`.

- A `View` holds business logic and returns a `Destination`, much like a web app returning
  `response.redirect(URL)`. A `Screen` draws and takes input. `gui/components` are
  primitives. Views must not know about pixel-level rendering.
- `Destination(View_cls, view_args, skip_current_view, clear_history)`. `BackStackView` is
  an empty marker class meaning "pop the back stack".
- **Screen lifecycle:** `View.run_screen()` creates the Screen and calls `display()`, which
  renders it, starts its threads and returns what `_run()` returns. Override `_run()` for
  interaction and `_render()` for custom drawing. Screens are dataclasses, so a subclass's
  `__post_init__` must call `super().__post_init__()`.
- `Controller` and `Settings` are singletons (`models/singleton.py`). The `Controller`
  holds all cross-view state. Going to `MainMenuView` clears the back stack,
  `resume_main_flow`, and the PSBT, descriptor and address state (`Controller.start()`),
  but not sign-message data, image-entropy frames or the seeds in `SeedStorage`.
- Multi-step journeys that can be interrupted (scan a QR mid-flow, then resume) are tracked
  by `Controller.resume_main_flow` against the `FLOW__*` constants in `controller.py`.

Two things that trip people up:

- **Redirect pattern:** to leave a View before it runs, call
  `self.set_redirect(destination)` from `__init__` / `__post_init__` and return
  immediately. Call `super().__init__()` (or `super().__post_init__()`) first: it resets
  the redirect, and a View that skips it raises on `has_redirect`.
- **Imports:** circular imports are structural here (`controller.py` documents this), so
  import `Controller`, and any sibling View module that could import yours back, inside
  methods. Generic Screens and the base classes in `views/view.py` are fine at module top.
  `LoadingScreenThread` must be imported inside methods, because `tests/base.py` patches
  it at its source.

## Core domain

- **Seeds** (`models/seed.py`) are BIP-39 mnemonics, optionally with a passphrase, plus an
  `ElectrumSeed` subclass with deliberately reduced functionality (`docs/electrum.md`).
  They live in `SeedStorage` on the `Controller`, in memory only, for as long as the device
  is powered.
- **Seed creation** supports BIP-39 word entry, dice rolls, and camera image entropy. The
  entropy-to-mnemonic code is in `helpers/mnemonic_generation.py`; `tools/mnemonic.py`
  wraps it as a verification CLI (see `docs/dice_verification.md`).
- **QR is the only I/O channel.** `QRType` in `models/qr_type.py` lists the formats
  `models/decode_qr.py` recognizes; the output formats are the encoder classes in
  `models/encode_qr.py`. The SeedQR spec and its test vectors are in `docs/seed_qr/`.
- **PSBT signing:** `models/psbt_parser.py` treats everything the coordinator supplies as
  an unverified claim. Only `verified_*` values, re-derived from the seed or a user-supplied
  descriptor, may drive a decision; `claimed_*` values are for display only (see the
  `PSBTParser` docstring). Failed checks raise `PSBTVerificationError` subclasses, which
  `PSBTOverviewView` routes to error Views. The review flow in `views/psbt_views.py`:
  overview → a warning if needed → math → address details → change details → OP_RETURN →
  finalize.
- **Settings** are declared, not hardcoded: every option is a `SettingsEntry` in
  `models/settings_definition.py`, which drives the settings UI, SettingsQR parsing, and
  on-disk persistence automatically. Add options there, not in the views.
- Views are grouped by domain: `psbt_views`, `scan_views`, `seed_views`, `settings_views`,
  `tools_views`.

## Runtime environment

In production the app runs on SeedSigner OS, not a general-purpose Linux host, and the
differences matter when writing code:

- **No TCP/IP networking.** Release kernels have no IP stack, network interfaces, Wi-Fi or
  Bluetooth (`CONFIG_NET` is on only so mdev can get hotplug events over netlink), and
  BusyBox has no networking applets. Don't assume sockets, DNS, HTTP or NTP.
- **The root filesystem is an initramfs in RAM** and is discarded on power-off. The only
  persistent writable location is `/mnt/microsd`, the FAT boot partition, while a card is
  inserted. `settings.json` goes there if the user enables persistent settings.
- **The app runs as root** from `/opt/src`, started by a BusyBox init script. No account can
  log in: root and the system accounts are all locked.
- **The shipped tree is stripped.** `tests/`, `tools/`, `docs/`, `.git` and packaging
  metadata don't reach the device. Parts of the Python standard library are removed too
  (`asyncio`, `email`, `http`, `xml`, `tarfile`, `unittest`, `multiprocessing` and more;
  see `post-build.sh` in seedsigner-os), so an import that passes CI can still fail on the
  device.
- **Behavior is keyed off the hostname.** `Settings.HOSTNAME` is compared against
  `Settings.SEEDSIGNER_OS` (`"seedsigner-os"`) to choose the settings path, microSD
  detection and version lookups. Dev OS images and Raspberry Pi OS builds use other
  hostnames and take the fallback paths. Mark dev-only code (such as the one HTTP call, in
  `helpers/version.py`) with `@not_allowed_in_seedsigner_os`.
- **Python:** the device runs Python 3.12, but `requires-python` is `>=3.10` and CI also
  tests 3.10, so code must stay 3.10-compatible.
- `-dev` OS images add networking and SSH for on-device development and are explicitly not
  security-hardened. They are not representative of production.

[`docs/seedsigner_os.md`](docs/seedsigner_os.md) covers the OS in depth: the boot chain, how
this repo's code gets into an image, per-board hardware differences, and reproducible
builds. Read it before changing anything that touches boot, packaging, persistence, or
process privileges, and before drawing conclusions about the device's security properties.

## Commands

Run these from the repo root.

```bash
pip3 install -r requirements.txt -r tests/requirements.txt -r l10n/requirements-l10n.txt
pip3 install -e .                      # required: `seedsigner` must be importable
                                       # system dep: libzbar0 (or zbar-tools)
python setup.py compile_catalog        # .po -> .mo; needed for non-English locales, the
                                       # l10n tests and the screenshot generator
pytest
pytest tests/test_seed.py::test_name
pytest tests/screenshot_generator/generator.py --locale es
./tests/run_full_coverage.sh
```

Clone with `--recurse-submodules`. **No linter or formatter is configured**: match the style
of the surrounding code and do not reformat untouched lines.

## Testing

- Read `tests/base.py` first. It stubs the hardware modules (and a few heavy ones) into
  `sys.modules` with `MagicMock` **before** any `seedsigner` import, and that ordering is
  load-bearing. `BaseTest` resets the `Controller` and `Settings` singletons between tests.
  The screenshot generator has its own stubs. No emulator lives in this repo.
- `FlowTest` / `FlowStep` / `run_sequence()` is the framework for asserting navigation
  sequences. From the PR template: "Any new or altered functionality should be covered in a
  unit test. Any new or updated sequences require FlowTests."
- PSBT tests build their fixtures with `tests/psbt_testing_util.py`.
- The camera, video stream and display drivers are `omit`-ed from coverage in
  `pyproject.toml`; don't chase coverage there.
- New or changed Screens need screenshots in the PR. Add a `ScreenshotConfig` (a View and
  its arguments) that reaches each one in `tests/screenshot_generator/generator.py`; apart
  from settings entries, nothing is picked up automatically, and CI renders every locale.
  Output goes to the `seedsigner-screenshots/` submodule; never commit it. The generator
  hard-fails without libraqm, which device-accurate rendering needs.

## Localization

Catalogs live in the **`seedsigner-translations` submodule** at
`src/seedsigner/resources/seedsigner-translations` (tracks `dev`), together with the Arabic,
CJK and Thai fonts (Devanagari is in `resources/fonts/`). `*.po` and `*.mo` are gitignored
in *this* repo. `SettingsConstants.get_detected_languages()` lists a language when its `.mo`
file exists and it is in `ALL_LOCALES`. Scripts the default OpenSans font doesn't cover
(Arabic, CJK, Devanagari, Thai) also need a font and a `BASE_LOCALE_FONTS` entry in
`gui/components.py`. Release builds trim the Arabic, CJK and Thai fonts to the characters
the catalogs use, so text in those scripts that isn't in a catalog won't render on the
device.

Translation happens on **Transifex**, not in pull requests. Pull with `tx pull -f --all`
from the submodule directory, then run `python setup.py compile_catalog` from the repo
root.

Three marking techniques, with the full rationale in [`l10n/README.md`](l10n/README.md):

- **`ButtonOption("...")`** for `button_data` entries. Marks the string for translation but
  **never returns a translated value**, because class attributes are evaluated once at
  import time and the English literal must stay the lookup key.
- **`_mft("...")`** (`mark_for_translation`, a no-op in `helpers/l10n.py`) for other
  class-level attributes. Use it sparingly.
- **`from gettext import gettext as _`** for dynamically evaluated code. Marks *and*
  retrieves.

Rule of thumb, from `l10n/README.md`: *"Mark for translation in the `View`. Retrieve
translated values in the `Screen`. Pass final display text into the basic gui
`Component`s."*

A `# TRANSLATOR_NOTE:` comment must sit on the line immediately before the executable line
it annotates. `.format()` goes **outside** the `_()` wrapper. Use `ngettext` for plurals.
Extraction keywords are configured in `setup.cfg`.

## Conventions

- The default branch is **`dev`**, not `main`. Both submodules track `dev`.
- From `.github/pull_request_template.md`: keep changes limited in scope, split unrelated
  findings into separate PRs, include screenshots for UI changes, and state which platform
  you tested on hands-on.
- Navigation wording (`views/view.py`): "Next" continues, "Done" ends a flow
  non-destructively, "OK"/"Close" exits a screen non-destructively, "Cancel" ends a task
  destructively.
