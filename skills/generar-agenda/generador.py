from __future__ import annotations

import csv
import io
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.models import FacturaConfirmada, RegistroRevision, formatear_importe_argentino


COLUMNAS_AGENDA = [
    "Vencimiento",
    "Empresa",
    "Servicio",
    "Importe",
    "Moneda",
    "Archivo de origen",
]


def generar_agenda_csv(
    registros: List[Union[FacturaConfirmada, RegistroRevision]],
    ruta_destino: Optional[Union[str, Path]] = None,
) -> str:
    """
    Skill especializada: generar-agenda.
    Genera el contenido CSV con formato y codificación aptos para Microsoft Excel
    en configuración regional argentina:
      - Delimitador: ';'
      - Separador decimal: ','
      - Codificación: UTF-8 con BOM (utf-8-sig)
      - Columnas obligatorias: Vencimiento, Empresa, Servicio, Importe, Moneda, Archivo de origen.
      - Monedas estrictamente separadas (sin mezclar montos).
    """
    buffer = io.StringIO()
    # Usar lineterminator='\r\n' para máxima compatibilidad con Excel en Windows
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)

    # Escribir encabezados
    escritor.writerow(COLUMNAS_AGENDA)

    for reg in registros:
        vto_vis = reg.fecha_vencimiento.strftime("%d/%m/%Y") if reg.fecha_vencimiento else ""
        imp_vis = formatear_importe_argentino(reg.importe)
        serv_vis = reg.servicio if reg.servicio else "No especificado"

        fila = [
            vto_vis,
            reg.empresa,
            serv_vis,
            imp_vis,
            reg.moneda,
            reg.archivo_origen,
        ]
        escritor.writerow(fila)

    contenido_csv = buffer.getvalue()

    if ruta_destino:
        path = Path(ruta_destino)
        # Guardar con utf-8-sig en modo binario para preservar saltos CRLF idénticos en cualquier SO
        path.write_bytes(contenido_csv.encode("utf-8-sig"))

    return contenido_csv


def generar_agenda_bytes(registros: List[Union[FacturaConfirmada, RegistroRevision]]) -> bytes:
    """Devuelve los bytes en codificación utf-8-sig listos para descarga."""
    texto = generar_agenda_csv(registros)
    return texto.encode("utf-8-sig")


def calcular_totales_por_moneda(
    registros: List[Union[FacturaConfirmada, RegistroRevision]]
) -> Dict[str, Decimal]:
    """
    Calcula los subtotales agrupados estrictamente por moneda.
    Regla: No sumar ni mezclar monedas dispares (ej. no sumar ARS con USD).
    """
    totales: Dict[str, Decimal] = defaultdict(Decimal)
    for reg in registros:
        if reg.importe is not None and reg.moneda:
            totales[reg.moneda] += reg.importe
    return dict(totales)

ESQUEMA_ENTRADA = {
    "type": "object",
    "properties": {
        "registros": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Lista de registros ordenados de facturas confirmadas a exportar.",
        },
        "ruta_destino": {
            "type": "string",
            "description": "Ruta opcional de guardado del archivo CSV en disco.",
        },
    },
    "required": ["registros"],
}


def invocar(entrada: dict) -> dict:
    """
    Contrato estándar de la skill: invocar(entrada: dict) -> dict.
    Envuelve generar_agenda_csv, generar_agenda_bytes y calcular_totales_por_moneda.
    """
    registros_in = entrada.get("registros", [])
    if not isinstance(registros_in, list):
        raise TypeError("El parámetro 'registros' debe ser una lista.")

    from datetime import date
    from decimal import Decimal

    objetos = []
    for r in registros_in:
        if isinstance(r, (FacturaConfirmada, RegistroRevision)):
            objetos.append(r)
        elif isinstance(r, dict):
            f_val = r.get("fecha_vencimiento")
            if isinstance(f_val, str):
                f_obj = date.fromisoformat(f_val)
            else:
                f_obj = f_val

            imp_val = r.get("importe")
            imp_dec = Decimal(str(imp_val)) if imp_val is not None else Decimal("0.00")

            reg = FacturaConfirmada(
                id=r.get("id", ""),
                archivo_origen=r.get("archivo_origen", ""),
                empresa=r.get("empresa", ""),
                servicio=r.get("servicio", ""),
                importe=imp_dec,
                moneda=r.get("moneda", "ARS"),
                fecha_vencimiento=f_obj,
                fue_modificado=r.get("fue_modificado", False),
            )
            objetos.append(reg)

    ruta_destino = entrada.get("ruta_destino")
    csv_str = generar_agenda_csv(objetos, ruta_destino=ruta_destino)
    csv_bytes = generar_agenda_bytes(objetos)
    totales = calcular_totales_por_moneda(objetos)

    return {
        "csv": csv_str,
        "csv_bytes": csv_bytes,
        "totales_por_moneda": {k: float(v) for k, v in totales.items()},
        "totales_decimal": totales,
    }
