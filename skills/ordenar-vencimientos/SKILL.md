---
name: ordenar-vencimientos
description: Ordena cronológicamente registros confirmados de facturas por fecha de vencimiento ascendente con desempate determinista por empresa y archivo de origen. Usar cuando los datos ya hayan sido validados por el usuario y se requiera estructurar la secuencia temporal de pagos.
---

# Procedimiento de la Skill: ordenar-vencimientos

## Objetivo
Tomar una lista de registros de facturas debidamente validados y ordenarlos cronológicamente por fecha de vencimiento ascendente de manera estable y determinista, sin alterar datos ni completar campos omitidos.

## Entradas (`invocar(entrada: dict) -> dict`)
- **registros**: Lista de objetos `FacturaConfirmada`, `RegistroRevision` o diccionarios con campos validados (`fecha_vencimiento`, `empresa`, `archivo_origen`).

## Pasos de Ejecución
1. **Validación de integridad**:
   Comprobar que cada registro posea una fecha de vencimiento válida (formato `date` o cadena ISO `AAAA-MM-DD`). Si alguno carece de fecha, detener la ejecución emitiendo un error.
2. **Definición de clave de ordenamiento compuesta**:
   Para cada registro se establece la tupla de orden:
   `(fecha_vencimiento, empresa.lower(), archivo_origen.lower())`.
3. **Ordenamiento determinista**:
   Ordenar la colección de forma ascendente. El criterio primario es la fecha; los criterios secundarios desempatan de forma predecible sin depender del orden de inserción inicial.
4. **Preservación de inmutabilidad**:
   Generar una nueva lista ordenada sin mutar los atributos de los objetos originales ni recalcular importes.

## Referencias a Consultar
- [politica-ordenamiento.md](references/politica-ordenamiento.md): Criterios de desempate, soporte multianual y garantía de no modificación de datos.

## Ejecutable
- Bash: `scripts/ejecutar.sh <registros_confirmados.json> [--json]`
- Python: `python scripts/ejecutar.py <registros_confirmados.json> [--json]`

## Salida de `invocar`
Diccionario con:
- `registros`: Lista de diccionarios ordenados.
- `objetos`: Lista de objetos `FacturaConfirmada` ordenados.

## Manejo de Errores
- **Registro con fecha nula**: La ejecución se interrumpe y se informa la excepción correspondiente para evitar agendas con fechas indefinidas.
- **Formato de entrada inválido**: El script CLI reporta un error estructurado por `stderr` y finaliza con código de salida 1.
