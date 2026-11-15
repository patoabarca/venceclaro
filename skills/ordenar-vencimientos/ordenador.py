from __future__ import annotations

from typing import List, Union
from core.models import FacturaConfirmada, RegistroRevision


def ordenar_vencimientos(
    registros: List[Union[FacturaConfirmada, RegistroRevision]]
) -> List[Union[FacturaConfirmada, RegistroRevision]]:
    """
    Skill especializada: ordenar-vencimientos.
    Ordena una lista de registros confirmados por fecha de vencimiento ascendente.
    Criterios de desempate secundarios estables:
      1. Fecha de vencimiento (ascendente)
      2. Nombre de la empresa emisora (ascendente, insensible a mayúsculas)
      3. Nombre del archivo de origen (ascendente, insensible a mayúsculas)

    Garantía: No modifica importes, no altera textos ni completa datos faltantes.
    """
    # Se crea una copia para asegurar pureza funcional
    def clave_orden(reg: Union[FacturaConfirmada, RegistroRevision]):
        fecha = reg.fecha_vencimiento
        if fecha is None:
            raise ValueError(
                f"No se puede ordenar el registro '{reg.archivo_origen}' porque carece de fecha de vencimiento."
            )
        empresa = (reg.empresa or "").strip().lower()
        archivo = (reg.archivo_origen or "").strip().lower()
        return (fecha, empresa, archivo)

    return sorted(registros, key=clave_orden)

ESQUEMA_ENTRADA = {
    "type": "object",
    "properties": {
        "registros": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Lista de registros de facturas confirmadas a ordenar cronológicamente.",
        }
    },
    "required": ["registros"],
}


def invocar(entrada: dict) -> dict:
    """
    Contrato estándar de la skill: invocar(entrada: dict) -> dict.
    Envuelve ordenar_vencimientos sin alterar la lógica de ordenamiento.
    """
    registros_in = entrada.get("registros", [])
    if not isinstance(registros_in, list):
        raise TypeError("El parámetro 'registros' debe ser una lista.")

    from datetime import date
    from decimal import Decimal

    # Reconstruir objetos si vienen como dicts
    objetos_a_ordenar = []
    for r in registros_in:
        if isinstance(r, (FacturaConfirmada, RegistroRevision)):
            objetos_a_ordenar.append(r)
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
            objetos_a_ordenar.append(reg)
        else:
            raise TypeError(f"Tipo de registro no soportado: {type(r)}")

    ordenados = ordenar_vencimientos(objetos_a_ordenar)

    salida_dicts = []
    for reg in ordenados:
        if isinstance(reg, FacturaConfirmada):
            salida_dicts.append({
                "id": reg.id,
                "archivo_origen": reg.archivo_origen,
                "empresa": reg.empresa,
                "servicio": reg.servicio,
                "importe": float(reg.importe),
                "importe_visual": reg.importe_visual,
                "moneda": reg.moneda,
                "fecha_vencimiento": reg.fecha_vencimiento_str,
                "fecha_vencimiento_visual": reg.fecha_vencimiento_visual,
                "fue_modificado": reg.fue_modificado,
            })
        else:
            salida_dicts.append(reg)

    return {
        "registros": salida_dicts,
        "objetos": ordenados,
    }
