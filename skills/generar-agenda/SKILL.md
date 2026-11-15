---
name: generar-agenda
description: Genera un archivo CSV estructurado con la agenda de vencimientos ordenada, aplicando formato regional argentino (separador punto y coma, coma decimal, codificación UTF-8 con BOM para Excel) y segregación estricta de monedas. Usar como paso final de exportación tras la confirmación y ordenamiento.
---

# Procedimiento de la Skill: generar-agenda

## Objetivo
Exportar la lista ordenada de comprobantes confirmados a un archivo CSV estructurado, garantizando compatibilidad inmediata con Microsoft Excel en configuración regional argentina y preservando la separación entre monedas.

## Entradas (`invocar(entrada: dict) -> dict`)
- **registros**: Lista de registros ordenados de tipo `FacturaConfirmada` o dicts equivalentes.
- **ruta_destino**: (Opcional) Ruta de guardado en disco para el archivo `.csv`.

## Pasos de Ejecución
1. **Configuración del formato regional**:
   Configurar el delimitador de campos en punto y coma (`;`), el salto de línea en CRLF (`\r\n`) y la codificación en `utf-8-sig` (BOM inicial).
2. **Generación de encabezados**:
   Escribir las columnas visibles reglamentarias:
   `Vencimiento;Empresa;Servicio;Importe;Moneda;Archivo de origen`.
3. **Escritura de filas con formato estricto**:
   - Fecha de vencimiento: `DD/MM/AAAA`.
   - Importe: formato numérico argentino (ej. `25.000,50`).
   - Moneda: código correspondiente (`ARS`, `USD`).
   - Empresa, servicio y nombre del archivo de origen sin truncar.
4. **Cálculo de subtotales segregados**:
   Calcular el total acumulado por cada moneda por separado. Bajo ninguna circunstancia calcular un importe consolidado que mezcle monedas.
5. **Emisión de la salida**:
   Retornar la cadena de texto CSV o escribir los bytes con codificación UTF-8-SIG en el destino indicado.

## Referencias a Consultar
- [politica-agenda.md](references/politica-agenda.md): Formato de columnas, directivas de codificación para Excel y prohibición de mezcla de monedas.

## Ejecutable
- Python: `python scripts/ejecutar.py <registros_ordenados.json> [--salida <agenda.csv>]`

## Salida de `invocar`
Diccionario con:
- `csv`: Texto plano del CSV generado.
- `csv_bytes`: Bytes codificados en `utf-8-sig` con BOM.
- `totales_por_moneda`: Diccionario con subtotales float por moneda.
- `totales_decimal`: Diccionario con subtotales Decimal por moneda.

## Manejo de Errores
- Si la lista de entrada está vacía, genera un CSV con únicamente los encabezados reglamentarios.
- Si algún registro presenta un importe no numérico, la skill interrumpe el proceso para proteger la consistencia financiera.
