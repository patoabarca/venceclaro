from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List

from dotenv import load_dotenv

ruta_env = Path(__file__).resolve().parent / ".env"
if ruta_env.exists():
    load_dotenv(ruta_env)

import pandas as pd
import streamlit as st

# Configurar path del proyecto
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.models import (
    EstadoProceso,
    RegistroRevision,
    formatear_fecha_argentina,
    formatear_importe_argentino,
)
from core.parser_utils import parsear_fecha_argentina, parsear_importe_argentino
from core.skill_loader import obtener_skill
from core.skill_loader import obtener_orquestador
OrquestadorVencimientos = obtener_orquestador().OrquestadorVencimientos


# Configuración de página
st.set_page_config(
    page_title="VenceClaro - Organizador de Vencimientos con LLM",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Estilos CSS de buen contraste y diseño claro
st.markdown(
    """
    <style>
    .main-title {
        color: #0f172a;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #334155;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .badge-status {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    .badge-inicial { background-color: #e2e8f0; color: #1e293b; }
    .badge-revision { background-color: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }
    .badge-completado { background-color: #d1fae5; color: #065f46; border: 1px solid #10b981; }
    .badge-error { background-color: #fee2e2; color: #991b1b; border: 1px solid #ef4444; }
    .card-resumen {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .obs-tag {
        color: #b45309;
        font-size: 0.85rem;
        background-color: #fffbeb;
        padding: 2px 6px;
        border-radius: 4px;
        border: 1px solid #fde68a;
    }
    .llm-box {
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def inicializar_sesion():
    """Garantiza la persistencia de estado durante la interacción de Streamlit."""
    if "orquestador" not in st.session_state:
        st.session_state.orquestador = OrquestadorVencimientos()
    if "fase" not in st.session_state:
        st.session_state.fase = "ingesta"  # "ingesta", "revision", "agenda"
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    if "datos_edicion" not in st.session_state:
        st.session_state.datos_edicion = {}


def reiniciar_todo():
    st.session_state.orquestador.reiniciar()
    st.session_state.fase = "ingesta"
    st.session_state.datos_edicion.clear()
    st.session_state.uploader_key += 1


inicializar_sesion()
orquestador: OrquestadorVencimientos = st.session_state.orquestador


# Encabezado y Alcance
st.markdown('<div class="main-title">📅 VenceClaro</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Organizador de facturas y servicios con Agente LLM y 5 skills descubiertas dinámicamente.</div>',
    unsafe_allow_html=True,
)

# Indicador de modo LLM vs determinista
if orquestador.usar_llm and orquestador.cliente_llm:
    proveedor_txt = "Google Gemini" if orquestador.proveedor_llm == "gemini" else "Anthropic Claude"
    st.success(f"🤖 **Modo Agente con LLM Activo ({proveedor_txt})**: El orquestador usa Tool Calling para delegar en las skills.")
else:
    msg_err = orquestador.error_llm or "No se detectó `GEMINI_API_KEY` en `.env`. El orquestador ejecuta el flujo con guardas deterministas."
    st.info(f"⚡ **Modo Determinista Activo**: {msg_err}")

with st.expander("ℹ️ Acerca de la arquitectura de 5 skills de VenceClaro", expanded=False):
    st.markdown(
        """
        **VenceClaro** implementa la arquitectura solicitada por la cátedra:
        1. **`organizar-vencimientos` (Orquestadora)**: Dueña del agente y del flujo. Recibe las herramientas y coordina con LLM o modo determinista.
        2. **`extraer-vencimiento` (Especializada)**: Extrae datos estructurados desde PDFs seleccionables conservando evidencia textual.
        3. **`ordenar-vencimientos` (Especializada)**: Ordena cronológicamente por vencimiento ascendente con desempate estable.
        4. **`generar-agenda` (Especializada)**: Produce el CSV regional argentino (`;` y coma decimal) para Excel con monedas separadas.
        5. **`enviar-agenda` (Especializada)**: Despacha la agenda por Gmail SMTP (TLS 587) con autorización explícita o simulación educativa.

        > **Seguridad y Veracidad:**
        > - El LLM **nunca calcula ni modifica** importes, fechas ni monedas. Esas tareas son 100% deterministas.
        > - El texto de los documentos se trata como **datos puros, nunca como instrucciones** (protección anti prompt-injection).
        > - El destinatario del correo es suministrado por el usuario, nunca por el modelo.
        """
    )

st.divider()

# Sección 1: Carga e Ingesta de Facturas (Coordinada por el Orquestador)
st.subheader("1. Ingesta de Facturas (Lote de Comprobantes)")

archivos_subidos = st.file_uploader(
    "Seleccioná una o varias facturas de servicios en formato PDF:",
    type=["pdf"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}",
    help="Podés subir comprobantes de a uno o varios a la vez. El orquestador los irá sumando a la misma agenda.",
)

col_btn, col_reset = st.columns([2, 3])
with col_btn:
    boton_agregar = st.button("➕ Procesar y agregar a la agenda", type="primary", use_container_width=True)
with col_reset:
    if st.button("🔄 Reiniciar todo y empezar de cero"):
        reiniciar_todo()
        st.rerun()

# Procesar archivos subidos al presionar el botón
if boton_agregar:
    if not archivos_subidos:
        st.warning("Por favor, seleccioná al menos un archivo PDF antes de presionar el botón.")
    else:
        with st.spinner("Orquestador ejecutando extracción con las skills especializadas..."):
            lista_tuplas = [(f.name, f.getvalue()) for f in archivos_subidos]
            nuevos = orquestador.agregar_archivos(lista_tuplas)

            # Inicializar los datos editables en sesión para cada nuevo registro
            for reg in nuevos:
                if reg.id not in st.session_state.datos_edicion:
                    imp_str = formatear_importe_argentino(reg.importe) if reg.importe is not None else ""
                    st.session_state.datos_edicion[reg.id] = {
                        "empresa": reg.empresa,
                        "servicio": reg.servicio,
                        "importe_str": imp_str,
                        "importe": reg.importe,
                        "moneda": reg.moneda or "ARS",
                        "fecha_vencimiento": reg.fecha_vencimiento,
                        "excluido": reg.excluido,
                    }
            st.session_state.uploader_key += 1
        st.rerun()

# Si ya hay comprobantes en el orquestador
if orquestador.registros_revision:
    st.markdown("---")
    st.markdown(f"#### 📦 Facturas en el lote actual: **{len(orquestador.registros_revision)} comprobante(s)**")

    # Mostrar resumen del LLM si existe
    if orquestador.resumen_llm:
        st.markdown(
            f"""
            <div class="llm-box">
                <strong>📝 Resumen del Agente Orquestador:</strong><br>
                {orquestador.resumen_llm}
            </div>
            """,
            unsafe_allow_html=True,
        )

    filas_resumen = []
    for r in orquestador.registros_revision:
        vto_txt = r.fecha_vencimiento.strftime("%d/%m/%Y") if r.fecha_vencimiento else "⚠️ Sin fecha"
        imp_txt = f"{formatear_importe_argentino(r.importe)} {r.moneda}" if r.importe else "⚠️ Sin importe"
        filas_resumen.append({
            "Archivo": r.archivo_origen,
            "Empresa": r.empresa if r.empresa else "⚠️ Incompleto",
            "Servicio": r.servicio if r.servicio else "-",
            "Importe": imp_txt,
            "Vencimiento": vto_txt,
            "Estado": "⚠️ Requiere revisión" if not r.tiene_campos_obligatorios else "✅ Extraído",
        })
    st.dataframe(pd.DataFrame(filas_resumen), use_container_width=True, hide_index=True)

    # Pregunta explícita de coordinación del orquestador
    st.info(
        f"🤖 **Coordinación del Orquestador:** "
        f"Tenés **{len(orquestador.registros_revision)} comprobante(s)** listos para la agenda. "
        "¿Deseás seguir cargando más facturas o avanzar al control de revisión y confirmación?"
    )

    col_mas, col_avanzar = st.columns([1, 1])
    with col_mas:
        st.caption("👉 Podés seleccionar otro PDF arriba y pulsar '➕ Procesar y agregar a la agenda'.")
    with col_avanzar:
        if st.button("➡️ Proceder a Revisión y Confirmar Agenda", type="primary", use_container_width=True):
            st.session_state.fase = "revision"
            st.rerun()

# Estado visible del proceso
estado_actual = orquestador.estado
clase_badge = {
    EstadoProceso.INICIAL: "badge-inicial",
    EstadoProceso.EXTRAYENDO: "badge-revision",
    EstadoProceso.REVISION_REQUERIDA: "badge-revision",
    EstadoProceso.DATOS_CONFIRMADOS: "badge-completado",
    EstadoProceso.ORDENAMIENTO_COMPLETADO: "badge-completado",
    EstadoProceso.AGENDA_LISTA: "badge-completado",
    EstadoProceso.ERROR: "badge-error",
}.get(estado_actual, "badge-inicial")

texto_estado = {
    EstadoProceso.INICIAL: "Esperando comprobantes",
    EstadoProceso.EXTRAYENDO: "Extrayendo texto y evidencia...",
    EstadoProceso.REVISION_REQUERIDA: "Punto de Control: Revisión humana requerida",
    EstadoProceso.DATOS_CONFIRMADOS: "Datos confirmados por el usuario",
    EstadoProceso.ORDENAMIENTO_COMPLETADO: "Vencimientos ordenados cronológicamente",
    EstadoProceso.AGENDA_LISTA: "Agenda final generada con éxito",
    EstadoProceso.ERROR: "Error en el procesamiento",
}.get(estado_actual, str(estado_actual))

st.markdown(
    f'<div><strong>Estado del Orquestador:</strong> <span class="badge-status {clase_badge}">{texto_estado}</span></div>',
    unsafe_allow_html=True,
)

# Traza de auditoría del agente visible
if orquestador.traza:
    with st.expander("🕵️ Ver Traza de Decisiones del Agente (Tool Calls y Políticas)", expanded=False):
        for paso in orquestador.traza:
            razon_txt = f" | Razón: <em>{paso.razon_llm}</em>" if paso.razon_llm else ""
            st.markdown(
                f"- **Paso {paso.paso}:** Skill `[{paso.skill_invocada}]` {razon_txt}<br>"
                f"&nbsp;&nbsp;↳ <em>Resultado:</em> `{paso.resultado_resumen}`",
                unsafe_allow_html=True,
            )


# Sección 2: Tabla de Revisión (Human-in-the-Loop)
mostrar_revision = (
    (st.session_state.fase in ("revision", "agenda"))
    or (orquestador.estado in (EstadoProceso.DATOS_CONFIRMADOS, EstadoProceso.ORDENAMIENTO_COMPLETADO, EstadoProceso.AGENDA_LISTA))
) and bool(orquestador.registros_revision)

if mostrar_revision:
    st.divider()
    st.subheader("2. Tabla de Revisión y Supervisión de Comprobantes (Human-in-the-Loop)")
    st.write(
        "Verificá los valores extraídos por la skill. Corregí cualquier campo incompleto o marcá la casilla **Excluir** para dejar fuera un archivo problemático."
    )

    registros_editados: List[RegistroRevision] = []

    for idx, reg in enumerate(orquestador.registros_revision):
        datos_guardados = st.session_state.datos_edicion.get(reg.id, {})
        with st.container(border=True):
            col_head1, col_head2 = st.columns([3, 1])
            with col_head1:
                st.markdown(f"📄 **Archivo:** `{reg.archivo_origen}`")
            with col_head2:
                excluir = st.checkbox(
                    "Excluir comprobante",
                    value=datos_guardados.get("excluido", reg.excluido),
                    key=f"excluir_{reg.id}",
                )

            # Mostrar observaciones y alertas
            if reg.observaciones:
                for obs in reg.observaciones:
                    st.markdown(f"⚠️ <span class='obs-tag'>{obs}</span>", unsafe_allow_html=True)

            # Formulario de edición
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1.5, 1.2, 1.8])

            with c1:
                empresa_val = st.text_input(
                    "Empresa *",
                    value=datos_guardados.get("empresa", reg.empresa),
                    key=f"emp_{reg.id}",
                    disabled=excluir,
                )
            with c2:
                servicio_val = st.text_input(
                    "Servicio",
                    value=datos_guardados.get("servicio", reg.servicio),
                    key=f"serv_{reg.id}",
                    disabled=excluir,
                )
            with c3:
                imp_orig = formatear_importe_argentino(reg.importe) if reg.importe is not None else ""
                imp_val_str = st.text_input(
                    "Importe (ej: 25.000,50) *",
                    value=datos_guardados.get("importe_str", imp_orig),
                    key=f"imp_{reg.id}",
                    disabled=excluir,
                )
            with c4:
                moneda_opciones = ["ARS", "USD", "EUR", "OTRA"]
                moneda_actual = datos_guardados.get("moneda", reg.moneda or "ARS")
                idx_moneda = moneda_opciones.index(moneda_actual) if moneda_actual in moneda_opciones else 0
                moneda_val = st.selectbox(
                    "Moneda *",
                    options=moneda_opciones,
                    index=idx_moneda,
                    key=f"mon_{reg.id}",
                    disabled=excluir,
                )
            with c5:
                fecha_actual = datos_guardados.get("fecha_vencimiento") or reg.fecha_vencimiento
                fecha_val = st.date_input(
                    "Vencimiento *",
                    value=fecha_actual if fecha_actual else date.today(),
                    format="DD/MM/YYYY",
                    key=f"vto_{reg.id}",
                    disabled=excluir,
                )

            # Mostrar evidencia textual capturada por la skill
            with st.expander("🔎 Ver evidencia textual de respaldo extraída del PDF"):
                if reg.evidencia_texto:
                    for k, v in reg.evidencia_texto.items():
                        st.markdown(f"- **{k.capitalize()}:** `{v}`")
                else:
                    st.write("No se pudo extraer evidencia textual automática para este comprobante.")

                st.caption(
                    f"Valores originales extraídos: Empresa: '{reg.valores_originales.get('empresa')}' | "
                    f"Importe: '{formatear_importe_argentino(reg.valores_originales.get('importe'))}' | "
                    f"Vencimiento: '{formatear_fecha_argentina(reg.valores_originales.get('fecha_vencimiento'))}'"
                )

            # Parsear importe editado
            importe_dec = parsear_importe_argentino(imp_val_str)

            # Actualizar datos de edición en la sesión
            st.session_state.datos_edicion[reg.id] = {
                "empresa": empresa_val,
                "servicio": servicio_val,
                "importe_str": imp_val_str,
                "importe": importe_dec,
                "moneda": moneda_val,
                "fecha_vencimiento": fecha_val,
                "excluido": excluir,
            }

            reg_actualizado = RegistroRevision(
                id=reg.id,
                archivo_origen=reg.archivo_origen,
                empresa=empresa_val,
                servicio=servicio_val,
                importe=importe_dec,
                moneda=moneda_val,
                fecha_vencimiento=fecha_val,
                excluido=excluir,
                observaciones=reg.observaciones,
                valores_originales=reg.valores_originales,
                evidencia_texto=reg.evidencia_texto,
            )
            registros_editados.append(reg_actualizado)

    st.markdown("<br>", unsafe_allow_html=True)
    col_conf, _ = st.columns([2, 3])
    with col_conf:
        boton_confirmar = st.button(
            "✅ Confirmar datos y generar agenda definitiva",
            type="primary",
            use_container_width=True,
        )

    if boton_confirmar:
        valido, errores = orquestador.validar_y_confirmar(registros_editados)
        if not valido:
            st.error("No se pudo generar la agenda debido a los siguientes impedimentos obligatorios:")
            for e in errores:
                st.markdown(f"- ❌ {e}")
            st.warning("Corregí los datos faltantes o marcá 'Excluir comprobante' para continuar.")
        else:
            st.session_state.fase = "agenda"
            st.success("¡Datos confirmados! Flujo reanudado con ordenamiento y generación de agenda.")
            st.rerun()


# Sección 3: Agenda Consolidada Ordenada y Exportación
if orquestador.estado == EstadoProceso.AGENDA_LISTA and orquestador.registros_ordenados:
    st.divider()
    st.subheader("3. Agenda Consolidada de Vencimientos")

    if orquestador.archivos_excluidos:
        st.info(
            f"ℹ️ **Facturas excluidas del reporte final ({len(orquestador.archivos_excluidos)}):** "
            + ", ".join([f"`{a}`" for a in orquestador.archivos_excluidos])
        )

    # Preparar DataFrame para visualización
    filas = [r.a_fila_agenda() for r in orquestador.registros_ordenados]
    df_agenda = pd.DataFrame(filas)

    st.dataframe(
        df_agenda,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Vencimiento": st.column_config.TextColumn("Vencimiento (DD/MM/AAAA)"),
            "Importe": st.column_config.TextColumn("Importe"),
            "Moneda": st.column_config.TextColumn("Moneda"),
        },
    )

    # Resumen de totales por moneda (estrictamente separados)
    st.markdown("#### Resumen Financiero por Moneda")
    st.caption("Conforme a la política de la clase, las monedas se mantienen separadas sin mezclar importes.")
    cols_totales = st.columns(len(orquestador.totales_por_moneda) if orquestador.totales_por_moneda else 1)
    for col, (mon, tot) in zip(cols_totales, orquestador.totales_por_moneda.items()):
        with col:
            st.metric(
                label=f"Total a pagar en {mon}",
                value=f"{formatear_importe_argentino(tot)} {mon}",
            )

    # Descarga directa vía CSV generado por la skill
    skill_gen = obtener_skill("generar-agenda")
    res_gen = skill_gen.invocar({"registros": orquestador.registros_ordenados})
    csv_bytes = res_gen["csv_bytes"]

    st.download_button(
        label="📥 Descargar Agenda Consolidada en CSV (Configuración Regional Argentina para Excel)",
        data=csv_bytes,
        file_name="agenda_vencimientos.csv",
        mime="text/csv",
        type="primary",
    )

    # Sección de Despacho de Correo (Skill: enviar-agenda)
    st.divider()
    st.subheader("📧 Despacho por Correo Electrónico (Skill: enviar-agenda)")
    st.write(
        "Podés enviar la agenda consolidada directamente a tu casilla de correo o la de un colega. "
        "El email incluirá el resumen financiero desglosado en el cuerpo y el archivo CSV adjunto."
    )

    col_mail_dest, col_mail_btn = st.columns([3, 2])
    with col_mail_dest:
        email_dest = st.text_input(
            "Correo electrónico de destino:",
            value=st.session_state.get("email_destino_guardado", ""),
            placeholder="ejemplo@gmail.com",
            key="input_email_destino",
        )
    with col_mail_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        boton_enviar_email = st.button("🚀 Enviar por Gmail", type="primary", use_container_width=True)

    with st.expander("⚙️ Configuración de Credenciales de Gmail (Opcional si usás .env)", expanded=False):
        st.caption(
            "Si ya tenés un archivo `.env` en la raíz con `GMAIL_REMITENTE` y `GMAIL_APP_PASSWORD`, no necesitás completar nada aquí."
        )
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            remitente_ui = st.text_input(
                "Tu cuenta de Gmail (Remitente):",
                value=os.getenv("GMAIL_REMITENTE", ""),
                placeholder="tu_cuenta@gmail.com",
                key="remitente_ui",
            )
        with col_c2:
            pass_ui = st.text_input(
                "Contraseña de Aplicación de Google (16 caracteres):",
                value=os.getenv("GMAIL_APP_PASSWORD", ""),
                type="password",
                placeholder="abcd efgh ijkl mnop",
                help="Generala en tu cuenta de Google > Seguridad > Contraseñas de aplicaciones.",
                key="pass_ui",
            )
        usar_dry_run = st.checkbox(
            "Modo demostración / simulación (validar empaquetado sin conectar a internet)",
            value=False,
            key="check_dry_run",
        )

    if boton_enviar_email:
        if not email_dest:
            st.warning("Por favor, ingresá una dirección de correo de destino.")
        else:
            st.session_state["email_destino_guardado"] = email_dest
            with st.spinner("Orquestador despachando agenda vía skill 'enviar-agenda'..."):
                exito, msg, modo = orquestador.despachar_agenda_por_correo(
                    destinatario=email_dest,
                    remitente=remitente_ui if remitente_ui else None,
                    password=pass_ui if pass_ui else None,
                    dry_run=usar_dry_run,
                    autorizacion_usuario=True,
                )
            if exito:
                if modo == "SIMULACION":
                    st.info(msg)
                else:
                    st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

    st.markdown("<br>", unsafe_allow_html=True)
    c_mas, c_nueva = st.columns([1, 1])
    with c_mas:
        if st.button("➕ Sumar otra factura a esta misma agenda", use_container_width=True):
            st.session_state.fase = "ingesta"
            st.rerun()
    with c_nueva:
        if st.button("🔄 Comenzar una agenda nueva desde cero", use_container_width=True):
            reiniciar_todo()
            st.rerun()
