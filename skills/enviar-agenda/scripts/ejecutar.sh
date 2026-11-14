#!/usr/bin/env bash
# Wrapper portable para ejecutar la skill enviar-agenda
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
    PYTHON_CMD="python"
fi
exec "$PYTHON_CMD" "$SCRIPT_DIR/ejecutar.py" "$@"
