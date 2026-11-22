#Este módulo guardará los mensajes intercambiados entre el usuario y el Arquitecto.
from shared.storage.database import conectar


def guardar_mensaje(
    proyecto_id: str,
    role: str,
    content: str
):
    """Guarda un mensaje en el proyecto."""

    if role not in ("user", "assistant"):
        raise ValueError("Rol de mensaje inválido.")

    if not content.strip():
        raise ValueError("El mensaje está vacío.")

    with conectar() as conn:

        conn.execute(
            """
            INSERT INTO messages (
                project_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (proyecto_id, role, content)
        )

        conn.execute(
            """
            UPDATE projects
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (proyecto_id,)
        )


def obtener_historial(proyecto_id: str) -> list[dict]:
    """Recupera la conversación en orden."""

    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE project_id = ?
            ORDER BY id ASC
            """,
            (proyecto_id,)
        ).fetchall()

    return [dict(row) for row in rows]
