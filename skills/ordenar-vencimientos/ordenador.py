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
