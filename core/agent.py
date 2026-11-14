from __future__ import annotations

import io
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union
from decimal import Decimal

from core.models import (
    EstadoProceso,
    FacturaConfirmada,
    FacturaExtraida,
    RegistroRevision,
)
from core.skill_loader import (
    obtener_extractor,
    obtener_generador,
    obtener_ordenador,
    obtener_remitente,
)


class AgenteVencimientos:
    """
    Agente Coordinador Determinista de Vencimientos.

    Implementación honesta:
    Coordina de manera secuencial y determinista las 4 skills del sistema:
      1. Skill 'extraer-vencimiento': parsea cada PDF con reglas explícitas y evidencia.
      2. Handoff de revisión: entrega los registros al usuario para validar/corregir.
      3. Reanudación del flujo: valida que no existan campos obligatorios omitidos.
      4. Skill 'ordenar-vencimientos': aplica ordenamiento cronológico y desempate estable.
      5. Skill 'generar-agenda': formatea el CSV regional argentino con monedas separadas.
    """

    def __init__(self):
        self.estado: EstadoProceso = EstadoProceso.INICIAL
        self.registros_extraidos: List[FacturaExtraida] = []
        self.registros_revision: List[RegistroRevision] = []
        self.registros_confirmados: List[FacturaConfirmada] = []
        self.registros_ordenados: List[FacturaConfirmada] = []
        self.archivos_excluidos: List[str] = []
        self.agenda_csv: Optional[str] = None
        self.totales_por_moneda: Dict[str, Decimal] = {}
        self.mensajes_estado: List[str] = []

    def reiniciar(self) -> None:
        """Reinicia el estado completo del agente."""
        self.estado = EstadoProceso.INICIAL
        self.registros_extraidos.clear()
        self.registros_revision.clear()
        self.registros_confirmados.clear()
        self.registros_ordenados.clear()
        self.archivos_excluidos.clear()
        self.agenda_csv = None
        self.totales_por_moneda.clear()
        self.mensajes_estado.clear()

    def procesar_archivos_iniciales(
        self, archivos: List[Tuple[str, Union[Path, bytes, BinaryIO]]]
    ) -> List[RegistroRevision]:
        """
        Paso 1 del orquestador: Invocación de la skill 'extraer-vencimiento'.
        Pasa de INICIAL -> EXTRAYENDO -> REVISION_REQUERIDA.
        Entrega al usuario la lista de registros para supervisión.
        """
        extractor_mod = obtener_extractor()

        self.reiniciar()
        self.estado = EstadoProceso.EXTRAYENDO
        self.mensajes_estado.append(f"Iniciando extracción para {len(archivos)} archivo(s)...")

        for nombre_archivo, contenido in archivos:
            extraida: FacturaExtraida = extractor_mod.extraer_datos_factura(contenido, nombre_archivo)
            self.registros_extraidos.append(extraida)

            # Crear registro de revisión conservando originales
            reg_rev = RegistroRevision.desde_factura_extraida(extraida)
            self.registros_revision.append(reg_rev)

        self.estado = EstadoProceso.REVISION_REQUERIDA
        self.mensajes_estado.append(
            "Extracción completada. Los comprobantes están listos para revisión y confirmación del usuario."
        )
        return self.registros_revision

    def agregar_archivos(
        self, archivos: List[Tuple[str, Union[Path, bytes, BinaryIO]]]
    ) -> List[RegistroRevision]:
        """
        Permite la ingesta incremental de facturas en el lote actual del orquestador.
        Si ya existen facturas cargadas, las nuevas se extraen y se agregan a la agenda en curso.
        """
        extractor_mod = obtener_extractor()
        self.estado = EstadoProceso.EXTRAYENDO
        self.mensajes_estado.append(f"Agregando {len(archivos)} archivo(s) al lote actual...")

        for nombre_archivo, contenido in archivos:
            # Evitar duplicados por nombre de archivo si ya existe en la revisión
            if any(r.archivo_origen == nombre_archivo for r in self.registros_revision):
                continue
            extraida: FacturaExtraida = extractor_mod.extraer_datos_factura(contenido, nombre_archivo)
            self.registros_extraidos.append(extraida)
            reg_rev = RegistroRevision.desde_factura_extraida(extraida)
            self.registros_revision.append(reg_rev)

        self.estado = EstadoProceso.REVISION_REQUERIDA
        self.mensajes_estado.append(
            f"Lote actualizado: {len(self.registros_revision)} factura(s) acumulada(s)."
        )
        return self.registros_revision

    def validar_y_confirmar(
        self, registros_modificados: List[RegistroRevision]
    ) -> Tuple[bool, List[str]]:
        """
        Paso 2 y 3 del orquestador: Validación de completitud y confirmación.
        Verifica que los comprobantes NO excluidos cuenten con todos los campos obligatorios.
        Si hay errores, permanece en REVISION_REQUERIDA y devuelve las fallas.
        Si es válido, reanuda el flujo y ejecuta ordenamiento y generación de agenda.
        """
        errores: List[str] = []
        self.registros_revision = registros_modificados

        incluidos = [r for r in self.registros_revision if not r.excluido]
        excluidos = [r for r in self.registros_revision if r.excluido]

        if not incluidos:
            errores.append(
                "No hay comprobantes incluidos para generar la agenda. Debe incluir al menos una factura válida."
            )
            return False, errores

        # Regla: No generar agenda mientras existan registros incluidos sin campos obligatorios
        for reg in incluidos:
            faltan = reg.faltantes()
            if faltan:
                errores.append(
                    f"Archivo '{reg.archivo_origen}': faltan campos obligatorios: {', '.join(faltan)}."
                )

        if errores:
            return False, errores

        # Si todo es válido, registrar excluidos y construir FacturaConfirmada
        self.archivos_excluidos = [r.archivo_origen for r in excluidos]
        self.registros_confirmados = []

        for reg in incluidos:
            cambio_alguno = any(
                reg.ha_cambiado(campo)
                for campo in ["empresa", "servicio", "importe", "moneda", "fecha_vencimiento"]
            )
            assert reg.fecha_vencimiento is not None
            assert reg.importe is not None

            conf = FacturaConfirmada(
                id=reg.id,
                archivo_origen=reg.archivo_origen,
                empresa=reg.empresa.strip(),
                servicio=reg.servicio.strip(),
                importe=reg.importe,
                moneda=reg.moneda.strip().upper(),
                fecha_vencimiento=reg.fecha_vencimiento,
                fue_modificado=cambio_alguno,
                valores_originales=reg.valores_originales,
            )
            self.registros_confirmados.append(conf)

        self.estado = EstadoProceso.DATOS_CONFIRMADOS
        self.mensajes_estado.append("Datos confirmados por el usuario. Reanudando flujo coordinado...")

        # Paso 4: Invocar skill 'ordenar-vencimientos'
        ordenador_mod = obtener_ordenador()
        self.registros_ordenados = ordenador_mod.ordenar_vencimientos(self.registros_confirmados)
        self.estado = EstadoProceso.ORDENAMIENTO_COMPLETADO
        self.mensajes_estado.append("Ordenamiento cronológico y desempate estable completados.")

        # Paso 5: Invocar skill 'generar-agenda'
        generador_mod = obtener_generador()
        self.agenda_csv = generador_mod.generar_agenda_csv(self.registros_ordenados)
        self.totales_por_moneda = generador_mod.calcular_totales_por_moneda(self.registros_ordenados)
        self.estado = EstadoProceso.AGENDA_LISTA
        self.mensajes_estado.append("Agenda CSV generada exitosamente con formato regional argentino.")

        return True, []

    def enviar_agenda_por_correo(
        self,
        destinatario: str,
        remitente: Optional[str] = None,
        password: Optional[str] = None,
        dry_run: bool = False,
    ) -> Tuple[bool, str, str]:
        """
        Paso coordinado: Invoca la skill especializada 'enviar-agenda' para despachar
        el CSV adjunto y el resumen de totales a la casilla de correo del usuario.
        """
        if not self.registros_ordenados or not self.agenda_csv:
            return False, "No hay una agenda generada disponible para enviar.", "ERROR"

        generador_mod = obtener_generador()
        csv_bytes = generador_mod.generar_agenda_bytes(self.registros_ordenados)

        remitente_mod = obtener_remitente()
        exito, msg, modo = remitente_mod.despachar_agenda_gmail(
            destinatario=destinatario,
            csv_bytes=csv_bytes,
            totales_por_moneda=self.totales_por_moneda,
            remitente=remitente,
            password=password,
            dry_run=dry_run,
        )
        if exito:
            self.mensajes_estado.append(f"Despacho de agenda a '{destinatario}' completado ({modo}).")
        return exito, msg, modo
