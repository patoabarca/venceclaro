#!/usr/bin/env python3
"""
Punto de entrada ejecutable para la skill extraer-vencimiento.
Uso: python ejecutar.py <ruta_a_factura.pdf> [otras_facturas.pdf ...]
"""

import argparse
import json
import sys
from pathlib import Path

# Agregar directorio de la skill y directorio raíz a sys.path
SKILL_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SKILL_DIR.parent.parent
for p in [str(SKILL_DIR), str(BASE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from extractor import invocar


def main():
    parser = argparse.ArgumentParser(
        description="Extrae campos estructurados y evidencia textual de facturas en PDF."
    )
    parser.add_argument(
        "archivos",
        nargs="+",
        help="Rutas a uno o más archivos PDF con texto seleccionable.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida estructurada en formato JSON.",
    )

    args = parser.parse_args()
    resultados = []
    hay_error_fatal = False

    for ruta_str in args.archivos:
        ruta = Path(ruta_str)
        if not ruta.exists():
            print(f"[ERROR] El archivo no existe: {ruta}", file=sys.stderr)
            hay_error_fatal = True
            continue

        try:
            res = invocar({"archivo": str(ruta)})
            resultados.append(res["registro"])
        except Exception as e:
            print(f"[ERROR] Falló extracción de {ruta.name}: {e}", file=sys.stderr)
            hay_error_fatal = True

    if args.json:
        print(json.dumps(resultados, indent=2, ensure_ascii=False))
    else:
        for r in resultados:
            print("=" * 60)
            print(f"Archivo:     {r['archivo_origen']}")
            print(f"Empresa:     {r['empresa'] or 'NO IDENTIFICADA'}")
            print(f"Servicio:    {r['servicio'] or 'NO IDENTIFICADO'}")
            print(f"Vencimiento: {r['fecha_vencimiento_visual'] or 'NO IDENTIFICADO'}")
            print(f"Importe:     {r['importe_formateado'] or 'NO IDENTIFICADO'} {r['moneda'] or ''}")
            print(f"Revisión:    {'SÍ' if r['requiere_revision'] else 'NO'}")
            if r['observaciones']:
                print("Observaciones:")
                for obs in r['observaciones']:
                    print(f"  - {obs}")
            if r['evidencia_texto']:
                print("Evidencia textual:")
                for campo, ev in r['evidencia_texto'].items():
                    print(f"  - {campo}: {ev}")
        print("=" * 60)

    if hay_error_fatal and not resultados:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
