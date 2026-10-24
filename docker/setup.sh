#!/bin/bash

set -euo pipefail

uv sync --frozen
exec tail -f /dev/null
