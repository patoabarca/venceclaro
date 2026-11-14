import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.models import FacturaConfirmada
from core.skill_loader import obtener_ordenador


def test_ordenamiento_fechas_multiples_meses_y_anios():
    ordenador = obtener_ordenador()

    reg1 = FacturaConfirmada(
        id="1", archivo_origen="f1.pdf", empresa="AySA", servicio="Agua",
        importe=Decimal("12300.00"), moneda="ARS", fecha_vencimiento=date(2027, 1, 10)
    )
    reg2 = FacturaConfirmada(
        id="2", archivo_origen="f2.pdf", empresa="Telecom", servicio="Internet",
        importe=Decimal("50000.00"), moneda="ARS", fecha_vencimiento=date(2026, 5, 28)
    )
    reg3 = FacturaConfirmada(
        id="3", archivo_origen="f3.pdf", empresa="Edesur", servicio="Luz",
        importe=Decimal("25000.00"), moneda="ARS", fecha_vencimiento=date(2026, 6, 15)
    )

    ordenados = ordenador.ordenar_vencimientos([reg1, reg2, reg3])

    # El orden debe ser: Mayo 2026 -> Junio 2026 -> Enero 2027
    assert [r.id for r in ordenados] == ["2", "3", "1"]


def test_ordenamiento_desempate_estable_por_empresa_y_archivo():
    ordenador = obtener_ordenador()
    misma_fecha = date(2026, 6, 15)

    # Misma fecha, distintas empresas
    reg_b = FacturaConfirmada(
        id="b", archivo_origen="factura_z.pdf", empresa="Metrogas", servicio="Gas",
        importe=Decimal("15000.00"), moneda="ARS", fecha_vencimiento=misma_fecha
    )
    reg_a = FacturaConfirmada(
        id="a", archivo_origen="factura_a.pdf", empresa="Edesur", servicio="Luz",
        importe=Decimal("20000.00"), moneda="ARS", fecha_vencimiento=misma_fecha
    )
    # Misma fecha y misma empresa, distinto archivo
    reg_a2 = FacturaConfirmada(
        id="a2", archivo_origen="factura_b.pdf", empresa="Edesur", servicio="Luz",
        importe=Decimal("10000.00"), moneda="ARS", fecha_vencimiento=misma_fecha
    )

    ordenados = ordenador.ordenar_vencimientos([reg_b, reg_a2, reg_a])

    # Debe desempatar Edesur antes que Metrogas, y factura_a.pdf antes que factura_b.pdf
    assert [r.id for r in ordenados] == ["a", "a2", "b"]


def test_ordenamiento_falla_si_fecha_nula():
    ordenador = obtener_ordenador()
    reg_invalido = FacturaConfirmada(
        id="err", archivo_origen="error.pdf", empresa="Empresa", servicio="Servicio",
        importe=Decimal("1000.00"), moneda="ARS", fecha_vencimiento=None  # type: ignore
    )
    with pytest.raises(ValueError, match="carece de fecha de vencimiento"):
        ordenador.ordenar_vencimientos([reg_invalido])
