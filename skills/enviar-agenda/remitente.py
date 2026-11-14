from __future__ import annotations

import os
import re
import smtplib
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

try:
    from dotenv import load_dotenv
    # Cargar variables desde .env si existe en la raíz del proyecto
    ruta_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if ruta_env.exists():
        load_dotenv(ruta_env)
except ImportError:
    pass

from core.models import formatear_importe_argentino


PATRON_EMAIL = re.compile(r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$")


def validar_email(email: str) -> bool:
    """Valida la sintaxis básica de una dirección de correo bajo RFC 5322."""
    if not email or not isinstance(email, str):
        return False
    return bool(PATRON_EMAIL.match(email.strip()))


def armar_cuerpo_texto(totales_por_moneda: Dict[str, Decimal]) -> str:
    """Genera el cuerpo en texto plano con el resumen financiero."""
    lineas = [
        "¡Hola!",
        "",
        "Adjuntamos a este correo la agenda consolidada de vencimientos generada por VenceClaro.",
        "El archivo 'agenda_vencimientos.csv' está configurado con formato regional argentino",
        "(separador ';' y coma decimal) para abrirse directamente en Microsoft Excel.",
        "",
        "--- RESUMEN FINANCIERO A PAGAR ---",
    ]
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


def armar_cuerpo_html(totales_por_moneda: Dict[str, Decimal]) -> str:
    """Genera el cuerpo estilizado en HTML con diseño claro y accesible."""
    filas_totales = ""
    for mon, tot in totales_por_moneda.items():
        filas_totales += f"""
        <li style="margin-bottom: 6px; font-size: 15px;">
            <strong>Total en {mon}:</strong> <span style="color: #047857; font-weight: bold;">{formatear_importe_argentino(tot)} {mon}</span>
        </li>
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
            <p>¡Hola!</p>
            <p>Adjuntamos el archivo consolidado <strong>agenda_vencimientos.csv</strong> generado por <strong>VenceClaro</strong>.</p>
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
    totales_por_moneda: Dict[str, Decimal],
    remitente: Optional[str] = None,
    password: Optional[str] = None,
    dry_run: bool = False,
) -> Tuple[bool, str, str]:
    """
    Skill especializada: enviar-agenda.
    Despacha la agenda de vencimientos vía Gmail SMTP (TLS 587) con el CSV adjunto.

    Retorna: (exito: bool, mensaje: str, modo: "REAL" | "SIMULACION")
    """
    destinatario_limpio = destinatario.strip() if destinatario else ""
    if not validar_email(destinatario_limpio):
        return False, f"La dirección de correo '{destinatario}' no tiene una estructura válida.", "ERROR"

    # Resolver credenciales (parámetros explícitos o variables de entorno)
    remitente_resuelto = (remitente or os.getenv("GMAIL_REMITENTE", "")).strip()
    password_resuelto = (password or os.getenv("GMAIL_APP_PASSWORD", "")).strip().replace(" ", "")

    asunto = "📅 Agenda de Vencimientos - VenceClaro"
    texto_plano = armar_cuerpo_texto(totales_por_moneda)
    texto_html = armar_cuerpo_html(totales_por_moneda)

    # Modo simulación educativa si se solicita explícitamente o no hay credenciales configuradas
    if dry_run or not remitente_resuelto or not password_resuelto:
        msg_sim = (
            f"ℹ️ [Modo Simulación Educativo / Sandbox]: Correo validado para '{destinatario_limpio}'. "
            f"Adjunto 'agenda_vencimientos.csv' ({len(csv_bytes)} bytes) empaquetado exitosamente. "
            f"Para envío real en vivo, configurá tu cuenta Gmail y Contraseña de Aplicación de 16 caracteres."
        )
        return True, msg_sim, "SIMULACION"

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
            "Error de autenticación con Gmail. Verificá que el correo emisor y la contraseña de aplicación "
            "sean correctos (debe ser la contraseña de 16 letras generada en Google > Seguridad > Contraseñas de aplicaciones).",
            "ERROR",
        )
    except smtplib.SMTPException as e:
        return False, f"Falla en el protocolo SMTP de Gmail: {str(e)}", "ERROR"
    except Exception as e:
        return False, f"Error de conexión al enviar el correo: {str(e)}", "ERROR"
