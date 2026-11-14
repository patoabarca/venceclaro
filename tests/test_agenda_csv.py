import io
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.models import FacturaConfirmada
from core.skill_loader import obtener_generador


def test_generacion_agenda_columnas_y_formato_argentino():
    generador = obtener_generador()

    reg1 = FacturaConfirmada(
        id="1", archivo_origen="edesur.pdf", empresa="Edesur", servicio="Electricidad",
        importe=Decimal("25430.75"), moneda="ARS", fecha_vencimiento=date(2026, 6, 15)
    )
    reg2 = FacturaConfirmada(
        id="2", archivo_origen="aws.pdf", empresa="Amazon Web Services", servicio="Nube",
        importe=Decimal("45.50"), moneda="USD", fecha_vencimiento=date(2026, 8, 5)
    )

    csv_texto = generador.generar_agenda_csv([reg1, reg2])
    lineas = [l for l in csv_texto.splitlines() if l.strip()]

    # Verificar encabezados obligatorios
    assert lineas[0] == "Vencimiento;Empresa;Servicio;Importe;Moneda;Archivo de origen"

    # Verificar fila 1: formato fecha DD/MM/AAAA e importe argentino con coma
    assert lineas[1] == "15/06/2026;Edesur;Electricidad;25.430,75;ARS;edesur.pdf"

    # Verificar fila 2
    assert lineas[2] == "05/08/2026;Amazon Web Services;Nube;45,50;USD;aws.pdf"


def test_codificacion_utf8_con_bom_para_excel():
    generador = obtener_generador()
    reg = FacturaConfirmada(
        id="1", archivo_origen="telecom_año.pdf", empresa="Compañía Eléctrica", servicio="Atención Médica",
        importe=Decimal("1500.00"), moneda="ARS", fecha_vencimiento=date(2026, 5, 20)
    )

    csv_bytes = generador.generar_agenda_bytes([reg])

    # Debe comenzar con el BOM UTF-8 (\xef\xbb\xbf)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")
    # Debe decodificarse sin error preservando tildes y eñes
    texto_decodificado = csv_bytes.decode("utf-8-sig")
    assert "Compañía Eléctrica" in texto_decodificado
    assert "Atención Médica" in texto_decodificado


def test_segregacion_estricta_de_monedas_sin_mezcla():
    generador = obtener_generador()

    reg1 = FacturaConfirmada(
        id="1", archivo_origen="luz.pdf", empresa="Edesur", servicio="Luz",
        importe=Decimal("25000.00"), moneda="ARS", fecha_vencimiento=date(2026, 6, 15)
    )
    reg2 = FacturaConfirmada(
        id="2", archivo_origen="gas.pdf", empresa="Metrogas", servicio="Gas",
        importe=Decimal("15000.00"), moneda="ARS", fecha_vencimiento=date(2026, 6, 20)
    )
    reg3 = FacturaConfirmada(
        id="3", archivo_origen="cloud.pdf", empresa="AWS", servicio="Nube",
        importe=Decimal("50.00"), moneda="USD", fecha_vencimiento=date(2026, 7, 1)
    )

    totales = generador.calcular_totales_por_moneda([reg1, reg2, reg3])

    # No debe haber un total general que mezcle ARS con USD
    assert "ARS" in totales
    assert "USD" in totales
    assert totales["ARS"] == Decimal("40000.00")
    assert totales["USD"] == Decimal("50.00")
    assert len(totales) == 2
