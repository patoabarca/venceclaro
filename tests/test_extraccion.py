import sys
from decimal import Decimal
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.skill_loader import obtener_extractor
from core.parser_utils import parsear_importe_argentino, parsear_fecha_argentina

EJEMPLOS_DIR = BASE_DIR / "ejemplos"


def test_parsear_importe_argentino_casos():
    assert parsear_importe_argentino("25.000,50") == Decimal("25000.50")
    assert parsear_importe_argentino("1.234.567,89") == Decimal("1234567.89")
    assert parsear_importe_argentino("1500,00") == Decimal("1500.00")
    assert parsear_importe_argentino("1500") == Decimal("1500.00")
    assert parsear_importe_argentino("$ 148.950,25") == Decimal("148950.25")
    assert parsear_importe_argentino("invalido") is None


def test_parsear_fecha_argentina_casos():
    from datetime import date
    assert parsear_fecha_argentina("15/06/2026") == date(2026, 6, 15)
    assert parsear_fecha_argentina("28-05-2026") == date(2026, 5, 28)
    assert parsear_fecha_argentina("10 de Enero de 2027") == date(2027, 1, 10)
    assert parsear_fecha_argentina("sin fecha") is None


def test_extraccion_factura_edesur_compatible():
    extractor = obtener_extractor()
    ruta = EJEMPLOS_DIR / "factura_edesur_luz.pdf"
    res = extractor.extraer_datos_factura(ruta, "factura_edesur_luz.pdf")

    assert res.empresa == "Edesur"
    assert res.servicio == "Electricidad"
    assert res.fecha_vencimiento.strftime("%d/%m/%Y") == "15/06/2026"
    assert res.importe == Decimal("25430.75")
    assert res.moneda == "ARS"
    assert "fecha_vencimiento" in res.evidencia_texto
    assert "importe" in res.evidencia_texto


def test_extraccion_factura_telecom_importe_complejo():
    extractor = obtener_extractor()
    ruta = EJEMPLOS_DIR / "factura_telecom_internet.pdf"
    res = extractor.extraer_datos_factura(ruta, "factura_telecom_internet.pdf")

    assert res.empresa == "Telecom"
    assert res.servicio == "Internet"
    assert res.fecha_vencimiento.strftime("%d/%m/%Y") == "28/05/2026"
    assert res.importe == Decimal("148950.25")
    assert res.moneda == "ARS"


def test_extraccion_factura_aysa_multianual():
    extractor = obtener_extractor()
    ruta = EJEMPLOS_DIR / "factura_aysa_agua.pdf"
    res = extractor.extraer_datos_factura(ruta, "factura_aysa_agua.pdf")

    assert res.empresa == "AySA"
    assert res.servicio == "Agua y Saneamiento"
    assert res.fecha_vencimiento.strftime("%d/%m/%Y") == "10/01/2027"
    assert res.importe == Decimal("12300.00")


def test_deteccion_ambiguedad_y_revision():
    extractor = obtener_extractor()
    ruta = EJEMPLOS_DIR / "factura_ambigua_montos.pdf"
    res = extractor.extraer_datos_factura(ruta, "factura_ambigua_montos.pdf")

    assert res.empresa == "Metrogas"
    assert res.requiere_revision is True
    # Debe haber advertencias sobre moneda '$' o múltiples vencimientos
    assert len(res.observaciones) > 0


def test_deteccion_archivo_sin_texto():
    extractor = obtener_extractor()
    ruta = EJEMPLOS_DIR / "factura_sin_texto.pdf"
    res = extractor.extraer_datos_factura(ruta, "factura_sin_texto.pdf")

    assert res.requiere_revision is True
    assert any("no contiene texto seleccionable" in obs for obs in res.observaciones)
