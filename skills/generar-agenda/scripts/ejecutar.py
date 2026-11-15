#!/usr/bin/env python3
"""
Punto de entrada ejecutable para la skill generar-agenda.
Uso: python ejecutar.py <registros_ordenados.json> [--salida agenda.csv]
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SKILL_DIR.parent.parent
for p in [str(SKILL_DIR), str(BASE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from generador import invocar, formatear_importe_argentino
from decimal import Decimal


def main():
    parser = argparse.ArgumentParser(
        description="Genera archivo CSV de agenda de vencimientos compatible con Excel regional argentino."
    )
    parser.add_argument(
        "archivo_json",
        help="Archivo JSON con registros ordenados o '-' para entrada estándar.",
    )
    parser.add_argument(
        "--salida",
        "-o",
        help="Ruta del archivo CSV de salida. Si no se especifica, imprime en consola.",
    )

    args = parser.parse_args()

    try:
        if args.archivo_json == "-":
            contenido = sys.stdin.read()
        else:
            ruta = Path(args.archivo_json)
            if not ruta.exists():
                print(f"[ERROR] Archivo no encontrado: {ruta}", file=sys.stderr)
                sys.exit(1)
            contenido = ruta.read_text(encoding="utf-8")

        datos_crudos = json.loads(contenido)
    except Exception as e:
        print(f"[ERROR] No se pudo leer el JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        res = invocar({"registros": datos_crudos, "ruta_destino": args.salida})
        csv_texto = res["csv"]
        totales = res["totales_decimal"]

        if args.salida:
            print(f"[OK] Agenda guardada exitosamente en: {args.salida}")
            print("Totales discriminados por moneda:")
            for mon, total in totales.items():
                print(f"  - {mon}: {formatear_importe_argentino(total)}")
        else:
            sys.stdout.write(csv_texto)
    except Exception as e:
        print(f"[ERROR] Falló la generación de agenda: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
