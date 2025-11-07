#!/usr/bin/env bash
set -e
VENV=.venv
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
  source "$VENV/bin/activate"
  pip install --quiet -r requirements.txt
else
  source "$VENV/bin/activate"
fi
python main.py "$@"
