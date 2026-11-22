
import pytest

from architect import SCHEMA, validar_especificacion


def especificacion_valida():
    """Crea datos de prueba sin llamar a Groq."""

    data = {
        nombre: (
            [] if esquema["type"] == "array" else ""
        )
        for nombre, esquema in SCHEMA["properties"].items()
    }

    data.update({
        "estado": "REVISAR",
        "nombre_proyecto": "Inventario",
        "objetivo": "Gestionar productos",
        "requisitos_confirmados": [
            "Registrar productos"
        ],
        "requisitos_funcionales": [{
            "id": "RF-001",
            "titulo": "Registrar productos",
            "descripcion": "Permitir registrar productos",
            "prioridad": "Obligatorio",
            "origen": "Usuario",
        }],
        "criterios_aceptacion": [{
            "id": "CA-001",
            "requisito_id": "RF-001",
            "descripcion": (
                "Al registrar un producto válido, "
                "el sistema confirma su creación."
            ),
            "origen": "Propuesta",
        }],
    })

    return data


def test_especificacion_correcta():
    data = especificacion_valida()

    assert validar_especificacion(data) == data


def test_identificador_duplicado():
    data = especificacion_valida()

    data["requisitos_funcionales"].append(
        data["requisitos_funcionales"][0].copy()
    )

    with pytest.raises(ValueError, match="duplicado"):
        validar_especificacion(data)


def test_referencia_inexistente():
    data = especificacion_valida()

    data["criterios_aceptacion"][0][
        "requisito_id"
    ] = "RF-999"

    with pytest.raises(ValueError, match="inexistente"):
        validar_especificacion(data)


def test_requisito_sin_criterio():
    data = especificacion_valida()
    data["criterios_aceptacion"] = []

    with pytest.raises(ValueError, match="sin criterios"):
        validar_especificacion(data)
