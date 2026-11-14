# Política de Orquestación y Coordinación del Flujo

## 1. Principio de Separación de Responsabilidades
- La skill `organizar-vencimientos` actúa exclusivamente como coordinadora del flujo integral.
- No debe contener reglas heurísticas de extracción de texto PDF (delegadas a `extraer-vencimiento`).
- No debe alterar ni ordenar listas por cuenta propia (delegado a `ordenar-vencimientos`).
- No debe formatear cadenas CSV ni escribir archivos de exportación directamente (delegado a `generar-agenda`).

## 2. Flujo Secuencial con Supervisión Humana (Human-in-the-Loop)
El flujo reglamentario se divide en 5 etapas secuenciales:
1. **Extracción**: Invocación paralela o por lotes de `extraer-vencimiento` para cada comprobante PDF.
2. **Handoff de Revisión**: Presentación explícita al usuario de los datos obtenidos y sus observaciones para revisión.
3. **Reanudación del Flujo**: El usuario confirma correcciones y/o exclusión de documentos ilegibles o incompletos.
4. **Ordenamiento**: Una vez confirmados los datos válidos, se invoca `ordenar-vencimientos`.
5. **Generación de Agenda**: Se invoca `generar-agenda` para producir el CSV compatible con Excel.

## 3. Condiciones de Bloqueo y Exclusión
- La generación de la agenda definitiva queda bloqueada mientras existan comprobantes incluidos que carezcan de cualquiera de los cuatro campos obligatorios:
  - Empresa emisora.
  - Fecha de vencimiento válida.
  - Importe estrictamente positivo.
  - Moneda identificada.
- El usuario tiene la facultad de marcar un comprobante como `excluido`. En tal caso, el archivo no bloquea el flujo y se informa explícitamente en el resumen de auditoría cuáles archivos quedaron fuera.

## 4. Trazabilidad de Cambios
- Durante toda la sesión deben conservarse en memoria los valores originalmente extraídos junto con los valores corregidos por el usuario, permitiendo auditoría y transparencia sobre las modificaciones manuales.
