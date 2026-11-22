#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${SFM_TEST_PYTHON:-$ROOT/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then PYTHON=python3; fi
export PYTHONPATH="$ROOT/src"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
"$PYTHON" -m sfm_fx_new_age --check
"$PYTHON" -m compileall -q "$ROOT/src" "$ROOT/tests"
"$PYTHON" -m pytest "$ROOT/tests" -q
"$PYTHON" -m sfm_fx_new_age --offline-checkpoint
"$PYTHON" -m sfm_fx_new_age --summary-json
