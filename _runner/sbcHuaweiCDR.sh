#!/bin/bash
set -eo pipefail

export PATH=/usr/bin:/bin
export HOME=/home/eburwic

VENV_PY="/home/eburwic/SCRIPTS/sbc/.venv/bin/python"
SCRIPT="/home/eburwic/SCRIPTS/sbc/sbcHuaweiCDR.py"

exec "$VENV_PY" "$SCRIPT"
