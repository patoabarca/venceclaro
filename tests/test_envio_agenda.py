import sys
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.agent import AgenteVencimientos
from core.skill_loader import obtener_remitente

EJEMPLOS_DIR = BASE_DIR / "ejemplos"


def test_validacion_sintaxis_email():
    remitente_mod = obtener_remitente()

    assert remitente_mod.validar_email("usuario@gmail.com") is True
    assert remitente_mod.validar_email("nombre.apellido+tag@empresa.com.ar") is True
    assert remitente_mod.validar_email("invalido@") is False
    assert remitente_mod.validar_email("sin_arroba.com") is False
    assert remitente_mod.validar_email("") is False


def test_construccion_mensaje_con_adjunto():
    remitente_mod = obtener_remitente()

    csv_dummy = "Vencimiento;Empresa;Servicio;Importe;Moneda;Archivo de origen\r\n15/05/2026;Edesur;Luz;14.250,00;ARS;factura.pdf\r\n".encode("utf-8-sig")
    totales = {"ARS": Decimal("14250.00")}

    texto = remitente_mod.armar_cuerpo_texto(totales)
    html = remitente_mod.armar_cuerpo_html(totales)

    assert "14.250,00" in texto
    assert "14.250,00" in html

    msg = remitente_mod.construir_mensaje(
        remitente="remitente@gmail.com",
        destinatario="destino@gmail.com",
        asunto="Prueba Agenda",
        cuerpo_texto=texto,
        cuerpo_html=html,
        csv_bytes=csv_dummy,
        nombre_adjunto="agenda_vencimientos.csv",
    )

    assert msg["From"] == "remitente@gmail.com"
    assert msg["To"] == "destino@gmail.com"
    assert msg["Subject"] == "Prueba Agenda"

    # Verificar que contenga el adjunto
    adjuntos = [p for p in msg.iter_attachments()]
    assert len(adjuntos) == 1
    assert adjuntos[0].get_filename() == "agenda_vencimientos.csv"


def test_despacho_modo_simulacion_educativo():
    remitente_mod = obtener_remitente()

    csv_dummy = "dummy_content".encode("utf-8-sig")
    exito, msg, modo = remitente_mod.despachar_agenda_gmail(
        destinatario="alumno@universidad.edu.ar",
        csv_bytes=csv_dummy,
        totales_por_moneda={"ARS": Decimal("1000.00")},
        dry_run=True,
    )

    assert exito is True
    assert modo == "SIMULACION"
    assert "alumno@universidad.edu.ar" in msg


def test_agente_flujo_enviar_agenda_correo():
    agente = AgenteVencimientos()

    archivos = [
        ("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf"),
    ]
    agente.procesar_archivos_iniciales(archivos)
    agente.validar_y_confirmar(agente.registros_revision)

    # El agente debe permitir despachar en modo simulación
    exito, msg, modo = agente.enviar_agenda_por_correo(
        destinatario="profesor@diplomatura.edu.ar",
        dry_run=True,
    )

    assert exito is True
    assert modo == "SIMULACION"
    assert any("profesor@diplomatura.edu.ar" in m for m in agente.mensajes_estado)
