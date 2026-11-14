---
name: extraer-vencimiento
description: Extrae campos estructurados (empresa, servicio, importe, moneda, vencimiento) y evidencia textual desde archivos PDF de facturas con texto seleccionable. Usar cuando se necesite digitalizar y auditar una factura individual sin alterar el orden ni generar archivos finales.
---

# Procedimiento de la Skill: extraer-vencimiento

## Objetivo
Procesar un documento PDF de factura de servicios y extraer un registro de datos estructurado acompañado de la evidencia textual que respalda cada valor obtenido, respetando los estándares numéricos y de fechas argentinos.

## Entradas
- **fuente**: Archivo PDF accesible por ruta del sistema de archivos, flujo binario o bytes en memoria.
- **nombre_archivo**: Nombre representativo del archivo de origen (ej. `factura_luz.pdf`).

## Pasos de Ejecución
1. **Verificación de capa de texto**:
   Extraer el texto con la biblioteca `pypdf`. Si el texto resultante tiene menos de 20 caracteres útiles, marcar inmediatamente como no compatible con el MVP (requiere revisión o exclusión) y registrar la observación.
2. **Identificación de la empresa emisora**:
   Examinar los encabezados del documento buscando nombres de prestatarias reconocidas o patrones como `Razón Social:` o `Empresa:`. Capturar el fragmento textual como evidencia.
3. **Identificación del tipo de servicio**:
   Clasificar el servicio según palabras clave (Electricidad, Gas Natural, Agua, Internet, Telefonía, etc.) o inferir el rubro habitual de la prestataria identificada.
4. **Detección de la fecha de vencimiento**:
   Localizar de manera estricta patrones de vencimiento (`Vencimiento`, `Vto`, `1er Vto`). Descartar fechas identificadas como `Fecha de Emisión`. En caso de múltiples vencimientos, tomar el primero y solicitar confirmación al usuario.
5. **Detección del importe a pagar**:
   Buscar la etiqueta `Total a pagar` o `Importe Total`. Omitir montos rotulados como `Subtotal` o `IVA`. Interpretar los importes con el formato argentino (punto de miles, coma decimal).
6. **Validación de la moneda**:
   Verificar si existe indicación explícita (`ARS`, `PESOS`, `USD`). Si únicamente se detecta el símbolo `$`, asignar advertencia de revisión indicando que `$` no define unívocamente la moneda.
7. **Consolidación del registro**:
   Construir el objeto `FacturaExtraida` con el mapa de evidencias y la lista de observaciones de validación.

## Referencias a Consultar
- [politica-extraccion.md](file:///c:/Users/Asus/Documents/Diplomatura%20IA/venceclaro/skills/extraer-vencimiento/references/politica-extraccion.md): Reglas de no invención de datos, formato argentino y tratamiento pasivo de documentos.

## Ejecutable
- Bash: `scripts/ejecutar.sh <ruta_factura.pdf> [--json]`
- Python: `python scripts/ejecutar.py <ruta_factura.pdf> [--json]`

## Salida
Objeto o diccionario `FacturaExtraida` conteniendo:
- `id`: Identificador único del registro.
- `archivo_origen`: Nombre del archivo procesado.
- `empresa`: Razón social o nombre comercial identificado.
- `servicio`: Rubro o tipo de servicio prestado.
- `importe`: Monto en tipo `Decimal`.
- `moneda`: Código de moneda (`ARS`, `USD`).
- `fecha_vencimiento`: Fecha en formato ISO (`AAAA-MM-DD`).
- `evidencia_texto`: Diccionario con las frases exactas del documento que justifican los datos.
- `requiere_revision`: Indicador booleano de si hay campos faltantes o ambiguos.
- `observaciones`: Lista de advertencias para el usuario.

## Manejo de Errores
- **Archivo inexistente o ilegible**: Retorna código de salida distinto de cero en CLI o un registro marcado con `excluido = true` y observación de error en la API Python.
- **Documento sin capa de texto**: No aborta el proceso global; marca el registro con advertencia explícita para que el usuario pueda transcribir o excluir el comprobante.
- **Falta de certeza en datos**: No inventa información; deja el campo vacío y marca `requiere_revision = true`.
