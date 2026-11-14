import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.agent import AgenteVencimientos
from core.models import EstadoProceso

EJEMPLOS_DIR = BASE_DIR / "ejemplos"


def test_flujo_completo_con_archivo_excluido_y_correccion():
    agente = AgenteVencimientos()

    archivos = [
        ("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf"),
        ("factura_telecom_internet.pdf", EJEMPLOS_DIR / "factura_telecom_internet.pdf"),
        ("factura_sin_texto.pdf", EJEMPLOS_DIR / "factura_sin_texto.pdf"),
    ]

    # Paso 1: Iniciar extracción
    registros_rev = agente.procesar_archivos_iniciales(archivos)

    assert agente.estado == EstadoProceso.REVISION_REQUERIDA
    assert len(registros_rev) == 3

    # Identificar el registro sin texto
    reg_sin_texto = next(r for r in registros_rev if r.archivo_origen == "factura_sin_texto.pdf")
    assert reg_sin_texto.tiene_campos_obligatorios is False
    assert any("no contiene texto seleccionable" in obs for obs in reg_sin_texto.observaciones)

    # Intento 1: Confirmar sin excluir ni corregir el archivo sin texto -> DEBE FALLAR
    exito, errores = agente.validar_y_confirmar(registros_rev)
    assert exito is False
    assert len(errores) > 0
    assert any("factura_sin_texto.pdf" in err for err in errores)
    assert agente.estado == EstadoProceso.REVISION_REQUERIDA

    # Intento 2: Usuario excluye el archivo problemático y edita servicio de Telecom
    reg_sin_texto.excluido = True

    reg_telecom = next(r for r in registros_rev if r.archivo_origen == "factura_telecom_internet.pdf")
    # Preservar valores originales
    assert reg_telecom.valores_originales["servicio"] == "Internet"
    reg_telecom.servicio = "Internet Fibra Óptica 500M"

    # Confirmar
    exito2, errores2 = agente.validar_y_confirmar(registros_rev)
    assert exito2 is True
    assert len(errores2) == 0

    # Verificar avance automático por Ordenamiento y Agenda
    assert agente.estado == EstadoProceso.AGENDA_LISTA
    assert len(agente.registros_ordenados) == 2
    assert agente.archivos_excluidos == ["factura_sin_texto.pdf"]

    # Verificar que Telecom tenga la modificación registrada
    conf_telecom = next(r for r in agente.registros_ordenados if r.archivo_origen == "factura_telecom_internet.pdf")
    assert conf_telecom.fue_modificado is True
    assert conf_telecom.servicio == "Internet Fibra Óptica 500M"
    assert conf_telecom.valores_originales["servicio"] == "Internet"

    # Verificar que el orden sea cronológico (Mayo 2026 antes que Junio 2026)
    assert agente.registros_ordenados[0].archivo_origen == "factura_telecom_internet.pdf"
    assert agente.registros_ordenados[1].archivo_origen == "factura_edesur_luz.pdf"

    # Verificar que la agenda CSV contenga las dos facturas
    assert "factura_telecom_internet.pdf" in agente.agenda_csv
    assert "factura_edesur_luz.pdf" in agente.agenda_csv
    assert "factura_sin_texto.pdf" not in agente.agenda_csv


def test_rechazo_si_todos_excluidos():
    agente = AgenteVencimientos()
    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]
    regs = agente.procesar_archivos_iniciales(archivos)

    # Excluir la única factura
    regs[0].excluido = True

    exito, errores = agente.validar_y_confirmar(regs)
    assert exito is False
    assert "No hay comprobantes incluidos" in errores[0]


def test_agente_ingesta_incremental_varios_archivos():
    """Valida que el orquestador acumule facturas de a una o en lotes sucesivos sin perder las anteriores."""
    agente = AgenteVencimientos()

    # Cargar primera factura (Edesur)
    agente.agregar_archivos([("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")])
    assert len(agente.registros_revision) == 1
    assert agente.registros_revision[0].empresa == "Edesur"

    # Cargar segunda factura (Telecom)
    agente.agregar_archivos([("factura_telecom_internet.pdf", EJEMPLOS_DIR / "factura_telecom_internet.pdf")])
    assert len(agente.registros_revision) == 2

    # Intentar cargar un duplicado (debe omitirlo)
    agente.agregar_archivos([("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")])
    assert len(agente.registros_revision) == 2

    # Confirmar y verificar agenda consolidada única
    exito, errores = agente.validar_y_confirmar(agente.registros_revision)
    assert exito is True
    assert len(agente.registros_ordenados) == 2
    assert agente.estado == EstadoProceso.AGENDA_LISTA
