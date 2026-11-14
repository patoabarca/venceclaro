#!/usr/bin/env python3
"""
Punto de entrada ejecutable para la skill enviar-agenda.
Uso: python ejecutar.py --destino <correo> [--csv <archivo.csv>] [--dry-run]
"""

import argparse
import sys
from decimal import Decimal
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SKILL_DIR.parent.parent
for p in [str(SKILL_DIR), str(BASE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from remitente import despachar_agenda_gmail


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

    args = parser.parse_args()

    # Cargar CSV
    if args.csv:
        ruta_csv = Path(args.csv)
    else:
        ruta_csv = BASE_DIR / "agenda_vencimientos.csv"

    if ruta_csv.exists():
        csv_bytes = ruta_csv.read_bytes()
    else:
        # CSV mínimo de prueba si no existe archivo
        csv_bytes = "Vencimiento;Empresa;Servicio;Importe;Moneda;Archivo de origen\r\n".encode("utf-8-sig")

    exito, mensaje, modo = despachar_agenda_gmail(
        destinatario=args.destino,
        csv_bytes=csv_bytes,
        totales_por_moneda={"ARS": Decimal("15000.00")},
        remitente=args.remitente,
        password=args.password,
        dry_run=args.dry_run,
    )

    if exito:
        print(f"[{modo}] {mensaje}")
        sys.exit(0)
    else:
        print(f"[ERROR] {mensaje}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
