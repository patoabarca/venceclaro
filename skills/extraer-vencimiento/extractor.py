from __future__ import annotations

import io
import re
import uuid
from decimal import Decimal
from pathlib import Path
from typing import BinaryIO, List, Optional, Tuple, Union
import pypdf

from core.models import FacturaExtraida
from core.parser_utils import parsear_fecha_argentina, parsear_importe_argentino


SERVICIOS_CONOCIDOS = [
    (r"\b(electricidad|energ[ií]a el[eé]ctrica|luz)\b", "Electricidad"),
    (r"\b(gas natural|gas)\b", "Gas Natural"),
    (r"\b(agua potable|cloacas|agua y saneamiento|saneamiento)\b", "Agua y Saneamiento"),
    (r"\b(internet|banda ancha|fibra [oó]ptica)\b", "Internet"),
    (r"\b(telefon[ií]a celular|telefon[ií]a m[oó]vil|celular)\b", "Telefonía Móvil"),
    (r"\b(telefon[ií]a fija|telefon[ií]a)\b", "Telefonía Fija"),
    (r"\b(streaming|televisi[oó]n|cable|tv)\b", "Televisión por Cable"),
    (r"\b(servicios en la nube|cloud|hosting|servidor)\b", "Servicios en la Nube"),
]

EMPRESAS_CONOCIDAS = [
    "Edesur", "Edenor", "Metrogas", "Naturgy", "Camuzzi",
    "AySA", "Telecom", "Personal", "Claro", "Movistar",
    "Flow", "Telecentro", "iPlan", "Amazon Web Services", "Google Cloud"
]


def extraer_texto_pdf(fuente: Union[str, Path, BinaryIO, bytes]) -> str:
    """Extrae el contenido de texto de un archivo PDF usando pypdf."""
    stream: Union[Path, BinaryIO]
    if isinstance(fuente, (str, Path)):
        ruta = Path(fuente)
        if not ruta.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {ruta}")
        stream = ruta.open("rb")
    elif isinstance(fuente, bytes):
        stream = io.BytesIO(fuente)
    else:
        stream = fuente

    try:
        lector = pypdf.PdfReader(stream)
        textos = []
        for i, pagina in enumerate(lector.pages):
            texto_pag = pagina.extract_text() or ""
            textos.append(texto_pag)
        return "\n".join(textos)
    finally:
        if isinstance(fuente, (str, Path)) and 'stream' in locals() and hasattr(stream, 'close'):
            stream.close()


def extraer_datos_factura(
    fuente: Union[str, Path, BinaryIO, bytes],
    nombre_archivo: str,
    id_registro: Optional[str] = None
) -> FacturaExtraida:
    """
    Skill especializada: extraer-vencimiento.
    Extrae campos clave de la factura con evidencia textual sin inventar datos.
    """
    id_reg = id_registro or str(uuid.uuid4())[:8]
    evidencias = {}
    observaciones = []
    requiere_revision = False

    try:
        texto = extraer_texto_pdf(fuente)
    except Exception as e:
        return FacturaExtraida(
            id=id_reg,
            archivo_origen=nombre_archivo,
            requiere_revision=True,
            observaciones=[f"Error al abrir o leer el PDF: {str(e)}"],
            excluido=True,
        )

    # 1. Validación de texto utilizable (regla contra escaneados sin OCR)
    texto_limpio = texto.strip()
    if not texto_limpio or len(texto_limpio) < 20:
        return FacturaExtraida(
            id=id_reg,
            archivo_origen=nombre_archivo,
            requiere_revision=True,
            observaciones=[
                "El PDF no contiene texto seleccionable utilizable. "
                "Este MVP educativo no admite documentos escaneados sin capa de texto."
            ],
            excluido=False,
            texto_extraido_crudo=texto,
        )

    lineas = [l.strip() for l in texto.splitlines() if l.strip()]

    # 2. Extracción de Empresa Emisora
    empresa_detectada: Optional[str] = None
    for emp in EMPRESAS_CONOCIDAS:
        for l in lineas[:15]:  # Generalmente en el encabezado
            if re.search(rf"\b{re.escape(emp)}\b", l, re.IGNORECASE):
                empresa_detectada = emp
                evidencias["empresa"] = l
                break
        if empresa_detectada:
            break

    if not empresa_detectada:
        # Intento de búsqueda por etiqueta 'Razón Social' o 'Empresa:'
        match_emp = re.search(r"(?:empresa|raz[oó]n social|emisor)[\s:]+([A-Za-z0-9\s.]{3,35})", texto, re.IGNORECASE)
        if match_emp:
            empresa_detectada = match_emp.group(1).strip()
            evidencias["empresa"] = match_emp.group(0).strip()
        else:
            requiere_revision = True
            observaciones.append("No se pudo identificar la empresa emisora con certeza.")

    # 3. Extracción de Tipo de Servicio
    servicio_detectado: Optional[str] = None
    for patron, nombre_serv in SERVICIOS_CONOCIDOS:
        match_serv = re.search(patron, texto, re.IGNORECASE)
        if match_serv:
            servicio_detectado = nombre_serv
            evidencias["servicio"] = match_serv.group(0)
            break

    if not servicio_detectado:
        # Si la empresa es muy conocida, asociar servicio por defecto razonable o indicar general
        if empresa_detectada in ["Edesur", "Edenor"]:
            servicio_detectado = "Electricidad"
        elif empresa_detectada in ["Metrogas", "Naturgy", "Camuzzi"]:
            servicio_detectado = "Gas Natural"
        elif empresa_detectada in ["AySA"]:
            servicio_detectado = "Agua y Saneamiento"
        elif empresa_detectada in ["Telecom", "Personal", "Claro", "Movistar"]:
            servicio_detectado = "Telecomunicaciones"
        else:
            servicio_detectado = "Servicio General"
            observaciones.append("Tipo de servicio no especificado explícitamente en el texto.")

    # 4. Extracción de Fecha de Vencimiento
    # Regla: NO confundir con Fecha de Emisión
    # Buscar patrones explícitos de vencimiento
    vencimiento_detectado = None
    patron_vto = r"(?:vencimiento|vto\.?|primer vencimiento|1er vencimiento|fecha de vto\.?)[\s:]*([^\n\r]+)"
    matches_vto = list(re.finditer(patron_vto, texto, re.IGNORECASE))

    candidatos_vto = []
    for m in matches_vto:
        linea_vto = m.group(0)
        frag = m.group(1)
        f_parseada = parsear_fecha_argentina(frag)
        if f_parseada:
            candidatos_vto.append((f_parseada, linea_vto))

    if len(candidatos_vto) == 1:
        vencimiento_detectado = candidatos_vto[0][0]
        evidencias["fecha_vencimiento"] = candidatos_vto[0][1]
    elif len(candidatos_vto) > 1:
        # Múltiples vencimientos (ej. 1er y 2do vencimiento)
        # Tomar el primer vencimiento pero alertar para revisión
        vencimiento_detectado = candidatos_vto[0][0]
        evidencias["fecha_vencimiento"] = candidatos_vto[0][1]
        requiere_revision = True
        observaciones.append("Se detectaron múltiples fechas de vencimiento. Se preseleccionó el primer vencimiento.")
    else:
        # Verificar si solo hay fecha de emisión
        match_emision = re.search(r"(?:fecha de emisi[oó]n|emisi[oó]n)[\s:]*([^\n\r]+)", texto, re.IGNORECASE)
        if match_emision:
            evidencias["fecha_emision"] = match_emision.group(0)
            observaciones.append("Se encontró fecha de emisión pero NO fecha de vencimiento explícita.")
        else:
            observaciones.append("No se encontró fecha de vencimiento.")
        requiere_revision = True

    # 5. Extracción de Importe y Moneda
    # Regla: NO confundir con subtotal o IVA
    # Buscar "Total a pagar", "Importe total", "Total"
    importe_detectado: Optional[Decimal] = None
    candidatos_importe = []

    patron_total = r"(?:total a pagar|importe total|total factura|total a abonar|saldo a pagar|total)[\s:]*([$A-Za-z\s]*\s*[\d.,]+)"
    for m in re.finditer(patron_total, texto, re.IGNORECASE):
        linea_match = m.group(0)
        # Ignorar si es 'subtotal'
        if re.search(r"subtotal", linea_match, re.IGNORECASE):
            continue
        val_str = m.group(1)
        dec = parsear_importe_argentino(val_str)
        if dec is not None and dec > 0:
            candidatos_importe.append((dec, linea_match))

    if candidatos_importe:
        # Si hay varios, verificar si son idénticos o si difieren
        valores_unicos = set(c[0] for c in candidatos_importe)
        if len(valores_unicos) == 1:
            importe_detectado = candidatos_importe[0][0]
            evidencias["importe"] = candidatos_importe[0][1]
        else:
            # Tomar el mayor valor asociado a 'total a pagar' pero pedir revisión
            max_candidato = max(candidatos_importe, key=lambda x: x[0])
            importe_detectado = max_candidato[0]
            evidencias["importe"] = max_candidato[1]
            requiere_revision = True
            observaciones.append("Se encontraron varios importes etiquetados como total; requiere confirmación.")
    else:
        # Verificar si solo hay subtotal
        match_sub = re.search(r"subtotal[\s:]*([$A-Za-z\s]*\s*[\d.,]+)", texto, re.IGNORECASE)
        if match_sub:
            evidencias["subtotal"] = match_sub.group(0)
            observaciones.append("Se detectó solo un subtotal; no se halló total a pagar definitivo.")
        else:
            observaciones.append("No se pudo detectar el importe total.")
        requiere_revision = True

    # 6. Detección de Moneda
    # Regla: "Si la moneda no está identificada, pedir confirmación; no asumir que $ identifica inequívocamente una moneda."
    moneda_detectada: Optional[str] = None
    if re.search(r"\b(USD|U\$S|D[ÓO]LARES|DOLAR|US\$)\b", texto, re.IGNORECASE):
        moneda_detectada = "USD"
        evidencias["moneda"] = "USD detectado explícitamente"
    elif re.search(r"\b(ARS|PESOS|PESOS ARGENTINOS)\b", texto, re.IGNORECASE):
        moneda_detectada = "ARS"
        evidencias["moneda"] = "ARS detectado explícitamente"
    elif "$" in texto:
        # Solo aparece el símbolo $: pedir confirmación explícita
        moneda_detectada = "ARS"  # Sugerencia inicial
        requiere_revision = True
        observaciones.append("Moneda expresada con '$': confirmar si corresponde a ARS o USD.")
        evidencias["moneda"] = "Símbolo '$' detectado en el documento"
    else:
        moneda_detectada = None
        requiere_revision = True
        observaciones.append("Moneda no identificada en el documento.")

    # Marcar si faltan campos obligatorios
    if not empresa_detectada or not vencimiento_detectado or importe_detectado is None or not moneda_detectada:
        requiere_revision = True

    return FacturaExtraida(
        id=id_reg,
        archivo_origen=nombre_archivo,
        empresa=empresa_detectada,
        servicio=servicio_detectado,
        importe=importe_detectado,
        moneda=moneda_detectada,
        fecha_vencimiento=vencimiento_detectado,
        evidencia_texto=evidencias,
        requiere_revision=requiere_revision,
        observaciones=observaciones,
        excluido=False,
        texto_extraido_crudo=texto,
    )

ESQUEMA_ENTRADA = {
    "type": "object",
    "properties": {
        "archivo": {
            "type": "string",
            "description": "Nombre del archivo de factura en PDF a procesar.",
        },
    },
    "required": ["archivo"],
}


def invocar(entrada: Dict[str, Any]) -> Dict[str, Any]:
    """
    Contrato estándar de la skill: invocar(entrada: dict) -> dict.
    Envuelve extraer_datos_factura sin alterar la lógica de negocio.
    """
    archivo = entrada.get("archivo")
    if not archivo:
        raise ValueError("El parámetro 'archivo' es obligatorio en la entrada de extraer-vencimiento.")

    contenido = entrada.get("contenido_bytes")
    nombre_archivo = Path(archivo).name
    fuente = contenido if contenido is not None else Path(archivo)

    registro_extraido = extraer_datos_factura(fuente, nombre_archivo)
    return {
        "registro": registro_extraido.a_diccionario(),
        "objeto": registro_extraido,
    }
