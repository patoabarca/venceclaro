from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

# Asegurar importación de core
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.agent import AgenteVencimientos
from core.models import EstadoProceso, RegistroRevision


def coordinar_organizacion_vencimientos(
    archivos: List[Tuple[str, Union[Path, bytes, BinaryIO]]],
    salida_csv: Optional[Union[str, Path]] = None,
    auto_confirmar: bool = False,
) -> Dict[str, Any]:
    """
    Skill orquestadora: organizar-vencimientos.
    Coordina secuencialmente la extracción, revisión, ordenamiento y generación de agenda.

    En entornos automatizados (CLI o tests):
      Si `auto_confirmar` es True, verifica si todos los registros tienen campos obligatorios.
      Si cumplen, confirma automáticamente y genera la agenda.
      Si faltan campos o hay ambigüedad, suspende en REVISION_REQUERIDA y reporta los detalles.
    """
    agente = AgenteVencimientos()
    registros_rev = agente.procesar_archivos_iniciales(archivos)

    resultado: Dict[str, Any] = {
        "estado": agente.estado.value,
        "mensajes": list(agente.mensajes_estado),
        "registros_extraidos": [r.a_diccionario() for r in agente.registros_extraidos],
        "requieren_revision": any(r.requiere_revision for r in agente.registros_extraidos),
        "archivos_excluidos": [],
        "agenda_csv": None,
        "totales_por_moneda": {},
    }

    if auto_confirmar:
        # Verificar si hay faltantes
        hay_faltantes = any(not r.tiene_campos_obligatorios for r in registros_rev if not r.excluido)
        if hay_faltantes:
            resultado["mensajes"].append(
                "No se pudo autoconfirmar: existen comprobantes con campos obligatorios incompletos."
            )
            return resultado

        exito, errores = agente.validar_y_confirmar(registros_rev)
        if not exito:
            resultado["estado"] = EstadoProceso.ERROR.value
            resultado["errores"] = errores
            return resultado

        if salida_csv and agente.agenda_csv:
            Path(salida_csv).write_text(agente.agenda_csv, encoding="utf-8-sig")

        resultado["estado"] = agente.estado.value
        resultado["mensajes"] = list(agente.mensajes_estado)
        resultado["registros_ordenados"] = [r.a_fila_agenda() for r in agente.registros_ordenados]
        resultado["archivos_excluidos"] = agente.archivos_excluidos
        resultado["agenda_csv"] = agente.agenda_csv
        resultado["totales_por_moneda"] = {k: float(v) for k, v in agente.totales_por_moneda.items()}

    return resultado
