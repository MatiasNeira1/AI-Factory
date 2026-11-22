
import json

import pytest

from agents.architect.schema import SCHEMA
from shared.storage import database
from shared.storage import specification_repository as repo

from shared.storage.project_repository import (
    crear_proyecto,
    obtener_proyecto,
    actualizar_estado,
)
from shared.storage.message_repository import obtener_historial


@pytest.fixture(autouse=True)
def preparar_db(tmp_path, monkeypatch):
    """Base aislada por prueba; no modifica factory.db."""

    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "test_factory.db"
    )

    monkeypatch.setattr(
        repo,
        "BASE_DIR",
        tmp_path
    )

    database.inicializar_database()


def crear_especificacion():
    """Genera datos válidos sin consultar Groq."""

    data = {
        campo: (
            [] if definicion["type"] == "array" else ""
        )
        for campo, definicion in SCHEMA["properties"].items()
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


def test_crear_primera_version():
    proyecto_id = crear_proyecto("Inventario")

    version = repo.registrar_propuesta(
        proyecto_id,
        crear_especificacion()
    )

    assert version == 1

    guardada = repo.obtener_version(
        proyecto_id, 1
    )

    assert guardada["status"] == "EN_REVISION"
    assert guardada["contenido"]["estado"] == "REVISAR"

    historial = obtener_historial(proyecto_id)

    assert len(historial) == 1
    assert historial[0]["role"] == "assistant"


def test_sustituir_propuesta():
    proyecto_id = crear_proyecto("Inventario")

    repo.registrar_propuesta(
        proyecto_id,
        crear_especificacion()
    )

    repo.registrar_propuesta(
        proyecto_id,
        crear_especificacion()
    )

    assert repo.obtener_version(
        proyecto_id, 1
    )["status"] == "SUSTITUIDA"

    assert repo.obtener_version(
        proyecto_id, 2
    )["status"] == "EN_REVISION"


def test_aprobacion_y_nueva_revision():
    proyecto_id = crear_proyecto("Inventario")

    repo.registrar_propuesta(
        proyecto_id,
        crear_especificacion()
    )

    repo.aprobar_version(proyecto_id, 1)

    assert obtener_proyecto(
        proyecto_id
    )["status"] == "APROBADO"

    repo.solicitar_revision(
        proyecto_id,
        "Agregar gestión de proveedores"
    )

    nueva = crear_especificacion()

    nueva["requisitos_confirmados"].append(
        "Agregar gestión de proveedores"
    )

    nueva["requisitos_funcionales"].append({
        "id": "RF-002",
        "titulo": "Gestionar proveedores",
        "descripcion": "Registrar proveedores",
        "prioridad": "Obligatorio",
        "origen": "Usuario",
    })

    nueva["criterios_aceptacion"].append({
        "id": "CA-002",
        "requisito_id": "RF-002",
        "descripcion": (
            "El registro de proveedor válido "
            "queda almacenado correctamente."
        ),
        "origen": "Propuesta",
    })

    assert repo.registrar_propuesta(
        proyecto_id, nueva
    ) == 2

    assert repo.obtener_version(
        proyecto_id, 1
    )["status"] == "APROBADA"

    assert repo.obtener_version(
        proyecto_id, 2
    )["status"] == "EN_REVISION"

    diferencias = repo.comparar_versiones(
        proyecto_id, 1, 2
    )

    nuevos = [
        item["elemento"]["id"]
        for item in diferencias["agregados"]
    ]

    assert "RF-002" in nuevos

    repo.aprobar_version(proyecto_id, 2)

    assert repo.obtener_version(
        proyecto_id, 2
    )["status"] == "APROBADA"


def test_no_aprobar_version_sustituida():
    proyecto_id = crear_proyecto("Inventario")

    repo.registrar_propuesta(
        proyecto_id,
        crear_especificacion()
    )

    repo.registrar_propuesta(
        proyecto_id,
        crear_especificacion()
    )

    with pytest.raises(ValueError):
        repo.aprobar_version(proyecto_id, 1)


def test_migracion_proyecto_anterior(tmp_path):
    proyecto_id = crear_proyecto("Proyecto anterior")

    actualizar_estado(
        proyecto_id, "APROBADO"
    )

    carpeta = tmp_path / "output" / proyecto_id
    carpeta.mkdir(parents=True)

    archivo = carpeta / "architecture.json"
    archivo.write_text(
        json.dumps(crear_especificacion()),
        encoding="utf-8"
    )

    assert repo.migrar_especificaciones_previas() == 1

    version = repo.obtener_version(proyecto_id, 1)

    assert version["status"] == "APROBADA"

    # La migración no debe duplicar registros.
    assert repo.migrar_especificaciones_previas() == 0
