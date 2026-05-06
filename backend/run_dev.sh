#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
