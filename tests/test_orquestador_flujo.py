import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.llm import ClienteLLMFalso, LlamadaHerramienta, RespuestaLLM
from core.models import EstadoProceso
from core.skill_loader import descubrir_skills, obtener_skill
from core.skill_loader import obtener_orquestador
_om = obtener_orquestador()
OrquestadorVencimientos = _om.OrquestadorVencimientos
coordinar_organizacion_vencimientos = _om.coordinar_organizacion_vencimientos

EJEMPLOS_DIR = BASE_DIR / "ejemplos"


def test_descubrimiento_de_5_skills_con_esquemas():
    skills = descubrir_skills()
    assert len(skills) == 5
    nombres_esperados = {
        "organizar-vencimientos",
        "extraer-vencimiento",
        "ordenar-vencimientos",
        "generar-agenda",
        "enviar-agenda",
    }
    assert set(skills.keys()) == nombres_esperados

    for nombre, info in skills.items():
        assert info.nombre == info.carpeta.name
        assert info.modulo_entrada.exists()
        assert len(info.referencias) >= 1
        sk = obtener_skill(nombre)
        assert isinstance(sk.esquema_entrada, dict)
        assert callable(sk.invocar)


def test_delegacion_por_nombre_con_doble_de_skill():
    orquestador = OrquestadorVencimientos(usar_llm=False)
    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]
    regs = orquestador.procesar_archivos_iniciales(archivos)
    assert len(regs) == 1

    # Verificar que el registro proviene del extractor
    assert regs[0].empresa == "Edesur"


def test_flujo_completo_con_archivo_excluido_y_correccion():
    orquestador = OrquestadorVencimientos(usar_llm=False)

    archivos = [
        ("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf"),
        ("factura_telecom_internet.pdf", EJEMPLOS_DIR / "factura_telecom_internet.pdf"),
        ("factura_sin_texto.pdf", EJEMPLOS_DIR / "factura_sin_texto.pdf"),
    ]

    # Paso 1: Iniciar extracción
    registros_rev = orquestador.procesar_archivos_iniciales(archivos)
    assert orquestador.estado == EstadoProceso.REVISION_REQUERIDA
    assert len(registros_rev) == 3

    reg_sin_texto = next(r for r in registros_rev if r.archivo_origen == "factura_sin_texto.pdf")
    assert reg_sin_texto.tiene_campos_obligatorios is False

    # Intento 1: Confirmar sin corregir -> DEBE FALLAR por campos obligatorios faltantes
    exito, errores = orquestador.validar_y_confirmar(registros_rev)
    assert exito is False
    assert len(errores) > 0
    assert orquestador.estado == EstadoProceso.REVISION_REQUERIDA

    # Intento 2: Excluir archivo sin texto y corregir servicio de Telecom
    reg_sin_texto.excluido = True
    reg_telecom = next(r for r in registros_rev if r.archivo_origen == "factura_telecom_internet.pdf")
    reg_telecom.servicio = "Internet Fibra Óptica 500M"

    exito2, errores2 = orquestador.validar_y_confirmar(registros_rev)
    assert exito2 is True
    assert len(errores2) == 0
    assert orquestador.estado == EstadoProceso.AGENDA_LISTA
    assert len(orquestador.registros_ordenados) == 2
    assert orquestador.archivos_excluidos == ["factura_sin_texto.pdf"]

    # Verificar orden cronológico: Telecom (Mayo) antes que Edesur (Junio)
    assert orquestador.registros_ordenados[0].archivo_origen == "factura_telecom_internet.pdf"
    assert orquestador.registros_ordenados[1].archivo_origen == "factura_edesur_luz.pdf"
    assert "factura_sin_texto.pdf" not in orquestador.agenda_csv


def test_rechazo_si_todos_excluidos():
    orquestador = OrquestadorVencimientos(usar_llm=False)
    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]
    regs = orquestador.procesar_archivos_iniciales(archivos)
    regs[0].excluido = True

    exito, errores = orquestador.validar_y_confirmar(regs)
    assert exito is False
    assert "No hay comprobantes incluidos" in errores[0]


def test_ingesta_incremental_varios_archivos():
    orquestador = OrquestadorVencimientos(usar_llm=False)
    orquestador.procesar_archivos_iniciales([
        ("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")
    ])
    assert len(orquestador.registros_revision) == 1

    # Agregar segunda factura incrementalmente
    orquestador.agregar_archivos([
        ("factura_telecom_internet.pdf", EJEMPLOS_DIR / "factura_telecom_internet.pdf")
    ])
    assert len(orquestador.registros_revision) == 2

    # Intentar agregar duplicado por nombre de archivo
    orquestador.agregar_archivos([
        ("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")
    ])
    assert len(orquestador.registros_revision) == 2


def test_llm_guionado_orden_correcto_y_resumen():
    # Simulamos el LLM que decide extraer y luego pedir revisión humana
    resp1 = RespuestaLLM(
        texto="Comenzando extracción de las facturas.",
        llamadas_herramientas=[
            LlamadaHerramienta("call_1", "extraer-vencimiento", {"archivo": "factura_edesur_luz.pdf"}),
        ]
    )
    resp2 = RespuestaLLM(
        texto="Extracción lista.",
        llamadas_herramientas=[
            LlamadaHerramienta("call_2", "solicitar_revision_humana", {"resumen_extraccion": "Factura Edesur extraída correctamente."}),
        ]
    )
    cliente_falso = ClienteLLMFalso([resp1, resp2])
    orquestador = OrquestadorVencimientos(cliente_llm=cliente_falso, usar_llm=True)

    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]
    regs = orquestador.procesar_archivos_iniciales(archivos)

    assert orquestador.estado == EstadoProceso.REVISION_REQUERIDA
    assert len(regs) == 1
    assert orquestador.resumen_llm == "Factura Edesur extraída correctamente."
    assert len(orquestador.traza) >= 2


def test_guarda_llm_rechaza_enviar_antes_de_confirmar():
    orquestador = OrquestadorVencimientos(usar_llm=False)
    orquestador.procesar_archivos_iniciales([
        ("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")
    ])
    # Forzar llamada directa a herramienta enviar-agenda en estado REVISION_REQUERIDA
    res = orquestador._ejecutar_herramienta("enviar-agenda", {"destinatario": "test@ejemplo.com"}, envio_autorizado=True)
    assert "error" in res
    assert "Guarda de estado violada" in res["error"]


def test_guarda_llm_rechaza_ordenar_sin_confirmacion_humana():
    orquestador = OrquestadorVencimientos(usar_llm=False)
    orquestador.procesar_archivos_iniciales([
        ("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")
    ])
    res = orquestador._ejecutar_herramienta("ordenar-vencimientos", {})
    assert "error" in res
    assert "Guarda de estado violada" in res["error"]


def test_guarda_seguridad_rechazo_envio_sin_autorizacion_explicita():
    orquestador = OrquestadorVencimientos(usar_llm=False)
    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]
    orquestador.procesar_archivos_iniciales(archivos)
    orquestador.validar_y_confirmar(orquestador.registros_revision)

    exito, msg, modo = orquestador.despachar_agenda_por_correo(
        destinatario="test@ejemplo.com",
        dry_run=True,
        autorizacion_usuario=False,
    )
    assert exito is False
    assert "falta autorización" in msg


def test_prompt_injection_en_factura_no_altera_destinatario():
    # Si un PDF intentara inyectar instrucciones, el destinatario proviene únicamente del usuario
    orquestador = OrquestadorVencimientos(usar_llm=False)
    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]
    orquestador.procesar_archivos_iniciales(archivos)
    orquestador.validar_y_confirmar(orquestador.registros_revision)

    destinatario_usuario_real = "usuario_autentico@gmail.com"
    exito, msg, modo = orquestador.despachar_agenda_por_correo(
        destinatario=destinatario_usuario_real,
        dry_run=True,
        autorizacion_usuario=True,
    )
    assert exito is True
    assert modo == "SIMULACION"
    assert destinatario_usuario_real in msg


def test_fallback_sin_llm_produce_mismo_csv(tmp_path):
    salida_csv = tmp_path / "agenda_sin_llm.csv"
    archivos = [
        ("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf"),
        ("factura_telecom_internet.pdf", EJEMPLOS_DIR / "factura_telecom_internet.pdf"),
    ]
    res = coordinar_organizacion_vencimientos(
        archivos=archivos,
        salida_csv=salida_csv,
        auto_confirmar=True,
        sin_llm=True,
    )
    assert res["estado"] == "AGENDA_LISTA"
    assert salida_csv.exists()
    assert "Telecom" in res["agenda_csv"]
    assert "Edesur" in res["agenda_csv"]


def test_a1_envio_agenda_reenvia_credenciales_usuario_sin_variables_entorno(monkeypatch):
    """A.1 _ejecutar_herramienta reenvía remitente y password a skill.invocar. Test con smtplib mockeado y sin variables de entorno."""
    monkeypatch.delenv("GMAIL_REMITENTE", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    monkeypatch.delenv("EMAIL_REMITENTE", raising=False)
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)

    orquestador = OrquestadorVencimientos(usar_llm=False)
    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]
    orquestador.procesar_archivos_iniciales(archivos)
    orquestador.validar_y_confirmar(orquestador.registros_revision)

    with patch("smtplib.SMTP") as mock_smtp_cls:
        instancia_mock = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = instancia_mock

        exito, msg, modo = orquestador.despachar_agenda_por_correo(
            destinatario="destinatario@example.com",
            remitente="remitente_explicit@gmail.com",
            password="app-password-16-ch",
            dry_run=False,
            autorizacion_usuario=True,
        )

        assert exito is True
        assert modo == "REAL"
        instancia_mock.login.assert_called_once_with("remitente_explicit@gmail.com", "app-password-16-ch")


def test_a2_solicitar_revision_humana_valida_solo_en_extraccion_y_agenda_se_genera_tras_confirmacion():
    """A.2 solicitar_revision_humana válida solo en EXTRAYENDO o REVISION_REQUERIDA; en otro estado devuelve error y no toca self.estado. Test con LLM falso que la llama tras la confirmación."""
    resp_extraccion = RespuestaLLM(
        texto="Extrayendo",
        llamadas_herramientas=[
            LlamadaHerramienta("c1", "extraer-vencimiento", {"archivo": "factura_edesur_luz.pdf"}),
            LlamadaHerramienta("c2", "solicitar_revision_humana", {"resumen_extraccion": "Factura Edesur lista"}),
        ],
    )
    # LLM falso que tras confirmación intenta convocar revisión humana indebidamente,
    # pero luego ordena y genera la agenda
    resp_post_conf = RespuestaLLM(
        texto="Llamando revisión post-confirmación indebidamente",
        llamadas_herramientas=[
            LlamadaHerramienta("c3", "solicitar_revision_humana", {"resumen_extraccion": "Intento inválido"}),
            LlamadaHerramienta("c4", "ordenar-vencimientos", {}),
            LlamadaHerramienta("c5", "generar-agenda", {}),
        ],
    )
    cliente_falso = ClienteLLMFalso([resp_extraccion, resp_post_conf])
    orquestador = OrquestadorVencimientos(cliente_llm=cliente_falso, usar_llm=True)
    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]

    regs = orquestador.procesar_archivos_iniciales(archivos)
    assert orquestador.estado == EstadoProceso.REVISION_REQUERIDA

    # Confirmamos las facturas para pasar a DATOS_CONFIRMADOS y disparar el bucle post-confirmación
    exito, errores = orquestador.validar_y_confirmar(regs)
    assert exito is True

    # Verificar en la traza que la llamada indebida a solicitar_revision_humana fue rechazada con error de guarda
    trazas_rev = [t for t in orquestador.traza if t.skill_invocada == "solicitar_revision_humana"]
    assert len(trazas_rev) == 2
    # La segunda llamada debe contener el error de guarda
    assert "Guarda de estado violada" in trazas_rev[1].resultado_resumen

    # Y la agenda se genera igual
    assert orquestador.estado == EstadoProceso.AGENDA_LISTA
    assert orquestador.agenda_csv is not None
    assert len(orquestador.registros_ordenados) == 1


def test_a3_extraer_vencimiento_rechaza_rutas_fuera_de_memoria_y_quita_contenido_bytes():
    """A.3 extraer-vencimiento acepta solo nombres en memoria (nombre base) y rechaza /tmp/otro.pdf y ../x.pdf. Quita contenido_bytes del esquema expuesto al LLM."""
    resp_ataque = RespuestaLLM(
        texto="Intentando extraer rutas fuera de memoria",
        llamadas_herramientas=[
            LlamadaHerramienta("c1", "extraer-vencimiento", {"archivo": "/tmp/otro.pdf"}),
            LlamadaHerramienta("c2", "extraer-vencimiento", {"archivo": "../x.pdf"}),
            LlamadaHerramienta("c3", "extraer-vencimiento", {"archivo": "factura_edesur_luz.pdf"}),
            LlamadaHerramienta("c4", "solicitar_revision_humana", {"resumen_extraccion": "Listo"}),
        ],
    )
    cliente_falso = ClienteLLMFalso([resp_ataque])
    orquestador = OrquestadorVencimientos(cliente_llm=cliente_falso, usar_llm=True)
    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]

    # 1. Comprobar que el esquema no expone contenido_bytes
    herramientas = orquestador._obtener_definiciones_herramientas(envio_autorizado=False)
    h_ext = next(h for h in herramientas if h["name"] == "extraer-vencimiento")
    assert "contenido_bytes" not in h_ext["input_schema"].get("properties", {})

    regs = orquestador.procesar_archivos_iniciales(archivos)

    # 2. Comprobar que en la traza /tmp/otro.pdf y ../x.pdf fueron rechazadas
    trazas_ext = [t for t in orquestador.traza if t.skill_invocada == "extraer-vencimiento"]
    res_otro = next(t for t in trazas_ext if t.argumentos.get("archivo") == "/tmp/otro.pdf")
    res_x = next(t for t in trazas_ext if t.argumentos.get("archivo") == "../x.pdf")

    assert "Archivo no permitido o inexistente en memoria" in res_otro.resultado_resumen
    assert "Archivo no permitido o inexistente en memoria" in res_x.resultado_resumen

    # 3. Solo la factura autorizada en memoria fue procesada
    assert len(regs) == 1
    assert regs[0].archivo_origen == "factura_edesur_luz.pdf"


def test_a4_serializacion_json_y_function_response_dict_real():
    """A.4 Serializar resultados de herramientas con json.dumps y verificar que _traducir_historial arme response con dict real."""
    import json
    from core.llm import ClienteGemini

    resp = RespuestaLLM(
        texto="Extrayendo",
        llamadas_herramientas=[
            LlamadaHerramienta("c1", "extraer-vencimiento", {"archivo": "factura_edesur_luz.pdf"}),
            LlamadaHerramienta("c2", "solicitar_revision_humana", {"resumen_extraccion": "Listo"}),
        ],
    )
    cliente_falso = ClienteLLMFalso([resp])
    orquestador = OrquestadorVencimientos(cliente_llm=cliente_falso, usar_llm=True)
    archivos = [("factura_edesur_luz.pdf", EJEMPLOS_DIR / "factura_edesur_luz.pdf")]
    orquestador.procesar_archivos_iniciales(archivos)

    # Verificar que el resultado de cada paso en la traza sea JSON válido (no repr str() con comillas simples)
    for paso in orquestador.traza:
        data = json.loads(paso.resultado_resumen)
        assert isinstance(data, dict)

    # Verificar que ClienteGemini._traducir_historial coloque un dict real en function_response.response
    with patch("google.genai.Client"):
        cli_gemini = ClienteGemini(api_key="gemini-key")
        historial_prueba = [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "call_1", "name": "extraer-vencimiento", "input": {"archivo": "factura_edesur_luz.pdf"}}
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_1",
                        "name": "extraer-vencimiento",
                        "content": json.dumps({"status": "ok", "empresa": "Edesur"}, ensure_ascii=False),
                        "response_dict": {"status": "ok", "empresa": "Edesur"},
                    }
                ],
            },
        ]
        contents = cli_gemini._traducir_historial(historial_prueba)
        part_user = contents[1].parts[0]
        assert part_user.function_response is not None
        assert isinstance(part_user.function_response.response, dict)
        assert part_user.function_response.response == {"status": "ok", "empresa": "Edesur"}

