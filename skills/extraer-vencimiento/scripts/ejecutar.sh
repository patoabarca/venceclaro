#!/usr/bin/env bash
# Punto de entrada ejecutable para la skill extraer-vencimiento.
# Propaga argumentos hacia la implementación Python y devuelve el código de salida.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="python"

if ! command -v "$PYTHON_EXEC" &> /dev/null; then
    PYTHON_EXEC="python3"
fi

"$PYTHON_EXEC" "$SCRIPT_DIR/ejecutar.py" "$@"
EXIT_CODE=$?
exit $EXIT_CODE
