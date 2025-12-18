#!/bin/bash
set -eo pipefail

export PATH=/usr/bin:/bin
export HOME=/home/eburwic

VENV_PY="/home/eburwic/SCRIPTS/tools/.venv/bin/python"
SCRIPT="/home/eburwic/SCRIPTS/tools/cnrReminder.py"

exec "$VENV_PY" "$SCRIPT"
