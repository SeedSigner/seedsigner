#!/bin/bash

# Clean up any prior coverage results
coverage erase

# Run the full test suite; `--parallel` writes coverage results to a separate file
# (otherwise it'll be overwritten in the next step)
coverage run --parallel -m pytest

# Generate screenshots (only need to run for one locale to assess coverage)
coverage run --parallel -m pytest tests/screenshot_generator/generator.py --locale es

# Combine the above coverage results
coverage combine

# Show the report in the terminal
coverage report

# Generate the interactive html report
coverage html
