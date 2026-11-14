# Política de Generación de Agenda y Exportación

## 1. Columnas Visibles Estándar
El archivo CSV generado debe contener exclusivamente las siguientes columnas en orden:
1. `Vencimiento`: Formato visual argentino `DD/MM/AAAA`.
2. `Empresa`: Razón social o prestataria.
3. `Servicio`: Tipo de servicio prestado.
4. `Importe`: Formato numérico argentino con punto de miles y coma decimal (ej. `25.000,50`).
5. `Moneda`: Identificador de moneda (`ARS`, `USD`).
6. `Archivo de origen`: Nombre del archivo PDF original.

## 2. Compatibilidad Regional Argentina con Microsoft Excel
- **Delimitador de campos**: Punto y coma (`;`). En entornos hispanohablantes donde la coma es el separador decimal, Excel requiere punto y coma como delimitador de columnas.
- **Codificación**: `UTF-8 con BOM` (`utf-8-sig`). Esta marca inicial previene la corrupción de caracteres con acentos, tildes, diéresis o `ñ` al abrir el archivo directamente con doble clic en Windows.
- **Salto de línea**: CRLF (`\r\n`).

## 3. Segregación Estricta de Monedas
- Está terminantemente prohibido consolidar o sumarizar importes en un único total general cuando existan diferentes monedas.
- Si una agenda contiene facturas en Pesos Argentinos (ARS) y en Dólares (USD), los resúmenes financieros deben mantenerse desagregados por moneda.
