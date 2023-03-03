# Running Tests

You must install the test-runner dependencies:
```
pip3 install -r tests/requirements.txt
```

Then make the `seedsigner` python module visible/importable to the tests by installing it:
```
pip3 install -e .
```

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

### Test Coverage
Run tests and generate test coverage
```
coverage run -m pytest
```

Show the resulting test coverage details:
```
coverage report
```

Generate the html overview:
```
coverage html
```
