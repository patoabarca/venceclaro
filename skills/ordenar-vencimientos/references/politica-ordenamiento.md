# Política de Ordenamiento de Vencimientos

## 1. Criterio Principal Temporal
- Los registros confirmados deben ordenarse estrictamente de forma cronológica ascendente por fecha de vencimiento (`AAAA-MM-DD`).
- Las facturas más próximas a vencer deben encabezar la agenda.
- El ordenamiento debe contemplar correctamente la transición entre diferentes meses y cambios de año calendario.

## 2. Criterios de Desempate Estables
- En caso de que dos o más facturas coincidan exactamente en la misma fecha de vencimiento:
  1. Se ordenan alfabéticamente por el nombre de la empresa emisora (insensible a mayúsculas/minúsculas).
  2. Si persiste el empate en fecha y empresa, se ordenan alfabéticamente por el nombre del archivo de origen.
- Esto garantiza un ordenamiento determinista y reproducible en cualquier entorno.

## 3. Principio de Inmutabilidad
- Esta skill no debe modificar importes, ni inferir monedas, ni completar campos omitidos, ni interpretar texto de documentos.
- Únicamente organiza la secuencia de registros validados.

## 4. Requisitos Previos de Entrada
- Todo registro ingresado a esta etapa debe contar obligatoriamente con una fecha de vencimiento válida.
- Si un registro contiene una fecha nula, la skill debe abortar la operación con un error explícito.
