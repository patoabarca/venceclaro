# Política de Generación de Agenda y Exportación

## 1. Columnas Visibles Estándar
- El archivo CSV generado debe contener exclusivamente las siguientes columnas exactas y en orden: `Vencimiento`, `Empresa`, `Servicio`, `Importe`, `Moneda`, `Archivo de origen`. [AGE-1]
- Fecha en formato visual argentino `DD/MM/AAAA` e importe con formato numérico argentino de punto de miles y coma decimal (ej. `25.000,50`). [AGE-2]

## 2. Compatibilidad Regional Argentina con Microsoft Excel
- **Delimitador de campos**: Punto y coma (`;`). [AGE-3]
- **Codificación**: `UTF-8 con BOM` (`utf-8-sig`), cuyos bytes inician con `EF BB BF` preservando tildes y caracteres `ñ`. [AGE-4]
- **Salto de línea**: CRLF (`\r\n`). [AGE-5]

## 3. Segregación Estricta de Monedas
- Si una agenda contiene facturas en Pesos Argentinos (ARS) y en Dólares (USD), los resúmenes financieros deben mantenerse desagregados por moneda, sin existir nunca un total consolidado o mezclado. [AGE-6]
