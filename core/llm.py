from __future__ import annotations

import os
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


class ClienteAnthropic(ClienteLLM):
    """Implementación oficial para Anthropic Claude usando el SDK 'anthropic'."""

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
            # Transformar herramientas a formato Anthropic:
            # {"name": ..., "description": ..., "input_schema": ...}
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
