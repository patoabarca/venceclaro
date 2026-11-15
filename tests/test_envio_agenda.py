import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.skill_loader import descubrir_skills, obtener_skill, _cargar_modulo_python

_rem_info = descubrir_skills()["enviar-agenda"]
_rem_mod = _cargar_modulo_python("enviar-agenda", _rem_info.modulo_entrada)
validar_email = _rem_mod.validar_email
construir_mensaje = _rem_mod.construir_mensaje

CSV_TEST = b"Vencimiento;Empresa;Servicio;Importe;Moneda;Archivo de origen\r\n15/06/2026;Edesur;Luz;25.430,75;ARS;edesur.pdf\r\n"
TOTALES_TEST = {"ARS": Decimal("25430.75")}


def test_validacion_sintaxis_email():
    assert validar_email("usuario@gmail.com") is True
    assert validar_email("nombre.apellido+tag@empresa.com.ar") is True
    assert validar_email("correo_invalido") is False
    assert validar_email("@sin_usuario.com") is False
    assert validar_email("") is False


def test_construccion_mensaje_con_adjunto():
    msg = construir_mensaje(
        remitente="remitente@gmail.com",
        destinatario="destino@gmail.com",
        asunto="Prueba Agenda",
        cuerpo_texto="Texto plano de prueba",
        cuerpo_html="<p>HTML de prueba</p>",
        csv_bytes=CSV_TEST,
    )

    assert msg["From"] == "remitente@gmail.com"
    assert msg["To"] == "destino@gmail.com"
    assert msg["Subject"] == "Prueba Agenda"

    adjuntos = [p for p in msg.iter_attachments()]
    assert len(adjuntos) == 1
    assert adjuntos[0].get_filename() == "agenda_vencimientos.csv"
    assert adjuntos[0].get_payload(decode=True) == CSV_TEST


def test_despacho_modo_simulacion_educativo():
    skill = obtener_skill("enviar-agenda")
    res = skill.invocar({
        "destinatario": "estudiante@ejemplo.com",
        "csv_bytes": CSV_TEST,
        "totales_por_moneda": TOTALES_TEST,
        "dry_run": True,
    })

    assert res["exito"] is True
    assert res["modo"] == "SIMULACION"
    assert "Modo Simulación Educativo" in res["mensaje"]


def test_error_explicito_sin_credenciales_y_sin_dry_run():
    skill = obtener_skill("enviar-agenda")
    with patch.dict("os.environ", {"GMAIL_REMITENTE": "", "GMAIL_APP_PASSWORD": ""}):
        res = skill.invocar({
            "destinatario": "alguien@ejemplo.com",
            "csv_bytes": CSV_TEST,
            "totales_por_moneda": TOTALES_TEST,
            "dry_run": False,
        })
        assert res["exito"] is False
        assert res["modo"] == "ERROR"
        assert "Faltan credenciales" in res["mensaje"]


def test_envio_real_mockeado_con_smtp():
    skill = obtener_skill("enviar-agenda")
    with patch("smtplib.SMTP") as mock_smtp:
        instancia = MagicMock()
        mock_smtp.return_value.__enter__.return_value = instancia

        res = skill.invocar({
            "destinatario": "cliente@ejemplo.com",
            "csv_bytes": CSV_TEST,
            "totales_por_moneda": TOTALES_TEST,
            "remitente": "yo@gmail.com",
            "password": "pass_de_aplicacion",
            "dry_run": False,
        })

        assert res["exito"] is True
        assert res["modo"] == "REAL"
        assert "exitosamente" in res["mensaje"]
        assert instancia.starttls.called
        assert instancia.login.called
        assert instancia.send_message.called


def test_error_autenticacion_smtp_sin_exponer_password():
    import smtplib
    skill = obtener_skill("enviar-agenda")
    with patch("smtplib.SMTP") as mock_smtp:
        instancia = MagicMock()
        instancia.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        mock_smtp.return_value.__enter__.return_value = instancia

        password_secreta = "secreto_clave_123"
        res = skill.invocar({
            "destinatario": "cliente@ejemplo.com",
            "csv_bytes": CSV_TEST,
            "totales_por_moneda": TOTALES_TEST,
            "remitente": "yo@gmail.com",
            "password": password_secreta,
            "dry_run": False,
        })

        assert res["exito"] is False
        assert res["modo"] == "ERROR"
        assert "SMTPAuthenticationError" in res["mensaje"]
        assert password_secreta not in res["mensaje"]
