#!/bin/bash
set -eo pipefail

export PATH=/usr/bin:/bin
export HOME=/home/eburwic

VENV_PY="/home/eburwic/SCRIPTS/mrtg/.venv/bin/python"
SCRIPT="/home/eburwic/SCRIPTS/mrtg/mrtgThold.py"

exec "$VENV_PY" "$SCRIPT"
