#!/bin/sh

set -e

# Install Python dependencies
pip install fastapi uvicorn pytest-playwright

# Install Playwright with Chromium and dependencies
playwright install --with-deps chromium
