# Running Tests

The tests are designed to be run on non-Raspi hardware.

## Setup
On your testing machine you'll have to install:
```bash
# general dependencies
pip3 install -r requirements.txt

# test suite dependencies
pip3 install -r tests/requirements.txt
```

Then make the `seedsigner` python module visible/importable to the tests by installing it:
```
pip3 install -e .
```

## Running all tests, calculating overall test coverage
tldr: just run the convenience script from the project root:

```bash
./tests/run_full_coverage.sh
```

## Running tests manually
Run the whole test suite:
```
pytest
```

Run a specific test file:
```
pytest tests/test_this_file.py
```

Run a specific test:
```
pytest tests/test_this_file.py::test_this_specific_test
```

Force pytest to show logging output:
```bash
pytest tests/test_this_file.py::test_this_specific_test -o log_cli=1

# or (same result)

pytest tests/test_this_file.py::test_this_specific_test --log-cli-level=DEBUG
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
coverage run -m pytest
```

The screenshots can generate their own separate coverage report:
```bash
coverage run -m pytest tests/screenshot_generator/generator.py --locale es
```

Show the resulting test coverage details:
```bash
coverage report
```

Generate the interactive html report:
```bash
coverage html
```