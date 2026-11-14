from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class EstadoProceso(str, Enum):
    INICIAL = "INICIAL"
    EXTRAYENDO = "EXTRAYENDO"
    REVISION_REQUERIDA = "REVISION_REQUERIDA"
    DATOS_CONFIRMADOS = "DATOS_CONFIRMADOS"
    ORDENAMIENTO_COMPLETADO = "ORDENAMIENTO_COMPLETADO"
    AGENDA_LISTA = "AGENDA_LISTA"
    ERROR = "ERROR"


def formatear_importe_argentino(valor: Optional[Decimal]) -> str:
    """Convierte un Decimal en formato numérico argentino: 25.000,50."""
    if valor is None:
        return ""
    # Separar parte entera y decimal
    signo = "-" if valor < 0 else ""
    valor_abs = abs(valor)
    partes = f"{valor_abs:.2f}".split(".")
    entera = partes[0]
    decimal = partes[1]
    # Insertar puntos de miles
    entera_con_puntos = ""
    for i, digito in enumerate(reversed(entera)):
        if i > 0 and i % 3 == 0:
            entera_con_puntos = "." + entera_con_puntos
        entera_con_puntos = digito + entera_con_puntos
    return f"{signo}{entera_con_puntos},{decimal}"


def formatear_fecha_argentina(fecha: Optional[date]) -> str:
    """Convierte un objeto date o ISO string a DD/MM/AAAA."""
    if not fecha:
        return ""
    return fecha.strftime("%d/%m/%Y")


@dataclass
class FacturaExtraida:
    """Representa el registro extraído directamente del PDF con evidencia textual."""
    id: str
    archivo_origen: str
    empresa: Optional[str] = None
    servicio: Optional[str] = None
    importe: Optional[Decimal] = None
    moneda: Optional[str] = None
    fecha_vencimiento: Optional[date] = None  # Formato interno ISO
    evidencia_texto: Dict[str, str] = field(default_factory=dict)
    requiere_revision: bool = False
    observaciones: List[str] = field(default_factory=list)
    excluido: bool = False
    texto_extraido_crudo: Optional[str] = None

    @property
    def fecha_vencimiento_str(self) -> str:
        return self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else ""

    @property
    def fecha_vencimiento_visual(self) -> str:
        return formatear_fecha_argentina(self.fecha_vencimiento)

    @property
    def importe_visual(self) -> str:
        return formatear_importe_argentino(self.importe)

    def a_diccionario(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "archivo_origen": self.archivo_origen,
            "empresa": self.empresa,
            "servicio": self.servicio,
            "importe": float(self.importe) if self.importe is not None else None,
            "importe_formateado": self.importe_visual,
            "moneda": self.moneda,
            "fecha_vencimiento": self.fecha_vencimiento_str,
            "fecha_vencimiento_visual": self.fecha_vencimiento_visual,
            "evidencia_texto": self.evidencia_texto,
            "requiere_revision": self.requiere_revision,
            "observaciones": self.observaciones,
            "excluido": self.excluido,
        }


@dataclass
class RegistroRevision:
    """Registro editable en interfaz y sesión, conservando valores originales vs modificados."""
    id: str
    archivo_origen: str
    empresa: str
    servicio: str
    importe: Optional[Decimal]
    moneda: str
    fecha_vencimiento: Optional[date]
    excluido: bool = False
    observaciones: List[str] = field(default_factory=list)
    valores_originales: Dict[str, Any] = field(default_factory=dict)
    evidencia_texto: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def desde_factura_extraida(cls, extraida: FacturaExtraida) -> RegistroRevision:
        valores_orig = {
            "empresa": extraida.empresa or "",
            "servicio": extraida.servicio or "",
            "importe": extraida.importe,
            "moneda": extraida.moneda or "",
            "fecha_vencimiento": extraida.fecha_vencimiento,
        }
        return cls(
            id=extraida.id,
            archivo_origen=extraida.archivo_origen,
            empresa=extraida.empresa or "",
            servicio=extraida.servicio or "",
            importe=extraida.importe,
            moneda=extraida.moneda or "",
            fecha_vencimiento=extraida.fecha_vencimiento,
            excluido=extraida.excluido,
            observaciones=list(extraida.observaciones),
            valores_originales=valores_orig,
            evidencia_texto=dict(extraida.evidencia_texto),
        )

    def ha_cambiado(self, campo: str) -> bool:
        return self.valores_originales.get(campo) != getattr(self, campo, None)

    @property
    def tiene_campos_obligatorios(self) -> bool:
        return bool(
            self.empresa.strip()
            and self.importe is not None
            and self.importe > 0
            and self.moneda.strip()
            and self.fecha_vencimiento is not None
        )

    def faltantes(self) -> List[str]:
        faltan = []
        if not self.empresa.strip():
            faltan.append("Empresa")
        if self.importe is None or self.importe <= 0:
            faltan.append("Importe válido")
        if not self.moneda.strip():
            faltan.append("Moneda")
        if self.fecha_vencimiento is None:
            faltan.append("Fecha de vencimiento")
        return faltan


@dataclass
class FacturaConfirmada:
    """Registro validado y listo para ser ordenado y exportado."""
    id: str
    archivo_origen: str
    empresa: str
    servicio: str
    importe: Decimal
    moneda: str
    fecha_vencimiento: date
    fue_modificado: bool = False
    valores_originales: Dict[str, Any] = field(default_factory=dict)

    @property
    def fecha_vencimiento_str(self) -> str:
        return self.fecha_vencimiento.isoformat()

    @property
    def fecha_vencimiento_visual(self) -> str:
        return formatear_fecha_argentina(self.fecha_vencimiento)

    @property
    def importe_visual(self) -> str:
        return formatear_importe_argentino(self.importe)

    def a_fila_agenda(self) -> Dict[str, str]:
        """Devuelve las columnas visibles exigidas para la agenda."""
        return {
            "Vencimiento": self.fecha_vencimiento_visual,
            "Empresa": self.empresa,
            "Servicio": self.servicio if self.servicio else "No especificado",
            "Importe": self.importe_visual,
            "Moneda": self.moneda,
            "Archivo de origen": self.archivo_origen,
        }
