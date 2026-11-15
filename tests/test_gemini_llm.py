from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.llm import ClienteGemini, LlamadaHerramienta, RespuestaLLM
from core.skill_loader import descubrir_skills, obtener_skill, obtener_orquestador
_om = obtener_orquestador()
OrquestadorVencimientos = _om.OrquestadorVencimientos
coordinar_organizacion_vencimientos = _om.coordinar_organizacion_vencimientos


def test_5a_traducir_herramientas_arma_function_declarations_de_todas_las_skills():
    """5(a) _traducir_herramientas arma las function_declarations de todas las skills expuestas."""
    skills = descubrir_skills()
    orquestador = OrquestadorVencimientos(usar_llm=False)
    # Obtener herramientas con envío autorizado para incluir las 5 skills + solicitar_revision_humana
    herramientas = orquestador._obtener_definiciones_herramientas(envio_autorizado=True)

    with patch("google.genai.Client"):
        cliente = ClienteGemini(api_key="gemini-test-key")
        tools_gemini = cliente._traducir_herramientas(herramientas)

    assert len(tools_gemini) == 1
    tool = tools_gemini[0]
    nombres_declarados = [fd.name for fd in tool.function_declarations]

    assert "extraer-vencimiento" in nombres_declarados
    assert "ordenar-vencimientos" in nombres_declarados
    assert "generar-agenda" in nombres_declarados
    assert "enviar-agenda" in nombres_declarados
    assert "solicitar_revision_humana" in nombres_declarados

    for fd in tool.function_declarations:
        assert fd.description
        assert fd.parameters is not None
        # Verificar que no quedaron campos incompatibles con OpenAPI de Gemini
        assert "additionalProperties" not in fd.parameters
        assert "$schema" not in fd.parameters


def test_5b_traducir_historial_convierte_tool_use_y_tool_result():
    """5(b) _traducir_historial convierte tool_use y tool_result en function_call y function_response."""
    mensajes = [
        {"role": "user", "content": "Procesá la factura Edesur."},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Iniciando extracción."},
                {
                    "type": "tool_use",
                    "id": "gemini_call_1234",
                    "name": "extraer-vencimiento",
                    "input": {"archivo": "factura_edesur_luz.pdf"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "gemini_call_1234",
                    "name": "extraer-vencimiento",
                    "content": json.dumps({"status": "ok", "empresa": "Edesur"}, ensure_ascii=False),
                    "response_dict": {"status": "ok", "empresa": "Edesur"},
                }
            ],
        },
    ]

    with patch("google.genai.Client"):
        cliente = ClienteGemini(api_key="gemini-test-key")
        contents = cliente._traducir_historial(mensajes)

    assert len(contents) == 3

    # Turno 1: Usuario con texto
    assert contents[0].role == "user"
    assert contents[0].parts[0].text == "Procesá la factura Edesur."

    # Turno 2: Asistente (model) con texto y function_call
    assert contents[1].role == "model"
    partes_model = contents[1].parts
    assert len(partes_model) == 2
    assert partes_model[0].text == "Iniciando extracción."
    assert partes_model[1].function_call is not None
    assert partes_model[1].function_call.name == "extraer-vencimiento"
    assert partes_model[1].function_call.args == {"archivo": "factura_edesur_luz.pdf"}

    # Turno 3: Usuario con function_response
    assert contents[2].role == "user"
    partes_user = contents[2].parts
    assert len(partes_user) == 1
    assert partes_user[0].function_response is not None
    assert partes_user[0].function_response.name == "extraer-vencimiento"
    assert isinstance(partes_user[0].function_response.response, dict)
    assert partes_user[0].function_response.response == {"status": "ok", "empresa": "Edesur"}


def test_5c_generar_parsea_respuesta_simulada_con_id_propio():
    """5(c) generar parsea una respuesta simulada con function_call y genera id propio."""
    from google.genai import types

    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        # Crear respuesta simulada de Gemini con Part.from_function_call
        part_fc = types.Part.from_function_call(
            name="extraer-vencimiento",
            args={"archivo": "factura_edesur_luz.pdf"},
        )
        part_txt = types.Part.from_text(text="Voy a extraer el vencimiento.")

        mock_content = types.Content(role="model", parts=[part_txt, part_fc])
        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_resp = MagicMock()
        mock_resp.candidates = [mock_candidate]
        mock_resp.usage_metadata = MagicMock(prompt_token_count=120, candidates_token_count=45)

        mock_instance.models.generate_content.return_value = mock_resp

        cliente = ClienteGemini(api_key="gemini-test-key")
        respuesta = cliente.generar(
            mensajes=[{"role": "user", "content": "Extraer factura"}],
            herramientas=[{"name": "extraer-vencimiento", "description": "desc", "parameters": {}}],
        )

        assert respuesta.texto == "Voy a extraer el vencimiento."
        assert len(respuesta.llamadas_herramientas) == 1

        llamada = respuesta.llamadas_herramientas[0]
        assert llamada.nombre == "extraer-vencimiento"
        assert llamada.argumentos == {"archivo": "factura_edesur_luz.pdf"}
        # Comprobar que se generó un id propio que comienza con gemini_call_
        assert llamada.id.startswith("gemini_call_")
        assert respuesta.uso_tokens == {"input": 120, "output": 45}


def test_5d_sin_gemini_api_key_orquestador_cae_a_determinista_y_guarda_error_llm(monkeypatch):
    """5(d) Sin GEMINI_API_KEY el orquestador cae a modo determinista y guarda error_llm."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    orquestador = OrquestadorVencimientos(usar_llm=True)

    assert orquestador.usar_llm is False
    assert orquestador.cliente_llm is None
    assert orquestador.error_llm is not None
    assert "GEMINI_API_KEY" in orquestador.error_llm
    assert "Modo determinista activo" in orquestador.error_llm
    assert any(orquestador.error_llm in msg for msg in orquestador.mensajes_estado)


def test_6_preservar_thought_signatures():
    """6. Preservar thought signatures: se guardan en LlamadaHerramienta y se reenvían al traducir historial."""
    from google.genai import types

    thought_sig_bytes = b"\x01\x02\x03thought_signature_test_data"

    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        # Construir part con function_call y thought_signature
        part_fc = types.Part.from_function_call(
            name="ordenar-vencimientos",
            args={},
        )
        part_fc.thought_signature = thought_sig_bytes

        mock_content = types.Content(role="model", parts=[part_fc])
        mock_cand = MagicMock()
        mock_cand.content = mock_content
        mock_resp = MagicMock()
        mock_resp.candidates = [mock_cand]
        mock_resp.usage_metadata = None
        mock_instance.models.generate_content.return_value = mock_resp

        cliente = ClienteGemini(api_key="gemini-test-key")
        resp = cliente.generar(mensajes=[{"role": "user", "content": "Ordenar facturas"}])

        assert len(resp.llamadas_herramientas) == 1
        call = resp.llamadas_herramientas[0]
        # Verificar que thought_signature fue capturada
        assert call.thought_signature == thought_sig_bytes

        # Ahora simular el reenvío del historial con ese thought_signature
        historial_con_thought = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": call.id,
                        "name": call.nombre,
                        "input": call.argumentos,
                        "thought_signature": call.thought_signature,
                    }
                ],
            }
        ]

        contents_reconstruidos = cliente._traducir_historial(historial_con_thought)
        assert len(contents_reconstruidos) == 1
        part_reconstruida = contents_reconstruidos[0].parts[0]
        assert part_reconstruida.thought_signature == thought_sig_bytes
        assert part_reconstruida.function_call.name == "ordenar-vencimientos"
