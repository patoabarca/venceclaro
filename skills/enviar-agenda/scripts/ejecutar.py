#!/usr/bin/env python3
"""
Punto de entrada ejecutable para la skill enviar-agenda.
Uso: python ejecutar.py --destino <correo> [--csv <archivo.csv>] [--dry-run]
"""

import argparse
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SKILL_DIR.parent.parent
for p in [str(SKILL_DIR), str(BASE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from remitente import invocar


def main():
    parser = argparse.ArgumentParser(
        description="Despacha la agenda de vencimientos por correo electrónico vía Gmail SMTP con adjunto CSV."
    )
    parser.add_argument(
        "--destino",
        "-d",
        required=True,
        help="Dirección de correo electrónico de destino.",
    )
    parser.add_argument(
        "--csv",
        "-c",
        help="Ruta al archivo CSV de agenda a adjuntar. Si no se indica, busca 'agenda_vencimientos.csv'.",
    )
    parser.add_argument(
        "--remitente",
        "-r",
        help="Dirección Gmail de origen (o usar variable GMAIL_REMITENTE).",
    )
    parser.add_argument(
        "--password",
        "-p",
        help="Contraseña de aplicación de 16 caracteres (o usar variable GMAIL_APP_PASSWORD).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecuta en modo simulación educativa sin realizar conexión de red.",
    )
    parser.add_argument(
        "--intro",
        help="Texto introductorio opcional para el cuerpo del correo.",
    )

    args = parser.parse_args()

    entrada = {
        "destinatario": args.destino,
        "ruta_csv": args.csv or "agenda_vencimientos.csv",
        "remitente": args.remitente,
        "password": args.password,
        "dry_run": args.dry_run,
        "texto_intro": args.intro,
    }

    res = invocar(entrada)
    if res["exito"]:
        print(f"[OK] {res['mensaje']} (Modo: {res['modo']})")
        sys.exit(0)
    else:
        print(f"[ERROR] {res['mensaje']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
