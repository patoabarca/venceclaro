# Política de Ordenamiento de Vencimientos

## 1. Criterio Principal Temporal
- Los registros confirmados deben ordenarse estrictamente de forma cronológica ascendente por fecha de vencimiento (`AAAA-MM-DD`), contemplando la transición entre diferentes meses y cambios de año calendario. [ORD-1]

## 2. Criterios de Desempate Estables
- En caso de empate en fecha de vencimiento, se desempata alfabéticamente por empresa (insensible a mayúsculas/minúsculas) y luego por nombre de archivo de origen, garantizando un resultado determinista e independiente del orden de entrada. [ORD-2]

## 3. Principio de Inmutabilidad
- Esta skill no debe modificar importes, ni inferir monedas, ni completar campos omitidos, ni mutar la lista de entrada; únicamente organiza la secuencia de registros validados. [ORD-3]

## 4. Requisitos Previos de Entrada
- Todo registro ingresado a esta etapa debe contar obligatoriamente con una fecha de vencimiento válida; si un registro contiene una fecha nula, la skill debe abortar la operación con un error explícito. [ORD-4]
