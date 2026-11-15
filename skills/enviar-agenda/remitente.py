from __future__ import annotations

import os
import re
import smtplib
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import html

# Carga obligatoria y explícita de dotenv (sin try/except silencioso)
from dotenv import load_dotenv

ruta_env = Path(__file__).resolve().parent.parent.parent / ".env"
if ruta_env.exists():
    load_dotenv(ruta_env)

from core.models import formatear_importe_argentino

PATRON_EMAIL = re.compile(r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$")


def validar_email(email: str) -> bool:
    """Valida la sintaxis básica de una dirección de correo bajo RFC 5322."""
    if not email or not isinstance(email, str):
        return False
    return bool(PATRON_EMAIL.match(email.strip()))


def armar_cuerpo_texto(totales_por_moneda: Dict[str, Decimal], texto_intro: Optional[str] = None) -> str:
    """Genera el cuerpo en texto plano con el resumen financiero y texto opcional del LLM."""
    lineas = []
    if texto_intro and texto_intro.strip():
        lineas.append(texto_intro.strip())
        lineas.append("")
    else:
        lineas.extend([
            "¡Hola!",
            "",
            "Adjuntamos a este correo la agenda consolidada de vencimientos generada por VenceClaro.",
            "El archivo 'agenda_vencimientos.csv' está configurado con formato regional argentino",
            "(separador ';' y coma decimal) para abrirse directamente en Microsoft Excel.",
            "",
        ])

    lineas.append("--- RESUMEN FINANCIERO A PAGAR ---")
    if totales_por_moneda:
        for mon, tot in totales_por_moneda.items():
            lineas.append(f"• Total en {mon}: $ {formatear_importe_argentino(tot)} {mon}")
    else:
        lineas.append("• Sin totales registrados.")

    lineas.extend([
        "",
        "Atentamente,",
        "Agente VenceClaro - Organizador de Vencimientos",
    ])
    return "\n".join(lineas)


def armar_cuerpo_html(totales_por_moneda: Dict[str, Decimal], texto_intro: Optional[str] = None) -> str:
    """Genera el cuerpo estilizado en HTML con diseño claro y accesible, escapando el texto del LLM."""
    filas_totales = ""
    for mon, tot in totales_por_moneda.items():
        filas_totales += f"""
        <li style="margin-bottom: 6px; font-size: 15px;">
            <strong>Total en {mon}:</strong> <span style="color: #047857; font-weight: bold;">{formatear_importe_argentino(tot)} {mon}</span>
        </li>
        """

    intro_html = ""
    if texto_intro and texto_intro.strip():
        parrafos = [f"<p>{html.escape(p)}</p>" for p in texto_intro.strip().split("\n\n") if p.strip()]
        intro_html = "\n".join(parrafos)
    else:
        intro_html = """
        <p>¡Hola!</p>
        <p>Adjuntamos el archivo consolidado <strong>agenda_vencimientos.csv</strong> generado por <strong>VenceClaro</strong>.</p>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 580px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 24px;">
            <h2 style="color: #0f172a; margin-top: 0;">📅 Tu Agenda de Vencimientos</h2>
            {intro_html}
            <div style="background-color: #f1f5f9; border-left: 4px solid #0284c7; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
                <h4 style="margin: 0 0 8px 0; color: #0369a1;">Resumen Financiero por Moneda:</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    {filas_totales if filas_totales else '<li>Sin importes computados.</li>'}
                </ul>
            </div>
            <p style="font-size: 13px; color: #64748b;">
                ℹ️ <em>El archivo CSV adjunto cuenta con codificación UTF-8 con BOM y delimitador de punto y coma, listo para abrirse en Microsoft Excel sin desconfigurar importes ni acentos.</em>
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 12px; color: #94a3b8; margin-bottom: 0;">
                Enviado de forma automatizada por el Agente VenceClaro.
            </p>
        </div>
    </body>
    </html>
    """


def construir_mensaje(
    remitente: str,
    destinatario: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str,
    csv_bytes: bytes,
    nombre_adjunto: str = "agenda_vencimientos.csv",
) -> EmailMessage:
    """Construye el objeto EmailMessage multipart con texto, HTML y el archivo adjunto."""
    mensaje = EmailMessage()
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto

    mensaje.set_content(cuerpo_texto)
    mensaje.add_alternative(cuerpo_html, subtype="html")

    mensaje.add_attachment(
        csv_bytes,
        maintype="text",
        subtype="csv",
        filename=nombre_adjunto,
    )
    return mensaje


def despachar_agenda_gmail(
    destinatario: str,
    csv_bytes: bytes,
    totales_por_moneda: Dict[str, Union[Decimal, float]],
    remitente: Optional[str] = None,
    password: Optional[str] = None,
    dry_run: bool = False,
    texto_intro: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """
    Skill especializada: enviar-agenda.
    Despacha la agenda de vencimientos vía Gmail SMTP (TLS 587) con el CSV adjunto.
    Comportamiento:
      - dry_run=True explícito: ejecuta modo simulación educativa.
      - dry_run=False: exige credenciales reales. Si faltan, devuelve error explícito (NO simula en silencio).
      - Manejo de excepciones SMTP sin filtrar contraseñas en mensajes o trazas.
    Retorna: (exito: bool, mensaje: str, modo: "REAL" | "SIMULACION" | "ERROR")
    """
    destinatario_limpio = destinatario.strip() if destinatario else ""
    if not validar_email(destinatario_limpio):
        return False, f"La dirección de correo '{destinatario}' no tiene una estructura válida.", "ERROR"

    # Convertir totales a Decimal si vienen como float
    totales_dec: Dict[str, Decimal] = {}
    for k, v in totales_por_moneda.items():
        totales_dec[k] = Decimal(str(v)) if not isinstance(v, Decimal) else v

    # Modo simulación solo si se pidió EXPRESAMENTE con dry_run=True
    if dry_run:
        msg_sim = (
            f"ℹ️ [Modo Simulación Educativo / Sandbox]: Correo validado para '{destinatario_limpio}'. "
            f"Adjunto 'agenda_vencimientos.csv' ({len(csv_bytes)} bytes) empaquetado exitosamente. "
            f"Simulación finalizada sin conexiones externas."
        )
        return True, msg_sim, "SIMULACION"

    # Resolver credenciales (parámetros explícitos o variables de entorno)
    remitente_resuelto = (remitente or os.getenv("GMAIL_REMITENTE", "")).strip()
    password_resuelto = (password or os.getenv("GMAIL_APP_PASSWORD", "")).strip().replace(" ", "")

    if not remitente_resuelto or not password_resuelto:
        return (
            False,
            "Faltan credenciales de correo (GMAIL_REMITENTE / GMAIL_APP_PASSWORD). "
            "Configure las variables en el archivo .env o suministre credenciales para envío real, "
            "o active el modo simulación con dry_run=True.",
            "ERROR",
        )

    asunto = "📅 Agenda de Vencimientos - VenceClaro"
    texto_plano = armar_cuerpo_texto(totales_dec, texto_intro=texto_intro)
    texto_html = armar_cuerpo_html(totales_dec, texto_intro=texto_intro)

    # Envío real vía Gmail SMTP TLS
    try:
        msg = construir_mensaje(
            remitente=remitente_resuelto,
            destinatario=destinatario_limpio,
            asunto=asunto,
            cuerpo_texto=texto_plano,
            cuerpo_html=texto_html,
            csv_bytes=csv_bytes,
        )

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.ehlo()
            servidor.login(remitente_resuelto, password_resuelto)
            servidor.send_message(msg)

        return True, f"¡Correo enviado exitosamente a '{destinatario_limpio}' desde '{remitente_resuelto}'!", "REAL"

    except smtplib.SMTPAuthenticationError:
        return (
            False,
            "Error de autenticación con Gmail (SMTPAuthenticationError). Verifique que el correo emisor y la contraseña "
            "de aplicación sean correctos (debe ser la contraseña de 16 caracteres generada en Google > Seguridad > Contraseñas de aplicaciones).",
            "ERROR",
        )
    except smtplib.SMTPRecipientsRefused:
        return False, f"El servidor de Gmail rechazó la dirección de destinatario '{destinatario_limpio}'.", "ERROR"
    except smtplib.SMTPException as e:
        return False, f"Falla en el protocolo SMTP de Gmail: {type(e).__name__}", "ERROR"
    except Exception as e:
        return False, f"Error de conexión al enviar el correo: {type(e).__name__}", "ERROR"


ESQUEMA_ENTRADA = {
    "type": "object",
    "properties": {
        "destinatario": {
            "type": "string",
            "description": "Dirección de correo electrónico de destino donde se despachará la agenda.",
        },
        "csv_bytes": {
            "type": "string",
            "description": "Bytes en memoria del CSV de agenda a adjuntar.",
        },
        "totales_por_moneda": {
            "type": "object",
            "description": "Diccionario con los subtotales a pagar agrupados por moneda.",
        },
        "remitente": {
            "type": "string",
            "description": "Dirección de correo emisor de Gmail opcional (o se lee de entorno).",
        },
        "password": {
            "type": "string",
            "description": "Contraseña de aplicación de 16 caracteres de Gmail opcional (o se lee de entorno).",
        },
        "dry_run": {
            "type": "boolean",
            "description": "Si es True, ejecuta en modo simulación educativa sin conectar a la red.",
        },
        "texto_intro": {
            "type": "string",
            "description": "Texto introductorio opcional redactado por el agente para el cuerpo del correo.",
        },
    },
    "required": ["destinatario"],
}


def invocar(entrada: dict) -> dict:
    """
    Contrato estándar de la skill: invocar(entrada: dict) -> dict.
    Envuelve despachar_agenda_gmail.
    """
    destinatario = entrada.get("destinatario", "")
    csv_bytes = entrada.get("csv_bytes")
    if csv_bytes is None:
        # Si no se pasó en bytes directos, buscar archivo en disco
        ruta_csv = entrada.get("ruta_csv", "agenda_vencimientos.csv")
        p = Path(ruta_csv)
        if p.exists():
            csv_bytes = p.read_bytes()
        else:
            csv_bytes = b"Vencimiento;Empresa;Servicio;Importe;Moneda;Archivo de origen\r\n"

    totales = entrada.get("totales_por_moneda", {})
    remitente = entrada.get("remitente")
    password = entrada.get("password")
    dry_run = entrada.get("dry_run", False)
    texto_intro = entrada.get("texto_intro")

    exito, mensaje, modo = despachar_agenda_gmail(
        destinatario=destinatario,
        csv_bytes=csv_bytes,
        totales_por_moneda=totales,
        remitente=remitente,
        password=password,
        dry_run=dry_run,
        texto_intro=texto_intro,
    )

    return {
        "exito": exito,
        "mensaje": mensaje,
        "modo": modo,
    }
