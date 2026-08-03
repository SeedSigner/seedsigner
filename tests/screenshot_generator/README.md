# Screenshot Generator

The screenshot generator is implemented as a pytest test and writes its output to the
`seedsigner-screenshots` directory in the project root.

## Setup

Follow the [general test setup](../README.md#setup) before running the generator. The
translation catalogs are stored in a submodule and must be compiled before non-English
locales can be detected:

```bash
git submodule update --init --recursive \
    src/seedsigner/resources/seedsigner-translations
pip install -r l10n/requirements-l10n.txt
python setup.py compile_catalog
```

### macOS

The screenshot generator also needs the native `zbar` and `libraqm` libraries. These
steps use Python 3.12, which is included in the project's CI test matrix:

```bash
brew install python@3.12 zbar libraqm

"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
python -m pip install -r tests/requirements.txt
python -m pip install -r l10n/requirements-l10n.txt
python -m pip install -e .

# Rebuild Pillow so it detects Homebrew's libraqm installation.
python -m pip install --force-reinstall --no-binary Pillow Pillow==10.3.0

git submodule update --init --recursive \
    src/seedsigner/resources/seedsigner-translations
python setup.py compile_catalog

# Allow pyzbar to find Homebrew's libzbar at runtime.
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
```

Verify that Pillow was built with RAQM support:

```bash
python -c "from PIL import features; print(features.check('raqm'))"
```

The command should print `True`.

## Running the generator

From the project root, run:

```bash
# Generate screenshots for a specific locale
python -m pytest tests/screenshot_generator/generator.py --locale es

# Generate screenshots for all supported locales
python -m pytest tests/screenshot_generator/generator.py
```

You can also run a `coverage` report to see exactly what the screenshots are and are not hitting:

```bash
coverage erase
coverage run -m pytest tests/screenshot_generator/generator.py --locale es && coverage combine && coverage report

# Generate the interactive html report
coverage html
```
