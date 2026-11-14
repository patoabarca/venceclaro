# Política de Envío y Despacho de Agenda por Correo

## 1. Principio de Responsabilidad Delimitada
- La skill `enviar-agenda` tiene como única función técnica empaquetar y despachar la agenda de vencimientos vía correo electrónico (protocolo SMTP seguro sobre Gmail / API de correo).
- No altera los importes, fechas ni contenidos del archivo CSV provisto.
- No reemplaza la descarga local en la interfaz; actúa como canal de entrega complementario.

## 2. Protección Estricta de Credenciales y Privacidad
- Está terminantemente prohibido imprimir o persistir en registros de logs o trazas de auditoría la contraseña de aplicación de Gmail (*App Password*).
- Las credenciales se obtienen prioritariamente de variables de entorno (`GMAIL_REMITENTE`, `GMAIL_APP_PASSWORD`), del archivo `.env` o del formulario protegido en memoria de la sesión.
- En caso de error de autenticación, el mensaje informativo debe orientar al usuario sobre cómo generar su contraseña de 16 caracteres en Google sin exponer información interna.

## 3. Integridad del Correo y Adjunto
- **Asunto estandarizado**: `📅 Agenda de Vencimientos - VenceClaro`
- **Cuerpo estructurado (Multipart Texto y HTML)**:
  - Incluye tabla sintética de comprobantes con sus fechas de vencimiento.
  - Informa los subtotales desagregados estrictamente por moneda (ARS / USD).
- **Archivo adjunto**:
  - Nombre: `agenda_vencimientos.csv`.
  - Tipo MIME: `text/csv`.
  - Codificación preservada: UTF-8 con BOM (`utf-8-sig`) para compatibilidad directa con Microsoft Excel en la máquina del destinatario.

## 4. Validación de Dirección y Modo Sandbox Educativo
- Antes de iniciar la conexión de red, la dirección del destinatario debe validarse bajo formato RFC 5322.
- **Modo Sandbox / Simulación Educativa**: Si el entorno de ejecución no dispone de credenciales de Gmail cargadas (por ejemplo, durante la evaluación docente o pruebas locales rápidas), la skill valida el empaquetado del mensaje y simula el despacho exitoso devolviendo un identificador simbólico `SIM-GMAIL-OK`, evitando bloqueos en la demostración académica.
