
import pytest

from shared.storage import database
from shared.storage.project_repository import crear_proyecto

from modules.project_management.ingestion import importar_documento
from modules.project_management.retriever import buscar_fragmentos
from modules.project_management.service import (
    rag_activado,
    configurar_rag,
    construir_contexto,
)


@pytest.fixture(autouse=True)
def base_temporal(tmp_path, monkeypatch):
    """Aísla las pruebas de la base de datos real."""

    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "test_rag.db",
    )

    database.inicializar_database()


def test_rag_desactivado_por_defecto():
    """Verifica que RAG comience desactivado."""

    proyecto = crear_proyecto("Inventario")

    assert rag_activado(proyecto) is False

    configurar_rag(proyecto, True)
    assert rag_activado(proyecto) is True

    configurar_rag(proyecto, False)
    assert rag_activado(proyecto) is False


def test_configuracion_independiente_por_proyecto():
    """Verifica que cada proyecto tenga su configuración."""

    proyecto_a = crear_proyecto("Inventario")
    proyecto_b = crear_proyecto("Clínica")

    configurar_rag(proyecto_a, True)

    assert rag_activado(proyecto_a) is True
    assert rag_activado(proyecto_b) is False


def test_importar_y_buscar_documento(tmp_path):
    """Verifica la importación y recuperación documental."""

    archivo = tmp_path / "riesgos.txt"

    archivo.write_text(
        "La matriz de riesgos permite evaluar "
        "la probabilidad y el impacto de los riesgos "
        "identificados durante un proyecto.",
        encoding="utf-8",
    )

    resultado = importar_documento(str(archivo))

    assert resultado["importado"] is True
    assert resultado["fragmentos"] >= 1

    encontrados = buscar_fragmentos(
        "evaluar riesgos del proyecto"
    )

    assert len(encontrados) >= 1
    assert encontrados[0]["documento"] == "riesgos.txt"

    contexto = construir_contexto(encontrados)

    assert contexto is not None
    assert "riesgos.txt" in contexto
    assert "probabilidad" in contexto


def test_no_duplicar_documento(tmp_path):
    """Verifica que un archivo no se indexe dos veces."""

    archivo = tmp_path / "planificacion.txt"

    archivo.write_text(
        "La planificación del cronograma "
        "organiza las actividades del proyecto.",
        encoding="utf-8",
    )

    primero = importar_documento(str(archivo))
    segundo = importar_documento(str(archivo))

    assert primero["importado"] is True
    assert segundo["importado"] is False
