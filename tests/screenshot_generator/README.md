# Screenshot Generator

From the project root, run:
```bash
# Generate screenshots for a specific locale
uv run poe screenshots --locale es

# Generate screenshots for all supported locales
uv run poe screenshots
```

You can also run a `coverage` report to see exactly what the screenshots are and are not hitting:
```bash
uv run coverage erase
uv run coverage run -m pytest tests/screenshot_generator/generator.py --locale es && uv run coverage combine && uv run coverage report

# Generate the interactive html report
uv run coverage html
```

Writes the screenshots to a dir in the project root: `seedsigner-screenshots`.
