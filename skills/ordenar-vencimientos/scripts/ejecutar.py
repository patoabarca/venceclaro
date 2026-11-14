#!/usr/bin/env python3
"""
Punto de entrada ejecutable para la skill ordenar-vencimientos.
Uso: python ejecutar.py <datos_confirmados.json> [--json]
     cat datos.json | python ejecutar.py - [--json]
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
from ordenador import ordenar_vencimientos


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

    registros: list[FacturaConfirmada] = []
    for d in datos_crudos:
        try:
            # Parsear fecha si viene como string
            f_str = d.get("fecha_vencimiento")
            if isinstance(f_str, str):
                f_obj = date.fromisoformat(f_str)
            else:
                f_obj = f_str

            imp = d.get("importe")
            imp_dec = Decimal(str(imp)) if imp is not None else Decimal("0.00")

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
        except Exception as err:
            print(f"[ERROR] Registro inválido para ordenamiento: {err}", file=sys.stderr)
            sys.exit(1)

    try:
        ordenados = ordenar_vencimientos(registros)
    except Exception as e:
        print(f"[ERROR] Error durante el ordenamiento: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        salida = [
            {
                "id": r.id,
                "archivo_origen": r.archivo_origen,
                "empresa": r.empresa,
                "servicio": r.servicio,
                "importe": float(r.importe),
                "importe_visual": r.importe_visual,
                "moneda": r.moneda,
                "fecha_vencimiento": r.fecha_vencimiento_str,
                "fecha_vencimiento_visual": r.fecha_vencimiento_visual,
            }
            for r in ordenados
        ]
        print(json.dumps(salida, indent=2, ensure_ascii=False))
    else:
        print(f"{'Vencimiento':<12} | {'Empresa':<20} | {'Servicio':<18} | {'Importe':>15} | {'Moneda':<6} | {'Archivo'}")
        print("-" * 90)
        for r in ordenados:
            print(
                f"{r.fecha_vencimiento_visual:<12} | "
                f"{r.empresa:<20} | "
                f"{r.servicio:<18} | "
                f"{r.importe_visual:>15} | "
                f"{r.moneda:<6} | "
                f"{r.archivo_origen}"
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
