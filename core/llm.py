from __future__ import annotations

import json
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LlamadaHerramienta:
    """Representa una llamada a herramienta emitida por el LLM."""
    id: str
    nombre: str
    argumentos: Dict[str, Any]


@dataclass
class RespuestaLLM:
    """Respuesta unificada de un proveedor de LLM."""
    texto: Optional[str] = None
    llamadas_herramientas: List[LlamadaHerramienta] = field(default_factory=list)
    uso_tokens: Optional[Dict[str, int]] = None


class ClienteLLM(ABC):
    """Interfaz abstracta para proveedores de Modelos de Lenguaje."""

    @abstractmethod
    def generar(
        self,
        mensajes: List[Dict[str, Any]],
        herramientas: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        temperatura: float = 0.0,
    ) -> RespuestaLLM:
        """
        Recibe historial de mensajes y definiciones de herramientas en formato JSON Schema,
        devolviendo texto explicativo o llamadas a herramientas.
        """
        pass


def sanitizar_esquema_gemini(esquema: Any) -> Any:
    """
    Adapta un JSON Schema al subconjunto soportado por Google Gemini OpenAPI:
      - Convierte tipos a mayúsculas ('STRING', 'OBJECT', 'ARRAY', 'BOOLEAN', 'NUMBER', 'INTEGER').
      - Remueve claves no soportadas como 'additionalProperties', '$schema', 'title', 'definitions'.
      - Procesa recursivamente propiedades y elementos.
    """
    if not isinstance(esquema, dict):
        return esquema

    campos_ignorados = {"additionalProperties", "$schema", "title", "definitions"}
    resultado: Dict[str, Any] = {}

    for clave, valor in esquema.items():
        if clave in campos_ignorados:
            continue

        if clave == "type" and isinstance(valor, str):
            resultado[clave] = valor.upper()
        elif clave == "properties" and isinstance(valor, dict):
            resultado[clave] = {pk: sanitizar_esquema_gemini(pv) for pk, pv in valor.items()}
        elif clave == "items" and isinstance(valor, dict):
            resultado[clave] = sanitizar_esquema_gemini(valor)
        elif isinstance(valor, dict):
            resultado[clave] = sanitizar_esquema_gemini(valor)
        else:
            resultado[clave] = valor

    # Si es de tipo OBJECT y no tiene properties definidas, asignar dict vacío
    if resultado.get("type") == "OBJECT" and "properties" not in resultado:
        resultado["properties"] = {}

    return resultado


class ClienteGemini(ClienteLLM):
    """
    Implementación oficial para Google Gemini usando el SDK 'google-genai'.
    Soporta Tool Calling, desactiva la ejecución automática del SDK (las guardas las aplica el orquestador),
    y traduce el historial entre formatos neutros/Anthropic y Gemini Content.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from google import genai

        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        if not self.api_key:
            raise ValueError(
                "No se encontró GEMINI_API_KEY. Configure la variable de entorno en .env "
                "(obtenela gratis en https://aistudio.google.com/apikey) o proporcione api_key."
            )
        self.model = (model or os.getenv("LLM_MODEL", "gemini-2.5-flash")).strip()
        self.client = genai.Client(api_key=self.api_key)

    def _traducir_herramientas(self, herramientas: List[Dict[str, Any]]) -> List[Any]:
        """Convierte las definiciones de herramientas en types.Tool con function_declarations de Gemini."""
        from google.genai import types

        declaraciones = []
        for h in herramientas:
            nombre = h.get("name") or h.get("nombre")
            descripcion = h.get("description") or h.get("descripcion", "")
            raw_schema = h.get("input_schema") or h.get("parameters") or {"type": "object", "properties": {}}
            schema_adaptado = sanitizar_esquema_gemini(raw_schema)

            declaraciones.append(
                types.FunctionDeclaration(
                    name=nombre,
                    description=descripcion,
                    parameters=schema_adaptado,
                )
            )

        return [types.Tool(function_declarations=declaraciones)] if declaraciones else []

    def _traducir_historial(self, mensajes: List[Dict[str, Any]]) -> List[Any]:
        """
        Traduce el historial de mensajes al formato types.Content de Google Gemini.
        Mapea:
          - role 'user' con texto -> types.Content(role='user', parts=[Part.from_text(...)])
          - role 'assistant' con texto o tool_use -> types.Content(role='model', parts=[...])
          - role 'user' con tool_result -> types.Content(role='user', parts=[Part.from_function_response(...)])
        """
        from google.genai import types

        contents: List[Any] = []
        # Mapa para asociar tool_use_id con el nombre de la herramienta si fuera necesario
        id_a_nombre_herramienta: Dict[str, str] = {}

        for msg in mensajes:
            role = msg.get("role", "user")
            content = msg.get("content")

            # Caso 1: Texto plano simple
            if isinstance(content, str):
                role_gemini = "user" if role == "user" else "model"
                contents.append(
                    types.Content(
                        role=role_gemini,
                        parts=[types.Part.from_text(text=content)],
                    )
                )
                continue

            # Caso 2: Bloques estructurados (Anthropic o neutro)
            if isinstance(content, list):
                if role in ("assistant", "model"):
                    partes_model = []
                    for bloque in content:
                        if isinstance(bloque, dict):
                            tipo = bloque.get("type")
                            if tipo == "text" and bloque.get("text"):
                                partes_model.append(types.Part.from_text(text=bloque["text"]))
                            elif tipo == "tool_use":
                                nombre_fn = bloque.get("name", "")
                                tool_id = bloque.get("id", "")
                                if tool_id and nombre_fn:
                                    id_a_nombre_herramienta[tool_id] = nombre_fn
                                argumentos = bloque.get("input") or bloque.get("args") or {}
                                partes_model.append(
                                    types.Part.from_function_call(
                                        name=nombre_fn,
                                        args=argumentos,
                                    )
                                )
                    if partes_model:
                        contents.append(types.Content(role="model", parts=partes_model))

                elif role == "user":
                    partes_user = []
                    for bloque in content:
                        if isinstance(bloque, dict):
                            tipo = bloque.get("type")
                            if tipo == "tool_result":
                                tool_id = bloque.get("tool_use_id", "")
                                nombre_fn = bloque.get("name") or id_a_nombre_herramienta.get(tool_id, "herramienta")
                                raw_res = bloque.get("content", {})
                                if isinstance(raw_res, dict):
                                    resp_dict = raw_res
                                elif isinstance(raw_res, str):
                                    try:
                                        parsed = json.loads(raw_res)
                                        resp_dict = parsed if isinstance(parsed, dict) else {"result": parsed}
                                    except Exception:
                                        resp_dict = {"output": raw_res}
                                else:
                                    resp_dict = {"output": str(raw_res)}

                                partes_user.append(
                                    types.Part.from_function_response(
                                        name=nombre_fn,
                                        response=resp_dict,
                                    )
                                )
                            elif tipo == "text" and bloque.get("text"):
                                partes_user.append(types.Part.from_text(text=bloque["text"]))
                    if partes_user:
                        contents.append(types.Content(role="user", parts=partes_user))

        return contents

    def generar(
        self,
        mensajes: List[Dict[str, Any]],
        herramientas: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        temperatura: float = 0.0,
    ) -> RespuestaLLM:
        from google.genai import types

        tools_gemini = self._traducir_herramientas(herramientas) if herramientas else []
        contents_gemini = self._traducir_historial(mensajes)

        # Desactivar la ejecución automática de funciones del SDK:
        # las herramientas las ejecuta exclusivamente el orquestador con sus guardas de estado.
        config = types.GenerateContentConfig(
            temperature=temperatura,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        if system_prompt:
            config.system_instruction = system_prompt
        if tools_gemini:
            config.tools = tools_gemini

        resp = self.client.models.generate_content(
            model=self.model,
            contents=contents_gemini,
            config=config,
        )

        texto_acumulado: List[str] = []
        llamadas: List[LlamadaHerramienta] = []

        if resp.candidates:
            for cand in resp.candidates:
                if cand.content and cand.content.parts:
                    for part in cand.content.parts:
                        if part.text:
                            texto_acumulado.append(part.text)
                        if part.function_call:
                            # Gemini no entrega IDs para function_calls; generamos uno propio
                            call_id = f"gemini_call_{uuid.uuid4().hex[:8]}"
                            nombre_call = part.function_call.name
                            args_call = dict(part.function_call.args) if part.function_call.args else {}
                            llamadas.append(
                                LlamadaHerramienta(
                                    id=call_id,
                                    nombre=nombre_call,
                                    argumentos=args_call,
                                )
                            )

        texto_final = "\n".join(texto_acumulado).strip() if texto_acumulado else None

        uso_tokens: Optional[Dict[str, int]] = None
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            uso_tokens = {
                "input": getattr(resp.usage_metadata, "prompt_token_count", 0),
                "output": getattr(resp.usage_metadata, "candidates_token_count", 0),
            }

        return RespuestaLLM(
            texto=texto_final,
            llamadas_herramientas=llamadas,
            uso_tokens=uso_tokens,
        )


class ClienteAnthropic(ClienteLLM):
    """Implementación alternativa opcional para Anthropic Claude usando el SDK 'anthropic'."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        import anthropic

        self.api_key = (api_key or os.getenv("ANTHROPIC_API_KEY", "")).strip()
        if not self.api_key:
            raise ValueError(
                "No se encontró ANTHROPIC_API_KEY. Configure la variable de entorno o instancie con api_key."
            )
        self.model = (model or os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")).strip()
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generar(
        self,
        mensajes: List[Dict[str, Any]],
        herramientas: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        temperatura: float = 0.0,
    ) -> RespuestaLLM:
        params: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": mensajes,
            "temperature": temperatura,
        }
        if system_prompt:
            params["system"] = system_prompt

        if herramientas:
            tools_anthropic = []
            for h in herramientas:
                tools_anthropic.append({
                    "name": h["name"],
                    "description": h.get("description", ""),
                    "input_schema": h.get("input_schema") or h.get("parameters") or {"type": "object", "properties": {}},
                })
            params["tools"] = tools_anthropic

        resp = self.client.messages.create(**params)

        texto_acumulado = []
        llamadas: List[LlamadaHerramienta] = []

        for block in resp.content:
            if block.type == "text":
                texto_acumulado.append(block.text)
            elif block.type == "tool_use":
                llamadas.append(
                    LlamadaHerramienta(
                        id=block.id,
                        nombre=block.name,
                        argumentos=block.input if isinstance(block.input, dict) else {},
                    )
                )

        texto_final = "\n".join(texto_acumulado) if texto_acumulado else None
        return RespuestaLLM(
            texto=texto_final,
            llamadas_herramientas=llamadas,
            uso_tokens={"input": resp.usage.input_tokens, "output": resp.usage.output_tokens},
        )


class ClienteLLMFalso(ClienteLLM):
    """
    Cliente falso programable para pruebas unitarias sin red ni consumo de tokens.
    Permite inyectar una secuencia predeterminada de respuestas.
    """

    def __init__(self, respuestas_guionadas: Optional[List[RespuestaLLM]] = None):
        self.respuestas = list(respuestas_guionadas or [])
        self.llamadas_recibidas: List[Dict[str, Any]] = []

    def agregar_respuesta(self, respuesta: RespuestaLLM) -> None:
        self.respuestas.append(respuesta)

    def generar(
        self,
        mensajes: List[Dict[str, Any]],
        herramientas: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        temperatura: float = 0.0,
    ) -> RespuestaLLM:
        self.llamadas_recibidas.append({
            "mensajes": mensajes,
            "herramientas": herramientas,
            "system_prompt": system_prompt,
        })
        if self.respuestas:
            return self.respuestas.pop(0)
        # Respuesta por defecto si no quedan en el guion
        return RespuestaLLM(texto="Proceso completado por el cliente simulado.")
