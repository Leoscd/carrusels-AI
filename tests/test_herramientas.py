"""Tests para herramientas del agente."""
import pytest

from src.orquestador.tools import (
    RUBROS_DESCRIPCIONES,
    actualizar_precio,
    get_tools,
)


class TestGetTools:
    """Tests para get_tools()."""
    
    def test_get_tools_retorna_19_rubros(self):
        """get_tools debe devolver exactamente 19 herramientas de rubros."""
        tools = get_tools()
        
        # Contar solo las herramientas de rubros (no las de precio/MO/conversación)
        herramientas_rubro = [
            t for t in tools 
            if t["function"]["name"] in RUBROS_DESCRIPCIONES
        ]
        
        assert len(herramientas_rubro) == 19, (
            f"Esperaba 19 herramientas de rubro, obtuve {len(herramientas_rubro)}"
        )
    
    def test_get_tools_total(self):
        """get_tools debe devolver todas las herramientas."""
        tools = get_tools()
        
        # 19 rubros + 4 de precio/MO + 1 de conversación = 24
        assert len(tools) == 24, f"Esperaba 24 herramientas, obtuve {len(tools)}"


class TestActualizarPrecio:
    """Tests para actualizar precio."""
    
    def test_actualizar_precio(self):
        """Test de actualizar precio de material."""
        # Test de estructura - la función acepta los parámetros correctos
        from src.orquestador.tools import actualizar_precio
        import inspect
        sig = inspect.signature(actualizar_precio)
        
        params = list(sig.parameters.keys())
        assert "codigo_material" in params
        assert "nuevo_precio" in params
        assert "descripcion_usuario" in params
        assert "empresa_id" in params


# pytest fixtures si hacen falta
@pytest.fixture
def mock_empresa():
    """Mock de empresa para tests."""
    from unittest.mock import MagicMock
    return MagicMock()