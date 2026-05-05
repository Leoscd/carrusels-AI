"""Herramientas del orquestador para el agente."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from src.datos.loader import (
    actualizar_precio_material,
    actualizar_precio_mano_obra,
    cargar_empresa,
    listar_materiales_con_descripcion,
    listar_mo_con_descripcion,
)
from src.rubros.base import REGISTRY, ResultadoPresupuesto


# =============================================================================
# Herramientas de los 19 rubros del REGISTRY
# =============================================================================


def _pydantic_a_tool(schema: type[BaseModel]) -> dict[str, Any]:
    """Convierte un schema Pydantic en tool JSON schema."""
    props: dict[str, dict[str, Any]] = {}
    required: list[str] = []

    for name, field in schema.model_fields.items():
        field_info = field.annotation
        # Extraer tipo básico
        if hasattr(field_info, "__origin__"):
            # Literal u otra generic
            origin = getattr(field_info, "__origin__", None)
            if origin is list:
                item_type = field_info.__args__[0]
                tipo_py = f"{item_type.__name__}[]"
            elif origin is dict:
                tipo_py = "object"
            else:
                tipo_py = "string"
        elif hasattr(field_info, "__constraints__"):
            # BaseModel
            tipo_py = "object"
        elif field_info is int or field_info is int | None:
            tipo_py = "integer"
        elif field_info is float or field_info is float | None:
            tipo_py = "number"
        elif field_info is str or field_info is str | None:
            tipo_py = "string"
        elif field_info is bool or field_info is bool | None:
            tipo_py = "boolean"
        else:
            tipo_py = "string"

        # Agregar enum si es Literal
        enum_vals = None
        if hasattr(field_info, "__origin__") and hasattr(field_info, "__args__"):
            from typing import get_args, get_origin
            origin = get_origin(field_info)
            if origin is list:
                args = get_args(field_info)
                if args:
                    tipo_item = args[0]
                    if hasattr(tipo_item, "__values__"):
                        enum_vals = list(tipo_item.__values__)
            elif origin is Literal:
                enum_vals = list(get_args(field_info))

        prop: dict[str, Any] = {"type": tipo_py}
        if enum_vals:
            prop["enum"] = enum_vals
        if field.is_required():
            required.append(name)
        if field.default is not None and field.default != ...:
            prop["default"] = field.default
        if field.description:
            prop["description"] = field.description
        props[name] = prop

    tool_props = {
        "type": "object",
        "properties": props,
        "required": required,
    }
    return tool_props


# Descripciones de los 19 tool rub del REGISTRY
RUBROS_DESCRIPCIONES: dict[str, dict[str, Any]] = {
    "techo_chapa": {
        "description": "Presupuesto de techo de chapas galvanizadas o zinc. Requiere ancho y largo en metros.",
        "parameters": {
            "ancho": {"type": "number", "description": "Ancho del techo en metros"},
            "largo": {"type": "number", "description": "Largo del techo en metros"},
            "tipo_chapa": {"type": "string", "enum": ["galvanizada_075", "galvanizada_090", "zinc_075", "color_075"], "default": "galvanizada_075"},
            "tipo_perfil": {"type": "string", "enum": ["C60", "C100", "C160"], "default": "C100"},
            "separacion_correa_m": {"type": "number", "default": 1.0},
        },
        "required": ["ancho", "largo"],
    },
    "cubierta_tejas": {
        "description": "Presupuesto de cubierta de tejas cerámicas o cemento.",
        "parameters": {
            "ancho": {"type": "number"},
            "largo": {"type": "number"},
            "tipo_teja": {"type": "string", "enum": ["ceramica_colonial", "cemento"]},
            "pendiente_pct": {"type": "number", "default": 30},
        },
        "required": ["ancho", "largo"],
    },
    "mamposteria": {
        "description": "Muro de mampostería de ladrillos huecos o comunes.",
        "parameters": {
            "largo": {"type": "number"},
            "alto": {"type": "number"},
            "tipo": {"type": "string", "enum": ["hueco_12", "hueco_18", "comun"]},
        },
        "required": ["largo", "alto"],
    },
    "losa": {
        "description": "Losa de hormigon armado entrepisos.",
        "parameters": {
            "ancho": {"type": "number"},
            "largo": {"type": "number"},
            "espesor_cm": {"type": "number", "default": 12},
        },
        "required": ["ancho", "largo"],
    },
    "contrapiso": {
        "description": "Contrapiso de hormona sobre radier.",
        "parameters": {
            "superficie_m2": {"type": "number"},
            "espesor_cm": {"type": "number", "default": 8},
        },
        "required": ["superficie_m2"],
    },
    "revoque_grueso": {
        "description": "Revoque粗o (jarra) sobre pared.",
        "parameters": {
            "superficie_m2": {"type": "number"},
            "espesor_cm": {"type": "number", "default": 1.5},
        },
        "required": ["superficie_m2"],
    },
    "revoque_fino": {
        "description": "Revoque fino (tenido) sobre revoque粗o.",
        "parameters": {
            "superficie_m2": {"type": "number"},
            "espesor_cm": {"type": "number", "default": 0.5},
        },
        "required": ["superficie_m2"],
    },
    "revestimiento_banio": {
        "description": "Revestimiento de baño con porcelanato o cerámico.",
        "parameters": {
            "superficie_piso_m2": {"type": "number", "default": 0},
            "superficie_pared_m2": {"type": "number", "default": 0},
            "material_piso": {"type": "string", "enum": ["porcelanato_60x60", "porcelanato_60x60_premium", "ceramico_30x30", "ceramico_45x45"]},
            "material_pared": {"type": "string", "enum": ["porcelanato_60x60", "ceramico_pared_25x35", "ceramico_30x30"]},
            "incluye_alzada_cocina": {"type": "boolean", "default": False},
            "superficie_alzada_m2": {"type": "number", "default": 0},
        },
        "required": ["superficie_piso_m2", "superficie_pared_m2", "material_piso", "material_pared"],
    },
    "instalacion_electrica": {
        "description": "Instalación eléctrica básica o completa.",
        "parameters": {
            "superficie_m2": {"type": "number"},
            "tipo": {"type": "string", "enum": ["basica", "completa"]},
            "cantidad_bocas": {"type": "number", "default": 0},
            "incluye_tablero": {"type": "boolean", "default": True},
        },
        "required": ["superficie_m2"],
    },
    "instalacion_sanitaria": {
        "description": "Instalación sanitaria de agua fría y desagües.",
        "parameters": {
            "cantidad_banos": {"type": "number"},
            "cantidad_cocinas": {"type": "number", "default": 0},
            "metros_lineales_agua_fria": {"type": "number", "default": 0},
            "metros_lineales_desague": {"type": "number", "default": 0},
            "tipo_cano": {"type": "string", "enum": ["pvc", "polipropileno"]},
        },
        "required": ["cantidad_banos"],
    },
    "piso_ceramico": {
        "description": "Piso cerámico o porcelanato.",
        "parameters": {
            "superficie_m2": {"type": "number"},
            "material": {"type": "string", "enum": ["ceramico_30x30", "ceramico_45x45", "porcelanato_60x60", "porcelanato_60x60_premium"]},
            "incluye_zocalo": {"type": "boolean", "default": False},
            "perimetro_m": {"type": "number", "default": 0},
        },
        "required": ["superficie_m2"],
    },
    "columna_hormigon": {
        "description": "Columna de hormigónarmado.",
        "parameters": {
            "seccion": {"type": "string", "enum": ["20x20", "25x25", "30x30", "30x40", "40x40"], "default": "25x25"},
            "altura_m": {"type": "number"},
            "cantidad": {"type": "integer", "default": 1},
        },
        "required": ["altura_m"],
    },
    "viga_encadenado": {
        "description": "Viga o encadenado de hormigón.",
        "parameters": {
            "longitud_ml": {"type": "number"},
            "base_cm": {"type": "integer", "default": 20},
            "alto_cm": {"type": "integer", "default": 30},
            "tipo": {"type": "string", "enum": ["encadenado", "viga_dintel"], "default": "encadenado"},
        },
        "required": ["longitud_ml"],
    },
    "fundacion": {
        "description": "Fundación zapata aislada o viga de fundación.",
        "parameters": {
            "tipo": {"type": "string", "enum": ["zapata_aislada", "viga_fundacion"], "default": "zapata_aislada"},
            "largo_m": {"type": "number", "default": 0.80},
            "ancho_m": {"type": "number", "default": 0.80},
            "alto_m": {"type": "number", "default": 0.50},
            "cantidad": {"type": "integer", "default": 1},
            "longitud_ml": {"type": "number", "default": 0},
            "base_cm": {"type": "integer", "default": 40},
        },
        "required": [],
    },
    "escalera_hormigon": {
        "description": "Escalera de hormigón armado.",
        "parameters": {
            "cantidad_escalones": {"type": "integer"},
            "ancho_m": {"type": "number", "default": 1.20},
            "huella_cm": {"type": "number", "default": 28},
            "contrahuela_cm": {"type": "number", "default": 18},
        },
        "required": ["cantidad_escalones"],
    },
    "pintura": {
        "description": "Pintura interior, exterior o esmalte.",
        "parameters": {
            "superficie_m2": {"type": "number"},
            "tipo": {"type": "string", "enum": ["latex_interior", "latex_exterior", "esmalte_sintetico"], "default": "latex_interior"},
            "manos": {"type": "integer", "default": 2},
            "incluye_fijador": {"type": "boolean", "default": True},
        },
        "required": ["superficie_m2"],
    },
    "cielorraso_durlock": {
        "description": "Cielorraso Durlock.",
        "parameters": {
            "superficie_m2": {"type": "number"},
            "tipo": {"type": "string", "enum": ["simple", "doble"], "default": "simple"},
            "con_estructura": {"type": "boolean", "default": True},
        },
        "required": ["superficie_m2"],
    },
    "membrana_impermeabilizante": {
        "description": "Membrana asfáltica o líquida.",
        "parameters": {
            "superficie_m2": {"type": "number"},
            "tipo": {"type": "string", "enum": ["membrana_asfaltica", "liquida"], "default": "membrana_asfaltica"},
            "capas": {"type": "integer", "default": 2},
        },
        "required": ["superficie_m2"],
    },
    "estructura_metalica": {
        "description": "Estructura metálicade perfiles IPN.",
        "parameters": {
            "longitud_ml": {"type": "number"},
            "tipo_perfil": {"type": "string", "enum": ["IPN_120"], "default": "IPN_120"},
            "incluye_pintura_anticorrosiva": {"type": "boolean", "default": True},
        },
        "required": ["longitud_ml"],
    },
}


# =============================================================================
# Herramientas de actualización de precio
# =============================================================================


def actualizar_precio(
    codigo_material: str,
    nuevo_precio: float,
    descripcion_usuario: str,
    empresa_id: str = "estudio_ramos",
) -> str:
    """Actualiza el precio de un material en el catálogo de la empresa.
    
    Args:
        codigo_material: Código del material en mayúsculas (ej: CEMENTO_PORTLAND, HIERRO_12)
        nuevo_precio: Nuevo precio unitario
        descripcion_usuario: Descripción coloquial del material
        empresa_id: ID de la empresa (default: estudio_ramos)
    
    Returns:
        Mensaje de confirmación con precio anterior y nuevo
    """
    precio_anterior = actualizar_precio_material(
        empresa_id=empresa_id,
        codigo=codigo_material.upper(),
        nuevo_precio=Decimal(str(nuevo_precio)),
    )
    return (
        f"✅ *{codigo_material}* actualizado\n"
        f"Precio anterior: ${float(precio_anterior):,.2f}\n"
        f"Precio nuevo: ${nuevo_precio:,.2f}"
    )


def actualizar_mano_obra(
    codigo_tarea: str,
    nuevo_precio: float,
    descripcion_usuario: str,
    empresa_id: str = "estudio_ramos",
) -> str:
    """Actualiza el precio de mano de obra en el catálogo.
    
    Args:
        codigo_tarea: Código de la tarea en mayúsculas (ej: PINTURA, COLOCACION_CERAMICO)
        nuevo_precio: Nuevo precio por unidad
        descripcion_usuario: Descripción coloquial
        empresa_id: ID de la empresa
    
    Returns:
        Mensaje de confirmación
    """
    precio_anterior = actualizar_precio_mano_obra(
        empresa_id=empresa_id,
        tarea=codigo_tarea.upper(),
        nuevo_precio=Decimal(str(nuevo_precio)),
    )
    return (
        f"✅ MO *{codigo_tarea}* actualizada\n"
        f"Precio anterior: ${float(precio_anterior):,.2f}\n"
        f"Precio nuevo: ${nuevo_precio:,.2f}"
    )


def listar_materiales(
    empresa_id: str = "estudio_ramos",
) -> list[dict]:
    """Lista materiales disponibles con código, descripción, unidad y precio."""
    return listar_materiales_con_descripcion(empresa_id)


def listar_mano_obra(
    empresa_id: str = "estudio_ramos",
) -> list[dict]:
    """Lista tareas de mano de obra disponibles."""
    return listar_mo_con_descripcion(empresa_id)


# =============================================================================
# Herramientas de conversación
# =============================================================================


def nueva_conversacion(
    empresa_id: str = "estudio_ramos",
) -> str:
    """Inicia una nueva conversación/presupuesto desde cero.
    
    Limpia el contexto de conversación guardado.
    Útil cuando el arquitecto quiere empezar un presupuesto nuevo.
    """
    # El清理 real del contexto se maneja en el handler del bot.
    # Esta función devuelve el mensaje de confirmación.
    return (
        f"✅ Nueva conversación iniciada\n"
        f"Empresa: {empresa_id}\n"
        f"El contexto anterior se ha limpiado. ¡Listo para un nuevo presupuesto!"
    )


# =============================================================================
# Función get_tools() - devuelve todas las herramientas disponibles
# =============================================================================


def get_tools() -> list[dict[str, Any]]:
    """Devuelve todas las herramientas disponibles para el agente."""
    tools: list[dict[str, Any]] = []

    # 1. Agregar herramientas de los 19 rubros
    for nombre, info in RUBROS_DESCRIPCIONES.items():
        # Buscar el schema en REGISTRY
        calc = REGISTRY.get(nombre)
        if calc is None:
            continue

        tool_def: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": nombre,
                "description": info["description"],
                "parameters": {
                    "type": "object",
                    "properties": info["parameters"],
                    "required": info.get("required", []),
                },
            },
        }
        tools.append(tool_def)

    # 2. Herramientas de actualización de precio
    tools.extend([
        {
            "type": "function",
            "function": {
                "name": "actualizar_precio",
                "description": "Actualiza el precio de un material en el catálogo de la empresa.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "codigo_material": {"type": "string", "description": "Código del material en mayúsculas (ej: CEMENTO_PORTLAND)"},
                        "nuevo_precio": {"type": "number", "description": "Nuevo precio unitario"},
                        "descripcion_usuario": {"type": "string", "description": "Descripción coloquial del material"},
                        "empresa_id": {"type": "string", "default": "estudio_ramos"},
                    },
                    "required": ["codigo_material", "nuevo_precio", "descripcion_usuario"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "actualizar_mano_obra",
                "description": "Actualiza el precio de mano de obra en el catálogo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "codigo_tarea": {"type": "string", "description": "Código de la tarea en mayúsculas (ej: PINTURA)"},
                        "nuevo_precio": {"type": "number", "description": "Nuevo precio por unidad"},
                        "descripcion_usuario": {"type": "string", "description": "Descripción coloquial"},
                        "empresa_id": {"type": "string", "default": "estudio_ramos"},
                    },
                    "required": ["codigo_tarea", "nuevo_precio", "descripcion_usuario"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "listar_materiales",
                "description": "Lista materiales disponibles con código, descripción, unidad y precio.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "empresa_id": {"type": "string", "default": "estudio_ramos"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "listar_mano_obra",
                "description": "Lista tareas de mano de obra disponibles.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "empresa_id": {"type": "string", "default": "estudio_ramos"},
                    },
                },
            },
        },
    ])

    # 3. Herramientas de conversación
    tools.extend([
        {
            "type": "function",
            "function": {
                "name": "nueva_conversacion",
                "description": "Inicia una nueva conversación/presupuesto desde cero. Limpia el contexto.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "empresa_id": {"type": "string", "default": "estudio_ramos"},
                    },
                },
            },
        },
    ])

    return tools