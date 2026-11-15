# Política de Envío de Agenda y Seguridad

## 1. Principio de No Emisión Inadvertida
- Ningún correo electrónico debe ser transmitido sin la voluntad y autorización explícita del usuario.
- El destinatario debe ser provisto directamente por el usuario (mediante el campo en la interfaz o el argumento `--enviar-a` en el CLI). Está terminantemente prohibido que un modelo de lenguaje o un documento PDF defina o altere el destinatario.

## 2. Gestión de Credenciales y Secretos
- Las credenciales de Gmail (`GMAIL_REMITENTE` y `GMAIL_APP_PASSWORD`) deben administrarse exclusivamente mediante variables de entorno en el archivo `.env`.
- La contraseña de aplicación debe ser la clave de 16 caracteres generada en la configuración de seguridad de Google.
- **Regla de Confidencialidad Absoluta:** Bajo ninguna circunstancia la contraseña debe registrarse en logs, imprimirse en consola, incluirse en excepciones ni pasarse como contexto a ningún modelo de lenguaje.

## 3. Modo Simulación Educativo (*Dry-Run*)
- Para pruebas automatizadas, demostraciones o revisiones sin impacto externo, se debe utilizar el parámetro `dry_run=True`.
- En modo simulación, la skill valida la sintaxis del correo, empaqueta el mensaje con el archivo adjunto `agenda_vencimientos.csv` y devuelve éxito sin entablar conexión de red con los servidores de Google.
- Si no se suministraron credenciales y no se solicitó expresamente `dry_run=True`, la skill debe rechazar la operación con un error explícito; **no debe caer silenciosamente a modo simulación**.

## 4. Integridad del Mensaje
- El correo debe despacharse mediante `smtp.gmail.com:587` con cifrado `STARTTLS`.
- El mensaje debe contener formato multipart (texto plano y HTML estilizado) con el resumen financiero segregado por moneda, y el archivo `agenda_vencimientos.csv` adjunto con codificación UTF-8 con BOM.
- Cualquier texto introductorio redactado por un modelo de lenguaje debe ser escapado apropiadamente para prevenir inyecciones HTML.
