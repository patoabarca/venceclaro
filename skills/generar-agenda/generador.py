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
        # Guardar con utf-8-sig (con BOM) para que Excel reconozca tildes y caracteres especiales
        path.write_text(contenido_csv, encoding="utf-8-sig")

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
