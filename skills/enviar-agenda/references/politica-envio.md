# Política de Envío de Agenda y Seguridad

## 1. Principio de No Emisión Inadvertida
- Ningún correo electrónico debe ser transmitido sin la voluntad y autorización explícita del usuario, y el destinatario debe ser provisto directamente por el usuario (no por el LLM ni por el PDF). [ENV-1]

## 2. Gestión de Credenciales y Secretos
- **Regla de Confidencialidad Absoluta:** Bajo ninguna circunstancia la contraseña de aplicación debe registrarse en logs, mensajes de error, excepciones, traza de auditoría ni pasarse como contexto al LLM. [ENV-2]

## 3. Modo Simulación Educativo (*Dry-Run*)
- En modo simulación (`dry_run=True`), la skill valida y empaqueta el mensaje con la agenda adjunta pero no entabla conexión SMTP con los servidores de red. [ENV-3]
- Si no se suministraron credenciales y no se solicitó expresamente `dry_run=True`, la skill debe rechazar la operación con un error explícito; nunca debe caer silenciosamente a modo simulación. [ENV-4]

## 4. Integridad del Mensaje
- El correo debe despacharse mediante el servidor `smtp.gmail.com:587` con cifrado `STARTTLS`. [ENV-5]
- El mensaje debe contener formato multipart (texto plano y HTML estilizado) con el resumen financiero segregado por moneda, y el archivo `agenda_vencimientos.csv` adjunto con codificación UTF-8 con BOM. [ENV-6]
- Cualquier texto introductorio redactado por un modelo de lenguaje debe ser escapado apropiadamente para prevenir inyecciones HTML (un `<script>` queda inerte en el HTML). [ENV-7]
