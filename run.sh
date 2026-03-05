#!/usr/bin/env bash
# Run the chat app locally for testing.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
