import sys
from decimal import Decimal
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.skill_loader import obtener_skill
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
    skill = obtener_skill("extraer-vencimiento")
    ruta = EJEMPLOS_DIR / "factura_edesur_luz.pdf"
    res = skill.invocar({"archivo": str(ruta)})
    reg = res["registro"]

    assert reg["empresa"] == "Edesur"
    assert reg["servicio"] == "Electricidad"
    assert reg["fecha_vencimiento_visual"] == "15/06/2026"
    assert reg["importe"] == 25430.75
    assert reg["moneda"] == "ARS"
    assert "fecha_vencimiento" in reg["evidencia_texto"]
    assert "importe" in reg["evidencia_texto"]


def test_extraccion_factura_telecom_importe_complejo():
    skill = obtener_skill("extraer-vencimiento")
    ruta = EJEMPLOS_DIR / "factura_telecom_internet.pdf"
    res = skill.invocar({"archivo": str(ruta)})
    reg = res["registro"]

    assert reg["empresa"] == "Telecom"
    assert reg["servicio"] == "Internet"
    assert reg["fecha_vencimiento_visual"] == "28/05/2026"
    assert reg["importe"] == 148950.25
    assert reg["moneda"] == "ARS"


def test_extraccion_factura_aysa_multianual():
    skill = obtener_skill("extraer-vencimiento")
    ruta = EJEMPLOS_DIR / "factura_aysa_agua.pdf"
    res = skill.invocar({"archivo": str(ruta)})
    reg = res["registro"]

    assert reg["empresa"] == "AySA"
    assert reg["servicio"] == "Agua y Saneamiento"
    assert reg["fecha_vencimiento_visual"] == "10/01/2027"
    assert reg["importe"] == 12300.00


def test_deteccion_ambiguedad_y_revision():
    skill = obtener_skill("extraer-vencimiento")
    ruta = EJEMPLOS_DIR / "factura_ambigua_montos.pdf"
    res = skill.invocar({"archivo": str(ruta)})
    reg = res["registro"]

    assert reg["empresa"] == "Metrogas"
    assert reg["requiere_revision"] is True
    assert len(reg["observaciones"]) > 0


def test_deteccion_archivo_sin_texto():
    skill = obtener_skill("extraer-vencimiento")
    ruta = EJEMPLOS_DIR / "factura_sin_texto.pdf"
    res = skill.invocar({"archivo": str(ruta)})
    reg = res["registro"]

    assert reg["requiere_revision"] is True
    assert any("no contiene texto seleccionable" in obs for obs in reg["observaciones"])
