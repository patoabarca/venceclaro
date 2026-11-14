from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple


MESES_ESPANOL = {
    "enero": 1, "ene": 1,
    "febrero": 2, "feb": 2,
    "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6,
    "julio": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "septiembre": 9, "sep": 9, "set": 9,
    "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11,
    "diciembre": 12, "dic": 12,
}


def parsear_importe_argentino(texto: str) -> Optional[Decimal]:
    """
    Interpreta un importe en formato numérico argentino (punto de miles y coma decimal).
    Ejemplos soportados:
      - '25.000,50' -> Decimal('25000.50')
      - '1.234.567,89' -> Decimal('1234567.89')
      - '1500,00' -> Decimal('1500.00')
      - '1500' -> Decimal('1500.00')
    """
    if not texto:
        return None
    limpio = texto.strip()
    # Eliminar símbolos de moneda y caracteres de control
    limpio = re.sub(r"[^\d.,]", "", limpio)
    if not limpio:
        return None

    try:
        # Caso estándar argentino: tiene coma como separador decimal
        if "," in limpio:
            partes = limpio.split(",")
            if len(partes) == 2:
                parte_entera = partes[0].replace(".", "")
                parte_decimal = partes[1]
                # Validar que ambas partes contengan solo dígitos
                if parte_entera.isdigit() and parte_decimal.isdigit():
                    return Decimal(f"{parte_entera}.{parte_decimal}")
        # Si tiene puntos pero no coma:
        # Puede ser miles sin centavos ('25.000') o decimal anglosajón
        elif "." in limpio:
            partes = limpio.split(".")
            # Si el último grupo tiene 3 dígitos, casi con certeza es separador de miles: '25.000'
            if len(partes[-1]) == 3:
                entera = "".join(partes)
                if entera.isdigit():
                    return Decimal(f"{entera}.00")
            # Si tiene un solo punto y 2 decimales: '2500.50' (por si acaso viene formato mixto)
            elif len(partes) == 2 and len(partes[1]) == 2 and partes[0].isdigit() and partes[1].isdigit():
                return Decimal(f"{partes[0]}.{partes[1]}")
            else:
                entera = "".join(partes)
                if entera.isdigit():
                    return Decimal(f"{entera}.00")
        else:
            # Solo dígitos enteros
            if limpio.isdigit():
                return Decimal(f"{limpio}.00")
    except (InvalidOperation, ValueError):
        return None

    return None


def parsear_fecha_argentina(texto: str) -> Optional[date]:
    """
    Interpreta una fecha en formato DD/MM/AAAA, DD-MM-AAAA o con mes en palabras.
    Ejemplos:
      - '15/05/2026' -> date(2026, 5, 15)
      - '15-05-2026' -> date(2026, 5, 15)
      - '15 de Mayo de 2026' -> date(2026, 5, 15)
    """
    if not texto:
        return None

    limpio = texto.strip().lower()

    # Formato numérico DD/MM/AAAA o DD-MM-AAAA
    coincidencia_num = re.search(r"\b(0?[1-9]|[12]\d|3[01])[/\-.](0?[1-9]|1[0-2])[/\-.](20\d{2})\b", limpio)
    if coincidencia_num:
        dia, mes, anio = coincidencia_num.groups()
        try:
            return date(int(anio), int(mes), int(dia))
        except ValueError:
            return None

    # Formato con nombre de mes: '15 de Mayo de 2026' o '15 Mayo 2026'
    patron_mes = r"\b(0?[1-9]|[12]\d|3[01])\s+(?:de\s+)?([a-z]{3,10})\s+(?:de\s+)?(20\d{2})\b"
    coincidencia_pal = re.search(patron_mes, limpio)
    if coincidencia_pal:
        dia_s, mes_s, anio_s = coincidencia_pal.groups()
        mes_num = MESES_ESPANOL.get(mes_s)
        if mes_num:
            try:
                return date(int(anio_s), mes_num, int(dia_s))
            except ValueError:
                return None

    return None
