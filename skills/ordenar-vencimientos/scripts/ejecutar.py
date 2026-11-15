#!/usr/bin/env python3
"""
Punto de entrada ejecutable para la skill ordenar-vencimientos.
Uso: python ejecutar.py <datos_confirmados.json> [--json]
     cat datos.json | python ejecutar.py - [--json]
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

from ordenador import invocar


def main():
    parser = argparse.ArgumentParser(
        description="Ordena cronológicamente registros confirmados de facturas."
    )
    parser.add_argument(
        "archivo_json",
        help="Archivo JSON con la lista de registros o '-' para leer desde entrada estándar.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida estructurada en JSON.",
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
        print(f"[ERROR] No se pudo leer el JSON de entrada: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(datos_crudos, list):
        print("[ERROR] El JSON de entrada debe ser una lista de registros.", file=sys.stderr)
        sys.exit(1)

    try:
        res = invocar({"registros": datos_crudos})
        salida = res["registros"]
    except Exception as e:
        print(f"[ERROR] Error durante el ordenamiento: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(salida, indent=2, ensure_ascii=False))
    else:
        print(f"{'Vencimiento':<12} | {'Empresa':<20} | {'Servicio':<18} | {'Importe':>15} | {'Moneda':<6} | {'Archivo'}")
        print("-" * 90)
        for r in salida:
            print(
                f"{r.get('fecha_vencimiento_visual', ''):<12} | "
                f"{r.get('empresa', ''):<20} | "
                f"{r.get('servicio', ''):<18} | "
                f"{r.get('importe_visual', ''):>15} | "
                f"{r.get('moneda', ''):<6} | "
                f"{r.get('archivo_origen', '')}"
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
