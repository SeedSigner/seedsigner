# Screenshot Generator

From the project root, run:
```bash
# Generate screenshots for a specific locale
pytest tests/screenshot_generator/generator.py --locale es

# Generate screenshots for all supported locales
pytest tests/screenshot_generator/generator.py
```

You can also run a `coverage` report to see exactly what the screenshots are and are not hitting:
```bash
coverage erase
coverage run -m pytest tests/screenshot_generator/generator.py --locale es && coverage combine && coverage report

# Generate the interactive html report
coverage html
```

Writes the screenshots to a dir in the project root: `seedsigner-screenshots`.
