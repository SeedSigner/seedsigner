# Running Tests

The tests are designed to be run on non-Raspi hardware.

## Setup
Follow the [development setup](../README.md#development-environment), including
fetching the submodules and compiling translations before running tests.

On macOS, install zbar with `brew install zbar`. If pyzbar cannot find it, set
`export DYLD_LIBRARY_PATH="$(brew --prefix zbar)/lib"`. If QR decoding crashes
on Apple Silicon, use the Linux Docker environment below.

## Running the tests in Docker
From the repo root, after fetching the submodules:

```bash
docker build -f docker/Dockerfile -t seedsigner-dev .
docker run --rm -v "$(pwd)":/seedsigner seedsigner-dev bash -c "
  uv sync --frozen --group l10n &&
  uv run poe translations-compile &&
  uv run poe test
"
```

For an interactive shell, run:

```bash
docker compose run --rm seedsigner-dev bash
```

Run the sync and translation commands above before testing in that shell.

## Running all tests, calculating overall test coverage
tldr: just run the convenience script from the project root:

```bash
uv run poe coverage
```

## Running tests manually
`uv run` executes a command inside the project environment, so you never have to
activate the venv yourself. `uv run poe` lists the project's named tasks;
`uv run poe test` is the test suite, and any extra arguments are passed through
to `pytest`.

Run the whole test suite:
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