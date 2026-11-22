
import sqlite3

import pytest

from shared.storage import database
from shared.storage.project_repository import (
    crear_proyecto,
    listar_proyectos,
    obtener_proyecto,
    actualizar_estado,
)
from shared.storage.message_repository import (
    guardar_mensaje,
    obtener_historial,
)


@pytest.fixture(autouse=True)
def base_temporal(tmp_path, monkeypatch):
    """Utiliza una base de datos aislada por prueba."""

    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "test_factory.db",
    )

    database.inicializar_database()


def test_crear_proyecto():
    proyecto_id = crear_proyecto("Inventario")

    proyecto = obtener_proyecto(proyecto_id)

    assert proyecto is not None
    assert proyecto["name"] == "Inventario"
    assert proyecto["status"] == "EN_PROCESO"


def test_guardar_y_recuperar_mensajes():
    proyecto_id = crear_proyecto("Clínica dental")

    guardar_mensaje(
        proyecto_id,
        "user",
        "Quiero gestionar citas.",
    )

    guardar_mensaje(
        proyecto_id,
        "assistant",
        '{"estado": "ACLARAR"}',
    )

    historial = obtener_historial(proyecto_id)

    assert len(historial) == 2
    assert historial[0]["role"] == "user"
    assert historial[1]["role"] == "assistant"


def test_listar_y_aprobar_proyectos():
    proyecto_id = crear_proyecto("E-commerce")

    assert len(listar_proyectos()) == 1

    actualizar_estado(
        proyecto_id,
        "APROBADO",
    )

    proyecto = obtener_proyecto(proyecto_id)

    assert proyecto["status"] == "APROBADO"


def test_no_permitir_mensajes_sin_proyecto():
    with pytest.raises(sqlite3.IntegrityError):
        guardar_mensaje(
            "proyecto-inexistente",
            "user",
            "Mensaje de prueba",
        )
