#!/bin/bash
# Install spaCy large model from local wheel file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WHEEL_PATH="$PROJECT_ROOT/services/sandbox/packages/en_core_web_lg-3.8.0-py3-none-any.whl"

if [ ! -f "$WHEEL_PATH" ]; then
    echo "Error: Wheel file not found at $WHEEL_PATH"
    echo "Downloading from GitHub..."
    pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
else
    echo "Installing spaCy large model from local wheel..."
    pip install "$WHEEL_PATH"
fi

echo "✓ spaCy large model installed successfully"
