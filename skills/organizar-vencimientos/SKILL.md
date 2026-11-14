---
name: organizar-vencimientos
description: Skill orquestadora de VenceClaro. Coordina el flujo completo entre las skills especializadas (extracción, ordenamiento y generación de agenda) incorporando el punto de control de revisión humana y preservando la trazabilidad de cambios. Usar como punto de entrada de alto nivel para organizar facturas de servicios.
---

# Procedimiento de la Skill: organizar-vencimientos

## Distinción entre la Skill Orquestadora y las Skills Especializadas
Mientras que las skills especializadas (`extraer-vencimiento`, `ordenar-vencimientos`, `generar-agenda`) encapsulan una única responsabilidad técnica acotada (lectura de documentos, ordenamiento determinista y exportación de archivos), la skill `organizar-vencimientos` **no ejecuta trabajo de bajo nivel**: su función primordial es coordinar el ciclo de vida del agente, gestionar las transiciones de estado, supervisar los puntos de control con el usuario y encadenar las salidas de una etapa con las entradas de la siguiente.

## Objetivo
Gestionar el flujo integral de organización de vencimientos de facturas en PDF garantizando que ningún comprobante sea ordenado ni exportado a la agenda sin haber superado la validación de completitud y la confirmación explícita del usuario.

## Entradas
- **archivos**: Colección de archivos PDF suministrados por el usuario.
- **salida_csv**: (Opcional) Ruta de exportación de la agenda final.
- **auto_confirmar**: (Opcional, para entornos automatizados o CLI) Bandera para confirmar automáticamente si no hay ambigüedades.

## Pasos de Ejecución
1. **Invocación de la Extracción**:
   Invocar la skill `extraer-vencimiento` para cada uno de los archivos recibidos. Almacenar los registros extraídos y el mapa de evidencias textuales.
2. **Entrega de Registros para Revisión (Handoff)**:
   Cambiar el estado a `REVISION_REQUERIDA`. Poner a disposición del usuario la tabla de comprobantes con sus advertencias, campos faltantes y valores originales.
3. **Pausa y Espera Activa de Supervisión**:
   El agente detiene el avance automático a la espera de que el usuario:
   - Corrija valores incompletos o ambiguos (empresa, servicio, vencimiento, importe, moneda).
   - Marque como `excluido` aquellos archivos no computables o no deseados.
   - Accione la confirmación explícita.
4. **Reanudación y Validación de Integridad**:
   Al recibir la confirmación:
   - Si existen comprobantes no excluidos con campos obligatorios vacíos o montos no positivos, rechazar la confirmación, permanecer en `REVISION_REQUERIDA` e informar las faltas.
   - Si todos los comprobantes incluidos son válidos, registrar los archivos excluidos, cambiar el estado a `DATOS_CONFIRMADOS` y reanudar el flujo.
5. **Invocación del Ordenamiento**:
   Invocar la skill `ordenar-vencimientos` enviando exclusivamente los registros confirmados. Cambiar el estado a `ORDENAMIENTO_COMPLETADO`.
6. **Invocación de la Generación de Agenda**:
   Invocar la skill `generar-agenda` para formatear el archivo CSV en configuración regional argentina y calcular los totales desagregados por moneda.
7. **Retorno de Resultados y Estado Final**:
   Establecer el estado en `AGENDA_LISTA` y devolver el archivo CSV, los totales por moneda, la lista de archivos excluidos y el registro de auditoría.

## Referencias a Consultar
- [politica-orquestacion.md](file:///c:/Users/Asus/Documents/Diplomatura%20IA/venceclaro/skills/organizar-vencimientos/references/politica-orquestacion.md): Directivas de coordinación, handoff humano y segregación de responsabilidades.

## Ejecutable
- Bash: `scripts/ejecutar.sh <facturas.pdf...> [--salida agenda.csv] [--auto-confirmar] [--json]`
- Python: `python scripts/ejecutar.py <facturas.pdf...> [--salida agenda.csv] [--auto-confirmar] [--json]`

## Salida
Diccionario u objeto de resultado con:
- `estado`: Estado final del proceso (`AGENDA_LISTA`, `REVISION_REQUERIDA` o `ERROR`).
- `registros_ordenados`: Lista ordenada de comprobantes.
- `archivos_excluidos`: Nombres de facturas excluidas del reporte.
- `agenda_csv`: Contenido del CSV generado.
- `totales_por_moneda`: Subtotales agrupados por divisa.

## Manejo de Errores
- Si ocurre una falla en la lectura de un PDF, la skill aísla el error en el comprobante afectado sin detener el procesamiento del resto del lote.
- Si el usuario intenta confirmar sin facturas incluidas o con datos faltantes, se emite una lista descriptiva de errores sin avanzar hacia el ordenamiento.
