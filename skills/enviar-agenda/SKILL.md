---
name: enviar-agenda
description: Despacha la agenda de vencimientos consolidada por correo electrónico a través de la API/SMTP de Gmail, incorporando el archivo CSV regional adjunto y el resumen financiero por moneda en el cuerpo del mensaje. Usar como canal de entrega final tras la generación de la agenda.
---

# Procedimiento de la Skill: enviar-agenda

## Objetivo
Despachar de forma segura y automatizada la agenda consolidada de vencimientos hacia la casilla de correo del usuario, adjuntando el archivo CSV compatible con Excel y presentando el resumen financiero desglosado en el cuerpo del correo.

## Entradas
- **destinatario**: Dirección de correo electrónico de destino (ej. `usuario@gmail.com`).
- **csv_bytes**: Contenido binario del archivo `agenda_vencimientos.csv` generado por `generar-agenda`.
- **totales_por_moneda**: Diccionario de totales financieros agrupados por moneda.
- **remitente**: (Opcional) Dirección Gmail de origen. Si se omite, se lee de variables de entorno (`GMAIL_REMITENTE`).
- **password**: (Opcional) Contraseña de aplicación de 16 caracteres de Google. Si se omite, se lee de `GMAIL_APP_PASSWORD`.
- **dry_run**: (Opcional, booleano) Si es verdadero o no hay credenciales disponibles, activa el modo simulación educativo sin realizar conexión externa.

## Pasos de Ejecución
1. **Validación formal de dirección**:
   Verificar que el email de destino cumpla con la estructura válida de correo electrónico.
2. **Construcción del mensaje MIME multipart**:
   - Crear el mensaje con cabeceras `From`, `To` y `Subject`.
   - Incorporar cuerpo de texto plano y cuerpo en HTML estilizado con el resumen por monedas.
   - Adjuntar el archivo `agenda_vencimientos.csv` con encabezado `Content-Disposition: attachment; filename="agenda_vencimientos.csv"`.
3. **Comprobación de credenciales y modo de despacho**:
   - Si no se suministraron credenciales y `dry_run` está activo, retornar éxito simulado con detalle del mensaje empaquetado.
   - Si se suministraron credenciales, iniciar sesión en `smtp.gmail.com:587` utilizando TLS (`STARTTLS`).
4. **Despacho del mensaje**:
   Transmitir el correo electrónico hacia el servidor de Gmail y capturar el acuse de recibo.
5. **Cierre seguro**:
   Finalizar la sesión SMTP liberando sockets y retornando el estado de confirmación.

## Referencias a Consultar
- [politica-envio.md](file:///c:/Users/Asus/Documents/Diplomatura%20IA/venceclaro/skills/enviar-agenda/references/politica-envio.md): Directivas de seguridad, protección de contraseñas de app y modo sandbox.

## Ejecutable
- Bash: `scripts/ejecutar.sh --destino <correo> --csv <archivo.csv> [--dry-run]`
- Python: `python scripts/ejecutar.py --destino <correo> --csv <archivo.csv> [--dry-run]`

## Salida
- Tupla o diccionario con:
  - `exito`: Booleano (`True` si se envió o simuló con éxito).
  - `mensaje`: Descripción del resultado (incluyendo ID de mensaje o advertencia).
  - `modo`: `"REAL"` o `"SIMULACION"`.

## Manejo de Errores
- Si la dirección de correo es sintácticamente inválida, interrumpe el flujo informando el error sin intentar conectar.
- Si Gmail rechaza la contraseña de aplicación (`SMTPAuthenticationError`), informa de manera clara que debe utilizarse la contraseña de 16 caracteres de Google.
- Si ocurre una desconexión o timeout de red, devuelve un mensaje explicativo sin provocar caída de la aplicación.
