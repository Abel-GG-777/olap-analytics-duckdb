#!/usr/bin/env bash
set -euo pipefail
python -m venv .pages-venv
.pages-venv/bin/python -m pip install -r requirements-dev.txt
.pages-venv/bin/python -m ruff check app tests scripts
.pages-venv/bin/python -m pytest -q
npm ci
npm run build
