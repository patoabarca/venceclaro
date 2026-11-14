#!/usr/bin/env python3
"""
Punto de entrada ejecutable para la skill generar-agenda.
Uso: python ejecutar.py <registros_ordenados.json> [--salida agenda.csv]
"""

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SKILL_DIR.parent.parent
for p in [str(SKILL_DIR), str(BASE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.models import FacturaConfirmada
from generador import generar_agenda_csv, calcular_totales_por_moneda, formatear_importe_argentino


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

    registros: list[FacturaConfirmada] = []
    for d in datos_crudos:
        f_val = d.get("fecha_vencimiento")
        if isinstance(f_val, str):
            f_obj = date.fromisoformat(f_val)
        else:
            f_obj = f_val

        imp_val = d.get("importe")
        imp_dec = Decimal(str(imp_val)) if imp_val is not None else Decimal("0.00")

        reg = FacturaConfirmada(
            id=d.get("id", ""),
            archivo_origen=d.get("archivo_origen", ""),
            empresa=d.get("empresa", ""),
            servicio=d.get("servicio", ""),
            importe=imp_dec,
            moneda=d.get("moneda", "ARS"),
            fecha_vencimiento=f_obj,
            fue_modificado=d.get("fue_modificado", False),
        )
        registros.append(reg)

    try:
        csv_texto = generar_agenda_csv(registros, ruta_destino=args.salida)
        if args.salida:
            print(f"[OK] Agenda guardada exitosamente en: {args.salida}")
            totales = calcular_totales_por_moneda(registros)
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
