"""Tests para AgenteConversacional."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.orquestador.agente import AgenteConversacional, Historial


class TestAgenteConversacional:
    """Tests para la clase AgenteConversacional."""
    
    def test_agente_crear_instancia(self):
        """Debe crear instancia con modelo por defecto."""
        agente = AgenteConversacional()
        
        assert agente.modelo == "minimax/MiniMax-M2.5"
        assert agente._tools is not None
        assert len(agente._tools) > 0
    
    def test_agente_modelo_custom(self):
        """Debe aceptar modelo custom."""
        agente = AgenteConversacional(modelo="minimax/MiniMax-M2.1")
        
        assert agente.modelo == "minimax/MiniMax-M2.1"


class TestHistorial:
    """Tests para la clase Historial."""
    
    def test_historial_vacio(self):
        """Historial vacío debe retornar lista vacía."""
        h = Historial()
        assert h.a_lista() == []
    
    def test_historial_agregar(self):
        """Debe agregar mensajes correctamente."""
        h = Historial()
        h.agregar("user", "Hola")
        h.agregar("assistant", "Hola, ¿en qué puedo ayudarte?")
        
        mensajes = h.a_lista()
        assert len(mensajes) == 2
        assert mensajes[0]["role"] == "user"
        assert mensajes[0]["content"] == "Hola"
        assert mensajes[1]["role"] == "assistant"
    
    def test_historial_con_tool_calls(self):
        """Debe manejar tool_calls."""
        tool_calls = [
            {
                "id": "call_123",
                "function": {"name": "techo_chapa", "arguments": '{"ancho": 7, "largo": 10}'}
            }
        ]
        
        h = Historial()
        h.agregar("user", "Quiero un techo", tool_calls=tool_calls)
        
        mensajes = h.a_lista()
        assert len(mensajes) == 1
        assert "tool_calls" in mensajes[0]
        assert mensajes[0]["tool_calls"] == tool_calls


class TestAgenteProcesar:
    """Tests para el procesamiento del agente."""
    
    # Los tests de procesamiento requieren mocking completo del cliente async
    # Se pueden agregar cuando haya más integración