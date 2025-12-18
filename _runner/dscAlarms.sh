#!/bin/bash
set -eo pipefail

export PATH=/usr/bin:/bin
export HOME=/home/eburwic

VENV_PY="/home/eburwic/SCRIPTS/dsc/.venv/bin/python"
SCRIPT="/home/eburwic/SCRIPTS/dsc/dscAlarms.py"

exec "$VENV_PY" "$SCRIPT"
