"""Agente conversacional basado en MiniMax-M2.5 con tool use."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from src.config import settings
from src.orquestador import router
from src.orquestador.tools import get_tools
from src.rubros.base import ResultadoPresupuesto

log = logging.getLogger(__name__)

# Pricing MiniMax-M2.5
USD_PER_1M_INPUT = 0.30
USD_PER_1M_OUTPUT = 1.20


@dataclass
class Historial:
    """Historial de mensajes para contexto."""
    mensajes: list[dict[str, Any]] = field(default_factory=list)

    def agregar(self, rol: str, contenido: str, tool_calls: list | None = None) -> None:
        msg = {"role": rol, "content": contenido}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.mensajes.append(msg)

    def a_lista(self) -> list[dict[str, Any]]:
        return self.mensajes.copy()


def _extraer_tool_calls(resp: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrae tool calls de la respuesta del LLM de forma robusta."""
    tool_calls = resp.get("tool_calls", [])
    resultado = []
    for tc in tool_calls:
        # Puede ser objeto ChatCompletionToolCall o dict
        if hasattr(tc, "id"):
            tid = tc.id
            func = tc.function
            fname = func.name if hasattr(func, "name") else func.get("name", "")
            fargs = func.arguments if hasattr(func, "arguments") else func.get("arguments", "{}")
        elif isinstance(tc, dict):
            tid = tc.get("id", "")
            func = tc.get("function", {})
            fname = func.get("name", "")
            fargs = func.get("arguments", "{}")
        else:
            continue
        resultado.append({"id": tid, "name": fname, "arguments": fargs})
    return resultado


class AgenteConversacional:
    """Agente conversacional con tool use para presupuestación."""
    
    def __init__(self, modelo: str = "minimax/MiniMax-M2.5"):
        self.modelo = modelo
        self._cliente: AsyncOpenAI | None = None
        self._tools = get_tools()
        self._historiales: dict[str, Historial] = {}

    @property
    def cliente(self) -> AsyncOpenAI:
        if self._cliente is None:
            self._cliente = AsyncOpenAI(
                api_key=settings.minimax_api_key,
                base_url=settings.minimax_base_url,
                timeout=30.0,
            )
        return self._cliente

    def _obtener_historial(self, user_id: str) -> Historial:
        if user_id not in self._historiales:
            self._historiales[user_id] = Historial()
        return self._historiales[user_id]

    def _estimar_usd(self, tin: int, tout: int) -> float:
        return round(tin / 1_000_000 * USD_PER_1M_INPUT + tout / 1_000_000 * USD_PER_1M_OUTPUT, 6)

    async def procesar(self, user_id: str, empresa_id: str, mensaje: str) -> str:
        """Procesa mensaje del usuario y devuelve respuesta.
        
        Args:
            user_id: ID único del usuario
            empresa_id: ID de la empresa
            mensaje: Texto del usuario
            
        Returns:
            Respuesta formateada para el usuario
        """
        import re
        from src.bot import formatter
        
        historial = self._obtener_historial(user_id)
        
        # Agregar mensaje del usuario
        historial.agregar("user", mensaje)
        
        # Llamar al LLM con tool use
        respuesta = await self._llamar_llm(historial.a_lista(), empresa_id)
        
        # Procesar tool calls si hay
        tool_calls = _extraer_tool_calls(respuesta)
        if tool_calls:
            # Ejecutar tools y agregar resultados
            for tc in tool_calls:
                resultado = self._ejecutar_tool(tc, empresa_id)
                
                # Agregar tool call del assistant
                historial.agregar(
                    "assistant",
                    respuesta.get("content", ""),
                    tool_calls=[{
                        "id": tc["id"],
                        "function": {"name": tc["name"], "arguments": tc["arguments"]}
                    }]
                )
                
                # Formatear resultado para el LLM
                if isinstance(resultado, ResultadoPresupuesto):
                    resultado_str = formatter.formatear_presupuesto(resultado, "TMP")
                else:
                    resultado_str = json.dumps(resultado, ensure_ascii=False, default=str)
                
                # Agregar tool result
                historial.mensajes.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": resultado_str,
                })
            
            # Segunda llamada al LLM para generar respuesta final
            respuesta_final = await self._llamar_llm(historial.a_lista(), empresa_id)
            historial.agregar("assistant", respuesta_final.get("content", ""))
            
            content = respuesta_final.get("content", "")
            # Si hay resultado formateado en el content del tool, mostrarlo
            return self._armar_respuesta(content if content else resultado_str)
        else:
            # Sin tool calls - respuesta directa
            historial.agregar("assistant", respuesta.get("content", ""))
            return self._armar_respuesta(respuesta.get("content", ""))

    async def _llamar_llm(self, mensajes: list[dict[str, Any]], empresa_id: str) -> dict[str, Any]:
        """Llama al LLM con tool use enabled."""
        import re
        
        # Build system prompt
        system_prompt = (
            "Sos un asistente de presupuestos de construcción. "
            "Usá las herramientas disponibles para calcular presupuestos. "
            "Cuando tengas todos los parámetros necesarios, llamá a la herramienta correspondente. "
            "Si te falta información, pedila al usuario."
        )
        
        t0 = time.perf_counter()
        try:
            resp = await self.cliente.chat.completions.create(
                model=self.modelo,
                messages=[{"role": "system", "content": system_prompt}, *mensajes],
                tools=self._tools,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=1500,
            )
        except Exception as e:
            log.exception("Error en _llamar_llm")
            return {"content": f"Error: {e}", "tool_calls": []}
        
        latencia_ms = int((time.perf_counter() - t0) * 1000)
        
        choice = resp.choices[0]
        content = choice.message.content or ""
        tool_calls = choice.tool_calls or []
        
        # Account tokens
        if resp.usage:
            tin = resp.usage.prompt_tokens or 0
            tout = resp.usage.completion_tokens or 0
            usd = self._estimar_usd(tin, tout)
            from src.persistencia import db
            db.acumular_tokens(tin, tout, usd)
        
        # Strip think block
        clean = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        
        return {
            "content": clean,
            "tool_calls": tool_calls,
            "latencia_ms": latencia_ms,
        }

    def _ejecutar_tool(self, tool_call: dict[str, Any], empresa_id: str) -> ResultadoPresupuesto | dict[str, Any]:
        """Ejecuta una tool y devuelve el resultado."""
        nombre = tool_call.get("name", "")
        try:
            parametros = json.loads(tool_call.get("arguments", "{}"))
        except json.JSONDecodeError:
            return {"error": "JSON inválido en parámetros"}
        
        try:
            return router.despachar(nombre, parametros, empresa_id)
        except Exception as e:
            log.exception("Error ejecutando tool %s", nombre)
            return {"error": str(e)}

    def _armar_respuesta(self, contenido: str) -> str:
        """Arma respuesta formateada para el usuario."""
        return contenido.strip()