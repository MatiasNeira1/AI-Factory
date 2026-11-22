#Este archivo controlará si el RAG está activado para un proyecto y preparará los fragmentos que recibirá el Arquitecto
from shared.storage.database import conectar


def rag_activado(proyecto_id: str) -> bool:
    """Consulta la configuración RAG del proyecto."""

    with conectar() as conn:
        fila = conn.execute("""
            SELECT pm_rag_enabled
            FROM projects
            WHERE id = ?
        """, (proyecto_id,)).fetchone()

    if fila is None:
        raise ValueError("El proyecto no existe.")

    return bool(fila["pm_rag_enabled"])


def configurar_rag(proyecto_id: str, activar: bool):
    """Activa o desactiva RAG para un proyecto."""

    with conectar() as conn:
        cursor = conn.execute("""
            UPDATE projects
            SET pm_rag_enabled = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (int(activar), proyecto_id))

        if cursor.rowcount == 0:
            raise ValueError("El proyecto no existe.")


def construir_contexto(fragmentos: list[dict]) -> str | None:
    """Prepara material recuperado y sus referencias."""

    if not fragmentos:
        return None

    partes = []

    for numero, fragmento in enumerate(fragmentos, 1):
        partes.append(
            f"[FUENTE {numero}]\n"
            f"Documento: {fragmento['documento']}\n"
            f"Ubicación: {fragmento['ubicacion']}\n"
            f"Contenido:\n{fragmento['contenido']}"
        )

    return "\n\n".join(partes)
