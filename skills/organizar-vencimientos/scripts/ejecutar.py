#!/usr/bin/env python3
"""
Punto de entrada ejecutable para la skill orquestadora organizar-vencimientos.
Uso: python ejecutar.py <factura1.pdf> [factura2.pdf ...] [--salida agenda.csv] [--auto-confirmar] [--enviar-a <correo>] [--dry-run] [--sin-llm]
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

from orquestador import coordinar_organizacion_vencimientos


def main():
    parser = argparse.ArgumentParser(
        description="Orquesta el flujo completo de VenceClaro mediante LLM y skills especializadas."
    )
    parser.add_argument(
        "archivos",
        nargs="+",
        help="Rutas a los archivos PDF de facturas.",
    )
    parser.add_argument(
        "--salida",
        "-o",
        help="Ruta donde guardar el archivo CSV de agenda resultante.",
    )
    parser.add_argument(
        "--auto-confirmar",
        action="store_true",
        help="Confirmar y continuar automáticamente si todos los datos extraídos son válidos.",
    )
    parser.add_argument(
        "--enviar-a",
        help="Dirección de correo electrónico de destino para enviar la agenda.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Activa el modo simulación para el envío de correo sin conectar a internet.",
    )
    parser.add_argument(
        "--sin-llm",
        action="store_true",
        help="Ejecuta en modo puramente determinista sin invocar a Anthropic Claude.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida estructurada en JSON incluyendo la traza de decisiones.",
    )

    args = parser.parse_args()

    archivos_tuplas = []
    for f in args.archivos:
        ruta = Path(f)
        if not ruta.exists():
            print(f"[ERROR] Archivo no encontrado: {ruta}", file=sys.stderr)
            sys.exit(1)
        archivos_tuplas.append((ruta.name, ruta))

    resultado = coordinar_organizacion_vencimientos(
        archivos=archivos_tuplas,
        salida_csv=args.salida,
        auto_confirmar=args.auto_confirmar,
        enviar_a=args.enviar_a,
        dry_run=args.dry_run,
        sin_llm=args.sin_llm,
    )

    if args.json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print("=== ORQUESTACIÓN VENCECLARO ===")
        print(f"Estado final: {resultado['estado']}")
        for msg in resultado["mensajes"]:
            print(f"  * {msg}")

        if resultado.get("resumen_llm"):
            print(f"\n[Resumen del Agente]: {resultado['resumen_llm']}")

        if resultado.get("traza"):
            print("\n--- TRAZA DE DECISIONES DEL AGENTE ---")
            for t in resultado["traza"]:
                print(f"Paso {t['paso']}: [{t['skill']}] -> {t['resultado']}")

        if resultado.get("registros_ordenados"):
            print("\n--- AGENDA ORDENADA GENERADA ---")
            for fila in resultado["registros_ordenados"]:
                print(
                    f"{fila['Vencimiento']} | {fila['Empresa']} ({fila['Servicio']}): "
                    f"{fila['Importe']} {fila['Moneda']} [{fila['Archivo de origen']}]"
                )
            if args.salida:
                print(f"\nArchivo CSV generado en: {args.salida}")

        if resultado.get("envio"):
            env = resultado["envio"]
            print(f"\n[Despacho de Correo]: {env['mensaje']} (Modo: {env['modo']})")

        elif resultado.get("requieren_revision"):
            print("\n[ATENCIÓN] Hay comprobantes que requieren revisión o confirmación.")
            print("Ejecute la interfaz web interactiva con 'streamlit run app.py' para revisar y confirmar.")

    if resultado["estado"] == "ERROR":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
