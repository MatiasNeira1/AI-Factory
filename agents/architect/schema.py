#Este archivo define cómo deben estar organizados los datos


# Campos de texto de la especificación
TEXT_FIELDS = [
    "nombre_proyecto",
    "objetivo",
]

# Campos de tipo lista
LIST_FIELDS = [
    "requisitos_confirmados",
    "requisitos_obligatorios",
    "requisitos_opcionales",

    "preguntas_pendientes",
    "contradicciones",
    "bloqueos",
    "suposiciones",

    "actores",
    "requisitos_funcionales",
    "requisitos_no_funcionales",
    "stack_propuesto",
    "entidades",
    "endpoints",
    "criterios_aceptacion",
    "riesgos",

    "historias_usuario",
    "reglas_negocio",
]

PROPERTIES = {
    "estado": {
        "type": "string",
        "enum": ["ACLARAR", "REVISAR"],
    },
    **{
        field: {"type": "string"}
        for field in TEXT_FIELDS
    },
    **{
        field: {
            "type": "array",
            "items": {"type": "string"},
        }
        for field in LIST_FIELDS
    },
}

SCHEMA = {
    "type": "object",
    "properties": PROPERTIES,
    "required": list(PROPERTIES.keys()),
    "additionalProperties": False,
}


def crear_objeto_schema(propiedades):
    """Crea un esquema JSON de tipo objeto."""

    return {
        "type": "object",
        "properties": propiedades,
        "required": list(propiedades.keys()),
        "additionalProperties": False,
    }


REQUISITO_SCHEMA = crear_objeto_schema({
    "id": {"type": "string"},
    "titulo": {"type": "string"},
    "descripcion": {"type": "string"},
    "prioridad": {
        "type": "string",
        "enum": [
            "Obligatorio",
            "Opcional",
            "Sin definir",
        ],
    },
    "origen": {
        "type": "string",
        "enum": ["Usuario", "Propuesta"],
    },
})


HISTORIA_SCHEMA = crear_objeto_schema({
    "id": {"type": "string"},
    "actor": {"type": "string"},
    "necesidad": {"type": "string"},
    "beneficio": {"type": "string"},
    "requisitos_relacionados": {
        "type": "array",
        "items": {"type": "string"},
    },
})


REGLA_SCHEMA = crear_objeto_schema({
    "id": {"type": "string"},
    "descripcion": {"type": "string"},
    "origen": {
        "type": "string",
        "enum": ["Usuario", "Propuesta"],
    },
    "requisitos_relacionados": {
        "type": "array",
        "items": {"type": "string"},
    },
})


CRITERIO_SCHEMA = crear_objeto_schema({
    "id": {"type": "string"},
    "requisito_id": {"type": "string"},
    "descripcion": {"type": "string"},
    "origen": {
        "type": "string",
        "enum": ["Usuario", "Propuesta"],
    },
})


# Campos que contienen objetos estructurados.
SCHEMA["properties"].update({
    "requisitos_funcionales": {
        "type": "array",
        "items": REQUISITO_SCHEMA,
    },
    "requisitos_no_funcionales": {
        "type": "array",
        "items": REQUISITO_SCHEMA,
    },
    "historias_usuario": {
        "type": "array",
        "items": HISTORIA_SCHEMA,
    },
    "reglas_negocio": {
        "type": "array",
        "items": REGLA_SCHEMA,
    },
    "criterios_aceptacion": {
        "type": "array",
        "items": CRITERIO_SCHEMA,
    },
})

SCHEMA["required"] = list(SCHEMA["properties"])
