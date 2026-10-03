# Running Tests

The tests are designed to be run on non-Raspi hardware.

## Setup
On your testing machine you'll have to install [uv](https://docs.astral.sh/uv/getting-started/installation/) and the `zbar` system library (`sudo apt-get install libzbar0` on Debian/Ubuntu, `brew install zbar` on macOS). Then, from the project root:
```bash
uv sync
```

This installs the pinned dependencies from `uv.lock` (including the test suite dependencies) and makes the `seedsigner` python module visible/importable to the tests (editable install).

The l10n tests need the compiled translation catalogs:
```bash
uv run poe translations-compile
```

## Running all tests, calculating overall test coverage
tldr: just run the `coverage` task from the project root:

```bash
uv run poe coverage
```

## Running tests manually
Run the whole test suite (any extra arguments are passed through to `pytest`):
```
uv run poe test
```

Run a specific test file:
```
uv run poe test tests/test_this_file.py
```

Run a specific test:
```
uv run poe test tests/test_this_file.py::test_this_specific_test
```

Force pytest to show logging output:
```bash
uv run poe test tests/test_this_file.py::test_this_specific_test -o log_cli=1

# or (same result)

uv run poe test tests/test_this_file.py::test_this_specific_test --log-cli-level=DEBUG
```

Annoying complications:
* If you want to see `print()` statements that are in a test file, add `-s`
* Better idea: use a proper logger in the test file and use one of the above options to display logs


## Screenshot generator
The screenshot generator is meant to mostly be a utility and not really part of the test suite. However,
it is actually implemented to be run by `pytest`.

see: [Screenshot generator README](screenshot_generator/README.md)


## Generate coverage manually
Run tests and generate test coverage
```bash
uv run coverage run -m pytest
```

The screenshots can generate their own separate coverage report:
```bash
uv run coverage run -m pytest tests/screenshot_generator/generator.py --locale es
```

Show the resulting test coverage details:
```bash
uv run coverage report
```

Generate the interactive html report:
```bash
uv run coverage html
```